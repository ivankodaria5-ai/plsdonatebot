"""
Please Donate Bot v2 — Flask API
=================================
Порт: 5001  (задаётся в config.py через API_PORT)

Запуск:
    python server_v2.py
Публичный доступ:
    cloudflared tunnel --url http://localhost:5001
"""

import time, os, requests, threading, signal, sys, secrets
from flask import Flask, request, jsonify, Response
import db_v2
from config import API_PORT, API_SECRET, BOT_TOKEN, ADMIN_TG_ID

app = Flask(__name__)

# ── Session tokens: key → token (validated on every pd_update) ─────────────
# Prevents emulator-based bypass: bot must echo a rotating token from our server.
# Old scripts (no token) are accepted until they naturally restart.
_stokens: dict[str, str] = {}
_stokens_lock = threading.Lock()


def _encode_str_lua(s: str) -> str:
    """Encode string as a Lua char-code table with position-based XOR.
    Prevents trivial code.replace() sniffer bypass — string never appears in plaintext.
    Decode in Lua:  for i=1,#t do s=s..string.char(t[i]~(((i-1)*17+5)%97+3)) end
    """
    result = []
    for i, c in enumerate(s):
        result.append(str(ord(c) ^ ((i * 17 + 5) % 97 + 3)))
    return "{" + ",".join(result) + "}"


_PD_FUNC = (
    # Use bit32.bxor (Roblox/Luau) or fall back to pure-Lua XOR (Lua 5.1 exploits).
    # `~` as binary XOR is Lua 5.3+ only and causes a loadstring syntax error on
    # older exploit VMs, which is why the loader shows "Ошибка загрузки скрипта".
    "local _xor=bit32 and bit32.bxor "
    "or function(a,b) local r,p=0,1 while a>0 or b>0 do "
    "if a%2~=b%2 then r=r+p end "
    "a=math.floor(a/2) b=math.floor(b/2) p=p*2 end return r end\n"
    "local function _pd(t) local s='' for i=1,#t do "
    "s=s..string.char(_xor(t[i],((i-1)*17+5)%97+3)) end return s end\n"
)


def _inject_into_code(code: str, key: str, uid: str, api_url: str, token: str) -> str:
    """Inject user-specific values directly into the obfuscated code body.

    Replaces every _G.__* read with an encoded literal and every _G.__* = nil
    with a no-op. This means the script NEVER touches _G.* at runtime —
    setting _G.__BOUND_UID = 'anything' from outside has zero effect.
    """
    replacements = [
        # reads  →  encoded literal
        ('_G.__LICENSE_KEY or ""',   f'_pd({_encode_str_lua(key)})'),
        ('_G.__BOUND_UID or ""',     f'_pd({_encode_str_lua(uid)})'),
        ('_G.__API_URL or ""',       f'_pd({_encode_str_lua(api_url)})'),
        ('_G.__SESSION_TOKEN or ""', f'_pd({_encode_str_lua(token)})'),
        # clears  →  no-ops (keep semicolons so the one-liner doesn't break)
        ('_G.__LICENSE_KEY=nil',   'local _lk=nil'),
        ('_G.__BOUND_UID=nil',     'local _bu=nil'),
        ('_G.__API_URL=nil',       'local _au=nil'),
        ('_G.__SESSION_TOKEN=nil', 'local _st=nil'),
    ]
    for old, new in replacements:
        code = code.replace(old, new)
    # Prepend only the tiny decoder function — no _G.* globals at all
    return _PD_FUNC + code

# Кэш активных аккаунтов:
# { uid: { prev_donations, prev_raised, tg_id, session_id, session_start_stats, last_seen } }
_online_cache: dict[str, dict] = {}

# Аккаунт считается оффлайн если не было пинга дольше этого времени
_OFFLINE_THRESH = 35  # секунд

# ── Локальный лог сессий ───────────────────────────────────────────────────

_LOG_DIR  = os.path.dirname(os.path.abspath(__file__))
_LOG_PATH = os.path.join(_LOG_DIR, "sessions_log.txt")
_log_lock = threading.Lock()


