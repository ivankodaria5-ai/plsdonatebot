"""
MM2 Farm Dashboard Server
=========================
SETUP:
  1. pip install flask
  2. python server.py

PUBLIC ACCESS:
  winget install --id Cloudflare.cloudflared
  cloudflared tunnel --url http://localhost:5000
  -> paste URL into coin_farm.lua: DashUrl = "https://..."
"""

from flask import Flask, request, jsonify, Response
import time, socket, subprocess, threading, re, sqlite3, json, os, csv, io

app         = Flask(__name__)
accounts    = {}           # in-memory cache (MM2)
commands    = {}           # { "userId": { "CoinFarm": True, ... } }
pd_accounts = {}           # in-memory cache (Please Donate)
db_lock     = threading.Lock()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farm_data.db")

# ─── Database ─────────────────────────────────────────────

def _con():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db_lock:
        con = _con()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id            TEXT PRIMARY KEY,
                name          TEXT    NOT NULL DEFAULT '',
                coins_total   INTEGER NOT NULL DEFAULT 0,
                last_seen     REAL    NOT NULL DEFAULT 0,
                session_start REAL    NOT NULL DEFAULT 0,
                created_at    REAL    NOT NULL DEFAULT 0,
                bag           INTEGER NOT NULL DEFAULT 0,
                rounds        INTEGER NOT NULL DEFAULT 0,
                flings        INTEGER NOT NULL DEFAULT 0,
                hops          INTEGER NOT NULL DEFAULT 0,
                status        TEXT    NOT NULL DEFAULT 'Offline',
                role          TEXT    NOT NULL DEFAULT 'I',
                bag_full      INTEGER NOT NULL DEFAULT 0,
                state_json    TEXT    NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS current_sessions (
                account_id TEXT PRIMARY KEY,
                server_id  TEXT NOT NULL DEFAULT '',
                started_at REAL NOT NULL DEFAULT 0,
                coins      INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id     TEXT    NOT NULL,
                server_id      TEXT    NOT NULL DEFAULT '',
                started_at     REAL    NOT NULL DEFAULT 0,
                ended_at       REAL    NOT NULL DEFAULT 0,
                duration       REAL    NOT NULL DEFAULT 0,
                coins          INTEGER NOT NULL DEFAULT 0,
                coins_per_hour INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_sess_acc ON sessions(account_id, started_at);

            CREATE TABLE IF NOT EXISTS pd_accounts (
                id             TEXT PRIMARY KEY,
                name           TEXT    NOT NULL DEFAULT '',
                approached     INTEGER NOT NULL DEFAULT 0,
                agreed         INTEGER NOT NULL DEFAULT 0,
                refused        INTEGER NOT NULL DEFAULT 0,
                no_response    INTEGER NOT NULL DEFAULT 0,
                hops           INTEGER NOT NULL DEFAULT 0,
                donations      INTEGER NOT NULL DEFAULT 0,
                robux_gross     INTEGER NOT NULL DEFAULT 0,
                raised_current  INTEGER NOT NULL DEFAULT 0,
                last_seen      REAL    NOT NULL DEFAULT 0,
                session_start  REAL    NOT NULL DEFAULT 0,
                created_at     REAL    NOT NULL DEFAULT 0,
                status         TEXT    NOT NULL DEFAULT 'Offline'
            );
            CREATE TABLE IF NOT EXISTS pd_current_sessions (
                account_id     TEXT PRIMARY KEY,
                server_id      TEXT    NOT NULL DEFAULT '',
                started_at     REAL    NOT NULL DEFAULT 0,
                approached     INTEGER NOT NULL DEFAULT 0,
                agreed         INTEGER NOT NULL DEFAULT 0,
                refused        INTEGER NOT NULL DEFAULT 0,
                no_response    INTEGER NOT NULL DEFAULT 0,
                donations      INTEGER NOT NULL DEFAULT 0,
                robux_gross    INTEGER NOT NULL DEFAULT 0,
                raised_current INTEGER NOT NULL DEFAULT 0,
                snap_app       INTEGER NOT NULL DEFAULT 0,
                snap_agr       INTEGER NOT NULL DEFAULT 0,
                snap_ref       INTEGER NOT NULL DEFAULT 0,
                snap_nr        INTEGER NOT NULL DEFAULT 0,
                snap_don       INTEGER NOT NULL DEFAULT 0,
                snap_gross     INTEGER NOT NULL DEFAULT 0,
                snap_hops      INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS pd_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id     TEXT    NOT NULL,
                server_id      TEXT    NOT NULL DEFAULT '',
                started_at     REAL    NOT NULL DEFAULT 0,
                ended_at       REAL    NOT NULL DEFAULT 0,
                duration       REAL    NOT NULL DEFAULT 0,
                approached     INTEGER NOT NULL DEFAULT 0,
                agreed         INTEGER NOT NULL DEFAULT 0,
                refused        INTEGER NOT NULL DEFAULT 0,
                no_response    INTEGER NOT NULL DEFAULT 0,
                donations      INTEGER NOT NULL DEFAULT 0,
                robux_gross    INTEGER NOT NULL DEFAULT 0,
                snap_don       INTEGER NOT NULL DEFAULT 0,
                snap_gross     INTEGER NOT NULL DEFAULT 0,
                snap_app       INTEGER NOT NULL DEFAULT 0,
                snap_agr       INTEGER NOT NULL DEFAULT 0,
                snap_ref       INTEGER NOT NULL DEFAULT 0,
                snap_nr        INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_pd_sess_acc ON pd_sessions(account_id, started_at);

            CREATE TABLE IF NOT EXISTS pd_interactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id   TEXT NOT NULL,
                server_id    TEXT NOT NULL DEFAULT '',
                ts           REAL NOT NULL DEFAULT 0,
                target_name  TEXT NOT NULL DEFAULT '',
                bot_msg      TEXT NOT NULL DEFAULT '',
                player_reply TEXT NOT NULL DEFAULT '',
                outcome      TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_inter_acc ON pd_interactions(account_id, ts);

            CREATE TABLE IF NOT EXISTS pd_config (
                account_id       TEXT PRIMARY KEY,
                min_players      INTEGER NOT NULL DEFAULT 4,
                max_players      INTEGER NOT NULL DEFAULT 24,
                server_cooldown  INTEGER NOT NULL DEFAULT 60,
                clear_history    INTEGER NOT NULL DEFAULT 0,
                updated_at       REAL    NOT NULL DEFAULT 0
            );
        """)
        # Migration: add new columns to existing tables if they don't exist yet
        for tbl, col in [
            ("pd_accounts",         "donations"),
            ("pd_accounts",         "robux_gross"),
            ("pd_accounts",         "raised_current"),
            ("pd_current_sessions", "donations"),
            ("pd_current_sessions", "robux_gross"),
            ("pd_current_sessions", "raised_current"),
            ("pd_current_sessions", "snap_app"),
            ("pd_current_sessions", "snap_agr"),
            ("pd_current_sessions", "snap_ref"),
            ("pd_current_sessions", "snap_nr"),
            ("pd_current_sessions", "snap_don"),
            ("pd_current_sessions", "snap_gross"),
            ("pd_current_sessions", "snap_hops"),
            ("pd_sessions",         "donations"),
            ("pd_sessions",         "robux_gross"),
            ("pd_sessions",         "snap_don"),
            ("pd_sessions",         "snap_gross"),
            ("pd_sessions",         "snap_app"),
            ("pd_sessions",         "snap_agr"),
            ("pd_sessions",         "snap_ref"),
            ("pd_sessions",         "snap_nr"),
        ]:
            try:
                con.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")
            except Exception:
                pass  # column already exists
        con.commit()
        con.close()

def load_accounts_from_db():
    with db_lock:
        con = _con()
        accs = [dict(r) for r in con.execute("SELECT * FROM accounts").fetchall()]
        cs_map = {r["account_id"]: dict(r) for r in
                  con.execute("SELECT * FROM current_sessions").fetchall()}
        sess_map = {}
        for r in con.execute("SELECT * FROM sessions ORDER BY started_at ASC").fetchall():
            d = dict(r)
            sess_map.setdefault(d["account_id"], []).append(d)
        con.close()

    for row in accs:
        aid = row["id"]
        cs  = cs_map.get(aid)
        accounts[aid] = {
            "id":            aid,
            "name":          row["name"],
            "coins_total":   row["coins_total"],
            "last_seen":     row["last_seen"],
            "session_start": row["session_start"] or row["created_at"],
            "bag":           row["bag"],
            "rounds":        row["rounds"],
            "flings":        row["flings"],
            "hops":          row["hops"],
            "status":        row["status"],
            "role":          row["role"],
            "bag_full":      bool(row["bag_full"]),
            "state":         json.loads(row["state_json"] or "{}"),
            "current_session": {
                "server_id":  cs["server_id"]  if cs else "",
                "started_at": cs["started_at"] if cs else row["session_start"],
                "coins":      cs["coins"]      if cs else 0,
            },
            "sessions": sess_map.get(aid, []),
        }

def _db_upsert_account(con, acc):
    con.execute("""
        INSERT INTO accounts
            (id, name, coins_total, last_seen, session_start, created_at,
             bag, rounds, flings, hops, status, role, bag_full, state_json)
        VALUES
            (:id,:name,:coins_total,:last_seen,:session_start,:now,
             :bag,:rounds,:flings,:hops,:status,:role,:bag_full,:state_json)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, coins_total=excluded.coins_total,
            last_seen=excluded.last_seen, session_start=excluded.session_start,
            bag=excluded.bag, rounds=excluded.rounds, flings=excluded.flings,
            hops=excluded.hops, status=excluded.status, role=excluded.role,
            bag_full=excluded.bag_full, state_json=excluded.state_json
    """, {
        "id": acc["id"], "name": acc["name"],
        "coins_total":   acc.get("coins_total", 0),
        "last_seen":     acc.get("last_seen", time.time()),
        "session_start": acc.get("session_start", time.time()),
        "now":           time.time(),
        "bag":     acc.get("bag", 0),    "rounds": acc.get("rounds", 0),
        "flings":  acc.get("flings", 0), "hops":   acc.get("hops", 0),
        "status":  acc.get("status", "Lobby"),
        "role":    acc.get("role", "I"),
        "bag_full": int(acc.get("bag_full", False)),
        "state_json": json.dumps(acc.get("state", {})),
    })

def _db_upsert_cs(con, acc_id, cs):
    con.execute("""
        INSERT INTO current_sessions (account_id, server_id, started_at, coins)
        VALUES (?,?,?,?)
        ON CONFLICT(account_id) DO UPDATE SET
            server_id=excluded.server_id,
            started_at=excluded.started_at,
            coins=excluded.coins
    """, (acc_id, cs.get("server_id",""), cs.get("started_at", time.time()), cs.get("coins",0)))

def _db_insert_session(con, acc_id, sess):
    con.execute("""
        INSERT INTO sessions
            (account_id, server_id, started_at, ended_at, duration, coins, coins_per_hour)
        VALUES (?,?,?,?,?,?,?)
    """, (acc_id, sess.get("server_id",""), sess.get("started_at",0),
          sess.get("ended_at",0), sess.get("duration",0),
          sess.get("coins",0), sess.get("coins_per_hour",0)))

# ─── Please Donate DB helpers ──────────────────────────────

def load_pd_from_db():
    with db_lock:
        con = _con()
        accs   = [dict(r) for r in con.execute("SELECT * FROM pd_accounts").fetchall()]
        cs_map = {r["account_id"]: dict(r) for r in
                  con.execute("SELECT * FROM pd_current_sessions").fetchall()}
        sess_map = {}
        for r in con.execute("SELECT * FROM pd_sessions ORDER BY started_at ASC").fetchall():
            d = dict(r)
            sess_map.setdefault(d["account_id"], []).append(d)
        con.close()
    for row in accs:
        aid = row["id"]
        cs  = cs_map.get(aid)
        pd_accounts[aid] = {
            "id":              aid,
            "name":            row["name"],
            "approached":      row["approached"],
            "agreed":          row["agreed"],
            "refused":         row["refused"],
            "no_response":     row["no_response"],
            "hops":            row["hops"],
            "donations":       row["donations"],
            "robux_gross":     row["robux_gross"],
            "raised_current":  row["raised_current"],
            "last_seen":       row["last_seen"],
            "session_start":   row["session_start"] or row["created_at"],
            "created_at":      row["created_at"],
            "status":          row["status"],
            "current_session": {
                "server_id":     cs["server_id"]      if cs else "",
                "started_at":    cs["started_at"]     if cs else row["session_start"],
                "approached":    cs["approached"]     if cs else 0,
                "agreed":        cs["agreed"]         if cs else 0,
                "refused":       cs["refused"]        if cs else 0,
                "no_response":   cs["no_response"]    if cs else 0,
                "donations":     cs["donations"]      if cs else 0,
                "robux_gross":   cs["robux_gross"]    if cs else 0,
                "raised_current":cs["raised_current"] if cs else 0,
                "snap_app":      cs["snap_app"]       if cs else 0,
                "snap_agr":      cs["snap_agr"]       if cs else 0,
                "snap_ref":      cs["snap_ref"]       if cs else 0,
                "snap_nr":       cs["snap_nr"]        if cs else 0,
                "snap_don":      cs["snap_don"]       if cs else 0,
                "snap_gross":    cs["snap_gross"]     if cs else 0,
                "snap_hops":     cs["snap_hops"]      if cs else 0,
            },
            "sessions": sess_map.get(aid, []),
        }

def _db_upsert_pd_account(con, acc):
    con.execute("""
        INSERT INTO pd_accounts
            (id, name, approached, agreed, refused, no_response, hops,
             donations, robux_gross, raised_current, last_seen, session_start, created_at, status)
        VALUES
            (:id,:name,:approached,:agreed,:refused,:no_response,:hops,
             :donations,:robux_gross,:raised_current,:last_seen,:session_start,:now,:status)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, approached=excluded.approached,
            agreed=excluded.agreed, refused=excluded.refused,
            no_response=excluded.no_response, hops=excluded.hops,
            donations=excluded.donations, robux_gross=excluded.robux_gross,
            raised_current=excluded.raised_current,
            last_seen=excluded.last_seen, session_start=excluded.session_start,
            status=excluded.status
    """, {
        "id": acc["id"], "name": acc["name"],
        "approached":     acc.get("approached",     0),
        "agreed":         acc.get("agreed",         0),
        "refused":        acc.get("refused",         0),
        "no_response":    acc.get("no_response",    0),
        "hops":           acc.get("hops",           0),
        "donations":      acc.get("donations",      0),
        "robux_gross":    acc.get("robux_gross",    0),
        "raised_current": acc.get("raised_current", 0),
        "last_seen":      acc.get("last_seen",      time.time()),
        "session_start":  acc.get("session_start",  time.time()),
        "now":            time.time(),
        "status":         acc.get("status", "Active"),
    })

def _db_upsert_pd_cs(con, acc_id, cs):
    con.execute("""
        INSERT INTO pd_current_sessions
            (account_id, server_id, started_at, approached, agreed, refused, no_response,
             donations, robux_gross, raised_current,
             snap_app, snap_agr, snap_ref, snap_nr, snap_don, snap_gross, snap_hops)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(account_id) DO UPDATE SET
            server_id=excluded.server_id, started_at=excluded.started_at,
            approached=excluded.approached, agreed=excluded.agreed,
            refused=excluded.refused, no_response=excluded.no_response,
            donations=excluded.donations, robux_gross=excluded.robux_gross,
            raised_current=excluded.raised_current,
            snap_app=excluded.snap_app, snap_agr=excluded.snap_agr,
            snap_ref=excluded.snap_ref, snap_nr=excluded.snap_nr,
            snap_don=excluded.snap_don, snap_gross=excluded.snap_gross,
            snap_hops=excluded.snap_hops
    """, (acc_id, cs.get("server_id",""), cs.get("started_at", time.time()),
          cs.get("approached",0), cs.get("agreed",0), cs.get("refused",0),
          cs.get("no_response",0), cs.get("donations",0),
          cs.get("robux_gross",0), cs.get("raised_current",0),
          cs.get("snap_app",0), cs.get("snap_agr",0), cs.get("snap_ref",0),
          cs.get("snap_nr",0), cs.get("snap_don",0), cs.get("snap_gross",0),
          cs.get("snap_hops",0)))

def _db_insert_pd_session(con, acc_id, sess):
    con.execute("""
        INSERT INTO pd_sessions
            (account_id, server_id, started_at, ended_at, duration,
             approached, agreed, refused, no_response, donations, robux_gross,
             snap_don, snap_gross, snap_app, snap_agr, snap_ref, snap_nr)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (acc_id, sess.get("server_id",""), sess.get("started_at",0),
          sess.get("ended_at",0), sess.get("duration",0),
          sess.get("approached",0), sess.get("agreed",0), sess.get("refused",0),
          sess.get("no_response",0), sess.get("donations",0), sess.get("robux_gross",0),
          sess.get("snap_don",0), sess.get("snap_gross",0),
          sess.get("snap_app",0), sess.get("snap_agr",0),
          sess.get("snap_ref",0), sess.get("snap_nr",0)))

# ─── Helpers ──────────────────────────────────────────────

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def try_start_cloudflare():
    def run():
        try:
            proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line.strip())
                if m:
                    url = m.group(0)
                    print(f"\n{'='*55}\n  [CLOUDFLARE] {url}\n  Set DashUrl = \"{url}\"\n{'='*55}\n")
        except FileNotFoundError:
            print("  [INFO] cloudflared not found — no public URL")
        except Exception as e:
            print(f"  [cloudflared] {e}")
    threading.Thread(target=run, daemon=True).start()

# ─── Routes ───────────────────────────────────────────────

@app.route("/update", methods=["POST"])
def update():
    try:
        data = request.get_json(force=True)
        if not data or "id" not in data:
            return jsonify({"ok": False}), 400

        acc_id = str(data["id"])
        job_id = str(data.get("job_id", ""))
        coins  = int(data.get("coins", 0))
        now    = time.time()
        prev   = accounts.get(acc_id)

        with db_lock:
            con = _con()
            if prev is None:
                new_cs = {"server_id": job_id, "started_at": now, "coins": coins}
                accounts[acc_id] = {
                    "id": acc_id, "name": data.get("name", "Unknown"),
                    "coins_total": coins, "sessions": [],
                    "current_session": new_cs,
                    "state":         data.get("state", {}),
                    "last_seen":     now, "session_start": now,
                    "bag":      data.get("bag", 0),
                    "rounds":   data.get("rounds", 0),
                    "flings":   data.get("flings", 0),
                    "hops":     data.get("hops", 0),
                    "status":   data.get("status", "Lobby"),
                    "role":     data.get("role", "I"),
                    "bag_full": data.get("bag_full", False),
                }
                _db_upsert_account(con, accounts[acc_id])
                _db_upsert_cs(con, acc_id, new_cs)
            else:
                cs = prev.get("current_session", {})
                if job_id and cs.get("server_id") != job_id:
                    cs["ended_at"] = now
                    duration = now - cs.get("started_at", now)
                    cs["duration"] = duration
                    cs["coins_per_hour"] = (
                        round(cs.get("coins", 0) / (duration / 3600)) if duration > 60 else 0
                    )
                    prev.setdefault("sessions", []).append(dict(cs))
                    _db_insert_session(con, acc_id, cs)

                    new_cs = {"server_id": job_id, "started_at": now, "coins": coins}
                    prev["current_session"] = new_cs
                    _db_upsert_cs(con, acc_id, new_cs)
                else:
                    prev["current_session"]["coins"] = coins
                    _db_upsert_cs(con, acc_id, prev["current_session"])

                completed = sum(s.get("coins", 0) for s in prev.get("sessions", []))
                prev["coins_total"] = completed + coins
                prev["name"]      = data.get("name", prev.get("name"))
                prev["last_seen"] = now
                prev["state"]     = data.get("state", prev.get("state", {}))
                for f in ["bag","rounds","flings","hops","status","role","bag_full","session_start"]:
                    if f in data:
                        prev[f] = data[f]
                _db_upsert_account(con, prev)

            con.commit()
            con.close()

        cmds = commands.pop(acc_id, {})
        return jsonify({"ok": True, "commands": cmds})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/control", methods=["POST"])
def control():
    try:
        data = request.get_json(force=True)
        if not data or "id" not in data:
            return jsonify({"ok": False}), 400
        acc_id = str(data["id"])
        commands.setdefault(acc_id, {})
        for key in ["CoinFarm","Combat","NoClip","AutoReset","ServerHop","AntiFling","ForceHop"]:
            if key in data:
                commands[acc_id][key] = data[key]
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/accounts")
def get_accounts():
    result = {}
    for acc_id, acc in accounts.items():
        result[acc_id] = {**acc, "pending_commands": commands.get(acc_id, {})}
    return jsonify(result)


@app.route("/reset/<acc_id>", methods=["DELETE"])
def reset_stats(acc_id):
    if acc_id not in accounts:
        return jsonify({"ok": False, "error": "not found"}), 404
    acc = accounts[acc_id]
    acc["coins_total"] = 0
    acc["sessions"]    = []
    acc["current_session"] = {
        "server_id":  acc.get("current_session", {}).get("server_id", ""),
        "started_at": time.time(),
        "coins":      0,
    }
    with db_lock:
        con = _con()
        con.execute("UPDATE accounts SET coins_total=0 WHERE id=?", (acc_id,))
        con.execute("DELETE FROM sessions WHERE account_id=?", (acc_id,))
        con.execute(
            "UPDATE current_sessions SET coins=0, started_at=? WHERE account_id=?",
            (time.time(), acc_id)
        )
        con.commit()
        con.close()
    return jsonify({"ok": True})


@app.route("/history")
def get_history():
    result = []
    for acc_id, acc in accounts.items():
        for sess in acc.get("sessions", []):
            result.append({
                "account_id":     acc_id,
                "account_name":   acc.get("name", "Unknown"),
                "server_id":      sess.get("server_id", ""),
                "started_at":     sess.get("started_at", 0),
                "ended_at":       sess.get("ended_at", 0),
                "duration":       sess.get("duration", 0),
                "coins":          sess.get("coins", 0),
                "coins_per_hour": sess.get("coins_per_hour", 0),
            })
    result.sort(key=lambda x: x.get("started_at", 0), reverse=True)
    return jsonify(result)


@app.route("/pd_config/<uid>", methods=["GET"])
def pd_config_get(uid):
    """Bot fetches its config here at startup and before each hop."""
    with db_lock:
        con = _con()
        row = con.execute("SELECT * FROM pd_config WHERE account_id=?", (uid,)).fetchone()
        con.close()
    if row:
        cfg = dict(row)
        # If clear_history was set, reset it immediately after sending
        if cfg.get("clear_history"):
            with db_lock:
                con = _con()
                con.execute("UPDATE pd_config SET clear_history=0 WHERE account_id=?", (uid,))
                con.commit()
                con.close()
        return jsonify({
            "min_players":     cfg["min_players"],
            "max_players":     cfg["max_players"],
            "server_cooldown": cfg["server_cooldown"],
            "clear_history":   bool(cfg["clear_history"]),
        })
    # Return defaults if no config set yet
    return jsonify({"min_players": 4, "max_players": 24, "server_cooldown": 60, "clear_history": False})


@app.route("/pd_config/<uid>", methods=["POST"])
def pd_config_set(uid):
    """Dashboard saves config for a bot."""
    data = request.get_json(force=True) or {}
    now = time.time()
    with db_lock:
        con = _con()
        con.execute("""
            INSERT INTO pd_config (account_id, min_players, max_players, server_cooldown, clear_history, updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(account_id) DO UPDATE SET
                min_players=excluded.min_players,
                max_players=excluded.max_players,
                server_cooldown=excluded.server_cooldown,
                clear_history=excluded.clear_history,
                updated_at=excluded.updated_at
        """, (uid,
              int(data.get("min_players", 4)),
              int(data.get("max_players", 24)),
              int(data.get("server_cooldown", 60)),
              1 if data.get("clear_history") else 0,
              now))
        con.commit()
        con.close()
    return jsonify({"ok": True})


