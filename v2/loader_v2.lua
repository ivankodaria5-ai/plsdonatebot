local API = "https://antibody-camcorder-activities-text.trycloudflare.com"

-- services
local Players         = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local TweenService    = game:GetService("TweenService")
local player          = Players.LocalPlayer

-- ── GUI root ─────────────────────────────────────────────────────────────

local root = Instance.new("ScreenGui")
root.Name            = "PD_Bot_Loader"
root.ResetOnSpawn    = false
root.ZIndexBehavior  = Enum.ZIndexBehavior.Sibling
root.DisplayOrder    = 999
pcall(function() root.Parent = game:GetService("CoreGui") end)
if not root.Parent then root.Parent = player.PlayerGui end

-- ── Main frame ───────────────────────────────────────────────────────────

local W, H = 360, 188
local frame = Instance.new("Frame", root)
frame.Size              = UDim2.new(0, W, 0, H)
frame.Position          = UDim2.new(0.5, -W/2, 0.5, -H/2)
frame.BackgroundColor3  = Color3.fromRGB(12, 12, 20)
frame.BorderSizePixel   = 0
frame.ClipsDescendants  = true
Instance.new("UICorner", frame).CornerRadius = UDim.new(0, 14)

-- glow border
local border = Instance.new("UIStroke", frame)
border.Color     = Color3.fromRGB(90, 80, 220)
border.Thickness = 1.5

-- subtle top gradient
local topGrad = Instance.new("Frame", frame)
topGrad.Size              = UDim2.new(1, 0, 0, 3)
topGrad.Position          = UDim2.new(0, 0, 0, 0)
topGrad.BackgroundColor3  = Color3.fromRGB(110, 100, 255)
topGrad.BorderSizePixel   = 0

-- ── Header ───────────────────────────────────────────────────────────────

local header = Instance.new("Frame", frame)
header.Size             = UDim2.new(1, 0, 0, 48)
header.Position         = UDim2.new(0, 0, 0, 3)
header.BackgroundColor3 = Color3.fromRGB(18, 16, 32)
header.BorderSizePixel  = 0

local icon = Instance.new("TextLabel", header)
icon.Size               = UDim2.new(0, 36, 0, 36)
icon.Position           = UDim2.new(0, 14, 0.5, -18)
icon.BackgroundTransparency = 1
icon.Text               = "🤖"
icon.TextSize           = 22
icon.Font               = Enum.Font.Gotham

local titleLbl = Instance.new("TextLabel", header)
titleLbl.Size               = UDim2.new(1, -60, 0, 22)
titleLbl.Position           = UDim2.new(0, 52, 0, 6)
titleLbl.BackgroundTransparency = 1
titleLbl.Text               = "Please Donate Bot"
titleLbl.TextColor3         = Color3.fromRGB(235, 230, 255)
titleLbl.TextSize           = 15
titleLbl.Font               = Enum.Font.GothamBold
titleLbl.TextXAlignment     = Enum.TextXAlignment.Left

local subLbl = Instance.new("TextLabel", header)
subLbl.Size                 = UDim2.new(1, -60, 0, 16)
subLbl.Position             = UDim2.new(0, 52, 0, 26)
subLbl.BackgroundTransparency = 1
subLbl.Text                 = "t.me/coldyz"
subLbl.TextColor3           = Color3.fromRGB(100, 90, 180)
subLbl.TextSize             = 11
subLbl.Font                 = Enum.Font.Gotham
subLbl.TextXAlignment       = Enum.TextXAlignment.Left

-- ── Key input ────────────────────────────────────────────────────────────

local inputBg = Instance.new("Frame", frame)
inputBg.Size              = UDim2.new(1, -32, 0, 40)
inputBg.Position          = UDim2.new(0, 16, 0, 64)
inputBg.BackgroundColor3  = Color3.fromRGB(8, 8, 16)
inputBg.BorderSizePixel   = 0
Instance.new("UICorner", inputBg).CornerRadius = UDim.new(0, 8)
local inputStroke = Instance.new("UIStroke", inputBg)
inputStroke.Color    = Color3.fromRGB(55, 50, 100)
inputStroke.Thickness = 1