def _log_session_to_file(name: str, uid: str, started_at: float,
                          ended_at: float, duration: float, delta: dict):
    """Дописывает запись о закрытой сессии в sessions_log.txt."""
    def fmt_dur(s):
        s = int(s)
        h, m, sec = s // 3600, (s % 3600) // 60, s % 60
        if h:   return f"{h}ч {m}м"
        if m:   return f"{m}м {sec}с"
        return  f"{sec}с"

    dt_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at))
    dt_end   = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ended_at))
    dur_str  = fmt_dur(max(0, duration))
    app_s    = delta.get("approached",  0)
    agr_s    = delta.get("agreed",      0)
    ref_s    = delta.get("refused",     0)
    nr_s     = delta.get("no_response", 0)
    don_s    = delta.get("donations",   0)
    r_s      = delta.get("robux_gross", 0)
    conv     = f"{agr_s * 100 // app_s}%" if app_s else "—"

    line = (
        f"[{dt_start}] SESSION  {name} (uid:{uid})\n"
        f"  Старт: {dt_start}  →  Конец: {dt_end}  |  Длит: {dur_str}\n"
        f"  Подошёл: {app_s}  Согласился: {agr_s} ({conv})"
        f"  Отказал: {ref_s}  Нет ответа: {nr_s}\n"
        f"  Донаций: {don_s}  Заработано: R${r_s}"
        f"  (чист. R${int(r_s * 0.6)})\n"
        f"{'─' * 60}\n"
    )
    with _log_lock:
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[LOG] Ошибка записи в файл: {e}")


# ── Session watcher ────────────────────────────────────────────────────────

def _close_account_session(uid: str, info: dict, ended_at: float):
    """Закрыть сессию одного аккаунта: записать в БД + лог файл."""
    sid = info.get("session_id")
    if not sid:
        return
    acc = db_v2.get_account(uid)
    if not acc:
        return
    snap  = info.get("session_start_stats", {})
    delta = {
        k: max(0, (acc.get(k) or 0) - snap.get(k, 0))
        for k in ("approached", "agreed", "refused",
                  "no_response", "donations", "robux_gross")
    }
    db_v2.close_session(sid, ended_at, delta)

    # Рассчитать duration для лога
    started_at = info.get("session_start_stats", {})  # не то — берём из БД
    sess_row   = db_v2.get_sessions(uid, limit=1)
    dur        = (ended_at - sess_row[0]["started_at"]) if sess_row else 0
    name       = acc.get("name") or uid
    _log_session_to_file(name, uid, sess_row[0]["started_at"] if sess_row else ended_at,
                         ended_at, dur, delta)


def _session_watcher():
    """Фоновый поток: закрывает сессии аккаунтов ушедших оффлайн."""
    while True:
        time.sleep(20)
        now      = time.time()
        to_close = [
            (uid, info) for uid, info in list(_online_cache.items())
            if now - info.get("last_seen", 0) > _OFFLINE_THRESH
        ]
        for uid, info in to_close:
            _close_account_session(uid, info, info["last_seen"])
            _online_cache.pop(uid, None)


threading.Thread(target=_session_watcher, daemon=True).start()


# ── Graceful shutdown ──────────────────────────────────────────────────────
# Перехватывает Ctrl+C и SIGTERM (systemd stop / kill).
# Закрывает все активные сессии перед выходом — ничего не теряется.

def _graceful_shutdown(signum, frame):
    print("\n[v2] Получен сигнал завершения — закрываю активные сессии...")
    now = time.time()
    closed = 0
    for uid, info in list(_online_cache.items()):
        try:
            _close_account_session(uid, info, info.get("last_seen", now))
            closed += 1
        except Exception as e:
            print(f"[v2] Ошибка при закрытии сессии {uid}: {e}")
    _online_cache.clear()

    # Подчистить всё что watcher мог пропустить
    stale = db_v2.close_stale_sessions(now)
    print(f"[v2] Закрыто активных: {closed}, зависших: {stale}. Выход.")
    sys.exit(0)


signal.signal(signal.SIGINT,  _graceful_shutdown)
signal.signal(signal.SIGTERM, _graceful_shutdown)