@app.route("/pd_update", methods=["POST"])
def pd_update():
    try:
        data = request.get_json(force=True)
        if not data or "id" not in data:
            return jsonify({"ok": False}), 400
        acc_id         = str(data["id"])
        job_id         = str(data.get("job_id", ""))
        now            = time.time()
        # Values from bot — cumulative since last script start (reset on restart)
        b_app   = int(data.get("approached",    0))
        b_agr   = int(data.get("agreed",        0))
        b_ref   = int(data.get("refused",       0))
        b_nr    = int(data.get("no_response",   0))
        b_hops  = int(data.get("hops",          0))
        b_don   = int(data.get("donations",     0))
        b_gross = int(data.get("robux_gross",   0))
        b_raised= int(data.get("raised_current",0))
        prev    = pd_accounts.get(acc_id)

        # ── Delta helper: if value went BACKWARD the bot restarted → treat all as new ──
        def delta(new, old):
            return new if new < old else new - old

        print(f"[PD] {'NEW' if prev is None else 'UPD'} acc={acc_id} "
              f"name={data.get('name')} job={job_id[:8] if job_id else '?'} "
              f"app={b_app} agr={b_agr} ref={b_ref}")

        with db_lock:
            con = _con()
            if prev is None:
                # ── First time we see this bot ──
                # current_session stores: raw bot values + starting snapshot for per-server delta
                new_cs = {
                    "server_id":  job_id,  "started_at":    now,
                    "approached": b_app,   "agreed":         b_agr,
                    "refused":    b_ref,   "no_response":    b_nr,
                    "donations":  b_don,   "robux_gross":    b_gross,
                    "raised_current": b_raised,
                    # snapshot at session start — for "this server" display
                    "snap_app":   b_app,   "snap_agr":       b_agr,
                    "snap_ref":   b_ref,   "snap_nr":        b_nr,
                    "snap_don":   b_don,   "snap_gross":     b_gross,
                    "snap_hops":  b_hops,
                }
                pd_accounts[acc_id] = {
                    "id": acc_id, "name": data.get("name", "Unknown"),
                    # All-time totals — accumulated across all script runs
                    "approached": b_app,  "agreed":   b_agr,
                    "refused":    b_ref,  "no_response": b_nr,
                    "hops":    b_hops, "donations": b_don,
                    "robux_gross": b_gross, "raised_current": b_raised,
                    "last_seen": now, "session_start": now, "created_at": now,
                    "status": data.get("status", "Active"),
                    "current_session": new_cs, "sessions": [],
                }
                _db_upsert_pd_account(con, pd_accounts[acc_id])
                _db_upsert_pd_cs(con, acc_id, new_cs)
            else:
                cs = prev.get("current_session", {})
                # ── Compute deltas vs last bot report (handles restarts) ──
                d_app   = delta(b_app,   cs.get("approached",    0))
                d_agr   = delta(b_agr,   cs.get("agreed",        0))
                d_ref   = delta(b_ref,   cs.get("refused",       0))
                d_nr    = delta(b_nr,    cs.get("no_response",   0))
                d_don   = delta(b_don,   cs.get("donations",     0))
                d_gross = delta(b_gross, cs.get("robux_gross",   0))
                d_hops  = delta(b_hops,  cs.get("snap_hops",     0))

                if job_id and cs.get("server_id") != job_id:
                    # ── New server (hop or reconnect) ── save completed session ──
                    cs["ended_at"] = now
                    cs["duration"] = now - cs.get("started_at", now)
                    prev.setdefault("sessions", []).append(dict(cs))
                    _db_insert_pd_session(con, acc_id, cs)
                    # New session: snapshot starts at current bot values
                    new_cs = {
                        "server_id":  job_id,  "started_at":    now,
                        "approached": b_app,   "agreed":         b_agr,
                        "refused":    b_ref,   "no_response":    b_nr,
                        "donations":  b_don,   "robux_gross":    b_gross,
                        "raised_current": b_raised,
                        "snap_app":   b_app,   "snap_agr":       b_agr,
                        "snap_ref":   b_ref,   "snap_nr":        b_nr,
                        "snap_don":   b_don,   "snap_gross":     b_gross,
                        "snap_hops":  b_hops,
                    }
                    prev["current_session"] = new_cs
                    _db_upsert_pd_cs(con, acc_id, new_cs)
                else:
                    # ── Same server — update current session raw values ──
                    prev["current_session"].update({
                        "approached": b_app,   "agreed":      b_agr,
                        "refused":    b_ref,   "no_response": b_nr,
                        "donations":  b_don,   "robux_gross": b_gross,
                        "raised_current": b_raised,
                        # snap_* stays unchanged (set at session start)
                    })
                    _db_upsert_pd_cs(con, acc_id, prev["current_session"])

                # ── Detect bot restart: stats went backward OR bot was offline > 5 min ──
                gap_seconds = now - prev.get("last_seen", now)
                stats_reset = b_app < cs.get("approached", 0)
                if stats_reset or gap_seconds > 300:
                    prev["session_start"] = now
                    # Reset snap_* so "this server" counters restart cleanly from 0
                    prev["current_session"].update({
                        "snap_app":   b_app,  "snap_agr":   b_agr,
                        "snap_ref":   b_ref,  "snap_nr":    b_nr,
                        "snap_don":   b_don,  "snap_gross": b_gross,
                        "snap_hops":  b_hops,
                    })
                    _db_upsert_pd_cs(con, acc_id, prev["current_session"])

                # ── Accumulate all-time totals using deltas ──
                prev["approached"]    = prev.get("approached",    0) + d_app
                prev["agreed"]        = prev.get("agreed",        0) + d_agr
                prev["refused"]       = prev.get("refused",       0) + d_ref
                prev["no_response"]   = prev.get("no_response",   0) + d_nr
                prev["donations"]     = prev.get("donations",     0) + d_don
                prev["robux_gross"]   = prev.get("robux_gross",   0) + d_gross
                prev["hops"]          = prev.get("hops",          0) + d_hops
                # raised_current is absolute (never decreases in PD) — take max
                prev["raised_current"] = max(b_raised, prev.get("raised_current", 0))
                prev["last_seen"] = now
                prev["status"]    = data.get("status", prev.get("status", "Active"))
                prev["name"]      = data.get("name",   prev.get("name", "Unknown"))
                _db_upsert_pd_account(con, prev)

            # ── Store interaction log entries ──
            interactions = data.get("interactions", [])
            if interactions:
                for entry in interactions:
                    con.execute("""
                        INSERT INTO pd_interactions
                            (account_id, server_id, ts, target_name, bot_msg, player_reply, outcome)
                        VALUES (?,?,?,?,?,?,?)
                    """, (acc_id, job_id,
                          float(entry.get("ts", now)),
                          str(entry.get("name",  ""))[:64],
                          str(entry.get("bot",   ""))[:256],
                          str(entry.get("reply", ""))[:256],
                          str(entry.get("outcome",""))[:32]))

            con.commit()
            con.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/pd_interactions/<acc_id>")