local keyBox = Instance.new("TextBox", inputBg)
keyBox.Size                = UDim2.new(1, -16, 1, 0)
keyBox.Position            = UDim2.new(0, 10, 0, 0)
keyBox.BackgroundTransparency = 1
keyBox.PlaceholderText     = "Лицензионный ключ"
keyBox.PlaceholderColor3   = Color3.fromRGB(70, 65, 120)
keyBox.Text                = ""
keyBox.TextColor3          = Color3.fromRGB(220, 215, 255)
keyBox.TextSize            = 13
keyBox.Font                = Enum.Font.Code
keyBox.ClearTextOnFocus    = false

keyBox.Focused:Connect(function()
    TweenService:Create(inputStroke,
        TweenInfo.new(0.2), {Color = Color3.fromRGB(110, 100, 255)}):Play()
end)
keyBox.FocusLost:Connect(function()
    TweenService:Create(inputStroke,
        TweenInfo.new(0.2), {Color = Color3.fromRGB(55, 50, 100)}):Play()
end)

-- ── Run button ───────────────────────────────────────────────────────────

local btn = Instance.new("TextButton", frame)
btn.Size              = UDim2.new(1, -32, 0, 38)
btn.Position          = UDim2.new(0, 16, 0, 112)
btn.BackgroundColor3  = Color3.fromRGB(95, 85, 210)
btn.BorderSizePixel   = 0
btn.Text              = "Запустить"
btn.TextColor3        = Color3.fromRGB(255, 255, 255)
btn.TextSize          = 14
btn.Font              = Enum.Font.GothamBold
btn.AutoButtonColor   = false
Instance.new("UICorner", btn).CornerRadius = UDim.new(0, 8)

-- button hover
btn.MouseEnter:Connect(function()
    TweenService:Create(btn, TweenInfo.new(0.15),
        {BackgroundColor3 = Color3.fromRGB(115, 105, 235)}):Play()
end)
btn.MouseLeave:Connect(function()
    TweenService:Create(btn, TweenInfo.new(0.15),
        {BackgroundColor3 = Color3.fromRGB(95, 85, 210)}):Play()
end)

-- ── Status bar ───────────────────────────────────────────────────────────

local status = Instance.new("TextLabel", frame)
status.Size                 = UDim2.new(1, -32, 0, 18)
status.Position             = UDim2.new(0, 16, 0, 158)
status.BackgroundTransparency = 1
status.Text                 = "Введи ключ и нажми Запустить"
status.TextColor3           = Color3.fromRGB(85, 80, 140)
status.TextSize             = 11
status.Font                 = Enum.Font.Gotham
status.TextXAlignment       = Enum.TextXAlignment.Center

-- ── Drag ─────────────────────────────────────────────────────────────────

local dragging, dragStart, startPos
header.InputBegan:Connect(function(inp)
    if inp.UserInputType == Enum.UserInputType.MouseButton1 then
        dragging  = true
        dragStart = inp.Position
        startPos  = frame.Position
    end
end)
UserInputService.InputChanged:Connect(function(inp)
    if dragging and inp.UserInputType == Enum.UserInputType.MouseMovement then
        local d = inp.Position - dragStart
        frame.Position = UDim2.new(
            startPos.X.Scale, startPos.X.Offset + d.X,
            startPos.Y.Scale, startPos.Y.Offset + d.Y)
    end
end)
UserInputService.InputEnded:Connect(function(inp)
    if inp.UserInputType == Enum.UserInputType.MouseButton1 then
        dragging = false
    end
end)

-- ── Helpers ───────────────────────────────────────────────────────────────

local httprequest = (syn and syn.request)
    or (http and http.request)
    or http_request
    or (fluxus and fluxus.request)
    or request