def _send_tg(chat_id: int, text: str):
    """Отправить сообщение в Telegram напрямую через Bot API."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception:
        pass


def _fmt_time(ts: float | None) -> str:
    if not ts:
        return "—"
    diff = time.time() - ts
    if diff < 60:
        return f"{int(diff)}с назад"
    if diff < 3600:
        return f"{int(diff/60)}мин назад"
    return f"{int(diff/3600)}ч назад"


# ── Активация ключа ────────────────────────────────────────────────────────

@app.route("/v2/activate", methods=["POST"])
def activate():
    data = request.get_json(silent=True) or {}
    key            = data.get("key", "").strip()
    roblox_user_id = str(data.get("roblox_user_id", "")).strip()
    roblox_name    = data.get("roblox_name", "").strip()

    if not key or not roblox_user_id:
        return jsonify({"ok": False, "error": "Missing key or roblox_user_id"}), 400

    lic = db_v2.get_license(key)
    if not lic:
        return jsonify({"ok": False, "error": "Key not found"}), 403
    if lic["status"] != "active":
        return jsonify({"ok": False, "error": "Key revoked"}), 403

    first_time = False
    if lic["roblox_user_id"] is None:
        db_v2.bind_license(key, roblox_user_id, roblox_name)
        first_time = True
        _send_tg(lic["tg_id"],
                 f"🟢 <b>Скрипт активирован!</b>\n"
                 f"👤 Аккаунт: <b>{roblox_name}</b>\n"
                 f"🕐 Время: {time.strftime('%H:%M %d.%m.%Y')}")
    elif lic["roblox_user_id"] != roblox_user_id:
        return jsonify({"ok": False, "error": "Key already bound to another account"}), 403

    db_v2.touch_license(key)
    return jsonify({"ok": True, "first_time": first_time})


# ── Получение скрипта (loader делает этот запрос) ─────────────────────────

@app.route("/v2/ping")
def ping():
    return jsonify({"ok": True, "keys": db_v2.count_licenses()})


@app.route("/v2/getscript")
def get_script():
    key = request.args.get("key", "").strip()
    uid = request.args.get("uid", "").strip()

    print(f"[GETSCRIPT] key={repr(key)} uid={repr(uid)}")

    if not key or not uid:
        print("[GETSCRIPT] Missing key or uid")
        return Response("Missing key or uid", status=400)

    lic = db_v2.get_license(key)
    print(f"[GETSCRIPT] lic={lic}")
    if not lic:
        return Response("Key not found", status=403)
    if lic["status"] != "active":
        return Response("Key revoked", status=403)

    if lic["roblox_user_id"] is None:
        # Первый запуск — привязываем (roblox_name узнаем при первом pd_update)
        db_v2.bind_license(key, uid, "")
        _send_tg(lic["tg_id"],
                 f"🟢 <b>Скрипт запущен впервые!</b>\n"
                 f"🆔 Roblox ID: <code>{uid}</code>\n"
                 f"🕐 {time.strftime('%H:%M %d.%m.%Y')}\n\n"
                 f"Ключ привязан к этому аккаунту.")
    elif lic["roblox_user_id"] != uid:
        return Response("Key already bound to another account", status=403)

    db_v2.touch_license(key)

    script_path = os.path.join(os.path.dirname(__file__), "obfuscated_script.lua")
    if not os.path.exists(script_path):
        return Response("Script file not found on server", status=500)

    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()

    api_url = request.host_url.rstrip("/")

    # Generate session token for this key (rotate each fresh load)
    token = secrets.token_hex(16)
    with _stokens_lock:
        _stokens[key] = token

    # Inject values directly into the obfuscated code — no _G.* globals.
    # The attacker cannot bypass by setting _G.__BOUND_UID etc. because
    # the script never reads _G.* at all after this transformation.
    final_code = _inject_into_code(code, key, uid, api_url, token)
    return Response(final_code, status=200, mimetype="text/plain")


# ── Обновление статистики (каждые 5 сек из Lua) ────────────────────────────

@app.route("/v2/pd_update", methods=["POST"])
def pd_update():
    data = request.get_json(silent=True) or {}
    key  = data.get("key", "").strip()
    uid  = str(data.get("id", "")).strip()

    if not key or not uid:
        return jsonify({"ok": False, "error": "Missing key or id"}), 400

    lic = db_v2.get_license(key)
    if not lic:
        return Response("Key not found", status=403)
    if lic["status"] != "active":
        return Response("Key revoked", status=403)
    if lic["roblox_user_id"] and lic["roblox_user_id"] != uid:
        return Response("Unauthorized account", status=403)

    # ── Session token validation ──────────────────────────────────────────
    # Scripts that were issued a token MUST echo it back correctly.
    # Old running scripts (pre-token) have no token → accepted, but issued one now.
    sent_token = data.get("session_token", "")
    with _stokens_lock:
        expected = _stokens.get(key)
    if expected and sent_token and sent_token != expected:
        # Token mismatch: emulator/replay attack — reject
        return Response("Invalid session token", status=403)
    # Rotate token: generate a new one and return it in the response
    new_token = secrets.token_hex(16)
    with _stokens_lock:
        _stokens[key] = new_token

    now = time.time()
    db_v2.touch_license(key)

    # Обновляем имя если пустое
    if lic["roblox_name"] == "" and data.get("name"):
        db_v2.bind_license(key, uid, data["name"])

    # ── One key = one account check ───────────────────────────────────────
    # A key may only run on the one Roblox account it was bound to.
    # If somehow a different uid is online under the same key, reject it.
    active_uids = [u for u in _online_cache if _online_cache[u].get("key") == key and u != uid]
    if active_uids:
        return Response("Key already active on another account", status=403)

    # Сохраняем статистику
    db_v2.upsert_account(uid, key, data)

    new_donations = data.get("donations",   0)
    new_raised    = data.get("robux_gross", 0)

    # ── Session tracking ─────────────────────────────────────────────────
    is_new_session = uid not in _online_cache
    if is_new_session:
        sid = db_v2.open_session(uid, now)
        _online_cache[uid] = {
            "prev_donations":      new_donations,
            "prev_raised":         new_raised,
            "tg_id":               lic["tg_id"],
            "key":                 key,
            "session_id":          sid,
            "session_start_stats": {
                "approached":  data.get("approached",  0),
                "agreed":      data.get("agreed",      0),
                "refused":     data.get("refused",     0),
                "no_response": data.get("no_response", 0),
                "donations":   new_donations,
                "robux_gross": new_raised,
            },
            "last_seen": now,
        }
    else:
        _online_cache[uid]["last_seen"] = now

    # ── Donation notification ─────────────────────────────────────────────
    prev = _online_cache[uid]
    if new_donations > prev["prev_donations"]:
        gained      = new_raised - prev["prev_raised"]
        roblox_name = data.get("name", uid)
        _send_tg(lic["tg_id"],
                 f"💸 <b>Новая донация!</b>\n"
                 f"👤 {roblox_name}\n"
                 f"💰 +R$ {gained} (всего: R$ {new_raised})\n"
                 f"🎁 Донаций всего: {new_donations}")

    _online_cache[uid]["prev_donations"] = new_donations
    _online_cache[uid]["prev_raised"]    = new_raised

    return jsonify({"ok": True, "nt": new_token})


# ── Статистика пользователя ────────────────────────────────────────────────

@app.route("/v2/my_stats")
def my_stats():
    key = request.args.get("key", "").strip()
    if not key:
        return jsonify({"error": "Missing key"}), 400

    lic = db_v2.get_license(key)
    if not lic:
        return jsonify({"error": "Key not found"}), 404

    acc = db_v2.get_account_by_license(key)
    return jsonify({
        "license": {
            "key":            lic["key"],
            "status":         lic["status"],
            "roblox_name":    lic["roblox_name"],
            "roblox_user_id": lic["roblox_user_id"],
            "activated_at":   lic["activated_at"],
        },
        "account": dict(acc) if acc else None,
    })


# ── Внутренний эндпоинт для TG-уведомлений от бота ────────────────────────

@app.route("/v2/notify", methods=["POST"])
def notify():
    if request.headers.get("X-Secret") != API_SECRET:
        return Response("Forbidden", status=403)
    data    = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    text    = data.get("text", "")
    if chat_id and text:
        _send_tg(int(chat_id), text)
    return jsonify({"ok": True})


# ── Общая статистика (для /stats в боте) ──────────────────────────────────

@app.route("/v2/admin_stats")
def admin_stats():
    if request.headers.get("X-Secret") != API_SECRET:
        return Response("Forbidden", status=403)
    return jsonify({
        "total_users":   db_v2.count_users(),
        "total_keys":    db_v2.count_licenses(),
        "active_now":    db_v2.count_active_accounts(),
        "total_robux":   db_v2.total_robux(),
        "pending_apps":  db_v2.count_pending_applications(),
    })


if __name__ == "__main__":
    db_v2.init_db()

    # Закрыть зависшие сессии от предыдущего запуска
    stale = db_v2.close_stale_sessions()
    if stale:
        print(f"[v2] Закрыто {stale} зависших сессий после перезапуска")

    # Заголовок в лог-файле
    with _log_lock:
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'═' * 60}\n"
                    f"  СЕРВЕР ЗАПУЩЕН: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    f"  (порт {API_PORT})\n"
                    f"{'═' * 60}\n"
                )
        except Exception:
            pass

    print(f"[v2] API запущен на порту {API_PORT}")
    print(f"[v2] Лог сессий: {_LOG_PATH}")
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