def get_pd_interactions(acc_id):
    """Paginated interaction log. acc_id='__all__' returns all bots."""
    try:
        limit  = min(int(request.args.get("limit",  200)), 500)
        offset = max(int(request.args.get("offset", 0)),   0)
        outcome_filter = request.args.get("outcome", "")
        player_filter  = request.args.get("player",  "").strip()
        with db_lock:
            con = _con()
            conditions = []
            params = []
            if acc_id != "__all__":
                conditions.append("account_id=?")
                params.append(acc_id)
            if outcome_filter:
                conditions.append("outcome=?")
                params.append(outcome_filter)
            if player_filter:
                conditions.append("LOWER(target_name) LIKE ?")
                params.append("%" + player_filter.lower() + "%")
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            total = con.execute(
                f"SELECT COUNT(*) FROM pd_interactions {where}", params
            ).fetchone()[0]
            rows = con.execute(
                f"SELECT * FROM pd_interactions {where} ORDER BY ts DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            con.close()
        return jsonify({"total": total, "rows": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/pd_accounts")
def get_pd_accounts():
    return jsonify(pd_accounts)


@app.route("/pd_occupied_servers")
def pd_occupied_servers():
    """Return server IDs where our bots are currently active (seen < 3 min ago).
    Bots call this before picking a new server to avoid doubling up."""
    now = time.time()
    occupied = {}  # server_id -> bot name
    for acc_id, acc in pd_accounts.items():
        last_seen = acc.get("last_seen", 0)
        if now - last_seen > 180:   # offline > 3 min — skip
            continue
        cs = acc.get("current_session", {})
        sid = cs.get("server_id", "")
        if sid:
            occupied[sid] = acc.get("name", acc_id)
    return jsonify({"occupied": occupied, "ts": int(now)})


@app.route("/pd_reset/<acc_id>", methods=["DELETE"])
def pd_reset(acc_id):
    if acc_id not in pd_accounts:
        return jsonify({"ok": False, "error": "not found"}), 404
    acc = pd_accounts[acc_id]
    acc.update({"approached": 0, "agreed": 0, "refused": 0, "no_response": 0,
                "hops": 0, "donations": 0, "robux_gross": 0, "raised_current": 0, "sessions": []})
    acc["current_session"] = {
        "server_id":     acc.get("current_session", {}).get("server_id", ""),
        "started_at":    time.time(),
        "approached": 0, "agreed": 0, "refused": 0, "no_response": 0,
        "donations": 0,  "robux_gross": 0, "raised_current": 0,
    }
    with db_lock:
        con = _con()
        con.execute("UPDATE pd_accounts SET approached=0,agreed=0,refused=0,no_response=0,hops=0,donations=0,robux_gross=0,raised_current=0 WHERE id=?", (acc_id,))
        con.execute("DELETE FROM pd_sessions WHERE account_id=?", (acc_id,))
        con.execute("UPDATE pd_current_sessions SET approached=0,agreed=0,refused=0,no_response=0,donations=0,robux_gross=0,raised_current=0,started_at=? WHERE account_id=?", (time.time(), acc_id))
        con.commit()
        con.close()
    return jsonify({"ok": True})


@app.route("/analytics_data")
def analytics_data():
    import datetime as _dt
    period    = request.args.get("period",    "all")   # today|yesterday|7d|all|custom
    date_from = request.args.get("date_from", "")      # YYYY-MM-DD
    date_to   = request.args.get("date_to",   "")      # YYYY-MM-DD (inclusive)
    # ts_from_client: local-midnight Unix epoch sent by the browser (fixes timezone mismatch)
    ts_from_client = request.args.get("ts_from_client", "")
    now = time.time()

    # Compute LOCAL boundaries using client-supplied midnight when available
    if ts_from_client:
        try:
            client_today_start = int(ts_from_client)
        except ValueError:
            client_today_start = None
    else:
        client_today_start = None

    # Fallback: use server local time (not UTC) so "today" matches the dashboard
    local_now = _dt.datetime.now()
    today_start   = int(local_now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    yesterday_start = today_start - 86400

    if period == "today":
        ts_from = client_today_start if client_today_start is not None else today_start
        ts_to   = None
    elif period == "yesterday":
        yest_start = (client_today_start - 86400) if client_today_start is not None else yesterday_start
        ts_from, ts_to = yest_start, (client_today_start if client_today_start is not None else today_start)
    elif period == "7d":
        ts_from, ts_to = int(now) - 7 * 86400, None
    elif period == "custom" and (date_from or date_to):
        try:
            ts_from = int(_dt.datetime.strptime(date_from, "%Y-%m-%d").timestamp()) if date_from else None
            ts_to   = int((_dt.datetime.strptime(date_to, "%Y-%m-%d") + _dt.timedelta(days=1)).timestamp()) if date_to else None
        except ValueError:
            ts_from, ts_to = None, None
    else:  # all / lifetime
        ts_from, ts_to = None, None

    def _where(alias=""):
        col = f"{alias}started_at" if alias else "started_at"
        parts = []
        if ts_from is not None:
            parts.append(f"{col} >= {ts_from}")
        if ts_to is not None:
            parts.append(f"{col} < {ts_to}")
        return ("WHERE " + " AND ".join(parts)) if parts else ""

    with db_lock:
        con = _con()

        # Completed sessions
        hourly_rows = con.execute(f"""
            SELECT
                CAST(strftime('%H', datetime(started_at, 'unixepoch', 'localtime')) AS INTEGER) AS hour,
                SUM(robux_gross) AS robux,
                SUM(approached)  AS approached,
                SUM(agreed)      AS agreed
            FROM pd_sessions
            {_where()}
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        sess_where = _where()
        join_cond = ("AND s." + sess_where[6:]) if sess_where else ""
        bot_rows = con.execute(f"""
            SELECT a.id, a.name,
                   COALESCE(SUM(s.robux_gross),0) AS robux_gross,
                   COALESCE(SUM(s.approached),0)  AS approached,
                   COALESCE(SUM(s.agreed),0)      AS agreed,
                   CASE WHEN a.hops < 100000 THEN a.hops ELSE 0 END AS hops
            FROM pd_accounts a
            LEFT JOIN pd_sessions s ON s.account_id = a.id {join_cond}
            GROUP BY a.id
        """).fetchall()

        server_rows = con.execute(f"""
            SELECT server_id,
                   SUM(approached)  AS approached,
                   SUM(agreed)      AS agreed,
                   SUM(robux_gross) AS robux,
                   SUM(duration)/60.0 AS duration_min
            FROM pd_sessions
            WHERE server_id != '' {(" AND " + _where()[6:]) if _where() else ""}
            GROUP BY server_id
            ORDER BY robux DESC
            LIMIT 20
        """).fetchall()

        # ── Also include ACTIVE (not yet closed) current sessions ──
        # These are missing from pd_sessions until the bot hops to a new server.
        cs_rows = con.execute("SELECT * FROM pd_current_sessions").fetchall()
        con.close()

    # Build hourly map from completed sessions
    hourly_map = {}
    for r in hourly_rows:
        h = r["hour"]
        hourly_map[h] = {
            "robux":      (r["robux"]      or 0),
            "approached": (r["approached"] or 0),
            "agreed":     (r["agreed"]     or 0),
        }

    # Per-bot delta accumulators for active sessions
    cs_by_account = {}
    cur_hour = _dt.datetime.now().hour
    for cs in cs_rows:
        cs = dict(cs)
        started = cs.get("started_at", 0)
        # Only include if this session falls within the selected period
        if ts_from is not None and started < ts_from:
            continue
        if ts_to is not None and started >= ts_to:
            continue
        aid = cs["account_id"]
        d_app   = max(0, (cs.get("approached",  0) or 0) - (cs.get("snap_app",   0) or 0))
        d_agr   = max(0, (cs.get("agreed",      0) or 0) - (cs.get("snap_agr",   0) or 0))
        d_gross = max(0, (cs.get("robux_gross", 0) or 0) - (cs.get("snap_gross", 0) or 0))
        cs_by_account[aid] = {"app": d_app, "agr": d_agr, "gross": d_gross}
        # Add to current hour in hourly chart
        hm = hourly_map.setdefault(cur_hour, {"robux": 0, "approached": 0, "agreed": 0})
        hm["robux"]      += d_gross
        hm["approached"] += d_app
        hm["agreed"]     += d_agr

    hourly = []
    for h in range(24):
        row = hourly_map.get(h, {"robux": 0, "approached": 0, "agreed": 0})
        hourly.append({
            "hour":      h,
            "robux":     row["robux"],
            "approached":row["approached"],
            "agreed":    row["agreed"],
        })

    bots = []
    for r in bot_rows:
        aid  = r["id"]
        cs_d = cs_by_account.get(aid, {"app": 0, "agr": 0, "gross": 0})
        app_ = (r["approached"] or 0) + cs_d["app"]
        agr  = (r["agreed"]     or 0) + cs_d["agr"]
        gross= (r["robux_gross"]or 0) + cs_d["gross"]
        bots.append({
            "id":         aid,
            "name":       r["name"],
            "robux_gross":gross,
            "approached": app_,
            "agreed":     agr,
            "hops":       r["hops"] or 0,
            "conv_rate":  round(agr / app_ * 100, 1) if app_ > 0 else 0.0,
        })

    servers = []
    for r in server_rows:
        app_ = r["approached"] or 0
        agr  = r["agreed"]     or 0
        servers.append({
            "server_id":   r["server_id"],
            "approached":  app_,
            "agreed":      agr,
            "robux":       r["robux"]       or 0,
            "duration_min":round(r["duration_min"] or 0, 1),
            "conv_rate":   round(agr / app_ * 100, 1) if app_ > 0 else 0.0,
        })

    return jsonify({
        "hourly":  hourly,
        "bots":    bots,
        "servers": servers,
        "period":  period,
        "ts":      int(now),
    })


@app.route("/interactions_data")
def interactions_data():
    """Aggregated interaction statistics for the Interactions analysis page."""
    with db_lock:
        con = _con()

        # 1. Outcome totals
        outcome_rows = con.execute("""
            SELECT outcome, COUNT(*) AS cnt
            FROM pd_interactions
            GROUP BY outcome
        """).fetchall()

        # 2. Top 40 player replies (non-empty)
        reply_rows = con.execute("""
            SELECT LOWER(TRIM(player_reply)) AS reply, COUNT(*) AS cnt
            FROM pd_interactions
            WHERE player_reply != '' AND outcome IN ('agreed','refused')
            GROUP BY LOWER(TRIM(player_reply))
            ORDER BY cnt DESC
            LIMIT 40
        """).fetchall()

        # 3. Per-bot outcome breakdown
        bot_outcome_rows = con.execute("""
            SELECT account_id,
                   SUM(CASE WHEN outcome='agreed'      THEN 1 ELSE 0 END) AS agreed,
                   SUM(CASE WHEN outcome='refused'     THEN 1 ELSE 0 END) AS refused,
                   SUM(CASE WHEN outcome='no_response' THEN 1 ELSE 0 END) AS no_response,
                   SUM(CASE WHEN outcome='left'        THEN 1 ELSE 0 END) AS left_,
                   COUNT(*) AS total
            FROM pd_interactions
            GROUP BY account_id
        """).fetchall()

        # 4. Hourly interaction distribution (using pd_interactions timestamp)
        hourly_rows = con.execute("""
            SELECT
                CAST(strftime('%H', datetime(ts, 'unixepoch')) AS INTEGER) AS hour,
                SUM(CASE WHEN outcome='agreed'      THEN 1 ELSE 0 END) AS agreed,
                SUM(CASE WHEN outcome='refused'     THEN 1 ELSE 0 END) AS refused,
                SUM(CASE WHEN outcome='no_response' THEN 1 ELSE 0 END) AS no_response,
                SUM(CASE WHEN outcome='left'        THEN 1 ELSE 0 END) AS left_,
                COUNT(*) AS total
            FROM pd_interactions
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        # 5. Top 20 most-contacted players
        top_players = con.execute("""
            SELECT target_name,
                   COUNT(*) AS total,
                   SUM(CASE WHEN outcome='agreed'  THEN 1 ELSE 0 END) AS agreed,
                   SUM(CASE WHEN outcome='refused' THEN 1 ELSE 0 END) AS refused
            FROM pd_interactions
            WHERE target_name != ''
            GROUP BY target_name
            ORDER BY total DESC
            LIMIT 20
        """).fetchall()

        # 6. Top 20 donors (players who agreed most)
        top_donors = con.execute("""
            SELECT target_name,
                   SUM(CASE WHEN outcome='agreed' THEN 1 ELSE 0 END) AS agreed,
                   COUNT(*) AS total
            FROM pd_interactions
            WHERE target_name != ''
            GROUP BY target_name
            HAVING agreed > 0
            ORDER BY agreed DESC
            LIMIT 20
        """).fetchall()

        # 7. No-response rate by hour (% of total that gave no reply)
        no_resp_hourly = con.execute("""
            SELECT
                CAST(strftime('%H', datetime(ts, 'unixepoch')) AS INTEGER) AS hour,
                ROUND(100.0 * SUM(CASE WHEN outcome='no_response' THEN 1 ELSE 0 END) / COUNT(*), 1) AS no_resp_pct
            FROM pd_interactions
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        con.close()

    outcomes = {r["outcome"]: r["cnt"] for r in outcome_rows}

    hourly_map = {r["hour"]: dict(r) for r in hourly_rows}
    nr_map     = {r["hour"]: r["no_resp_pct"] for r in no_resp_hourly}
    hourly = []
    for h in range(24):
        base = hourly_map.get(h, {"hour": h, "agreed": 0, "refused": 0,
                                   "no_response": 0, "left_": 0, "total": 0})
        hourly.append({
            "hour":        h,
            "agreed":      base["agreed"]      or 0,
            "refused":     base["refused"]      or 0,
            "no_response": base["no_response"] or 0,
            "left":        base["left_"]        or 0,
            "total":       base["total"]        or 0,
            "no_resp_pct": nr_map.get(h, 0)    or 0,
        })

    return jsonify({
        "outcomes":    outcomes,
        "replies":     [dict(r) for r in reply_rows],
        "bots":        [dict(r) for r in bot_outcome_rows],
        "hourly":      hourly,
        "top_players": [dict(r) for r in top_players],
        "top_donors":  [dict(r) for r in top_donors],
    })


_INTERACTIONS_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ПД Анализ диалогов</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#07070e;color:#e2e2f0;min-height:100vh;padding:24px 32px}
a.back{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#7c6aff;
  text-decoration:none;margin-bottom:20px;padding:6px 14px;border-radius:8px;
  border:1px solid rgba(124,106,255,.25);background:rgba(124,106,255,.08);transition:.15s}
a.back:hover{background:rgba(124,106,255,.2)}
h1{font-size:24px;font-weight:800;margin-bottom:4px}
.sub{font-size:13px;color:#55556a;margin-bottom:28px}
/* Summary stats row */
.stats-row{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:24px}
.stat-card{background:#111118;border:1px solid rgba(255,255,255,.07);border-radius:14px;
  padding:18px 20px;text-align:center}
.stat-card .num{font-size:32px;font-weight:800;line-height:1}
.stat-card .lbl{font-size:11px;color:#55556a;letter-spacing:.07em;text-transform:uppercase;
  margin-top:6px;font-weight:600}
/* Grid */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:18px}
.card{background:#111118;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:22px}
.card.full{grid-column:1/-1}
.card h2{font-size:14px;font-weight:700;color:#c0c0d8;margin-bottom:16px;letter-spacing:.02em}
canvas{max-height:280px;width:100%!important}
/* Tables */
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:7px 12px;color:#55556a;font-weight:700;font-size:10.5px;
  letter-spacing:.07em;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,.07)}
td{padding:7px 12px;border-bottom:1px solid rgba(255,255,255,.04);color:#b8b8cc}
tr:hover td{background:rgba(255,255,255,.025)}
/* Badges */
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700}
.b-green{background:rgba(34,197,94,.14);color:#22c55e}
.b-red{background:rgba(239,68,68,.14);color:#ef4444}
.b-yellow{background:rgba(234,179,8,.14);color:#eab308}
.b-blue{background:rgba(56,189,248,.14);color:#38bdf8}
.b-muted{background:rgba(100,116,139,.14);color:#64748b}
.b-purple{background:rgba(124,106,255,.14);color:#7c6aff}
/* Progress bar */
.bar-wrap{background:rgba(255,255,255,.06);border-radius:4px;height:6px;overflow:hidden;margin-top:4px}
.bar-fill{height:100%;border-radius:4px;transition:.3s}
/* Filter row */
.filter-row{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:center}
.filter-row select,.filter-row input{
  background:#1a1a28;border:1px solid rgba(255,255,255,.1);border-radius:8px;
  color:#e2e2f0;font-size:13px;padding:7px 12px;outline:none;font-family:inherit}
.filter-row select:focus,.filter-row input:focus{border-color:rgba(124,106,255,.5)}
.btn{padding:7px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;
  font-family:inherit;transition:.15s}
.btn-primary{background:#7c6aff;color:#fff}
.btn-primary:hover{background:#6a58ee}
.btn-outline{background:transparent;border:1px solid rgba(255,255,255,.12);color:#9494a8}
.btn-outline:hover{background:rgba(255,255,255,.06)}
/* Word cloud table */
.reply-grid{display:flex;flex-wrap:wrap;gap:8px}
.reply-tag{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;
  border-radius:20px;border:1px solid rgba(255,255,255,.1);background:#1a1a28;
  font-size:12px;cursor:default;transition:.15s}
.reply-tag:hover{border-color:rgba(124,106,255,.4);background:rgba(124,106,255,.08)}
.reply-tag .cnt{font-size:10px;color:#55556a;font-weight:700}
/* Pagination */
.pager{display:flex;gap:8px;align-items:center;margin-top:12px;justify-content:flex-end}
.pager span{font-size:12px;color:#55556a}
/* Responsive */
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}.stats-row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.stats-row{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<a href="/" class="back">← Дашборд</a>
<h1>💬 Анализ диалогов</h1>
<p class="sub">Полная разбивка каждого диалога — кто отвечает, что пишет, когда и почему</p>

<!-- Summary row -->
<div class="stats-row" id="statsRow">
  <div class="stat-card"><div class="num" id="sTotal" style="color:#7c6aff">—</div><div class="lbl">Всего подошёл</div></div>
  <div class="stat-card"><div class="num" id="sAgreed" style="color:#22c55e">—</div><div class="lbl">Согласились</div></div>
  <div class="stat-card"><div class="num" id="sRefused" style="color:#ef4444">—</div><div class="lbl">Отказали</div></div>
  <div class="stat-card"><div class="num" id="sNoResp" style="color:#64748b">—</div><div class="lbl">Нет ответа</div></div>
  <div class="stat-card"><div class="num" id="sConv" style="color:#eab308">—</div><div class="lbl">% конверсии</div></div>
</div>

<div class="grid3">
  <!-- Outcome doughnut -->
  <div class="card">
    <h2>Разбивка по результатам</h2>
    <canvas id="chartOutcome"></canvas>
  </div>
  <!-- Hourly agreed vs refused -->
  <div class="card">
    <h2>Диалоги по часам суток</h2>
    <canvas id="chartHourly"></canvas>
  </div>
  <!-- No-response % by hour -->
  <div class="card">
    <h2>% игнора по часам</h2>
    <canvas id="chartIgnore"></canvas>
  </div>
</div>

<div class="grid2">
  <!-- Player replies word cloud -->
  <div class="card">
    <h2>Что пишут игроки <span style="color:#55556a;font-size:11px;font-weight:400">(топ 40 ответов)</span></h2>
    <div class="reply-grid" id="replyCloud"></div>
  </div>
  <!-- Per-bot breakdown -->
  <div class="card">
    <h2>Разбивка по ботам</h2>
    <div style="overflow-x:auto">
    <table id="tblBots">
      <thead><tr>
        <th>Бот</th><th>Подошёл</th><th>Согласились</th><th>Отказали</th><th>Молчали</th><th>% согл.</th>
      </tr></thead>
      <tbody></tbody>
    </table>
    </div>
  </div>
</div>

<div class="grid2">
  <!-- Top players contacted -->
  <div class="card">
    <h2>Самые часто контактируемые игроки</h2>
    <div style="overflow-x:auto">
    <table id="tblPlayers">
      <thead><tr><th>#</th><th>Игрок</th><th>Раз</th><th>Согласились</th><th>Отказали</th><th>%</th></tr></thead>
      <tbody></tbody>
    </table>
    </div>
  </div>
  <!-- Top donors -->
  <div class="card">
    <h2>Самые щедрые игроки <span style="color:#55556a;font-size:11px;font-weight:400">(чаще всего соглашались)</span></h2>
    <div style="overflow-x:auto">
    <table id="tblDonors">
      <thead><tr><th>#</th><th>Игрок</th><th>Согласились</th><th>Всего подходил</th><th>%</th></tr></thead>
      <tbody></tbody>
    </table>
    </div>
  </div>
</div>

<!-- Raw interaction log -->
<div class="card" style="margin-bottom:24px">
  <h2>Полный лог диалогов</h2>
  <div class="filter-row">
    <select id="fBot"><option value="">Все боты</option></select>
    <select id="fOutcome">
      <option value="">Все результаты</option>
      <option value="agreed">Согласился</option>
      <option value="refused">Отказал</option>
      <option value="no_response">Молчал</option>
      <option value="left">Ушёл</option>
    </select>
    <input id="fPlayer" placeholder="Поиск по нику игрока..." style="min-width:180px">
    <button class="btn btn-primary" onclick="loadLog(0)">Применить</button>
    <button class="btn btn-outline" onclick="document.getElementById('fBot').value='';document.getElementById('fOutcome').value='';document.getElementById('fPlayer').value='';loadLog(0)">Сбросить</button>
    <span id="logTotal" style="font-size:12px;color:#55556a;margin-left:4px"></span>
  </div>
  <div style="overflow-x:auto">
  <table id="tblLog">
    <thead><tr>
      <th>Время</th><th>Бот</th><th>Игрок</th><th>Сообщение бота</th><th>Ответ игрока</th><th>Результат</th>
    </tr></thead>
    <tbody id="logBody"></tbody>
  </table>
  </div>
  <div class="pager">
    <button class="btn btn-outline" id="btnPrev" onclick="changePage(-1)">← Назад</button>
    <span id="pageInfo">Страница 1</span>
    <button class="btn btn-outline" id="btnNext" onclick="changePage(1)">Вперёд →</button>
  </div>
</div>

<script>
const OUTCOME_COLORS = {
  agreed:      {bg:'rgba(34,197,94,.7)',  border:'#22c55e'},
  refused:     {bg:'rgba(239,68,68,.7)', border:'#ef4444'},
  no_response: {bg:'rgba(100,116,139,.6)',border:'#64748b'},
  left:        {bg:'rgba(234,179,8,.6)', border:'#eab308'},
};
const OUTCOME_BADGE = {
  agreed:      '<span class="badge b-green">Согласился</span>',
  refused:     '<span class="badge b-red">Отказал</span>',
  no_response: '<span class="badge b-muted">Молчал</span>',
  left:        '<span class="badge b-yellow">Ушёл</span>',
};

let logPage  = 0;
let logLimit = 50;
let logTotalCount = 0;
let allBots  = [];

function fmt(ts){
  const d = new Date(ts*1000);
  return d.toLocaleDateString('ru-RU') + ' ' + d.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
}
function pct(a,b){ return b>0 ? (a/b*100).toFixed(1)+'%' : '—'; }
function num(n){ return (n||0).toLocaleString(); }
function truncate(s,n){ return s && s.length>n ? s.slice(0,n)+'…' : (s||'—'); }

// ── Load aggregated data ──
fetch('/interactions_data').then(r=>r.json()).then(data=>{
  const o = data.outcomes || {};
  const agreed      = o.agreed      || 0;
  const refused     = o.refused     || 0;
  const no_response = o.no_response || 0;
  const left_       = o.left        || 0;
  const total = agreed + refused + no_response + left_;

  // Summary cards
  document.getElementById('sTotal').textContent  = num(total);
  document.getElementById('sAgreed').textContent  = num(agreed);
  document.getElementById('sRefused').textContent = num(refused);
  document.getElementById('sNoResp').textContent  = num(no_response);
  document.getElementById('sConv').textContent    = total>0 ? (agreed/total*100).toFixed(1)+'%' : '—';

  // Chart 1 — Doughnut
  new Chart(document.getElementById('chartOutcome'), {
    type: 'doughnut',
    data: {
      labels: ['Согласились','Отказали','Нет ответа','Ушли'],
      datasets:[{
        data:[agreed,refused,no_response,left_],
        backgroundColor:['rgba(34,197,94,.75)','rgba(239,68,68,.75)','rgba(100,116,139,.65)','rgba(234,179,8,.65)'],
        borderColor:['#22c55e','#ef4444','#64748b','#eab308'],
        borderWidth:1,
      }]
    },
    options:{
      cutout:'65%',
      plugins:{legend:{labels:{color:'#9494a8',font:{size:12}}}}
    }
  });

  // Chart 2 — Hourly stacked bar
  const hrs = data.hourly.map(h=>h.hour+':00');
  new Chart(document.getElementById('chartHourly'), {
    type:'bar',
    data:{
      labels: hrs,
      datasets:[
        {label:'Согласились',data:data.hourly.map(h=>h.agreed),backgroundColor:'rgba(34,197,94,.65)',borderRadius:2,stack:'s'},
        {label:'Отказали',data:data.hourly.map(h=>h.refused),backgroundColor:'rgba(239,68,68,.65)',borderRadius:2,stack:'s'},
        {label:'Молчали',data:data.hourly.map(h=>h.no_response),backgroundColor:'rgba(100,116,139,.55)',borderRadius:2,stack:'s'},
        {label:'Ушли',data:data.hourly.map(h=>h.left),backgroundColor:'rgba(234,179,8,.55)',borderRadius:2,stack:'s'},
      ]
    },
    options:{
      plugins:{legend:{labels:{color:'#9494a8',font:{size:11}}}},
      scales:{
        x:{ticks:{color:'#55556a',font:{size:10}},grid:{color:'rgba(255,255,255,.04)'},stacked:true},
        y:{ticks:{color:'#55556a'},grid:{color:'rgba(255,255,255,.04)'},stacked:true}
      }
    }
  });

  // Chart 3 — Ignore rate % by hour
  new Chart(document.getElementById('chartIgnore'), {
    type:'line',
    data:{
      labels: hrs,
      datasets:[{
        label:'% игнора',
        data: data.hourly.map(h=>h.no_resp_pct),
        borderColor:'rgba(100,116,139,1)',
        backgroundColor:'rgba(100,116,139,.15)',
        fill:true, tension:.4, pointRadius:3,
      }]
    },
    options:{
      plugins:{legend:{labels:{color:'#9494a8',font:{size:12}}}},
      scales:{
        x:{ticks:{color:'#55556a',font:{size:10}},grid:{color:'rgba(255,255,255,.04)'}},
        y:{ticks:{color:'#55556a',callback:v=>v+'%'},grid:{color:'rgba(255,255,255,.04)'},min:0,max:100}
      }
    }
  });

  // Reply word cloud
  const cloud = document.getElementById('replyCloud');
  const maxCnt = data.replies.length ? data.replies[0].cnt : 1;
  data.replies.forEach(r=>{
    const sz = 12 + Math.round((r.cnt / maxCnt) * 10);
    const op = 0.5 + (r.cnt / maxCnt) * 0.5;
    const tag = document.createElement('div');
    tag.className = 'reply-tag';
    tag.title = `Написано ${r.cnt} раз`;
    tag.style.fontSize = sz + 'px';
    tag.style.opacity  = op;
    tag.innerHTML = `<span>${r.reply || '(пусто)'}</span><span class="cnt">${r.cnt}</span>`;
    cloud.appendChild(tag);
  });

  // Per-bot table
  allBots = data.bots;
  const botSel = document.getElementById('fBot');
  data.bots.forEach(b=>{
    const opt = document.createElement('option');
    opt.value = b.account_id; opt.textContent = b.account_id;
    botSel.appendChild(opt);
  });
  const botTbody = document.querySelector('#tblBots tbody');
  data.bots.forEach(b=>{
    const conv = b.total>0 ? (b.agreed/b.total*100).toFixed(1)+'%' : '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="font-weight:600;color:#e2e2f0">${b.account_id}</td>
      <td>${num(b.total)}</td>
      <td><span class="badge b-green">${num(b.agreed)}</span></td>
      <td><span class="badge b-red">${num(b.refused)}</span></td>
      <td><span class="badge b-muted">${num(b.no_response)}</span></td>
      <td><span class="badge b-purple">${conv}</span></td>
    `;
    botTbody.appendChild(tr);
  });

  // Top players table
  const ptbody = document.querySelector('#tblPlayers tbody');
  data.top_players.forEach((p,i)=>{
    const rate = p.total>0 ? (p.agreed/p.total*100).toFixed(0)+'%' : '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:#55556a">${i+1}</td>
      <td style="font-weight:600;color:#e2e2f0">${p.target_name}</td>
      <td>${num(p.total)}</td>
      <td><span class="badge b-green">${num(p.agreed)}</span></td>
      <td><span class="badge b-red">${num(p.refused)}</span></td>
      <td>${rate}</td>
    `;
    ptbody.appendChild(tr);
  });

  // Top donors table
  const dtbody = document.querySelector('#tblDonors tbody');
  data.top_donors.forEach((p,i)=>{
    const rate = p.total>0 ? (p.agreed/p.total*100).toFixed(0)+'%' : '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:#55556a">${i+1}</td>
      <td style="font-weight:600;color:#e2e2f0">${p.target_name}</td>
      <td><span class="badge b-green">${num(p.agreed)}</span></td>
      <td>${num(p.total)}</td>
      <td><span class="badge b-purple">${rate}</span></td>
    `;
    dtbody.appendChild(tr);
  });

  // Initial log load
  loadLog(0);
});

// ── Raw log pagination ──
function loadLog(page){
  logPage = page;
  const bot     = document.getElementById('fBot').value;
  const outcome = document.getElementById('fOutcome').value;
  const player  = document.getElementById('fPlayer').value.trim();

  const offset = page * logLimit;
  let url = `/pd_interactions/${encodeURIComponent(bot || '__all__')}?limit=${logLimit}&offset=${offset}`;
  if(outcome) url += '&outcome=' + encodeURIComponent(outcome);
  if(player)  url += '&player='  + encodeURIComponent(player);

  fetch(url).then(r=>r.json()).then(data=>{
    logTotalCount = data.total || 0;
    document.getElementById('logTotal').textContent = `${num(logTotalCount)} записей`;
    document.getElementById('pageInfo').textContent =
      `Страница ${page+1} / ${Math.max(1,Math.ceil(logTotalCount/logLimit))}`;
    document.getElementById('btnPrev').disabled = page <= 0;
    document.getElementById('btnNext').disabled = (page+1)*logLimit >= logTotalCount;

    const tbody = document.getElementById('logBody');
    tbody.innerHTML = '';
    (data.rows||[]).forEach(row=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="white-space:nowrap;color:#55556a;font-size:11px">${fmt(row.ts)}</td>
        <td style="font-size:11px;color:#9494a8">${row.account_id}</td>
        <td style="font-weight:600;color:#e2e2f0">${row.target_name||'—'}</td>
        <td style="max-width:260px;color:#b0b0c4;font-size:12px" title="${(row.bot_msg||'').replace(/"/g,'&quot;')}">${truncate(row.bot_msg,60)}</td>
        <td style="max-width:160px;color:#c8c8d8;font-size:12px" title="${(row.player_reply||'').replace(/"/g,'&quot;')}">${truncate(row.player_reply,40)||'—'}</td>
        <td>${OUTCOME_BADGE[row.outcome]||row.outcome}</td>
      `;
      tbody.appendChild(tr);
    });
    if(!data.rows||!data.rows.length){
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#55556a;padding:24px">Диалоги не найдены</td></tr>';
    }
  });
}

function changePage(delta){
  const next = logPage + delta;
  const maxPage = Math.ceil(logTotalCount / logLimit) - 1;
  if(next >= 0 && next <= maxPage) loadLog(next);
}
</script>
</body>
</html>"""


@app.route("/interactions")
def interactions_page():
    return _INTERACTIONS_HTML


# ─── CSV / Excel export endpoints ────────────────────────────────────────────

def _csv_response(filename, headers, rows):
    """Build a downloadable CSV response."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    buf.seek(0)
    return Response(
        buf.getvalue().encode("utf-8-sig"),   # utf-8-sig = BOM for Excel
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/export/interactions.csv")
def export_interactions():
    """Download the full PD interaction log as CSV."""
    account_filter = request.args.get("account", "")
    outcome_filter = request.args.get("outcome", "")
    limit = min(int(request.args.get("limit", 50000)), 200000)
    with db_lock:
        con = _con()
        conditions, params = [], []
        if account_filter:
            conditions.append("account_id=?"); params.append(account_filter)
        if outcome_filter:
            conditions.append("outcome=?"); params.append(outcome_filter)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = con.execute(
            f"SELECT id, ts, account_id, server_id, target_name, bot_msg, player_reply, outcome "
            f"FROM pd_interactions {where} ORDER BY ts DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        con.close()

    def fmt_ts(ts):
        import datetime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""

    data = [
        (r["id"], fmt_ts(r["ts"]), r["account_id"], r["server_id"],
         r["target_name"], r["bot_msg"], r["player_reply"], r["outcome"])
        for r in rows
    ]
    return _csv_response(
        "pd_interactions.csv",
        ["ID", "Время", "Бот", "Сервер", "Игрок", "Сообщение бота", "Ответ игрока", "Результат"],
        data
    )


@app.route("/export/pd_sessions.csv")
def export_pd_sessions():
    """Download the full PD session history as CSV."""
    account_filter = request.args.get("account", "")
    with db_lock:
        con = _con()
        conditions, params = [], []
        if account_filter:
            conditions.append("account_id=?"); params.append(account_filter)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = con.execute(
            f"""SELECT s.id, s.started_at, s.ended_at, s.duration,
                       a.name AS bot_name, s.account_id, s.server_id,
                       s.approached, s.agreed, s.refused, s.no_response,
                       s.donations, s.robux_gross,
                       ROUND(s.robux_gross * 0.6, 0) AS robux_net
                FROM pd_sessions s
                LEFT JOIN pd_accounts a ON a.id = s.account_id
                {where}
                ORDER BY s.started_at DESC""",
            params
        ).fetchall()
        con.close()

    def fmt_ts(ts):
        import datetime
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""

    def fmt_dur(sec):
        sec = int(sec or 0)
        h, m = divmod(sec // 60, 60)
        return f"{h}ч {m}мин" if h else f"{m}мин"

    data = [
        (r["id"], r["bot_name"] or r["account_id"], r["server_id"],
         fmt_ts(r["started_at"]), fmt_ts(r["ended_at"]), fmt_dur(r["duration"]),
         r["approached"] or 0, r["agreed"] or 0, r["refused"] or 0,
         r["no_response"] or 0,
         round(r["agreed"] / r["approached"] * 100, 1) if (r["approached"] or 0) > 0 else 0,
         r["donations"] or 0, r["robux_gross"] or 0, int(r["robux_net"] or 0))
        for r in rows
    ]
    return _csv_response(
        "pd_sessions.csv",
        ["ID", "Бот", "Сервер", "Начало", "Конец", "Длительность",
         "Подошёл", "Согласились", "Отказали", "Нет ответа", "% согласий",
         "Донации", "Робукс (гросс)", "Робукс (чистыми)"],
        data
    )


@app.route("/export/pd_summary.csv")
def export_pd_summary():
    """Download per-bot all-time summary as CSV."""
    with db_lock:
        con = _con()
        rows = con.execute("""
            SELECT a.name, a.id,
                   a.approached, a.agreed, a.refused, a.no_response,
                   a.hops, a.donations, a.robux_gross,
                   ROUND(a.robux_gross * 0.6, 0) AS robux_net,
                   COUNT(s.id) AS sessions_count,
                   SUM(s.duration) AS total_seconds
            FROM pd_accounts a
            LEFT JOIN pd_sessions s ON s.account_id = a.id
            GROUP BY a.id
            ORDER BY a.robux_gross DESC
        """).fetchall()
        con.close()

    def fmt_dur(sec):
        import datetime
        return str(datetime.timedelta(seconds=int(sec or 0)))

    data = [
        (r["name"] or r["id"], r["id"],
         r["approached"] or 0, r["agreed"] or 0, r["refused"] or 0,
         r["no_response"] or 0,
         round(r["agreed"] / r["approached"] * 100, 1) if (r["approached"] or 0) > 0 else 0,
         r["hops"] or 0, r["donations"] or 0,
         r["robux_gross"] or 0, int(r["robux_net"] or 0),
         r["sessions_count"] or 0, fmt_dur(r["total_seconds"]))
        for r in rows
    ]
    return _csv_response(
        "pd_summary.csv",
        ["Бот", "ID", "Подошёл", "Согласились", "Отказали", "Нет ответа",
         "% согласий", "Хопов", "Донаций", "Робукс (гросс)", "Робукс (чистыми)",
         "Сессий", "Общее время"],
        data
    )


@app.route("/export/analytics_hourly.csv")
def export_analytics_hourly():
    """Download hourly aggregated stats as CSV."""
    with db_lock:
        con = _con()
        rows = con.execute("""
            SELECT
                CAST(strftime('%H', datetime(ts, 'unixepoch')) AS INTEGER) AS hour,
                COUNT(*) AS total,
                SUM(CASE WHEN outcome='agreed'      THEN 1 ELSE 0 END) AS agreed,
                SUM(CASE WHEN outcome='refused'     THEN 1 ELSE 0 END) AS refused,
                SUM(CASE WHEN outcome='no_response' THEN 1 ELSE 0 END) AS no_response,
                SUM(CASE WHEN outcome='left'        THEN 1 ELSE 0 END) AS left_
            FROM pd_interactions
            GROUP BY hour
            ORDER BY hour
        """).fetchall()
        con.close()

    data = [
        (f"{r['hour']:02d}:00",
         r["total"] or 0, r["agreed"] or 0, r["refused"] or 0,
         r["no_response"] or 0, r["left_"] or 0,
         round((r["agreed"] or 0) / (r["total"] or 1) * 100, 1))
        for r in rows
    ]
    return _csv_response(
        "pd_analytics_by_hour.csv",
        ["Час", "Всего", "Согласились", "Отказали", "Нет ответа", "Ушли", "% согласий"],
        data
    )


@app.route("/export/top_replies.csv")
def export_top_replies():
    """Download top player replies (what players actually write)."""
    with db_lock:
        con = _con()
        rows = con.execute("""
            SELECT LOWER(TRIM(player_reply)) AS reply, outcome, COUNT(*) AS cnt
            FROM pd_interactions
            WHERE player_reply != ''
            GROUP BY LOWER(TRIM(player_reply)), outcome
            ORDER BY cnt DESC
            LIMIT 1000
        """).fetchall()
        con.close()

    data = [(r["reply"], r["outcome"], r["cnt"]) for r in rows]
    return _csv_response(
        "pd_top_replies.csv",
        ["Ответ игрока", "Результат", "Кол-во"],
        data
    )


@app.route("/export")
def export_index():
    """Export hub page — links to all CSV downloads."""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Экспорт данных</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#07070e;color:#e2e2f0;min-height:100vh;padding:32px}
a.back{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#7c6aff;text-decoration:none;
  margin-bottom:24px;padding:6px 14px;border-radius:8px;border:1px solid rgba(124,106,255,.25);
  background:rgba(124,106,255,.08)}
a.back:hover{background:rgba(124,106,255,.2)}
h1{font-size:22px;font-weight:800;margin-bottom:6px}
.sub{font-size:13px;color:#55556a;margin-bottom:32px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:#111118;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:22px}
.card h2{font-size:14px;font-weight:700;margin-bottom:6px}
.card p{font-size:12px;color:#7070a0;margin-bottom:16px;line-height:1.6}
.dl-btn{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;border-radius:9px;
  background:#7c6aff;color:#fff;text-decoration:none;font-size:13px;font-weight:600;transition:.15s}
.dl-btn:hover{background:#6a58ee}
.dl-btn.secondary{background:rgba(124,106,255,.12);color:#a78bfa;border:1px solid rgba(124,106,255,.25)}
.dl-btn.secondary:hover{background:rgba(124,106,255,.22)}
.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:10px}
.t-green{background:rgba(34,197,94,.12);color:#22c55e}
.t-blue{background:rgba(56,189,248,.12);color:#38bdf8}
.t-yellow{background:rgba(234,179,8,.12);color:#eab308}
.t-purple{background:rgba(124,106,255,.12);color:#a78bfa}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.filters select,.filters input{
  background:#1a1a28;border:1px solid rgba(255,255,255,.1);border-radius:8px;
  color:#e2e2f0;font-size:12px;padding:5px 10px;outline:none;font-family:inherit}
</style>
</head>
<body>
<a href="/" class="back">← Дашборд</a>
<h1>📥 Экспорт данных</h1>
<p class="sub">Скачайте данные в формате CSV — открывается в Excel, Google Sheets, LibreOffice</p>

<div class="grid">

  <div class="card">
    <span class="tag t-green">CSV</span>
    <h2>Лог взаимодействий</h2>
    <p>Каждый диалог: бот, игрок, что написал бот, что ответил игрок, результат (согласился/отказал/молчал). До 50 000 записей.</p>
    <div class="filters">
      <select id="f-acc-int" onchange="updateLinks()">
        <option value="">Все боты</option>
      </select>
      <select id="f-oc-int" onchange="updateLinks()">
        <option value="">Все результаты</option>
        <option value="agreed">Согласился</option>
        <option value="refused">Отказал</option>
        <option value="no_response">Молчал</option>
        <option value="left">Ушёл</option>
      </select>
    </div>
    <a id="dl-int" href="/export/interactions.csv" class="dl-btn">⬇ Скачать interactions.csv</a>
  </div>

  <div class="card">
    <span class="tag t-blue">CSV</span>
    <h2>История сессий (PD)</h2>
    <p>Каждая сессия на сервере: бот, сервер, время, длительность, approached / agreed / refused, донации, робуксы (гросс и чистые).</p>
    <div class="filters">
      <select id="f-acc-ses" onchange="updateLinks()">
        <option value="">Все боты</option>
      </select>
    </div>
    <a id="dl-ses" href="/export/pd_sessions.csv" class="dl-btn">⬇ Скачать pd_sessions.csv</a>
  </div>

  <div class="card">
    <span class="tag t-purple">CSV</span>
    <h2>Сводка по ботам</h2>
    <p>Итоговая статистика каждого бота: всего подошёл, согласились, % конверсии, хопов, донаций, чистый заработок, общее время работы.</p>
    <a href="/export/pd_summary.csv" class="dl-btn">⬇ Скачать pd_summary.csv</a>
  </div>

  <div class="card">
    <span class="tag t-yellow">CSV</span>
    <h2>Аналитика по часам</h2>
    <p>Сколько взаимодействий в каждый час суток: согласились / отказали / молчали / ушли + % конверсии по часу. Удобно для анализа лучшего времени.</p>
    <a href="/export/analytics_hourly.csv" class="dl-btn">⬇ Скачать analytics_by_hour.csv</a>
  </div>

  <div class="card">
    <span class="tag t-green">CSV</span>
    <h2>Топ ответов игроков</h2>
    <p>Что именно пишут игроки в ответ на сообщения бота. Топ-1000 фраз с разбивкой по результату. Полезно для улучшения парсинга YES/NO.</p>
    <a href="/export/top_replies.csv" class="dl-btn">⬇ Скачать top_replies.csv</a>
  </div>

  <div class="card" style="border-color:rgba(56,189,248,.2)">
    <span class="tag t-blue">Подсказка</span>
    <h2>Как открыть в Excel</h2>
    <p>1. Скачайте файл<br>2. Откройте Excel → Данные → Из текста/CSV<br>3. Кодировка: UTF-8<br>4. Разделитель: запятая<br><br>Или просто дважды кликните — Excel откроет сам (Windows).</p>
    <a href="https://docs.google.com/spreadsheets/u/0/" target="_blank" class="dl-btn secondary">🔗 Открыть Google Sheets</a>
  </div>

</div>

<script>
fetch('/pd_accounts').then(r=>r.json()).then(data=>{
  var bots = Object.values(data);
  ['f-acc-int','f-acc-ses'].forEach(function(id){
    var sel = document.getElementById(id);
    bots.forEach(function(b){
      var o = document.createElement('option');
      o.value = b.id; o.textContent = b.name || b.id;
      sel.appendChild(o);
    });
  });
});

function updateLinks() {
  var accInt = document.getElementById('f-acc-int').value;
  var oc     = document.getElementById('f-oc-int').value;
  var accSes = document.getElementById('f-acc-ses').value;

  var pInt = new URLSearchParams();
  if(accInt) pInt.set('account', accInt);
  if(oc)     pInt.set('outcome', oc);
  document.getElementById('dl-int').href = '/export/interactions.csv' + (pInt.toString() ? '?' + pInt : '');

  var pSes = new URLSearchParams();
  if(accSes) pSes.set('account', accSes);
  document.getElementById('dl-ses').href = '/export/pd_sessions.csv' + (pSes.toString() ? '?' + pSes : '');
}
</script>
</body>
</html>"""


_ANALYTICS_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ПД Аналитика</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#0a0a0f;color:#e8e8f0;min-height:100vh;padding:24px}
h1{font-size:22px;font-weight:700;margin-bottom:4px}
.subtitle{font-size:13px;color:#6b6b80;margin-bottom:16px}
.back{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#7c6aff;
      text-decoration:none;margin-bottom:20px;padding:6px 12px;border-radius:8px;
      border:1px solid rgba(124,106,255,.25);background:rgba(124,106,255,.08);transition:.15s}
.back:hover{background:rgba(124,106,255,.16)}
/* Period bar */
.period-bar{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.period-btn{padding:6px 16px;border-radius:8px;border:1px solid rgba(255,255,255,.1);
  background:rgba(255,255,255,.04);color:#9494a8;font-size:13px;font-weight:600;
  cursor:pointer;transition:.15s;font-family:inherit}
.period-btn:hover{background:rgba(255,255,255,.08)}
.period-btn.active{background:rgba(124,106,255,.18);border-color:rgba(124,106,255,.5);color:#a78bfa}
/* Date range row */
.date-row{display:flex;gap:10px;align-items:center;margin-bottom:20px;flex-wrap:wrap}
.date-row input[type=date]{
  background:#1a1a28;border:1px solid rgba(255,255,255,.1);border-radius:8px;
  color:#e8e8f0;font-size:13px;padding:6px 12px;outline:none;font-family:inherit;
  color-scheme:dark}
.date-row input[type=date]:focus{border-color:rgba(124,106,255,.5)}
.date-row label{font-size:12px;color:#6b6b80}
.apply-btn{padding:6px 18px;border-radius:8px;border:none;background:#7c6aff;
  color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s}
.apply-btn:hover{background:#6a58ee}
/* Live indicator */
.refresh-info{margin-left:auto;font-size:12px;color:#55556a;display:flex;align-items:center;gap:8px}
.live-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;
  animation:pulse 2s infinite;display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
/* Summary row */
.sum-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.sum-card{background:#111118;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:16px 20px}
.sum-card .num{font-size:28px;font-weight:800;line-height:1}
.sum-card .lbl{font-size:10px;color:#55556a;letter-spacing:.07em;text-transform:uppercase;margin-top:5px;font-weight:600}
/* Charts */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#111118;border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px}
.card.full{grid-column:1/-1}
.card h2{font-size:15px;font-weight:600;margin-bottom:18px;color:#e8e8f0}
canvas{max-height:300px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:#6b6b80;font-weight:600;font-size:11px;
   letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,.07)}
td{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.04);color:#c8c8d8}
tr:hover td{background:rgba(255,255,255,.03)}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}
.green{background:rgba(34,197,94,.12);color:#22c55e}
.purple{background:rgba(124,106,255,.12);color:#7c6aff}
@media(max-width:768px){.grid{grid-template-columns:1fr}.card.full{grid-column:auto}.sum-row{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<a href="/" class="back">← Дашборд</a>
<h1>📊 ПД Аналитика</h1>
<p class="subtitle">Разбивка по часам суток, ботам и серверам</p>

<!-- Quick period buttons -->
<div class="period-bar">
  <button class="period-btn" data-p="today"     onclick="setPeriod(this)">Сегодня</button>
  <button class="period-btn" data-p="yesterday" onclick="setPeriod(this)">Вчера</button>
  <button class="period-btn" data-p="7d"        onclick="setPeriod(this)">7 дней</button>
  <button class="period-btn active" data-p="all" onclick="setPeriod(this)">Лайфтайм</button>
  <div class="refresh-info">
    <span class="live-dot"></span>
    <span id="lastUpd">обновляется…</span>
  </div>
</div>

<!-- Custom date range -->
<div class="date-row">
  <label>С:</label>
  <input type="date" id="dateFrom">
  <label>По:</label>
  <input type="date" id="dateTo">
  <button class="apply-btn" onclick="applyCustomRange()">Применить</button>
  <span id="rangeLabel" style="font-size:12px;color:#6b6b80;margin-left:4px"></span>
</div>

<!-- Summary numbers -->
<div class="sum-row">
  <div class="sum-card"><div class="num" id="sRobux"  style="color:#22c55e">—</div><div class="lbl">Робуксы (гросс)</div></div>
  <div class="sum-card"><div class="num" id="sAppr"   style="color:#7c6aff">—</div><div class="lbl">Подошёл</div></div>
  <div class="sum-card"><div class="num" id="sAgreed" style="color:#eab308">—</div><div class="lbl">Согласились</div></div>
  <div class="sum-card"><div class="num" id="sConv"   style="color:#38bdf8">—</div><div class="lbl">% конверсии</div></div>
</div>

<div class="grid">
  <div class="card"><h2>Робукс по часам суток</h2><canvas id="chartHourly"></canvas></div>
  <div class="card"><h2>% конверсии по часам</h2><canvas id="chartConv"></canvas></div>
  <div class="card"><h2>Сравнение ботов</h2><canvas id="chartBots"></canvas></div>
  <div class="card">
    <h2>Топ серверов</h2>
    <div style="overflow-x:auto">
    <table id="tblServers">
      <thead><tr><th>ID сервера</th><th>Подошёл</th><th>Согласились</th><th>Робуксы</th><th>% согласий</th><th>Длительность</th></tr></thead>
      <tbody></tbody>
    </table>
    </div>
  </div>
</div>

<script>
const CD = {
  plugins:{ legend:{ labels:{ color:'#9494a8', font:{size:12} } } },
  scales:{
    x:{ ticks:{color:'#6b6b80'}, grid:{color:'rgba(255,255,255,.05)'} },
    y:{ ticks:{color:'#6b6b80'}, grid:{color:'rgba(255,255,255,.05)'} },
  }
};

let charts = {};
let currentPeriod = 'all';
let customFrom = '', customTo = '';
let refreshTimer = null;

// Set today as default max for date pickers
const todayStr = new Date().toISOString().slice(0,10);
document.getElementById('dateFrom').max = todayStr;
document.getElementById('dateTo').max   = todayStr;
document.getElementById('dateTo').value = todayStr;

function setPeriod(btn) {
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentPeriod = btn.dataset.p;
  customFrom = ''; customTo = '';
  document.getElementById('rangeLabel').textContent = '';
  loadData();
}

function applyCustomRange() {
  const f = document.getElementById('dateFrom').value;
  const t = document.getElementById('dateTo').value;
  if (!f && !t) return;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  currentPeriod = 'custom';
  customFrom = f; customTo = t;
  document.getElementById('rangeLabel').textContent =
    (f || '…') + ' → ' + (t || '…');
  loadData();
}

function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch(e){} });
  charts = {};
}

function fmt2(n){ return (n||0).toLocaleString('ru-RU'); }

function buildUrl() {
  let url = '/analytics_data?period=' + currentPeriod;
  // Send local midnight as Unix epoch so server uses client timezone, not UTC
  const d = new Date(); d.setHours(0,0,0,0);
  url += '&ts_from_client=' + Math.floor(d.getTime()/1000);
  if (currentPeriod === 'custom') {
    if (customFrom) url += '&date_from=' + customFrom;
    if (customTo)   url += '&date_to='   + customTo;
  }
  return url;
}

function loadData() {
  fetch(buildUrl()).then(r=>r.json()).then(data=>{
    const now = new Date();
    document.getElementById('lastUpd').textContent =
      'обновлено ' + now.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});

    const totRobux  = data.bots.reduce((s,b)=>s+b.robux_gross, 0);
    const totAppr   = data.bots.reduce((s,b)=>s+b.approached,  0);
    const totAgreed = data.bots.reduce((s,b)=>s+b.agreed,      0);
    document.getElementById('sRobux').textContent  = 'R$' + fmt2(totRobux);
    document.getElementById('sAppr').textContent   = fmt2(totAppr);
    document.getElementById('sAgreed').textContent = fmt2(totAgreed);
    document.getElementById('sConv').textContent   = totAppr>0 ? (totAgreed/totAppr*100).toFixed(1)+'%' : '—';

    destroyCharts();
    const hours = data.hourly.map(h=>h.hour+':00');

    charts.hourly = new Chart(document.getElementById('chartHourly'), {
      type:'bar',
      data:{ labels:hours, datasets:[{
        label:'Робукс (гросс)', data:data.hourly.map(h=>h.robux),
        backgroundColor:'rgba(34,197,94,.6)', borderColor:'rgba(34,197,94,1)',
        borderWidth:1, borderRadius:4,
      }]},
      options:{...CD}
    });

    charts.conv = new Chart(document.getElementById('chartConv'), {
      type:'line',
      data:{ labels:hours, datasets:[{
        label:'% конверсии',
        data:data.hourly.map(h=> h.approached>0 ? +(h.agreed/h.approached*100).toFixed(1) : 0),
        borderColor:'rgba(124,106,255,1)', backgroundColor:'rgba(124,106,255,.15)',
        fill:true, tension:.4, pointRadius:3,
      }]},
      options:{...CD}
    });

    charts.bots = new Chart(document.getElementById('chartBots'), {
      type:'bar',
      data:{ labels:data.bots.map(b=>b.name), datasets:[
        { label:'Робукс (гросс)', data:data.bots.map(b=>b.robux_gross),
          backgroundColor:'rgba(234,179,8,.6)', borderRadius:4 },
        { label:'Согласились', data:data.bots.map(b=>b.agreed),
          backgroundColor:'rgba(34,197,94,.5)', borderRadius:4 },
      ]},
      options:{ indexAxis:'y', ...CD }
    });

    const tbody = document.querySelector('#tblServers tbody');
    tbody.innerHTML = '';
    if (!data.servers.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#55556a;padding:16px">Нет данных за этот период</td></tr>';
    }
    data.servers.forEach(s=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-family:monospace;font-size:11px;color:#6b6b80">${s.server_id.slice(0,14)}…</td>
        <td>${s.approached}</td><td>${s.agreed}</td>
        <td><span class="badge green">R$${s.robux}</span></td>
        <td><span class="badge purple">${s.conv_rate}%</span></td>
        <td>${s.duration_min} мин</td>`;
      tbody.appendChild(tr);
    });

    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(loadData, 30000);
  }).catch(()=>{
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(loadData, 30000);
  });
}

loadData();
</script>
</body>
</html>"""


@app.route("/analytics")
def analytics():
    return _ANALYTICS_HTML


@app.route("/")
def dashboard():
    return DASHBOARD_HTML

# ─── Dashboard HTML ───────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Игровой Дашборд</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #0a0a0f;
  --surface:  #111118;
  --surface2: #1a1a24;
  --border:   rgba(255,255,255,.07);
  --border2:  rgba(255,255,255,.13);
  --text:     #e8e8f0;
  --muted:    #6b6b80;
  --accent:   #7c6aff;
  --accent2:  #a78bfa;
  --green:    #22c55e;
  --yellow:   #eab308;
  --red:      #ef4444;
  --blue:     #3b82f6;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg); color: var(--text);
  min-height: 100vh; font-size: 14px; line-height: 1.5;
}

/* ── Header ── */
.header {
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(12px);
  background: rgba(10,10,15,.88);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: stretch;
  padding: 0 24px; height: 52px; gap: 4px;
}
.brand {
  display: flex; align-items: center; gap: 8px;
  font-weight: 700; font-size: 15px; color: var(--text);
  padding-right: 20px; white-space: nowrap; flex-shrink: 0;
}
.brand-icon { color: var(--accent); font-size: 20px; }
.nav-tabs { display: flex; align-items: stretch; flex: 1; }
.nav-tab {
  display: flex; align-items: center; padding: 0 18px;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; border: none; background: none;
  border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s; white-space: nowrap;
}
.nav-tab:hover { color: var(--text); }
.nav-tab.active { color: var(--text); border-bottom-color: var(--accent); }
.header-right { display: flex; align-items: center; gap: 12px; margin-left: auto; }
.live-pill {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--muted);
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green); flex-shrink: 0;
  box-shadow: 0 0 0 0 rgba(34,197,94,.4);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%   { box-shadow: 0 0 0 0   rgba(34,197,94,.4); }
  70%  { box-shadow: 0 0 0 6px rgba(34,197,94,0); }
  100% { box-shadow: 0 0 0 0   rgba(34,197,94,0); }
}
.cd-num {
  font-variant-numeric: tabular-nums; font-weight: 700;
  color: var(--accent); min-width: 10px; text-align: center;
}

/* ── Summary bar ── */
.summary-bar {
  display: grid; grid-template-columns: repeat(6,1fr);
  background: var(--surface); border-bottom: 1px solid var(--border);
}
.scard {
  padding: 16px 20px; border-right: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 5px;
}
.scard:last-child { border-right: none; }
.sval {
  font-size: 22px; font-weight: 700; color: var(--text);
  font-variant-numeric: tabular-nums; letter-spacing: -.5px; line-height: 1.1;
}
.sval .green { color: var(--green); }
.slbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .6px; }

/* ── Analytics ── */
.analytics {
  background: var(--bg); border-bottom: 1px solid var(--border);
  padding: 14px 24px;
}
.analytics-inner { display: flex; gap: 40px; flex-wrap: wrap; }
.analytics-section { flex: 1; min-width: 200px; }
.analytics-label {
  font-size: 9px; text-transform: uppercase; letter-spacing: 1px;
  color: var(--muted); margin-bottom: 10px; font-weight: 600;
}
.top-list { display: flex; gap: 24px; flex-wrap: wrap; }
.top-item { display: flex; align-items: center; gap: 8px; }
.top-medal { font-size: 16px; }
.top-name { font-size: 13px; font-weight: 600; }
.top-coins { font-size: 12px; color: var(--muted); }
.perf-row { display: flex; gap: 24px; flex-wrap: wrap; }
.perf-m { }
.perf-v { font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
.perf-l { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; margin-top: 1px; }

/* ── Content area ── */
.content-area { padding: 16px 24px 80px; }
.view-controls { display: flex; justify-content: flex-end; margin-bottom: 16px; }
.view-btns {
  display: flex; border: 1px solid var(--border2); border-radius: 8px; overflow: hidden;
}
.view-btn {
  padding: 6px 14px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: none; background: transparent;
  color: var(--muted); transition: all .15s; font-family: inherit;
}
.view-btn:hover { color: var(--text); background: var(--surface2); }
.view-btn.active { background: var(--accent); color: #fff; }

/* ── Cards grid ── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px,1fr));
  gap: 16px;
}

/* ── Card ── */
.card {
  background: var(--surface); border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
  border-top: 2px solid transparent;
  padding: 16px; transition: box-shadow .15s;
  animation: fadeIn .3s ease;
}
.card.is-online { border-top-color: var(--accent); }
.card.is-offline { border-top-color: var(--red); }
.card:hover { box-shadow: 0 0 0 1px var(--border2); }
@keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }

.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.role-badge {
  width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff;
}
.rb-M { background: var(--red); }
.rb-S { background: var(--yellow); }
.rb-I { background: var(--blue); }
.rb-q { background: var(--muted); }
.card-info { flex: 1; min-width: 0; }
.card-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-uid { font-size: 10px; color: var(--muted); margin-top: 1px; }
.status-badge {
  padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .4px; white-space: nowrap; flex-shrink: 0;
}
.sb-Farming  { background: rgba(34,197,94,.13); color: var(--green);  border: 1px solid rgba(34,197,94,.28); }
.sb-Idle     { background: rgba(234,179,8,.1);  color: var(--yellow); border: 1px solid rgba(234,179,8,.25); }
.sb-Lobby    { background: rgba(59,130,246,.1); color: var(--blue);   border: 1px solid rgba(59,130,246,.25); }
.sb-Offline  { background: rgba(239,68,68,.1);  color: var(--red);    border: 1px solid rgba(239,68,68,.2); }

.card-metrics {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
  margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
}
.metric-val { font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.1; }
.metric-lbl { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .4px; margin-top: 2px; }

.bag-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.bag-lbl { font-size: 11px; color: var(--muted); white-space: nowrap; }
.bag-track { flex: 1; height: 5px; background: var(--surface2); border-radius: 3px; overflow: hidden; }
.bag-fill {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  transition: width .5s;
}
.bag-fill.full { background: var(--green); animation: bag-pulse 1.5s infinite; }
@keyframes bag-pulse { 0%,100%{opacity:1} 50%{opacity:.55} }
.bag-count { font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }

.mini-stats {
  display: grid; grid-template-columns: repeat(4,1fr); gap: 6px;
  margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
}
.mini-stat { background: var(--surface2); border-radius: 8px; padding: 6px 4px; text-align: center; }
.mini-val { font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; }
.mini-lbl { font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: .3px; margin-top: 1px; }

.toggles { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
.tog {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
  cursor: pointer; border: 1px solid; background: none;
  transition: all .12s; user-select: none; font-family: inherit;
}
.tog.on  { background: rgba(124,106,255,.13); border-color: rgba(124,106,255,.35); color: var(--accent2); }
.tog.off { background: var(--surface2); border-color: var(--border); color: var(--muted); }
.tog:hover { opacity: .8; }
.tog-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.tog.on  .tog-dot { background: var(--accent2); }
.tog.off .tog-dot { background: var(--muted); }
.pend-icon { font-size: 9px; opacity: .7; }

.card-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.btn {
  padding: 5px 12px; border-radius: 8px; font-size: 11px; font-weight: 600;
  cursor: pointer; border: 1px solid; background: none; transition: opacity .12s;
  white-space: nowrap; font-family: inherit;
}
.btn:hover { opacity: .78; }
.btn-ghost   { color: var(--text);   border-color: var(--border2); }
.btn-ghost:hover { background: var(--surface2); }
.btn-accent  { color: var(--accent2); border-color: rgba(124,106,255,.35); }
.btn-green   { color: var(--green);  border-color: rgba(34,197,94,.35); }
.btn-red     { color: var(--red);    border-color: rgba(239,68,68,.35); }
.btn-blue    { color: var(--blue);   border-color: rgba(59,130,246,.35); }

.inline-confirm { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: var(--muted); }
.icbtn { padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 600; cursor: pointer; border: 1px solid; background: none; font-family: inherit; }
.icbtn-y { color: var(--red);   border-color: rgba(239,68,68,.4); }
.icbtn-n { color: var(--muted); border-color: var(--border2); }

/* ── List view ── */
.list-wrap { overflow-x: auto; }
.list-tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.list-tbl th {
  padding: 10px 14px; text-align: left; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .5px; color: var(--muted);
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
.list-tbl td { padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.list-tbl tr:last-child td { border-bottom: none; }
.list-tbl tr:hover td { background: var(--surface2); }
.list-tbl tr.is-offline { color: var(--muted); }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); }

/* ── History tab ── */
.history-page { padding-bottom: 60px; }
.history-filters {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 12px 24px; border-bottom: 1px solid var(--border);
}
.flt-sel, .flt-inp, .flt-date {
  background: var(--surface); border: 1px solid var(--border2);
  border-radius: 8px; color: var(--text); padding: 7px 12px;
  font-size: 12px; outline: none; transition: border-color .15s; font-family: inherit;
}
.flt-sel:focus, .flt-inp:focus, .flt-date:focus { border-color: var(--accent); }
.flt-date { color-scheme: dark; }
.flt-inp { min-width: 190px; }
.btn-clr {
  padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border2);
  background: none; color: var(--muted); font-size: 12px; cursor: pointer;
  transition: all .15s; font-family: inherit;
}
.btn-clr:hover { color: var(--text); background: var(--surface2); }

.hist-tbl-wrap { padding: 0 24px; overflow-x: auto; }
.hist-tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.hist-tbl th {
  padding: 10px 12px; text-align: left; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .5px; color: var(--muted);
  border-bottom: 1px solid var(--border); white-space: nowrap; cursor: pointer;
  transition: color .12s; user-select: none;
}
.hist-tbl th:hover { color: var(--text); }
.hist-tbl th .si { margin-left: 4px; font-size: 9px; opacity: .35; }
.hist-tbl th.sorted-asc .si::after { content: ' ▲'; opacity: 1; }
.hist-tbl th.sorted-dsc .si::after { content: ' ▼'; opacity: 1; }
.hist-tbl th:not(.sorted-asc):not(.sorted-dsc) .si::after { content: ' ⬍'; }
.hist-tbl td { padding: 9px 12px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
.hist-tbl tr:nth-child(even) td { background: rgba(255,255,255,.018); }
.hist-tbl tr:hover td { background: var(--surface2); }
.hist-tbl tr:last-child td { border-bottom: none; }
.acc-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 7px; vertical-align: middle; flex-shrink: 0; }

.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 5px; padding: 16px 24px; flex-wrap: wrap;
}
.pg-btn {
  padding: 5px 11px; border-radius: 7px; border: 1px solid var(--border2);
  background: none; color: var(--muted); font-size: 12px; cursor: pointer;
  transition: all .12s; font-family: inherit;
}
.pg-btn:hover:not(:disabled) { color: var(--text); background: var(--surface2); }
.pg-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.pg-btn:disabled { opacity: .25; cursor: default; }
.pg-info { font-size: 12px; color: var(--muted); padding: 0 8px; }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.72);
  backdrop-filter: blur(4px); z-index: 1000;
  display: none; align-items: center; justify-content: center; padding: 20px;
}
.modal-overlay.open { display: flex; }
.modal-box {
  background: var(--surface); box-shadow: 0 0 0 1px var(--border2);
  border-radius: 16px; width: 100%; max-width: 680px; max-height: 82vh;
  display: flex; flex-direction: column;
  animation: modal-in .18s ease;
}
@keyframes modal-in { from { transform: scale(.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.modal-hdr {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.modal-title { font-size: 15px; font-weight: 600; }
.modal-close {
  width: 28px; height: 28px; border-radius: 6px;
  border: 1px solid var(--border2); background: none; color: var(--muted);
  cursor: pointer; font-size: 13px; transition: all .12s;
  display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: var(--surface2); color: var(--text); }
.modal-body { overflow-y: auto; flex: 1; }
.modal-stats { display: flex; border-bottom: 1px solid var(--border); }
.modal-stat { flex: 1; padding: 14px 20px; border-right: 1px solid var(--border); }
.modal-stat:last-child { border-right: none; }
.modal-stat-v { font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }
.modal-stat-l { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .4px; margin-top: 2px; }
.modal-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.modal-tbl th { padding: 9px 16px; text-align: left; font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); border-bottom: 1px solid var(--border); }
.modal-tbl td { padding: 9px 16px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
.modal-tbl tr:last-child td { border-bottom: none; }
.modal-tbl tr:hover td { background: var(--surface2); }
.now-dot { color: var(--green); font-size: 9px; font-weight: 700; margin-right: 4px; }

/* ── Toasts ── */
.toasts {
  position: fixed; bottom: 20px; right: 20px; z-index: 2000;
  display: flex; flex-direction: column; gap: 8px; pointer-events: none;
}
.toast {
  padding: 10px 16px; border-radius: 8px; font-size: 12px; font-weight: 500;
  border: 1px solid; backdrop-filter: blur(8px); pointer-events: auto;
  transform: translateX(calc(100% + 24px)); transition: transform .22s ease;
}
.toast.show { transform: translateX(0); }
.toast-s { background: rgba(34,197,94,.12);  border-color: rgba(34,197,94,.3);  color: var(--green); }
.toast-e { background: rgba(239,68,68,.12);  border-color: rgba(239,68,68,.3);  color: var(--red); }
.toast-i { background: rgba(124,106,255,.12); border-color: rgba(124,106,255,.3); color: var(--accent2); }

/* ── Empty ── */
.empty-state { text-align: center; padding: 70px 20px; color: var(--muted); font-size: 14px; }

/* ── Responsive ── */
@media (max-width:1100px) {
  .summary-bar { grid-template-columns: repeat(3,1fr); }
  .scard:nth-child(3) { border-right: none; }
}
@media (max-width:768px) {
  .summary-bar { grid-template-columns: repeat(2,1fr); }
  .scard:nth-child(2) { border-right: none; }
  .header { padding: 0 14px; }
  .content-area { padding: 12px 14px 60px; }
  .hist-tbl-wrap { padding: 0 14px; }
  .history-filters { padding: 10px 14px; }
  .analytics { padding: 12px 14px; }
  .cards-grid { grid-template-columns: 1fr; }
  .modal-stats { flex-direction: column; }
  .modal-stat { border-right: none; border-bottom: 1px solid var(--border); }
}
</style>
</head>
<body>

<header class="header">
  <div class="brand"><span class="brand-icon">⬡</span> Игровой Хаб</div>
  <nav class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('dashboard')">ММ2</button>
    <button class="nav-tab"        onclick="switchTab('history')">ММ2 История</button>
    <button class="nav-tab"        onclick="switchTab('pd')">Попрошайка</button>
    <button class="nav-tab"        onclick="switchTab('pd-history')">ПД История</button>
    <a class="nav-tab" href="/analytics" target="_blank" style="text-decoration:none">📊 Аналитика</a>
    <a class="nav-tab" href="/interactions" target="_blank" style="text-decoration:none">💬 Диалоги</a>
    <a class="nav-tab" href="/export" target="_blank" style="text-decoration:none">📥 Экспорт</a>
  </nav>
  <div class="header-right">
    <div class="live-pill">
      <div class="live-dot"></div>
      <span>Онлайн</span>
      <span class="cd-num" id="cd">5</span>
    </div>
  </div>
</header>

<!-- Dashboard -->
<div id="tab-dash">
  <div class="summary-bar" id="summary-bar"></div>
  <div class="analytics" id="analytics"></div>
  <div class="content-area">
    <div class="view-controls">
      <div class="view-btns">
        <button class="view-btn" id="vbtn-cards" onclick="switchView('cards')">&#8862; Карточки</button>
        <button class="view-btn" id="vbtn-list"  onclick="switchView('list')">&#9776; Список</button>
      </div>
    </div>
    <div id="cards-container"></div>
    <div id="list-container"  style="display:none"></div>
  </div>
</div>

<!-- History -->
<div id="tab-hist" style="display:none" class="history-page">
  <div class="summary-bar" id="hist-summary"></div>
  <div class="history-filters">
    <select class="flt-sel" id="flt-acc" onchange="histFilterChanged()">
      <option value="">Все аккаунты</option>
    </select>
    <input class="flt-inp" id="flt-srv" placeholder="Фильтр по ID сервера..." oninput="histFilterChanged()">
    <button class="btn-clr" onclick="clearHistFilters()">Сбросить</button>
  </div>
  <div class="hist-tbl-wrap">
    <table class="hist-tbl">
      <thead><tr>
        <th onclick="sortHist('account_name')">Аккаунт<span class="si" id="si-account_name"></span></th>
        <th onclick="sortHist('server_id')">Сервер<span class="si" id="si-server_id"></span></th>
        <th onclick="sortHist('started_at')">Начало<span class="si" id="si-started_at"></span></th>
        <th onclick="sortHist('duration')">Длительность<span class="si" id="si-duration"></span></th>
        <th onclick="sortHist('coins')">Монеты<span class="si" id="si-coins"></span></th>
        <th onclick="sortHist('coins_per_hour')">Монет/час<span class="si" id="si-coins_per_hour"></span></th>
      </tr></thead>
      <tbody id="hist-tbody"></tbody>
    </table>
  </div>
  <div class="pagination" id="hist-pg"></div>
</div>

<!-- Please Donate Dashboard -->
<div id="tab-pd" style="display:none">
  <div class="summary-bar" id="pd-summary-bar"></div>
  <div id="pd-period-row" style="background:var(--surface);border-bottom:1px solid var(--border);padding:8px 24px;display:flex;align-items:center;gap:8px;flex-wrap:wrap"></div>
  <div class="content-area">
    <div class="view-controls">
      <div class="view-btns">
        <button class="view-btn" id="pd-vbtn-cards" onclick="switchPdView('cards')">&#8862; Карточки</button>
        <button class="view-btn" id="pd-vbtn-list"  onclick="switchPdView('list')">&#9776; Список</button>
      </div>
    </div>
    <div id="pd-cards-container"></div>
    <div id="pd-list-container" style="display:none"></div>
  </div>
</div>

<!-- Please Donate History -->
<div id="tab-pd-hist" style="display:none" class="history-page">
  <div class="summary-bar" id="pd-hist-summary"></div>
  <div class="history-filters">
    <select class="flt-sel" id="pd-flt-acc" onchange="pdHistFilterChanged()">
      <option value="">Все аккаунты</option>
    </select>
    <input class="flt-inp" id="pd-flt-srv" placeholder="Фильтр по ID сервера..." oninput="pdHistFilterChanged()">
    <span style="font-size:11px;color:var(--muted)">С:</span>
    <input type="date" class="flt-date" id="pd-flt-from" onchange="pdHistFilterChanged()">
    <span style="font-size:11px;color:var(--muted)">По:</span>
    <input type="date" class="flt-date" id="pd-flt-to" onchange="pdHistFilterChanged()">
    <button class="btn-clr" onclick="clearPdHistFilters()">Сбросить</button>
  </div>
  <div class="hist-tbl-wrap">
    <table class="hist-tbl">
      <thead><tr>
        <th onclick="sortPdHist('account_name')">Аккаунт<span class="si" id="pdsi-account_name"></span></th>
        <th onclick="sortPdHist('server_id')">Сервер<span class="si" id="pdsi-server_id"></span></th>
        <th onclick="sortPdHist('started_at')">Начало<span class="si" id="pdsi-started_at"></span></th>
        <th onclick="sortPdHist('ended_at')">Конец<span class="si" id="pdsi-ended_at"></span></th>
        <th onclick="sortPdHist('duration')">Длительность<span class="si" id="pdsi-duration"></span></th>
        <th onclick="sortPdHist('approached')">Подошёл<span class="si" id="pdsi-approached"></span></th>
        <th onclick="sortPdHist('agreed')">Согласились<span class="si" id="pdsi-agreed"></span></th>
        <th onclick="sortPdHist('refused')">Отказали<span class="si" id="pdsi-refused"></span></th>
        <th onclick="sortPdHist('no_response')">Нет ответа<span class="si" id="pdsi-no_response"></span></th>
        <th onclick="sortPdHist('donations')">Донации<span class="si" id="pdsi-donations"></span></th>
        <th onclick="sortPdHist('robux_gross')">Чистые R$<span class="si" id="pdsi-robux_gross"></span></th>
        <th>Лог чата</th>
      </tr></thead>
      <tbody id="pd-hist-tbody"></tbody>
    </table>
  </div>
  <div class="pagination" id="pd-hist-pg"></div>
</div>

<!-- PD Modal -->
<div class="modal-overlay" id="pd-settings-modal" onclick="if(event.target===this)closePdSettings()">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-hdr">
      <div class="modal-title" id="pd-cfg-title">Настройки бота</div>
      <button class="modal-close" onclick="closePdSettings()">&#10005;</button>
    </div>
    <div class="modal-body" style="padding:20px">
      <input type="hidden" id="pd-cfg-aid">
      <div style="display:flex;flex-direction:column;gap:16px">

        <div>
          <label style="display:block;font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600;letter-spacing:.05em">МИН. ИГРОКОВ ДЛЯ ЗАХОДА</label>
          <input type="number" id="pd-cfg-min" min="1" max="24" value="4"
            style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 12px;font-size:14px">
          <div style="font-size:10px;color:var(--muted);margin-top:4px">Серверы с меньшим числом игроков пропускаются (по умолчанию: 4)</div>
        </div>

        <div>
          <label style="display:block;font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600;letter-spacing:.05em">МАКС. ИГРОКОВ ДЛЯ ЗАХОДА</label>
          <input type="number" id="pd-cfg-max" min="1" max="24" value="24"
            style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 12px;font-size:14px">
          <div style="font-size:10px;color:var(--muted);margin-top:4px">Серверы выше этого порога пропускаются (по умолчанию: 24)</div>
        </div>

        <div>
          <label style="display:block;font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600;letter-spacing:.05em">КУЛДАУН ПОВТОРНОГО ЗАХОДА (МИН.)</label>
          <input type="number" id="pd-cfg-cooldown" min="0" max="360" value="60"
            style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 12px;font-size:14px">
          <div style="font-size:10px;color:var(--muted);margin-top:4px">Не возвращаться на сервер указанное число минут (по умолчанию: 60)</div>
        </div>

        <div style="border-top:1px solid var(--border);padding-top:14px">
          <div style="font-size:11px;color:var(--muted);margin-bottom:8px;font-weight:600;letter-spacing:.05em">ИСТОРИЯ СЕРВЕРОВ</div>
          <button onclick="clearPdServerHistory(document.getElementById('pd-cfg-aid').value)"
            style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:var(--red);border-radius:8px;padding:8px 14px;cursor:pointer;font-size:13px;width:100%">
            🗑 Очистить историю серверов (бот забудет все посещённые)
          </button>
          <div style="font-size:10px;color:var(--muted);margin-top:4px">История очистится при следующем хопе бота</div>
        </div>

        <div style="display:flex;gap:10px;margin-top:4px">
          <button onclick="closePdSettings()"
            style="flex:1;background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:8px;padding:10px;cursor:pointer;font-size:13px">Отмена</button>
          <button onclick="savePdSettings()"
            style="flex:2;background:var(--accent);border:none;color:#fff;border-radius:8px;padding:10px;cursor:pointer;font-size:13px;font-weight:600">Сохранить</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="modal-overlay" id="pd-modal" onclick="if(event.target===this)closePdModal()">
  <div class="modal-box" style="max-width:820px">
    <div class="modal-hdr">
      <div class="modal-title" id="pd-modal-title">ПД История</div>
      <button class="modal-close" onclick="closePdModal()">&#10005;</button>
    </div>
    <!-- sub-tabs -->
    <div style="display:flex;gap:0;border-bottom:1px solid var(--border);padding:0 20px">
      <button id="pdmt-sessions" onclick="switchPdModalTab('sessions')"
        style="background:none;border:none;border-bottom:2px solid var(--accent);color:var(--text);padding:8px 16px;cursor:pointer;font-size:13px;font-weight:600">Сессии</button>
      <button id="pdmt-chatlog" onclick="switchPdModalTab('chatlog')"
        style="background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);padding:8px 16px;cursor:pointer;font-size:13px">Лог чата</button>
    </div>
    <div class="modal-body" id="pd-modal-body"></div>
    <div class="modal-body" id="pd-modal-chatlog" style="display:none"></div>
  </div>
</div>

<!-- Modal -->
<div class="modal-overlay" id="modal" onclick="handleModalBg(event)">
  <div class="modal-box">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-title">История</div>
      <button class="modal-close" onclick="closeModal()">&#10005;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<!-- Toasts -->
<div class="toasts" id="toasts"></div>

<script>
/* ── Constants ── */
var OFFLINE_THR  = 600;  // 10 min — generous buffer for hop + reconnect cycle
var REFRESH_MS   = 5000;
var HIST_PER_PAGE = 50;

/* ── State ── */
var allData   = {};
var pdData    = {};
var curTab    = localStorage.getItem('mm2_tab')    || 'dashboard';
var curView   = localStorage.getItem('mm2_view')   || 'cards';
var curPdView = localStorage.getItem('mm2_pd_view') || 'cards';
var cdVal     = 5;
var optimistic = {};

var histSortCol = 'started_at';
var histSortDir = -1;
var histPage    = 1;
var modalAccId  = null;

/* ── Utility ── */
function isOnline(a) { return (Date.now()/1000 - (a.last_seen||0)) < OFFLINE_THR; }
function trStatus(s) {
  return {'Farming':'Фармит','Idle':'Простой','Lobby':'Лобби','Offline':'Офлайн','Active':'Активен','Online':'Онлайн'}[s] || s;
}
function fmtN(n) { return Math.round(n||0).toLocaleString(); }
function fmtDur(s) {
  s = Math.floor(s||0);
  if (s < 60) return s + 's';
  var m = Math.floor(s/60), h = Math.floor(m/60);
  return h > 0 ? h + 'h ' + (m%60) + 'min' : m + 'min';
}
function fmtTime(ts) {
  if (!ts) return '—';
  var d = new Date(ts*1000);
  return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})
       + ' ' + d.toLocaleDateString([],{day:'2-digit',month:'2-digit'});
}
function fmtSrv(id) {
  if (!id) return '—';
  return id.length > 12 ? id.slice(0,6) + '…' + id.slice(-4) : id;
}
function esc(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function accentColor(name) {
  var h = 0;
  for (var i = 0; i < (name||'').length; i++) h = ((h<<5) - h + (name||'').charCodeAt(i)) | 0;
  return 'hsl(' + (Math.abs(h)%360) + ',58%,58%)';
}

/* ── Toast ── */
var _tid = 0;
function showToast(msg, type) {
  var id = ++_tid;
  var d = document.createElement('div');
  d.className = 'toast toast-' + (type||'i');
  d.textContent = msg;
  document.getElementById('toasts').appendChild(d);
  requestAnimationFrame(function() { requestAnimationFrame(function() { d.classList.add('show'); }); });
  setTimeout(function() {
    d.classList.remove('show');
    setTimeout(function() { d.remove(); }, 300);
  }, 3000);
}

/* ── Countdown ── */
function startCountdown() {
  cdVal = REFRESH_MS / 1000;
  updateCd();
  var t = setInterval(function() {
    cdVal--;
    updateCd();
    if (cdVal <= 0) {
      clearInterval(t);
      doRefresh(function() { startCountdown(); });
    }
  }, 1000);
}
function updateCd() {
  var el = document.getElementById('cd');
  if (el) el.textContent = cdVal > 0 ? cdVal : '↻';
}

/* ── Fetch ── */
function doRefresh(cb) {
  var p1 = fetch('/accounts').then(function(r) { return r.json(); }).then(function(data) {
    for (var id in optimistic) {
      var acc = data[id];
      if (!acc || !acc.state) continue;
      for (var k in optimistic[id]) {
        if (acc.state[k] === optimistic[id][k]) delete optimistic[id][k];
      }
      if (!Object.keys(optimistic[id]).length) delete optimistic[id];
    }
    allData = data;
  }).catch(function() {});
  var p2 = fetch('/pd_accounts').then(function(r) { return r.json(); }).then(function(data) {
    pdData = data;
  }).catch(function() {});
  Promise.all([p1, p2]).then(function() {
    if (curTab === 'dashboard') { renderSummary(); renderAnalytics(); renderView(); }
    else if (curTab === 'history') renderHistPage();
    else if (curTab === 'pd') { renderPdSummary(); renderPdView(); }
    else if (curTab === 'pd-history') renderPdHistPage();
    if (modalAccId) renderModal(modalAccId);
    if (pdModalAccId) renderPdModal(pdModalAccId);
    if (cb) cb();
  });
}

/* ── Tab / view ── */
function switchTab(tab) {
  curTab = tab;
  localStorage.setItem('mm2_tab', tab);
  var tabs = document.querySelectorAll('.nav-tab');
  tabs[0].classList.toggle('active', tab === 'dashboard');
  tabs[1].classList.toggle('active', tab === 'history');
  tabs[2].classList.toggle('active', tab === 'pd');
  tabs[3].classList.toggle('active', tab === 'pd-history');
  document.getElementById('tab-dash').style.display    = tab === 'dashboard'  ? '' : 'none';
  document.getElementById('tab-hist').style.display    = tab === 'history'    ? '' : 'none';
  document.getElementById('tab-pd').style.display      = tab === 'pd'         ? '' : 'none';
  document.getElementById('tab-pd-hist').style.display = tab === 'pd-history' ? '' : 'none';
  if (tab === 'history')    renderHistPage();
  else if (tab === 'pd')    { renderPdSummary(); renderPdView(); }
  else if (tab === 'pd-history') renderPdHistPage();
  else { renderSummary(); renderAnalytics(); renderView(); }
}
function switchView(v) {
  curView = v;
  localStorage.setItem('mm2_view', v);
  document.getElementById('vbtn-cards').classList.toggle('active', v === 'cards');
  document.getElementById('vbtn-list').classList.toggle('active',  v === 'list');
  document.getElementById('cards-container').style.display = v === 'cards' ? '' : 'none';
  document.getElementById('list-container').style.display  = v === 'list'  ? '' : 'none';
  renderView();
}
function renderView() {
  if (curView === 'cards') renderCards();
  else renderList();
}
function switchPdView(v) {
  curPdView = v;
  localStorage.setItem('mm2_pd_view', v);
  document.getElementById('pd-vbtn-cards').classList.toggle('active', v === 'cards');
  document.getElementById('pd-vbtn-list').classList.toggle('active',  v === 'list');
  document.getElementById('pd-cards-container').style.display = v === 'cards' ? '' : 'none';
  document.getElementById('pd-list-container').style.display  = v === 'list'  ? '' : 'none';
  renderPdView();
}
function renderPdView() {
  if (curPdView === 'cards') renderPdCards();
  else renderPdList();
}

/* ── Summary ── */
function renderSummary() {
  var now = Date.now()/1000;
  var accs = Object.values(allData);
  var totalCoins = 0, online = 0, totalRounds = 0, totalHops = 0, totalChr = 0;
  for (var i = 0; i < accs.length; i++) {
    var a = accs[i];
    totalCoins  += (a.coins_total || 0);
    totalRounds += (a.rounds || 0);
    totalHops   += (a.hops   || 0);
    if (isOnline(a)) {
      online++;
      var cs = a.current_session;
      if (cs && cs.started_at) {
        var dur = now - cs.started_at;
        if (dur > 120) totalChr += Math.round((cs.coins||0) / (dur/3600));
      }
    }
  }
  document.getElementById('summary-bar').innerHTML =
    '<div class="scard"><div class="sval">' + accs.length + '</div><div class="slbl">Аккаунты</div></div>' +
    '<div class="scard"><div class="sval"><span class="green">' + online + '</span> / ' + accs.length + '</div><div class="slbl">Онлайн</div></div>' +
    '<div class="scard"><div class="sval">' + fmtN(totalCoins) + '</div><div class="slbl">Монеты</div></div>' +
    '<div class="scard"><div class="sval">' + (totalChr ? '~' + fmtN(totalChr) : '—') + '</div><div class="slbl">Монет / час</div></div>' +
    '<div class="scard"><div class="sval">' + totalRounds + '</div><div class="slbl">Раунды</div></div>' +
    '<div class="scard"><div class="sval">' + totalHops + '</div><div class="slbl">Хопы</div></div>';
}

/* ── Analytics ── */
function renderAnalytics() {
  var now = Date.now()/1000;
  var accs = Object.values(allData);
  var sorted = accs.slice().sort(function(a,b) { return (b.coins_total||0)-(a.coins_total||0); });
  var medals = ['🥇','🥈','🥉'];
  var topHtml = sorted.slice(0,3).map(function(a,i) {
    return '<div class="top-item"><span class="top-medal">' + medals[i] + '</span>' +
           '<span class="top-name">' + esc(a.name||'?') + '</span>' +
           '<span class="top-coins">' + fmtN(a.coins_total||0) + ' 🪙</span></div>';
  }).join('');

  var onlineAccs = accs.filter(isOnline);
  var avgBag = 0, bestName = '', bestChr = 0, farming = 0;
  if (onlineAccs.length) {
    avgBag = Math.round(onlineAccs.reduce(function(s,a){return s+(a.bag||0);},0) / onlineAccs.length / 40 * 100);
    farming = onlineAccs.filter(function(a){return a.status==='Farming';}).length;
    for (var i = 0; i < onlineAccs.length; i++) {
      var a = onlineAccs[i], cs = a.current_session;
      if (cs && cs.started_at) {
        var dur = now - cs.started_at;
        if (dur > 120) {
          var chr = Math.round((cs.coins||0)/(dur/3600));
          if (chr > bestChr) { bestChr = chr; bestName = a.name||'?'; }
        }
      }
    }
  }
  document.getElementById('analytics').innerHTML =
    '<div class="analytics-inner">' +
      '<div class="analytics-section"><div class="analytics-label">Лучшие фермеры</div>' +
        '<div class="top-list">' + (topHtml || '<span style="color:var(--muted);font-size:12px">Нет данных</span>') + '</div>' +
      '</div>' +
      '<div class="analytics-section"><div class="analytics-label">Производительность</div>' +
        '<div class="perf-row">' +
          '<div class="perf-m"><div class="perf-v">' + avgBag + '%</div><div class="perf-l">Ср. заполнение сумки</div></div>' +
          '<div class="perf-m"><div class="perf-v" style="max-width:180px;overflow:hidden;text-overflow:ellipsis">' +
            (bestChr ? esc(bestName) + ' ~' + fmtN(bestChr) + '/ч' : '—') +
          '</div><div class="perf-l">Лучших монет/час</div></div>' +
          '<div class="perf-m"><div class="perf-v">' + farming + '</div><div class="perf-l">Фармят сейчас</div></div>' +
        '</div>' +
      '</div>' +
    '</div>';
}

/* ── Effective toggle state ── */
function effState(id, key, serverVal) {
  if (optimistic[id] && optimistic[id][key] !== undefined) return optimistic[id][key];
  return serverVal !== undefined ? serverVal : true;
}

/* ── Cards ── */
function renderCards() {
  var now = Date.now()/1000;
  var accs = Object.values(allData).sort(function(a,b) {
    var ao = isOnline(a), bo = isOnline(b);
    if (ao && !bo) return -1; if (!ao && bo) return 1;
    return (b.coins_total||0) - (a.coins_total||0);
  });
  var c = document.getElementById('cards-container');
  if (!accs.length) {
    c.innerHTML = '<div class="empty-state">Аккаунтов ещё нет. Запустите скрипт для начала работы.</div>';
    return;
  }
  c.innerHTML = '<div class="cards-grid">' + accs.map(function(a) { return buildCard(a, now); }).join('') + '</div>';
}

function buildCard(a, now) {
  var id  = a.id || '';
  var off = !isOnline(a);
  var cs  = a.current_session || {};
  var sc  = cs.coins || 0;
  var dur = cs.started_at ? now - cs.started_at : 0;
  var chr = dur > 120 ? Math.round(sc/(dur/3600)) : 0;
  var r   = a.role || 'I';
  var bag = a.bag  || 0;
  var pct = Math.min(100, Math.round(bag/40*100));
  var st  = a.state || {};
  var pnd = a.pending_commands || {};
  var sn  = (a.sessions||[]).length;
  var skey = off ? 'Offline' : (a.status||'Lobby');
  var rbCls = r==='M' ? 'rb-M' : r==='S' ? 'rb-S' : r==='I' ? 'rb-I' : 'rb-q';

  var SK = ['CoinFarm','Combat','NoClip','AutoReset','ServerHop','AntiFling'];
  var SL = {CoinFarm:'Фарм',Combat:'Бой',NoClip:'НоКлип',AutoReset:'АвтоСброс',ServerHop:'Хоп',AntiFling:'АнтиКидок'};
  var toggs = SK.map(function(k) {
    var val = effState(id, k, st[k]);
    var isPend = pnd[k] !== undefined && !(optimistic[id] && optimistic[id][k] !== undefined);
    return '<button class="tog ' + (val?'on':'off') + '" onclick="toggleKey(' + JSON.stringify(id) + ',' + JSON.stringify(k) + ',' + val + ')">' +
           '<span class="tog-dot"></span>' + SL[k] + (isPend ? '<span class="pend-icon">⏳</span>' : '') +
           '</button>';
  }).join('');

  return '<div class="card ' + (off?'is-offline':'is-online') + '">' +
    '<div class="card-head">' +
      '<div class="role-badge ' + rbCls + '">' + esc(r) + '</div>' +
      '<div class="card-info">' +
        '<div class="card-name">' + esc(a.name||'Неизвестен') + '</div>' +
        '<div class="card-uid">uid: ' + esc(id) + '</div>' +
      '</div>' +
      '<span class="status-badge sb-' + skey + '">' + trStatus(skey) + '</span>' +
    '</div>' +

    '<div class="card-metrics">' +
      '<div><div class="metric-val">' + fmtN(a.coins_total||0) + '</div><div class="metric-lbl">За всё время</div></div>' +
      '<div><div class="metric-val">' + fmtN(sc) + '</div><div class="metric-lbl">Этот сервер</div></div>' +
      '<div><div class="metric-val">' + (chr ? '~'+fmtN(chr) : '—') + '</div><div class="metric-lbl">Монет / час</div></div>' +
    '</div>' +

    '<div class="bag-row">' +
      '<span class="bag-lbl">Сумка</span>' +
      '<div class="bag-track"><div class="bag-fill' + (a.bag_full?' full':'') + '" style="width:' + pct + '%"></div></div>' +
      '<span class="bag-count">' + bag + '/40</span>' +
    '</div>' +

    '<div class="mini-stats">' +
      '<div class="mini-stat"><div class="mini-val">' + (a.rounds||0) + '</div><div class="mini-lbl">Раунды</div></div>' +
      '<div class="mini-stat"><div class="mini-val">' + (a.flings||0) + '</div><div class="mini-lbl">Кидки</div></div>' +
      '<div class="mini-stat"><div class="mini-val">' + (a.hops||0)   + '</div><div class="mini-lbl">Хопы</div></div>' +
      '<div class="mini-stat"><div class="mini-val">' + sn            + '</div><div class="mini-lbl">Сессии</div></div>' +
    '</div>' +

    '<div class="toggles">' + toggs + '</div>' +

    '<div class="card-actions">' +
      '<button class="btn btn-accent" onclick="doForceHop(' + JSON.stringify(id) + ')">&#x27F3; Принудит. хоп</button>' +
      '<button class="btn btn-green"  onclick="doStartAll(' + JSON.stringify(id) + ')">&#x25B6; Запустить всё</button>' +
      '<button class="btn btn-red"    onclick="doStopAll('  + JSON.stringify(id) + ')">&#x25A0; Остановить всё</button>' +
    '</div>' +
    '<div class="card-actions">' +
      '<button class="btn btn-blue"  onclick="openModal(' + JSON.stringify(id) + ')">&#x1F4CB; История</button>' +
      '<span id="rst-' + id + '">' +
        '<button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" onclick="confirmReset(' + JSON.stringify(id) + ')">&#x1F5D1; Сбросить</button>' +
      '</span>' +
    '</div>' +
  '</div>';
}

/* ── List ── */
function renderList() {
  var now = Date.now()/1000;
  var accs = Object.values(allData).sort(function(a,b) {
    var ao = isOnline(a), bo = isOnline(b);
    if (ao && !bo) return -1; if (!ao && bo) return 1;
    return (b.coins_total||0) - (a.coins_total||0);
  });
  var c = document.getElementById('list-container');
  if (!accs.length) {
    c.innerHTML = '<div class="empty-state">Аккаунтов ещё нет.</div>';
    return;
  }
  var rows = accs.map(function(a) {
    var off = !isOnline(a);
    var cs  = a.current_session || {};
    var sc  = cs.coins || 0;
    var dur = cs.started_at ? now - cs.started_at : 0;
    var chr = dur > 120 ? Math.round(sc/(dur/3600)) : 0;
    var r   = a.role || 'I';
    var skey = off ? 'Offline' : (a.status||'Lobby');
    var farmOn = effState(a.id, 'CoinFarm', (a.state||{}).CoinFarm);
    var col = accentColor(a.name||'?');
    var rbCls = r==='M' ? 'rb-M' : r==='S' ? 'rb-S' : r==='I' ? 'rb-I' : 'rb-q';
    var bag = a.bag||0, pct = Math.min(100, Math.round(bag/40*100));
    return '<tr class="' + (off?'is-offline':'') + '">' +
      '<td><div style="display:flex;align-items:center;gap:8px">' +
        '<span style="width:8px;height:8px;border-radius:50%;background:' + col + ';display:inline-block;flex-shrink:0"></span>' +
        '<div><div style="font-weight:600;font-size:12px">' + esc(a.name||'?') + '</div>' +
             '<div style="font-size:10px;color:var(--muted)">' + esc(a.id) + '</div></div>' +
      '</div></td>' +
      '<td><div class="role-badge ' + rbCls + '" style="width:22px;height:22px;font-size:9px">' + esc(r) + '</div></td>' +
      '<td><span class="status-badge sb-' + skey + '">' + trStatus(skey) + '</span></td>' +
      '<td style="font-weight:600">' + fmtN(a.coins_total||0) + '</td>' +
      '<td>' + fmtN(sc) + '</td>' +
      '<td style="color:var(--accent2)">' + (chr ? '~'+fmtN(chr) : '—') + '</td>' +
      '<td><div style="display:flex;align-items:center;gap:6px">' +
        '<div class="bag-track" style="width:55px"><div class="bag-fill' + (a.bag_full?' full':'') + '" style="width:' + pct + '%"></div></div>' +
        '<span style="font-size:10px;color:var(--muted)">' + bag + '/40</span>' +
      '</div></td>' +
      '<td>' + (a.rounds||0) + '</td>' +
      '<td>' + (a.hops||0)   + '</td>' +
      '<td><div style="display:flex;gap:5px">' +
        '<button class="tog ' + (farmOn?'on':'off') + '" style="font-size:10px;padding:3px 9px" onclick="toggleKey(' + JSON.stringify(a.id) + ',' + JSON.stringify('CoinFarm') + ',' + farmOn + ')">' +
          (farmOn?'Фарм ВКЛ':'Фарм ВЫКЛ') +
        '</button>' +
        '<button class="btn btn-accent" style="padding:3px 9px;font-size:10px" onclick="doForceHop(' + JSON.stringify(a.id) + ')">&#x27F3; Hop</button>' +
      '</div></td>' +
    '</tr>';
  }).join('');
  c.innerHTML = '<div class="list-wrap"><table class="list-tbl"><thead><tr>' +
    '<th>Аккаунт</th><th>Роль</th><th>Статус</th>' +
    '<th>За всё время</th><th>Этот сервер</th><th>Монет/час</th>' +
    '<th>Сумка</th><th>Раунды</th><th>Хопы</th><th>Управление</th>' +
  '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

/* ── Controls ── */
function sendCtrl(id, patch) {
  return fetch('/control', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(Object.assign({id: id}, patch))
  }).then(function(r) { if (!r.ok) throw new Error(r.status); });
}

function toggleKey(id, key, curVal) {
  var newVal = !curVal;
  if (!optimistic[id]) optimistic[id] = {};
  optimistic[id][key] = newVal;
  renderView();
  sendCtrl(id, (function(o){o[key]=newVal;return o;})({})).catch(function() {
    delete optimistic[id][key];
    showToast('Command error', 'e');
    renderView();
  });
}

function doForceHop(id) {
  sendCtrl(id, {ForceHop: true})
    .then(function() { showToast('Принудительный хоп отправлен!', 's'); })
    .catch(function() { showToast('Ошибка отправки команды', 'e'); });
}

function doStartAll(id) {
  var patch = {CoinFarm:true,Combat:true,NoClip:true,AutoReset:true,ServerHop:true,AntiFling:true};
  if (!optimistic[id]) optimistic[id] = {};
  Object.assign(optimistic[id], patch);
  renderView();
  sendCtrl(id, patch)
    .then(function() { showToast('Всё запущено', 's'); })
    .catch(function() {
      ['CoinFarm','Combat','NoClip','AutoReset','ServerHop','AntiFling'].forEach(function(k){delete optimistic[id][k];});
      showToast('Ошибка', 'e'); renderView();
    });
}

function doStopAll(id) {
  var patch = {CoinFarm:false,Combat:false,NoClip:false,AutoReset:false,ServerHop:false,AntiFling:false};
  if (!optimistic[id]) optimistic[id] = {};
  Object.assign(optimistic[id], patch);
  renderView();
  sendCtrl(id, patch)
    .then(function() { showToast('Всё остановлено', 's'); })
    .catch(function() {
      ['CoinFarm','Combat','NoClip','AutoReset','ServerHop','AntiFling'].forEach(function(k){delete optimistic[id][k];});
      showToast('Ошибка', 'e'); renderView();
    });
}

function confirmReset(id) {
  var el = document.getElementById('rst-' + id);
  if (!el) return;
  el.innerHTML = '<span class="inline-confirm">Точно? ' +
    '<button class="icbtn icbtn-y" onclick="doReset(' + JSON.stringify(id) + ')">Да</button> ' +
    '<button class="icbtn icbtn-n" onclick="cancelReset(' + JSON.stringify(id) + ')">Нет</button>' +
    '</span>';
}

function doReset(id) {
  fetch('/reset/' + id, {method:'DELETE'})
    .then(function() { showToast('Статистика сброшена', 's'); })
    .catch(function() { showToast('Ошибка сброса', 'e'); });
  cancelReset(id);
}

function cancelReset(id) {
  var el = document.getElementById('rst-' + id);
  if (!el) return;
  el.innerHTML = '<button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" onclick="confirmReset(' + JSON.stringify(id) + ')">&#x1F5D1; Сбросить</button>';
}

/* ── Modal ── */
function openModal(id) {
  modalAccId = id;
  renderModal(id);
  document.getElementById('modal').classList.add('open');
}
function closeModal() {
  document.getElementById('modal').classList.remove('open');
  modalAccId = null;
}
function handleModalBg(e) { if (e.target === document.getElementById('modal')) closeModal(); }

function renderModal(id) {
  var a = allData[id]; if (!a) return;
  var now = Date.now()/1000;
  var sessions = (a.sessions||[]).slice().reverse();
  var cs = a.current_session||{};
  var totalSess = sessions.length + (cs.server_id ? 1 : 0);
  var totalCoins = sessions.reduce(function(s,x){return s+(x.coins||0);},0) + (cs.coins||0);
  var avgChr = sessions.length ? Math.round(sessions.reduce(function(s,x){return s+(x.coins_per_hour||0);},0)/sessions.length) : 0;

  document.getElementById('modal-title').textContent = 'История: ' + (a.name||id);

  var rows = '';
  if (cs.server_id) {
    var dur = now - (cs.started_at||now);
    var chr = dur > 120 ? Math.round((cs.coins||0)/(dur/3600)) : 0;
    rows += '<tr>' +
      '<td><span class="now-dot">● Сейчас</span></td>' +
      '<td class="mono" title="' + esc(cs.server_id) + '">' + fmtSrv(cs.server_id) + '</td>' +
      '<td>' + fmtTime(cs.started_at) + '</td>' +
      '<td>' + fmtDur(dur) + '</td>' +
      '<td style="font-weight:600">' + fmtN(cs.coins||0) + '</td>' +
      '<td style="color:var(--accent2)">' + (chr ? '~'+fmtN(chr) : '—') + '</td>' +
    '</tr>';
  }
  sessions.forEach(function(s, i) {
    rows += '<tr>' +
      '<td style="color:var(--muted)">' + (sessions.length-i) + '</td>' +
      '<td class="mono" title="' + esc(s.server_id||'') + '">' + fmtSrv(s.server_id) + '</td>' +
      '<td>' + fmtTime(s.started_at) + '</td>' +
      '<td>' + fmtDur(s.duration) + '</td>' +
      '<td style="font-weight:600">' + fmtN(s.coins||0) + '</td>' +
      '<td style="color:var(--accent2)">' + (s.coins_per_hour ? '~'+fmtN(s.coins_per_hour) : '—') + '</td>' +
    '</tr>';
  });
  if (!rows) rows = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--muted)">Сессий ещё нет</td></tr>';

  document.getElementById('modal-body').innerHTML =
    '<div class="modal-stats">' +
      '<div class="modal-stat"><div class="modal-stat-v">' + totalSess + '</div><div class="modal-stat-l">Всего сессий</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + fmtN(totalCoins) + '</div><div class="modal-stat-l">Всего монет</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + (avgChr?'~'+fmtN(avgChr):'—') + '</div><div class="modal-stat-l">Ср. монет/час</div></div>' +
    '</div>' +
    '<table class="modal-tbl"><thead><tr>' +
      '<th>#</th><th>Сервер</th><th>Начало</th><th>Длительность</th><th>Монеты</th><th>Монет/час</th>' +
    '</tr></thead><tbody>' + rows + '</tbody></table>';
}

document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeModal(); });

/* ── History tab ── */
function renderHistPage() {
  var all = [];
  for (var id in allData) {
    var acc = allData[id];
    (acc.sessions||[]).forEach(function(s) {
      all.push(Object.assign({}, s, {account_id: id, account_name: acc.name||id}));
    });
  }

  /* update account dropdown */
  var sel = document.getElementById('flt-acc');
  var curSel = sel.value;
  var opts = '<option value="">Все аккаунты (' + all.length + ' сессий)</option>';
  for (var id in allData) {
    var nm = allData[id].name || id;
    opts += '<option value="' + id + '"' + (id===curSel?' selected':'') + '>' + esc(nm) + '</option>';
  }
  sel.innerHTML = opts;

  var fAcc = document.getElementById('flt-acc').value;
  var fSrv = (document.getElementById('flt-srv').value||'').toLowerCase();
  var rows = all.filter(function(r) {
    if (fAcc && r.account_id !== fAcc) return false;
    if (fSrv && !(r.server_id||'').toLowerCase().includes(fSrv)) return false;
    return true;
  });

  rows.sort(function(a,b) {
    var av = a[histSortCol] != null ? a[histSortCol] : 0;
    var bv = b[histSortCol] != null ? b[histSortCol] : 0;
    if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv||'').toLowerCase(); }
    return av < bv ? histSortDir : av > bv ? -histSortDir : 0;
  });

  /* hist summary */
  var n = rows.length;
  var tc = rows.reduce(function(s,r){return s+(r.coins||0);},0);
  var avgDur = n ? rows.reduce(function(s,r){return s+(r.duration||0);},0)/n : 0;
  var avgChr = n ? Math.round(rows.reduce(function(s,r){return s+(r.coins_per_hour||0);},0)/n) : 0;
  document.getElementById('hist-summary').innerHTML =
    '<div class="scard"><div class="sval">' + n + '</div><div class="slbl">Сессии</div></div>' +
    '<div class="scard"><div class="sval">' + fmtN(tc) + '</div><div class="slbl">Всего монет</div></div>' +
    '<div class="scard"><div class="sval">' + (n?fmtDur(Math.round(avgDur)):'—') + '</div><div class="slbl">Ср. длительность</div></div>' +
    '<div class="scard"><div class="sval">' + (avgChr?'~'+fmtN(avgChr):'—') + '</div><div class="slbl">Ср. монет/час</div></div>';

  /* sort icons */
  ['account_name','server_id','started_at','duration','coins','coins_per_hour'].forEach(function(col) {
    var el = document.getElementById('si-'+col);
    if (!el) return;
    var th = el.parentElement;
    th.classList.remove('sorted-asc','sorted-dsc');
    if (col === histSortCol) th.classList.add(histSortDir===1?'sorted-asc':'sorted-dsc');
  });

  /* paginate */
  var total = rows.length;
  var totalPages = Math.max(1, Math.ceil(total/HIST_PER_PAGE));
  histPage = Math.min(histPage, totalPages);
  var sl = rows.slice((histPage-1)*HIST_PER_PAGE, histPage*HIST_PER_PAGE);

  var tbody = document.getElementById('hist-tbody');
  if (!sl.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted)">Сессий не найдено</td></tr>';
  } else {
    tbody.innerHTML = sl.map(function(r) {
      var col = accentColor(r.account_name||'?');
      return '<tr>' +
        '<td><span class="acc-dot" style="background:' + col + '"></span>' + esc(r.account_name) + '</td>' +
        '<td class="mono" title="' + esc(r.server_id||'') + '">' + fmtSrv(r.server_id) + '</td>' +
        '<td>' + fmtTime(r.started_at) + '</td>' +
        '<td>' + fmtDur(r.duration) + '</td>' +
        '<td style="font-weight:600">' + fmtN(r.coins||0) + '</td>' +
        '<td style="color:var(--accent2)">' + (r.coins_per_hour?'~'+fmtN(r.coins_per_hour):'—') + '</td>' +
      '</tr>';
    }).join('');
  }

  /* pagination */
  if (totalPages <= 1) { document.getElementById('hist-pg').innerHTML = ''; return; }
  var pg = '';
  pg += '<button class="pg-btn" ' + (histPage<=1?'disabled':'onclick="prevHistPage()"') + '>&#x2190; Назад</button>';
  var st = Math.max(1, histPage-2), en = Math.min(totalPages, histPage+2);
  if (st > 1) pg += '<button class="pg-btn" onclick="gotoHistPage(1)">1</button>' + (st>2?'<span class="pg-info">…</span>':'');
  for (var i = st; i <= en; i++) {
    pg += '<button class="pg-btn' + (i===histPage?' active':'') + '" onclick="gotoHistPage(' + i + ')">' + i + '</button>';
  }
  if (en < totalPages) pg += (en<totalPages-1?'<span class="pg-info">…</span>':'') + '<button class="pg-btn" onclick="gotoHistPage(' + totalPages + ')">' + totalPages + '</button>';
  pg += '<span class="pg-info">Стр. ' + histPage + ' из ' + totalPages + '</span>';
  pg += '<button class="pg-btn" ' + (histPage>=totalPages?'disabled':'onclick="nextHistPage()"') + '>Вперёд &#x2192;</button>';
  document.getElementById('hist-pg').innerHTML = pg;
}

function sortHist(col) {
  histSortDir = col === histSortCol ? -histSortDir : -1;
  histSortCol = col;
  histPage = 1;
  renderHistPage();
}
function histFilterChanged() { histPage = 1; renderHistPage(); }
function clearHistFilters() {
  document.getElementById('flt-acc').value = '';
  document.getElementById('flt-srv').value = '';
  histPage = 1;
  renderHistPage();
}
function gotoHistPage(n) { histPage = n; renderHistPage(); }
function prevHistPage()  { histPage--; renderHistPage(); }
function nextHistPage()  { histPage++; renderHistPage(); }

/* ══════════════════════════════════════════
   PLEASE DONATE SECTION
   ══════════════════════════════════════════ */

var pdModalAccId = null;
var pdHistSortCol = 'started_at';
var pdHistSortDir = -1;
var pdHistPage = 1;
var pdPeriod = localStorage.getItem('pd_period') || 'all';

function pdIsOnline(a) { return (Date.now()/1000 - (a.last_seen||0)) < OFFLINE_THR; }

/* ── PD period-filtered session totals ── */
function getPdPeriodStats(period) {
  var now = Date.now() / 1000;
  var cutoff = 0;
  if (period === 'today') {
    var d = new Date(); d.setHours(0,0,0,0); cutoff = d.getTime()/1000;
  } else if (period === '7d')  { cutoff = now - 7  * 86400; }
  else if (period === '30d')   { cutoff = now - 30 * 86400; }

  var totApp=0, totAgr=0, totRef=0, totNr=0, totDon=0, totGross=0, totDur=0;
  for (var id in pdData) {
    var acc = pdData[id];
    if (period === 'all') {
      // Use pre-accumulated all-time account totals (most accurate)
      totApp   += (acc.approached  || 0);
      totAgr   += (acc.agreed      || 0);
      totRef   += (acc.refused     || 0);
      totNr    += (acc.no_response || 0);
      totDon   += (acc.donations   || 0);
      totGross += (acc.robux_gross || 0);
      // estimate duration from session_start
      var start = acc.session_start || acc.created_at || 0;
      if (start > 0) totDur += now - start;
    } else {
      // Sum from per-server sessions
      var sessions = (acc.sessions || []).filter(function(s) {
        return (s.started_at || 0) >= cutoff;
      });
      for (var j = 0; j < sessions.length; j++) {
        var s = sessions[j];
        totApp   += Math.max(0, (s.approached  ||0) - (s.snap_app  ||0));
        totAgr   += Math.max(0, (s.agreed      ||0) - (s.snap_agr  ||0));
        totRef   += Math.max(0, (s.refused     ||0) - (s.snap_ref  ||0));
        totNr    += Math.max(0, (s.no_response ||0) - (s.snap_nr   ||0));
        totDon   += Math.max(0, (s.donations   ||0) - (s.snap_don  ||0));
        totGross += Math.max(0, (s.robux_gross ||0) - (s.snap_gross||0));
        totDur   += (s.duration || 0);
      }
      // Current active session if within period
      var cs = acc.current_session || {};
      if (cs.server_id && (cs.started_at || 0) >= cutoff) {
        totApp   += Math.max(0, (cs.approached  ||0) - (cs.snap_app  ||0));
        totAgr   += Math.max(0, (cs.agreed      ||0) - (cs.snap_agr  ||0));
        totRef   += Math.max(0, (cs.refused     ||0) - (cs.snap_ref  ||0));
        totNr    += Math.max(0, (cs.no_response ||0) - (cs.snap_nr   ||0));
        totDon   += Math.max(0, (cs.donations   ||0) - (cs.snap_don  ||0));
        totGross += Math.max(0, (cs.robux_gross ||0) - (cs.snap_gross||0));
        totDur   += now - (cs.started_at || now);
      }
    }
  }
  return {app:totApp, agr:totAgr, ref:totRef, nr:totNr, don:totDon, gross:totGross, dur:totDur};
}

/* ── PD Summary ── */
function renderPdSummary() {
  var accs = Object.values(pdData);
  var now = Date.now() / 1000;
  var online = 0;

  // Current-server live totals (always all online bots, independent of period)
  var csApp = 0, csAgr = 0, csRef = 0, csNr = 0, csDon = 0, csGrossAll = 0;
  var totHops = 0;
  var sevenDaysAgo = Date.now()/1000 - 7*86400;
  for (var i = 0; i < accs.length; i++) {
    var a = accs[i];
    var isOn = pdIsOnline(a);
    if (isOn) online++;
    // Only count hops for bots active in last 7 days and with sane values (<100k)
    var bHops = a.hops || 0;
    if ((a.last_seen || 0) >= sevenDaysAgo && bHops < 100000) {
      totHops += bHops;
    }
    if (isOn) {
      var cs = a.current_session || {};
      csApp      += Math.max(0, (cs.approached  || 0) - (cs.snap_app  || 0));
      csAgr      += Math.max(0, (cs.agreed      || 0) - (cs.snap_agr  || 0));
      csRef      += Math.max(0, (cs.refused     || 0) - (cs.snap_ref  || 0));
      csNr       += Math.max(0, (cs.no_response || 0) - (cs.snap_nr   || 0));
      csDon      += Math.max(0, (cs.donations   || 0) - (cs.snap_don  || 0));
      csGrossAll += Math.max(0, (cs.robux_gross || 0) - (cs.snap_gross|| 0));
    }
  }

  // Period-filtered totals
  var pt = getPdPeriodStats(pdPeriod);
  var rate   = pt.app > 0 ? Math.round(pt.agr / pt.app * 100) : 0;
  var csRate = csApp  > 0 ? Math.round(csAgr  / csApp  * 100) : 0;
  var totNet = Math.floor(pt.gross * 0.6);
  var totFee = pt.gross - totNet;
  var csNet  = Math.floor(csGrossAll * 0.6);

  // R$/hour for current period
  var robuxPerHour = (pt.dur > 3600) ? Math.round(pt.gross / (pt.dur / 3600)) : 0;

  // Period label
  var PERIODS = {all:'Всё время', today:'Сегодня', '7d':'7 дней', '30d':'30 дней'};
  var periodLbl = PERIODS[pdPeriod] || 'Всё время';

  // Render period selector row
  document.getElementById('pd-period-row').innerHTML =
    '<span style="font-size:11px;color:var(--muted);font-weight:600">ПЕРИОД:</span>' +
    ['all','today','7d','30d'].map(function(p) {
      var lbl = PERIODS[p];
      var active = p === pdPeriod;
      return '<button onclick="setPdPeriod(\\'' + p + '\\')" ' +
        'style="padding:4px 12px;border-radius:6px;font-size:12px;font-weight:' + (active?'700':'500') + ';' +
        'border:1px solid ' + (active?'var(--accent)':'var(--border2)') + ';' +
        'background:' + (active?'rgba(124,106,255,.18)':'transparent') + ';' +
        'color:' + (active?'var(--accent2)':'var(--muted)') + ';cursor:pointer">' + lbl + '</button>';
    }).join('') +
    (pdPeriod !== 'all' ?
      '<span style="font-size:11px;color:var(--muted);margin-left:8px">Данные из истории сессий за: ' + periodLbl + '</span>' :
      '<span style="font-size:11px;color:var(--muted);margin-left:8px">Все накопленные данные с начала работы</span>') +
    (robuxPerHour > 0 ? '<span style="margin-left:auto;font-size:12px;color:#4ade80;font-weight:600">≈ R$ ' + fmtN(robuxPerHour) + '/ч сейчас</span>' : '');

  document.getElementById('pd-summary-bar').innerHTML =
    // Online
    '<div class="scard"><div class="sval"><span class="green">' + online + '</span> / ' + accs.length + '</div><div class="slbl">Онлайн</div></div>' +
    // Period totals
    '<div class="scard" style="background:rgba(99,102,241,.07);border-color:rgba(99,102,241,.25)">' +
      '<div style="font-size:9px;color:var(--accent2);font-weight:700;letter-spacing:.08em;margin-bottom:4px">' + periodLbl.toUpperCase() + ' — ВСЕГО</div>' +
      '<div style="display:flex;gap:10px">' +
        '<span><b>' + fmtN(pt.app) + '</b><br><span style="font-size:10px;color:var(--muted)">спрошено</span></span>' +
        '<span><b style="color:var(--green)">' + fmtN(pt.agr) + '</b><br><span style="font-size:10px;color:var(--muted)">согласились</span></span>' +
        '<span><b style="color:var(--red)">' + fmtN(pt.ref) + '</b><br><span style="font-size:10px;color:var(--muted)">отказали</span></span>' +
        '<span><b style="color:var(--muted)">' + fmtN(pt.nr) + '</b><br><span style="font-size:10px;color:var(--muted)">молчали</span></span>' +
      '</div>' +
    '</div>' +
    '<div class="scard"><div class="sval">' + rate + '%</div><div class="slbl">% согласий (' + periodLbl + ')</div></div>' +
    // Current servers (live only)
    '<div class="scard" style="background:rgba(74,222,128,.06);border-color:rgba(74,222,128,.2)">' +
      '<div style="font-size:9px;color:#4ade80;font-weight:700;letter-spacing:.08em;margin-bottom:4px">ТЕКУЩИЙ СЕРВЕР ● ОНЛАЙН</div>' +
      '<div style="display:flex;gap:10px">' +
        '<span><b>' + csApp + '</b><br><span style="font-size:10px;color:var(--muted)">спрошено</span></span>' +
        '<span><b style="color:var(--green)">' + csAgr + '</b><br><span style="font-size:10px;color:var(--muted)">согласились</span></span>' +
        '<span><b style="color:var(--red)">' + csRef + '</b><br><span style="font-size:10px;color:var(--muted)">отказали</span></span>' +
        '<span><b style="color:var(--muted)">' + csNr + '</b><br><span style="font-size:10px;color:var(--muted)">молчали</span></span>' +
      '</div>' +
    '</div>' +
    '<div class="scard"><div class="sval">' + csRate + '%</div><div class="slbl">% согласий (сейчас)</div></div>' +
    // Robux earned
    '<div class="scard" style="background:rgba(74,222,128,.06)">' +
      '<div style="font-size:9px;color:#4ade80;font-weight:700;letter-spacing:.08em;margin-bottom:2px">ЗАРАБОТАНО (' + periodLbl + ')</div>' +
      '<div class="sval" style="color:#4ade80;font-size:20px">R$ ' + fmtN(totNet) + '</div>' +
      '<div style="font-size:10px;color:var(--muted)">из ' + fmtN(pt.gross) + ' брутто · ком. R$ ' + fmtN(totFee) + '</div>' +
    '</div>' +
    // Donations count + current server R$
    '<div class="scard">' +
      '<div class="sval" style="color:#f59e0b">' + fmtN(pt.don) + '</div>' +
      '<div class="slbl">Донации (' + periodLbl + ')</div>' +
      (csNet > 0 ? '<div style="font-size:10px;color:#4ade80;margin-top:3px">+R$ ' + fmtN(csNet) + ' этот сервер</div>' : '') +
    '</div>' +
    '<div class="scard"><div class="sval">' + totHops + '</div><div class="slbl">Хопов всего</div></div>';
}

function setPdPeriod(p) {
  pdPeriod = p;
  localStorage.setItem('pd_period', p);
  renderPdSummary();
  renderPdView();
}

/* ── PD Cards ── */
function renderPdCards() {
  var now  = Date.now() / 1000;
  var accs = Object.values(pdData).sort(function(a,b) {
    var ao = pdIsOnline(a), bo = pdIsOnline(b);
    if (ao && !bo) return -1; if (!ao && bo) return 1;
    return (b.approached||0) - (a.approached||0);
  });
  var c = document.getElementById('pd-cards-container');
  if (!accs.length) {
    c.innerHTML = '<div class="empty-state">Ботов PD ещё нет.<br>Установите DASH_URL в botplsdonate.lua для начала работы.</div>';
    return;
  }
  c.innerHTML = '<div class="cards-grid">' + accs.map(function(a) { return buildPdCard(a, now); }).join('') + '</div>';
}

function buildPdCard(a, now) {
  var id   = a.id || '';
  var off  = !pdIsOnline(a);
  var cs   = a.current_session || {};
  var skey = off ? 'Offline' : (a.status || 'Active');
  var col  = accentColor(a.name || '?');

  // all-time totals (for breakdown / all-time display)
  var app   = a.approached   || 0;
  var agr   = a.agreed       || 0;
  var ref   = a.refused      || 0;
  var nr    = a.no_response  || 0;
  var don   = a.donations    || 0;
  var grossAllTime = a.robux_gross || 0;
  var raisedCur = a.raised_current || 0;
  var rate  = app > 0 ? Math.round(agr / app * 100) : 0;
  var sn    = (a.sessions || []).length + (cs.server_id ? 1 : 0);

  // current server session — show delta since session START (not cumulative since script start)
  var csApp   = Math.max(0, (cs.approached    || 0) - (cs.snap_app   || 0));
  var csAgr   = Math.max(0, (cs.agreed        || 0) - (cs.snap_agr   || 0));
  var csRef   = Math.max(0, (cs.refused       || 0) - (cs.snap_ref   || 0));
  var csNr    = Math.max(0, (cs.no_response   || 0) - (cs.snap_nr    || 0));
  var csDon   = Math.max(0, (cs.donations     || 0) - (cs.snap_don   || 0));
  var csGross = Math.max(0, (cs.robux_gross   || 0) - (cs.snap_gross || 0));
  var csNet   = Math.floor(csGross * 0.6);
  var csDur   = cs.started_at ? now - cs.started_at : 0;

  // uptime = time since last (re)start, resets after >5 min offline or script restart
  var firstSeen = a.session_start || a.created_at || 0;
  var totalUptime = firstSeen > 0 ? now - firstSeen : 0;

  // Period-filtered gross for the primary metric (matches summary calculation)
  var cutoff = 0;
  if (pdPeriod === 'today') { var _d2 = new Date(); _d2.setHours(0,0,0,0); cutoff = _d2.getTime()/1000; }
  else if (pdPeriod === '7d')  { cutoff = now - 7  * 86400; }
  else if (pdPeriod === '30d') { cutoff = now - 30 * 86400; }

  var gross;
  if (pdPeriod === 'all') {
    gross = grossAllTime;
  } else {
    gross = 0;
    var _cs2 = (a.sessions || []).filter(function(s) { return (s.started_at||0) >= cutoff; });
    for (var _ci = 0; _ci < _cs2.length; _ci++) {
      gross += Math.max(0, (_cs2[_ci].robux_gross||0) - (_cs2[_ci].snap_gross||0));
    }
    if (cs.server_id && (cs.started_at||0) >= cutoff) {
      gross += Math.max(0, (cs.robux_gross||0) - (cs.snap_gross||0));
    }
  }
  var net = Math.floor(gross * 0.6);
  var fee = gross - net;

  var PERIODS = {all:'Всё время', today:'Сегодня', '7d':'7 дней', '30d':'30 дней'};
  var periodLbl = PERIODS[pdPeriod] || 'Всё время';

  var sbCls = off ? 'sb-Offline' : (skey === 'Active' ? 'sb-Farming' : 'sb-Idle');

  // agree rate bar color
  var barColor = rate >= 10 ? 'linear-gradient(90deg,var(--green),#16a34a)'
               : rate >= 5  ? 'linear-gradient(90deg,#f59e0b,#d97706)'
               : 'linear-gradient(90deg,var(--red),#dc2626)';

  // R$/hour from current session (last ~csDur seconds)
  var csRobuxPerHour = (csDur > 300 && csGross > 0) ? Math.round(csGross / (csDur / 3600)) : 0;
  // R$/hour from selected period
  var periodDur2 = pdPeriod === 'all' ? totalUptime : (function() {
    var _dur = 0;
    var _s3 = (a.sessions || []).filter(function(s) { return (s.started_at||0) >= cutoff; });
    for (var _ki = 0; _ki < _s3.length; _ki++) _dur += (_s3[_ki].duration || 0);
    if (cs.server_id && (cs.started_at||0) >= cutoff) _dur += now - (cs.started_at || now);
    return _dur;
  })();
  var allRobuxPerHour = (periodDur2 > 3600 && gross > 0) ? Math.round(gross / (periodDur2 / 3600)) : 0;

  // Format date started
  var startedStr = firstSeen > 0 ? fmtTime(firstSeen) : '—';

  return '<div class="card ' + (off ? 'is-offline' : 'is-online') + '">' +
    // ── Header ──
    '<div class="card-head">' +
      '<div class="role-badge" style="background:' + col + ';width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px">💰</div>' +
      '<div class="card-info">' +
        '<div class="card-name">' + esc(a.name || 'Unknown') + '</div>' +
        '<div class="card-uid">uid: ' + esc(id) + '</div>' +
      '</div>' +
      '<span class="status-badge ' + sbCls + '">' + trStatus(skey) + '</span>' +
    '</div>' +

    // ── Uptime + hops row ──
    '<div style="display:flex;gap:10px;margin-bottom:10px;font-size:11px;color:var(--muted);align-items:center">' +
      '<span title="Время работы с последнего запуска">⏱ <b style="color:var(--text)">' + (totalUptime > 0 ? fmtDur(totalUptime) : '—') + '</b></span>' +
      '<span style="font-size:10px;color:var(--muted)">с ' + startedStr + '</span>' +
      '<span style="margin-left:auto">🔀 <b style="color:var(--text)">' + (a.hops||0) + '</b> хопов</span>' +
    '</div>' +

    // ── Primary metrics: Earned R$ | This server approached | Agree rate ──
    '<div class="card-metrics">' +
      '<div>' +
        '<div class="metric-val" style="color:#4ade80">R$ ' + fmtN(net) + '</div>' +
        '<div class="metric-lbl">Заработано (' + periodLbl + ')</div>' +
      '</div>' +
      '<div>' +
        '<div class="metric-val">' + fmtN(csApp) + '</div>' +
        '<div class="metric-lbl">Этот сервер</div>' +
      '</div>' +
      '<div>' +
        '<div class="metric-val">' + rate + '%</div>' +
        '<div class="metric-lbl">% согласий</div>' +
      '</div>' +
    '</div>' +

    // ── Robux details row ──
    '<div style="background:rgba(74,222,128,.06);border:1px solid rgba(74,222,128,.18);border-radius:8px;padding:7px 12px;margin-bottom:10px;font-size:11px">' +
      '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">' +
        '<span style="color:#fbbf24;font-weight:700">💰</span>' +
        (raisedCur > 0 ? '<span>Стенд: <b style="color:#94a3b8">R$ ' + fmtN(raisedCur) + '</b></span>' : '') +
        '<span>Брутто: <b style="color:#94a3b8">R$ ' + fmtN(gross) + '</b></span>' +
        '<span>Чистыми: <b style="color:#4ade80">R$ ' + fmtN(net) + '</b></span>' +
        (don > 0 ? '<span style="color:#f59e0b">' + fmtN(don) + ' дон.</span>' : '<span style="color:var(--muted)">0 донаций</span>') +
        (allRobuxPerHour > 0 ? '<span style="margin-left:auto;color:#4ade80;font-weight:700">≈R$ ' + allRobuxPerHour + '/ч</span>' : '') +
      '</div>' +
      (csGross > 0 || csRobuxPerHour > 0 ?
        '<div style="margin-top:4px;display:flex;gap:10px;font-size:10px;color:var(--muted)">' +
          '<span>Этот сервер: <b style="color:#4ade80">R$ ' + fmtN(Math.floor(csGross*0.6)) + '</b></span>' +
          (csRobuxPerHour > 0 ? '<span style="color:#4ade80;font-weight:600">≈R$ ' + csRobuxPerHour + '/ч сейчас</span>' : '') +
        '</div>' : '') +
    '</div>' +

    // ── Agree rate bar ──
    '<div class="bag-row">' +
      '<span class="bag-lbl">Согласились</span>' +
      '<div class="bag-track"><div class="bag-fill" style="width:' + Math.min(rate,100) + '%;background:' + barColor + '"></div></div>' +
      '<span class="bag-count">' + fmtN(agr) + ' / ' + fmtN(app) + '</span>' +
    '</div>' +

    // ── All-time breakdown ──
    '<div style="font-size:10px;color:var(--muted);font-weight:600;letter-spacing:.06em;margin:6px 0 4px">ЗА ВСЁ ВРЕМЯ</div>' +
    '<div class="mini-stats">' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--green)">'  + fmtN(agr) + '</div><div class="mini-lbl">Согласились</div></div>' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--red)">'    + fmtN(ref) + '</div><div class="mini-lbl">Отказали</div></div>' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--muted)">'  + fmtN(nr)  + '</div><div class="mini-lbl">Нет ответа</div></div>' +
      '<div class="mini-stat"><div class="mini-val">'                              + fmtN(app) + '</div><div class="mini-lbl">Подошёл</div></div>' +
    '</div>' +

    // ── This server breakdown ──
    '<div style="font-size:10px;color:var(--muted);font-weight:600;letter-spacing:.06em;margin:6px 0 4px">ЭТОТ СЕРВЕР' + (csDur>0?' <span style="font-weight:400;color:var(--accent2)">— ' + fmtDur(csDur) + '</span>':'') + '</div>' +
    '<div class="mini-stats">' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--green)">'  + csAgr + '</div><div class="mini-lbl">Согласились</div></div>' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--red)">'    + csRef + '</div><div class="mini-lbl">Отказали</div></div>' +
      '<div class="mini-stat"><div class="mini-val" style="color:var(--muted)">'  + csNr  + '</div><div class="mini-lbl">Нет ответа</div></div>' +
      '<div class="mini-stat"><div class="mini-val" style="color:#f59e0b">'       + (csDon > 0 ? csDon : '—') + '</div><div class="mini-lbl">Донации</div></div>' +
    '</div>' +

    // ── Actions ──
    '<div class="card-actions">' +
      '<button class="btn btn-blue" data-aid="' + id + '" onclick="openPdModal(this.dataset.aid)">📋 История</button>' +
      '<button class="btn btn-ghost" style="color:#94a3b8;border-color:rgba(148,163,184,.3)" data-aid="' + id + '" onclick="openPdSettings(this.dataset.aid)" title="Настройки бота">⚙️</button>' +
      '<span id="pdrst-' + id + '">' +
        '<button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" data-aid="' + id + '" onclick="confirmPdReset(this.dataset.aid)">🗑 Сбросить</button>' +
      '</span>' +
    '</div>' +
  '</div>';
}

/* ── PD List ── */
function renderPdList() {
  var now  = Date.now() / 1000;
  var PERIODS = {all:'Всё время', today:'Сегодня', '7d':'7 дней', '30d':'30 дней'};
  var periodLbl = PERIODS[pdPeriod] || 'Всё время';

  // Cutoff for period filtering (same logic as getPdPeriodStats)
  var cutoff = 0;
  if (pdPeriod === 'today') { var _d = new Date(); _d.setHours(0,0,0,0); cutoff = _d.getTime()/1000; }
  else if (pdPeriod === '7d')  { cutoff = now - 7  * 86400; }
  else if (pdPeriod === '30d') { cutoff = now - 30 * 86400; }

  var accs = Object.values(pdData).sort(function(a,b) {
    var ao = pdIsOnline(a), bo = pdIsOnline(b);
    if (ao && !bo) return -1; if (!ao && bo) return 1;
    return (b.robux_gross||0) - (a.robux_gross||0);
  });
  var c = document.getElementById('pd-list-container');
  if (!accs.length) {
    c.innerHTML = '<div class="empty-state">Ботов PD ещё нет.</div>';
    return;
  }
  var rows = accs.map(function(a) {
    var off  = !pdIsOnline(a);
    var cs   = a.current_session || {};
    var skey = off ? 'Offline' : (a.status || 'Active');
    var sbCls = off ? 'sb-Offline' : 'sb-Farming';
    var col  = accentColor(a.name || '?');

    var app   = a.approached   || 0;
    var agr   = a.agreed       || 0;
    var ref   = a.refused      || 0;
    var nr    = a.no_response  || 0;
    var don   = a.donations    || 0;
    var rate  = app > 0 ? Math.round(agr / app * 100) : 0;

    var csApp   = Math.max(0, (cs.approached  || 0) - (cs.snap_app  || 0));
    var csGross = Math.max(0, (cs.robux_gross || 0) - (cs.snap_gross|| 0));
    var csDur   = cs.started_at ? now - cs.started_at : 0;
    var barColor = rate >= 10 ? 'var(--green)' : rate >= 5 ? '#f59e0b' : 'var(--red)';

    // Period-filtered gross (matches summary calculation exactly)
    var gross;
    if (pdPeriod === 'all') {
      gross = a.robux_gross || 0;
    } else {
      gross = 0;
      var _sess = (a.sessions || []).filter(function(s) { return (s.started_at||0) >= cutoff; });
      for (var _j = 0; _j < _sess.length; _j++) {
        gross += Math.max(0, (_sess[_j].robux_gross||0) - (_sess[_j].snap_gross||0));
      }
      if (cs.server_id && (cs.started_at||0) >= cutoff) {
        gross += Math.max(0, (cs.robux_gross||0) - (cs.snap_gross||0));
      }
    }
    var net = Math.floor(gross * 0.6);

    // Uptime
    var firstSeen = a.session_start || a.created_at || 0;
    var uptime    = firstSeen > 0 ? now - firstSeen : 0;
    // R$/hour for the selected period
    var periodDur;
    if (pdPeriod === 'all') {
      periodDur = uptime;
    } else {
      periodDur = 0;
      var _s2 = (a.sessions || []).filter(function(s) { return (s.started_at||0) >= cutoff; });
      for (var _k = 0; _k < _s2.length; _k++) periodDur += (_s2[_k].duration || 0);
      if (cs.server_id && (cs.started_at||0) >= cutoff) periodDur += now - (cs.started_at || now);
    }
    var rph  = periodDur > 3600 && gross > 0 ? Math.round(gross / (periodDur / 3600)) : 0;
    // R$/hour current session (always live)
    var csRph = csDur > 300 && csGross > 0 ? Math.round(csGross / (csDur / 3600)) : 0;

    return '<tr class="' + (off ? 'is-offline' : '') + '">' +
      '<td><div style="display:flex;align-items:center;gap:8px">' +
        '<div style="width:8px;height:8px;border-radius:50%;background:' + col + ';flex-shrink:0"></div>' +
        '<div><div style="font-weight:600;font-size:12px">' + esc(a.name || '?') + '</div>' +
             '<div style="font-size:10px;color:var(--muted)">' + esc(a.id) + '</div></div>' +
      '</div></td>' +
      '<td><span class="status-badge ' + sbCls + '">' + trStatus(skey) + '</span></td>' +
      '<td style="color:var(--muted)">' + (uptime > 0 ? fmtDur(uptime) : '—') + '</td>' +
      '<td style="font-weight:700;color:#4ade80">' + (gross > 0 ? 'R$ ' + fmtN(net) : '—') + '</td>' +
      '<td style="color:var(--muted)">' + (rph > 0 ? '<span style="color:#4ade80">R$ ' + rph + '/ч</span>' : (csRph > 0 ? '<span style="color:#4ade80;opacity:.6">R$ ' + csRph + '/ч</span>' : '—')) + '</td>' +
      '<td style="font-weight:600">' + fmtN(app) + '</td>' +
      '<td>' + fmtN(csApp) + '</td>' +
      '<td><div style="display:flex;align-items:center;gap:6px">' +
        '<div class="bag-track" style="width:50px"><div class="bag-fill" style="width:' + Math.min(rate,100) + '%;background:' + barColor + '"></div></div>' +
        '<span style="font-size:11px;color:' + barColor + ';font-weight:700">' + rate + '%</span>' +
      '</div></td>' +
      '<td style="color:var(--green)">' + fmtN(agr) + '</td>' +
      '<td style="color:var(--red)">'   + fmtN(ref) + '</td>' +
      '<td style="color:var(--muted)">' + fmtN(nr)  + '</td>' +
      '<td>' + (a.hops || 0) + '</td>' +
      '<td><div style="display:flex;gap:5px">' +
        '<button class="btn btn-blue" style="padding:3px 9px;font-size:10px" data-aid="' + a.id + '" onclick="openPdModal(this.dataset.aid)">📋 История</button>' +
        '<button class="btn btn-ghost" style="padding:3px 9px;font-size:10px;color:#94a3b8;border-color:rgba(148,163,184,.3)" data-aid="' + a.id + '" onclick="openPdSettings(this.dataset.aid)">⚙️</button>' +
      '</div></td>' +
    '</tr>';
  }).join('');
  c.innerHTML = '<div class="list-wrap"><table class="list-tbl"><thead><tr>' +
    '<th>Аккаунт</th><th>Статус</th>' +
    '<th>Аптайм</th><th>Чистыми (' + periodLbl + ')</th><th>R$/ч</th>' +
    '<th>Подошёл</th><th>Этот сервер</th><th>% согласий</th>' +
    '<th>Согласились</th><th>Отказали</th><th>Нет ответа</th>' +
    '<th>Хопы</th><th>Управление</th>' +
  '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

/* ── PD Settings Modal ── */
function openPdSettings(id) {
  var a = pdData[id] || {};
  document.getElementById('pd-cfg-title').textContent = (a.name || id) + ' — Настройки';
  document.getElementById('pd-cfg-aid').value = id;
  // Load current config from server
  fetch('/pd_config/' + id)
    .then(function(r){ return r.json(); })
    .then(function(cfg){
      document.getElementById('pd-cfg-min').value = cfg.min_players || 4;
      document.getElementById('pd-cfg-max').value = cfg.max_players || 24;
      document.getElementById('pd-cfg-cooldown').value = cfg.server_cooldown || 60;
      document.getElementById('pd-settings-modal').classList.add('open');
    })
    .catch(function(){ showToast('Не удалось загрузить конфиг','e'); });
}
function closePdSettings() {
  document.getElementById('pd-settings-modal').classList.remove('open');
}
function savePdSettings() {
  var id  = document.getElementById('pd-cfg-aid').value;
  var min = parseInt(document.getElementById('pd-cfg-min').value) || 4;
  var max = parseInt(document.getElementById('pd-cfg-max').value) || 24;
  var cd  = parseInt(document.getElementById('pd-cfg-cooldown').value) || 60;
  fetch('/pd_config/' + id, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({min_players: min, max_players: max, server_cooldown: cd})
  }).then(function(){ showToast('Настройки сохранены ✓','s'); closePdSettings(); })
    .catch(function(){ showToast('Ошибка сохранения','e'); });
}
function clearPdServerHistory(id) {
  fetch('/pd_config/' + id, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({clear_history: true,
      min_players: parseInt(document.getElementById('pd-cfg-min').value)||4,
      max_players: parseInt(document.getElementById('pd-cfg-max').value)||24,
      server_cooldown: parseInt(document.getElementById('pd-cfg-cooldown').value)||60
    })
  }).then(function(){ showToast('История серверов очистится при следующем хопе ✓','s'); })
    .catch(function(){ showToast('Ошибка','e'); });
}

/* ── PD Reset ── */
function confirmPdReset(id) {
  var el = document.getElementById('pdrst-' + id);
  if (!el) return;
  el.innerHTML = '<span class="inline-confirm">Точно? ' +
    '<button class="icbtn icbtn-y" data-aid="' + id + '" onclick="doPdReset(this.dataset.aid)">Да</button> ' +
    '<button class="icbtn icbtn-n" data-aid="' + id + '" onclick="cancelPdReset(this.dataset.aid)">Нет</button>' +
    '</span>';
}
function doPdReset(id) {
  fetch('/pd_reset/' + id, {method:'DELETE'})
    .then(function() { showToast('Статистика ПД сброшена', 's'); })
    .catch(function() { showToast('Ошибка сброса', 'e'); });
  cancelPdReset(id);
}
function cancelPdReset(id) {
  var el = document.getElementById('pdrst-' + id);
  if (!el) return;
  el.innerHTML = '<button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" data-aid="' + id + '" onclick="confirmPdReset(this.dataset.aid)">🗑 Сбросить</button>';
}

/* ── PD Modal ── */
function openPdModal(id) {
  pdModalAccId = id;
  switchPdModalTab('sessions');
  renderPdModal(id);
  document.getElementById('pd-modal').classList.add('open');
}

function openPdModalOnChatLog(id) {
  pdModalAccId = id;
  // Set title
  var a = pdData[id];
  document.getElementById('pd-modal-title').textContent = 'ПД История: ' + ((a && a.name) || id);
  // Switch to chat log tab first (renders sessions tab as placeholder)
  renderPdModal(id);
  switchPdModalTab('chatlog');
  document.getElementById('pd-modal').classList.add('open');
}
function closePdModal() {
  document.getElementById('pd-modal').classList.remove('open');
  pdModalAccId = null;
  pdChatPage = 0;
}

var pdChatPage = 0;
var pdChatOutcome = '';
var pdModalSubTab = 'sessions';

function switchPdModalTab(tab) {
  pdModalSubTab = tab;
  var isSessions = tab === 'sessions';
  document.getElementById('pd-modal-body').style.display    = isSessions ? '' : 'none';
  document.getElementById('pd-modal-chatlog').style.display  = isSessions ? 'none' : '';
  document.getElementById('pdmt-sessions').style.borderBottomColor = isSessions ? 'var(--accent)' : 'transparent';
  document.getElementById('pdmt-sessions').style.color = isSessions ? 'var(--text)' : 'var(--muted)';
  document.getElementById('pdmt-chatlog').style.borderBottomColor  = isSessions ? 'transparent' : 'var(--accent)';
  document.getElementById('pdmt-chatlog').style.color  = isSessions ? 'var(--muted)' : 'var(--text)';
  if (!isSessions && pdModalAccId) loadPdChatLog(pdModalAccId, pdChatPage, pdChatOutcome);
}

var OUTCOME_COLOR = {
  'agreed':       '#4ade80',
  'agreed_2nd':   '#86efac',
  'refused':      '#f87171',
  'no_response':  '#94a3b8',
  'left':         '#f59e0b',
  'chase_fail':   '#475569',
};
var OUTCOME_LABEL = {
  'agreed':      '✅ Согласился',
  'agreed_2nd':  '✅ Согласился (2й раз)',
  'refused':     '❌ Отказал',
  'no_response': '🔇 Молчал',
  'left':        '🚪 Ушёл',
  'chase_fail':  '🏃 Убежал',
};

function pdChatFilterClick(el) { loadPdChatLog(el.dataset.acc, 0, el.dataset.oc); }
function pdChatNavClick(el)    { loadPdChatLog(el.dataset.acc, parseInt(el.dataset.pg)||0, el.dataset.oc); }
function loadPdChatLog(accId, page, outcome) {
  pdChatPage    = page    || 0;
  pdChatOutcome = outcome || '';
  var limit = 50;
  var url = '/pd_interactions/' + encodeURIComponent(accId) + '?limit=' + limit + '&offset=' + (page * limit);
  if (pdChatOutcome) url += '&outcome=' + encodeURIComponent(pdChatOutcome);
  var box = document.getElementById('pd-modal-chatlog');
    box.innerHTML = '<div style="padding:20px;color:var(--muted);text-align:center">Загрузка…</div>';
  fetch(url).then(function(r){return r.json();}).then(function(data){
    var rows = data.rows || [];
    var total = data.total || 0;
    var totalPages = Math.max(1, Math.ceil(total / limit));

    // Filter bar
    var filterHTML =
      '<div style="display:flex;gap:8px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);flex-wrap:wrap">' +
      '<span style="font-size:11px;color:var(--muted)">Фильтр:</span>' +
      ['','agreed','agreed_2nd','refused','no_response','left','chase_fail'].map(function(o) {
        var lbl = o ? (OUTCOME_LABEL[o] || o) : 'Все';
        var active = pdChatOutcome === o;
        return '<button data-acc="' + accId + '" data-oc="' + o + '" onclick="pdChatFilterClick(this)" ' +
          'style="font-size:11px;padding:3px 8px;border-radius:4px;border:1px solid ' +
          (active ? 'var(--accent)' : 'var(--border)') + ';background:' +
          (active ? 'rgba(99,102,241,.15)' : 'transparent') + ';color:' +
          (o ? (OUTCOME_COLOR[o] || 'var(--text)') : 'var(--text)') + ';cursor:pointer">' + lbl + '</button>';
      }).join('') +
      '<span style="margin-left:auto;font-size:11px;color:var(--muted)">' + total + ' записей</span>' +
      '</div>';

    // Table rows
    var tableRows = rows.length ? rows.map(function(r) {
      var oc = r.outcome || '';
      var color = OUTCOME_COLOR[oc] || 'var(--muted)';
      var label = OUTCOME_LABEL[oc] || oc;
      var d = new Date((r.ts||0)*1000);
      var timeStr = d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'}) +
                    ' ' + d.toLocaleDateString([],{day:'2-digit',month:'2-digit'});
      return '<tr>' +
        '<td style="color:var(--muted);white-space:nowrap;font-size:11px">' + timeStr + '</td>' +
        '<td style="font-weight:600;white-space:nowrap">' + esc(r.target_name||'?') + '</td>' +
        '<td style="color:#93c5fd;max-width:200px">' + esc(r.bot_msg||'—') + '</td>' +
        '<td style="color:#fde68a;max-width:180px">' + (r.player_reply ? esc(r.player_reply) : '<span style="color:var(--muted);font-style:italic">—</span>') + '</td>' +
        '<td style="color:' + color + ';font-weight:600;white-space:nowrap">' + label + '</td>' +
      '</tr>';
    }).join('') : '<tr><td colspan="5" style="text-align:center;padding:32px;color:var(--muted)">Взаимодействий пока нет</td></tr>';

    // Pagination
    var pgHTML = '';
    if (totalPages > 1) {
      pgHTML = '<div style="display:flex;gap:6px;padding:10px 16px;align-items:center">';
      pgHTML += (page<=0 ? '<button class="pg-btn" disabled>← Назад</button>' :
        '<button class="pg-btn" data-acc="' + accId + '" data-pg="' + (page-1) + '" data-oc="' + pdChatOutcome + '" onclick="pdChatNavClick(this)">← Назад</button>');
      pgHTML += '<span style="font-size:12px;color:var(--muted)">Стр. ' + (page+1) + ' / ' + totalPages + '</span>';
      pgHTML += (page>=totalPages-1 ? '<button class="pg-btn" disabled>Вперёд →</button>' :
        '<button class="pg-btn" data-acc="' + accId + '" data-pg="' + (page+1) + '" data-oc="' + pdChatOutcome + '" onclick="pdChatNavClick(this)">Вперёд →</button>');
      pgHTML += '</div>';
    }

    box.innerHTML = filterHTML +
      '<div style="overflow-x:auto">' +
      '<table class="modal-tbl"><thead><tr>' +
        '<th>Время</th><th>Игрок</th><th style="color:#93c5fd">Бот написал</th><th style="color:#fde68a">Ответ игрока</th><th>Результат</th>' +
      '</tr></thead><tbody>' + tableRows + '</tbody></table>' +
      '</div>' + pgHTML;
  }).catch(function(e) {
    box.innerHTML = '<div style="padding:20px;color:var(--red)">Ошибка загрузки: ' + e + '</div>';
  });
}

function renderPdModal(id) {
  var a = pdData[id]; if (!a) return;
  var now = Date.now() / 1000;
  var sessions = (a.sessions || []).slice().reverse();
  var cs = a.current_session || {};
  var totSess  = sessions.length + (cs.server_id ? 1 : 0);

  // use the cumulative all-time stats from the account object directly
  var totApp   = a.approached  || 0;
  var totAgr   = a.agreed      || 0;
  var totRef   = a.refused     || 0;
  var totNr    = a.no_response || 0;
  var totDon   = a.donations   || 0;
  var totGross = a.robux_gross || 0;
  var totNet   = Math.floor(totGross * 0.6);
  var rate     = totApp > 0 ? Math.round(totAgr / totApp * 100) : 0;

  // uptime since last (re)start
  var firstSeen = a.session_start || a.created_at || 0;
  var totalUp   = firstSeen > 0 ? now - firstSeen : 0;

  document.getElementById('pd-modal-title').textContent = 'ПД История: ' + (a.name || id);

  // ── Current session row ──
  var rows = '';
  if (cs.server_id) {
    var cDur = now - (cs.started_at || now);
    var cApp   = Math.max(0, (cs.approached  ||0) - (cs.snap_app  ||0));
    var cAgr   = Math.max(0, (cs.agreed      ||0) - (cs.snap_agr  ||0));
    var cRef   = Math.max(0, (cs.refused     ||0) - (cs.snap_ref  ||0));
    var cNr    = Math.max(0, (cs.no_response ||0) - (cs.snap_nr   ||0));
    var cDon   = Math.max(0, (cs.donations   ||0) - (cs.snap_don  ||0));
    var cGross = Math.max(0, (cs.robux_gross ||0) - (cs.snap_gross||0));
    var cNet = Math.floor(cGross * 0.6);
    var cRate = cApp > 0 ? Math.round(cAgr/cApp*100) : 0;
    rows += '<tr style="background:rgba(74,222,128,.04)">' +
      '<td><span class="now-dot">● Сейчас</span></td>' +
      '<td class="mono" title="' + esc(cs.server_id) + '">' + fmtSrv(cs.server_id) + '</td>' +
      '<td>' + fmtTime(cs.started_at) + '</td>' +
      '<td>' + fmtDur(cDur) + '</td>' +
      '<td>' + cApp + '</td>' +
      '<td style="color:var(--green)">' + cAgr + ' <span style="font-size:10px;color:var(--muted)">(' + cRate + '%)</span></td>' +
      '<td style="color:var(--red)">'   + cRef + '</td>' +
      '<td style="color:var(--muted)">' + cNr  + '</td>' +
      '<td style="color:#f59e0b">'      + (cDon || '—') + '</td>' +
      '<td style="color:#4ade80">'      + (cGross > 0 ? 'R$ ' + fmtN(cNet) : '—') + '</td>' +
    '</tr>';
  }

  // ── Past sessions ──
  sessions.forEach(function(s, i) {
    var sApp   = Math.max(0, (s.approached  ||0) - (s.snap_app  ||0));
    var sAgr   = Math.max(0, (s.agreed      ||0) - (s.snap_agr  ||0));
    var sRef   = Math.max(0, (s.refused     ||0) - (s.snap_ref  ||0));
    var sNr    = Math.max(0, (s.no_response ||0) - (s.snap_nr   ||0));
    var sDon   = Math.max(0, (s.donations   ||0) - (s.snap_don  ||0));
    var sGross = Math.max(0, (s.robux_gross ||0) - (s.snap_gross||0));
    var sNet = Math.floor(sGross * 0.6);
    var sRate = sApp > 0 ? Math.round(sAgr/sApp*100) : 0;
    rows += '<tr>' +
      '<td style="color:var(--muted)">' + (sessions.length - i) + '</td>' +
      '<td class="mono" title="' + esc(s.server_id||'') + '">' + fmtSrv(s.server_id) + '</td>' +
      '<td>' + fmtTime(s.started_at) + '</td>' +
      '<td>' + fmtDur(s.duration) + '</td>' +
      '<td>' + sApp + '</td>' +
      '<td style="color:var(--green)">' + sAgr + ' <span style="font-size:10px;color:var(--muted)">(' + sRate + '%)</span></td>' +
      '<td style="color:var(--red)">'   + sRef + '</td>' +
      '<td style="color:var(--muted)">' + sNr  + '</td>' +
      '<td style="color:#f59e0b">'      + (sDon || '—') + '</td>' +
      '<td style="color:#4ade80">'      + (sGross > 0 ? 'R$ ' + fmtN(sNet) : '—') + '</td>' +
    '</tr>';
  });
  if (!rows) rows = '<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--muted)">Сессий ещё нет</td></tr>';

  document.getElementById('pd-modal-body').innerHTML =
    // ── Summary stats ──
    '<div class="modal-stats">' +
      '<div class="modal-stat"><div class="modal-stat-v">' + totSess + '</div><div class="modal-stat-l">Серверов</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + fmtN(totApp) + '</div><div class="modal-stat-l">Подошёл</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v" style="color:var(--green)">' + fmtN(totAgr) + '</div><div class="modal-stat-l">Согласились</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v" style="color:var(--red)">'   + fmtN(totRef) + '</div><div class="modal-stat-l">Отказали</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v" style="color:var(--muted)">' + fmtN(totNr)  + '</div><div class="modal-stat-l">Нет ответа</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + rate + '%</div><div class="modal-stat-l">% согласий</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v" style="color:#f59e0b">' + fmtN(totDon)   + '</div><div class="modal-stat-l">Донации</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v" style="color:#4ade80">R$ ' + fmtN(totNet) + '</div><div class="modal-stat-l">Заработано</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + (totalUp > 0 ? fmtDur(totalUp) : '—') + '</div><div class="modal-stat-l">Аптайм</div></div>' +
      '<div class="modal-stat"><div class="modal-stat-v">' + (a.hops||0) + '</div><div class="modal-stat-l">Хопы</div></div>' +
    '</div>' +
    // ── Session table ──
    '<table class="modal-tbl"><thead><tr>' +
      '<th>#</th><th>Сервер</th><th>Начало</th><th>Длительность</th>' +
      '<th>Подошёл</th><th>Согласились</th><th>Отказали</th><th>Нет ответа</th>' +
      '<th>Донации</th><th>Чистые R$</th>' +
    '</tr></thead><tbody>' + rows + '</tbody></table>';
}

/* ── PD History Tab ── */
function renderPdHistPage() {
  var all = [];
  for (var id in pdData) {
    var acc = pdData[id];
    (acc.sessions || []).forEach(function(s) {
      // use per-session delta for donations/robux
      var row = Object.assign({}, s, {account_id: id, account_name: acc.name || id});
      row.approached  = Math.max(0, (s.approached  ||0) - (s.snap_app  ||0));
      row.agreed      = Math.max(0, (s.agreed      ||0) - (s.snap_agr  ||0));
      row.refused     = Math.max(0, (s.refused     ||0) - (s.snap_ref  ||0));
      row.no_response = Math.max(0, (s.no_response ||0) - (s.snap_nr   ||0));
      row.donations   = Math.max(0, (s.donations   ||0) - (s.snap_don  ||0));
      row.robux_gross = Math.max(0, (s.robux_gross ||0) - (s.snap_gross||0));
      row.ended_at    = (s.started_at||0) + (s.duration||0);
      all.push(row);
    });
    // also include active current session
    var cs = acc.current_session || {};
    if (cs.server_id) {
      var now2 = Date.now()/1000;
      all.push({
        account_id:   id,
        account_name: acc.name || id,
        server_id:    cs.server_id,
        started_at:   cs.started_at || 0,
        duration:     now2 - (cs.started_at || now2),
        ended_at:     null,
        approached:   Math.max(0,(cs.approached||0)  - (cs.snap_app||0)),
        agreed:       Math.max(0,(cs.agreed||0)      - (cs.snap_agr||0)),
        refused:      Math.max(0,(cs.refused||0)     - (cs.snap_ref||0)),
        no_response:  Math.max(0,(cs.no_response||0) - (cs.snap_nr||0)),
        donations:    Math.max(0,(cs.donations||0)   - (cs.snap_don||0)),
        robux_gross:  Math.max(0,(cs.robux_gross||0) - (cs.snap_gross||0)),
        _active:      true,
      });
    }
  }
  var sel = document.getElementById('pd-flt-acc');
  var curSel = sel.value;
  var opts = '<option value="">Все аккаунты (' + all.length + ' сессий)</option>';
  for (var id in pdData) {
    var nm = pdData[id].name || id;
    opts += '<option value="' + id + '"' + (id===curSel?' selected':'') + '>' + esc(nm) + '</option>';
  }
  sel.innerHTML = opts;

  var fAcc  = sel.value;
  var fSrv  = (document.getElementById('pd-flt-srv').value || '').toLowerCase();
  var fFrom = document.getElementById('pd-flt-from').value; // YYYY-MM-DD
  var fTo   = document.getElementById('pd-flt-to').value;
  // Convert date strings to epoch start/end
  var tsFrom = fFrom ? new Date(fFrom + 'T00:00:00').getTime()/1000 : null;
  var tsTo   = fTo   ? new Date(fTo   + 'T23:59:59').getTime()/1000 : null;
  var rows = all.filter(function(r) {
    if (fAcc && r.account_id !== fAcc) return false;
    if (fSrv && !(r.server_id||'').toLowerCase().includes(fSrv)) return false;
    if (tsFrom !== null && (r.started_at||0) < tsFrom) return false;
    if (tsTo   !== null && (r.started_at||0) > tsTo)   return false;
    return true;
  });
  rows.sort(function(a,b) {
    var av = a[pdHistSortCol] != null ? a[pdHistSortCol] : 0;
    var bv = b[pdHistSortCol] != null ? b[pdHistSortCol] : 0;
    if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv||'').toLowerCase(); }
    return av < bv ? pdHistSortDir : av > bv ? -pdHistSortDir : 0;
  });

  var n = rows.length;
  var totApp   = rows.reduce(function(s,r){return s+(r.approached||0);},0);
  var totAgr   = rows.reduce(function(s,r){return s+(r.agreed||0);},0);
  var totRef   = rows.reduce(function(s,r){return s+(r.refused||0);},0);
  var totNr    = rows.reduce(function(s,r){return s+(r.no_response||0);},0);
  var totDon   = rows.reduce(function(s,r){return s+(r.donations||0);},0);
  var totGross = rows.reduce(function(s,r){return s+(r.robux_gross||0);},0);
  var totNet   = Math.floor(totGross * 0.6);
  var totDur   = rows.reduce(function(s,r){return s+(r.duration||0);},0);
  var avgDur   = n ? totDur / n : 0;
  var rate     = totApp > 0 ? Math.round(totAgr/totApp*100) : 0;
  document.getElementById('pd-hist-summary').innerHTML =
    '<div class="scard"><div class="sval">' + n + '</div><div class="slbl">Сессии</div></div>' +
    '<div class="scard"><div class="sval">' + fmtN(totApp) + '</div><div class="slbl">Подошёл</div></div>' +
    '<div class="scard"><div class="sval" style="color:var(--green)">' + fmtN(totAgr) + '</div><div class="slbl">Согласились</div></div>' +
    '<div class="scard"><div class="sval" style="color:var(--red)">'   + fmtN(totRef) + '</div><div class="slbl">Отказали</div></div>' +
    '<div class="scard"><div class="sval" style="color:var(--muted)">' + fmtN(totNr)  + '</div><div class="slbl">Нет ответа</div></div>' +
    '<div class="scard"><div class="sval">' + rate + '%</div><div class="slbl">% согласий</div></div>' +
    '<div class="scard"><div class="sval" style="color:#f59e0b">' + fmtN(totDon)       + '</div><div class="slbl">Донации</div></div>' +
    '<div class="scard"><div class="sval" style="color:#4ade80">R$ ' + fmtN(totNet)    + '</div><div class="slbl">Заработано</div></div>' +
    '<div class="scard"><div class="sval">' + (n?fmtDur(Math.round(avgDur)):'—') + '</div><div class="slbl">Ср. длительность</div></div>' +
    '<div class="scard"><div class="sval">' + fmtDur(totDur) + '</div><div class="slbl">Общее время</div></div>';

  ['account_name','server_id','started_at','ended_at','duration','approached','agreed','refused','no_response','donations','robux_gross'].forEach(function(col) {
    var el = document.getElementById('pdsi-'+col);
    if (!el) return;
    var th = el.parentElement;
    th.classList.remove('sorted-asc','sorted-dsc');
    if (col === pdHistSortCol) th.classList.add(pdHistSortDir===1?'sorted-asc':'sorted-dsc');
  });

  var totalPages = Math.max(1, Math.ceil(n / HIST_PER_PAGE));
  pdHistPage = Math.min(pdHistPage, totalPages);
  var sl = rows.slice((pdHistPage-1)*HIST_PER_PAGE, pdHistPage*HIST_PER_PAGE);

  var tbody = document.getElementById('pd-hist-tbody');
  if (!sl.length) {
    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;padding:40px;color:var(--muted)">Сессий не найдено</td></tr>';
  } else {
    tbody.innerHTML = sl.map(function(r) {
      var col   = accentColor(r.account_name || '?');
      var app   = r.approached || 0, agr = r.agreed || 0;
      var rt    = app > 0 ? Math.round(agr/app*100) : 0;
      var don   = r.donations || 0;
      var gross = r.robux_gross || 0, net = Math.floor(gross * 0.6);
      var rowStyle = r._active ? ' style="background:rgba(74,222,128,.04)"' : '';
      var activeTag = r._active ? '<span class="now-dot" style="margin-right:4px">●</span>' : '';
      return '<tr' + rowStyle + '>' +
        '<td>' +
          '<span class="acc-dot" style="background:' + col + '"></span>' +
          activeTag +
          '<button data-aid="' + r.account_id + '" onclick="openPdModalOnChatLog(this.dataset.aid)" ' +
            'style="background:none;border:none;color:var(--text);cursor:pointer;font-size:13px;padding:0;text-decoration:underline dotted;text-underline-offset:2px">' +
            esc(r.account_name) +
          '</button>' +
        '</td>' +
        '<td class="mono" title="' + esc(r.server_id||'') + '">' + fmtSrv(r.server_id) + '</td>' +
        '<td>' + fmtTime(r.started_at) + '</td>' +
        '<td style="color:var(--muted)">' + (r._active ? '<span style="color:var(--green);font-size:11px">● сейчас</span>' : (r.ended_at ? fmtTime(r.ended_at) : '—')) + '</td>' +
        '<td>' + fmtDur(r.duration) + '</td>' +
        '<td>' + app + '</td>' +
        '<td style="color:var(--green);font-weight:600">' + agr + ' <span style="font-weight:400;color:var(--muted);font-size:10px">(' + rt + '%)</span></td>' +
        '<td style="color:var(--red)">'    + (r.refused||0)     + '</td>' +
        '<td style="color:var(--muted)">'  + (r.no_response||0) + '</td>' +
        '<td style="color:#f59e0b">'       + (don || '—')       + '</td>' +
        '<td style="color:#4ade80;font-weight:600">' + (gross > 0 ? 'R$ ' + fmtN(net) : '—') + '</td>' +
        '<td><button data-aid="' + r.account_id + '" onclick="openPdModalOnChatLog(this.dataset.aid)" ' +
          'style="font-size:11px;padding:2px 7px;border-radius:4px;border:1px solid var(--border);background:transparent;color:#93c5fd;cursor:pointer">💬 Лог</button></td>' +
      '</tr>';
    }).join('');
  }

  if (totalPages <= 1) { document.getElementById('pd-hist-pg').innerHTML = ''; return; }
  var pg = '';
  pg += '<button class="pg-btn" ' + (pdHistPage<=1?'disabled':'onclick="prevPdHistPage()"') + '>&#x2190; Назад</button>';
  var st = Math.max(1, pdHistPage-2), en = Math.min(totalPages, pdHistPage+2);
  for (var i = st; i <= en; i++) pg += '<button class="pg-btn' + (i===pdHistPage?' active':'') + '" onclick="gotoPdHistPage(' + i + ')">' + i + '</button>';
  pg += '<span class="pg-info">Стр. ' + pdHistPage + ' из ' + totalPages + '</span>';
  pg += '<button class="pg-btn" ' + (pdHistPage>=totalPages?'disabled':'onclick="nextPdHistPage()"') + '>Вперёд &#x2192;</button>';
  document.getElementById('pd-hist-pg').innerHTML = pg;
}

function sortPdHist(col) {
  pdHistSortDir = col === pdHistSortCol ? -pdHistSortDir : -1;
  pdHistSortCol = col;
  pdHistPage = 1;
  renderPdHistPage();
}
function pdHistFilterChanged() { pdHistPage = 1; renderPdHistPage(); }
function clearPdHistFilters() {
  document.getElementById('pd-flt-acc').value  = '';
  document.getElementById('pd-flt-srv').value  = '';
  document.getElementById('pd-flt-from').value = '';
  document.getElementById('pd-flt-to').value   = '';
  pdHistPage = 1;
  renderPdHistPage();
}
function gotoPdHistPage(n) { pdHistPage = n; renderPdHistPage(); }
function prevPdHistPage()   { pdHistPage--; renderPdHistPage(); }
function nextPdHistPage()   { pdHistPage++; renderPdHistPage(); }

/* ── Init ── */
switchTab(curTab);
switchView(curView);
switchPdView(curPdView);
doRefresh(function() { startCountdown(); });
</script>
</body>
</html>"""

# ─── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    load_accounts_from_db()
    load_pd_from_db()
    ip = get_local_ip()
    print("=" * 55)
    print("  MM2 Farm Hub  —  persistent storage: farm_data.db")
    print("=" * 55)
    print(f"  Local:  http://localhost:5000")
    print(f"  LAN:    http://{ip}:5000")
    print("=" * 55)
    try_start_cloudflare()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