local function setStatus(text, color)
    status.Text       = text
    status.TextColor3 = color or Color3.fromRGB(85, 80, 140)
end

local function setBusy(on)
    btn.Text              = on and "Загрузка..." or "Запустить"
    btn.BackgroundColor3  = on
        and Color3.fromRGB(55, 50, 110)
        or  Color3.fromRGB(95, 85, 210)
end

-- ── Launch ────────────────────────────────────────────────────────────────

btn.MouseButton1Click:Connect(function()
    local key = keyBox.Text:match("^%s*(.-)%s*$")
    if key == "" then
        setStatus("Введи лицензионный ключ", Color3.fromRGB(200, 160, 50))
        return
    end

    local uid = tostring(player.UserId)
    setBusy(true)
    setStatus("Проверяем ключ...", Color3.fromRGB(130, 120, 200))

    local ok, resp = pcall(function()
        return httprequest({
            Url    = API .. "/v2/getscript?key=" .. key .. "&uid=" .. uid,
            Method = "GET",
        })
    end)

    if not ok then
        setBusy(false)
        setStatus("Нет соединения. Попробуй VPN (Cloudflare заблокирован)", Color3.fromRGB(210, 80, 80))
        return
    end

    -- Cloudflare error pages (502/503/504/520-530) — tunnel down or overloaded
    -- 530 = Cloudflare "tunnel not found / offline" (most common for dead quick tunnels)
    if resp.StatusCode == 502 or resp.StatusCode == 503 or resp.StatusCode == 504
    or resp.StatusCode == 520 or resp.StatusCode == 521 or resp.StatusCode == 522
    or resp.StatusCode == 530 then
        setBusy(false)
        setStatus("Сервер временно недоступен. Подожди минуту", Color3.fromRGB(210, 150, 50))
        return
    end

    -- Extra safety: if body looks like HTML even with 200 — Cloudflare placeholder
    if resp.StatusCode == 200 and resp.Body and resp.Body:sub(1, 1) == "<" then
        setBusy(false)
        setStatus("Туннель недоступен — обнови URL или подожди", Color3.fromRGB(210, 80, 80))
        return
    end

    if resp.StatusCode == 403 then
        setBusy(false)
        local body = tostring(resp.Body or "")
        -- HTML body = Cloudflare access denied (Russia/region block), not our server
        if body == "" or body:sub(1, 1) == "<" then
            setStatus("Cloudflare заблокирован. Включи VPN и попробуй снова", Color3.fromRGB(210, 80, 80))
        else
            setStatus(body, Color3.fromRGB(210, 80, 80))
        end
        return
    end

    if resp.StatusCode ~= 200 or not resp.Body or resp.Body == "" then
        setBusy(false)
        setStatus("Ошибка сервера: " .. tostring(resp.StatusCode), Color3.fromRGB(210, 80, 80))
        return
    end

    -- Compile check before destroying GUI
    local fn, compileErr = loadstring(resp.Body)
    if not fn then
        setBusy(false)
        setStatus("Ошибка загрузки скрипта", Color3.fromRGB(210, 80, 80))
        warn("[PD Bot] " .. tostring(compileErr))
        return
    end

    -- Queue auto-reconnect on server hop
    local queueFunc = queueonteleport or queue_on_teleport
        or (syn and syn.queue_on_teleport) or function() end

    pcall(function()
        queueFunc([[
local _r=(syn and syn.request) or http_request or request
local _u=tostring(game:GetService("Players").LocalPlayer.UserId)
local _o,_p=pcall(_r,{Url="]] .. API .. [[/v2/getscript?key=]] .. key .. [[&uid=".._u,Method="GET"})
if _o and _p and _p.StatusCode==200 and _p.Body and _p.Body~="" then
    local _f=loadstring(_p.Body)
    if _f then pcall(_f) end
end
]])
    end)

    setStatus("Запускаем...", Color3.fromRGB(70, 200, 120))
    task.wait(0.6)
    root:Destroy()
    pcall(fn)
end)
