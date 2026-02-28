-- ==================== CONSTANTS & CONFIGURATION ====================
local PLACE_ID = 8737602449                            -- Please Donate place ID
local MIN_PLAYERS = 4                                  -- Minimum players in server (overridable from dashboard)
local MAX_PLAYERS_ALLOWED = 24                         -- Maximum players in server (overridable from dashboard)
local SERVER_COOLDOWN_MINS = 60                        -- Minutes to avoid rejoining a visited server (overridable)
local TELEPORT_RETRY_DELAY = 8                         -- Delay between teleport attempts
local TELEPORT_COOLDOWN = 30                           -- Cooldown between failed servers
local SCRIPT_URL = "https://raw.githubusercontent.com/ivankodaria5-ai/plsdonatebot/main/botplsdonate.lua"
local DASH_URL   = "https://tags-film-dry-comments.trycloudflare.com"

local BOOTH_CHECK_POSITION = Vector3.new(165, 0, 311)  -- Center point to search for booths
local MAX_BOOTH_DISTANCE = 92                          -- Max studs from check position
local TYPO_CHANCE = 0.45                               -- 15% chance to send message with typo

local MESSAGES = {
    "hey! donate pls? :)",
    "hi! can u donate?",
    "hello! donation? :D",
    "hey donate maybe?",
    "hi! pls donate im trying to save up",
    "heyy any donations?",
    "hello donate pls",
    "hi! help me out? any robux appreciated",
    "hey! donate? :)",
    "hii pls donate ty",
    "hey can u donate im close to my goal",
    "hello! robux pls?",
    "hi donate pls :D",
    "heyy donation? would mean a lot",
    "hey! pls help",
    "hi! any robux? trying to get something cool",
    "hello donate ty",
    "hey! can u help? even small amount helps",
    "hi pls donate :)",
    "heyy robux pls",
    "hey donate? ty appreciate it",
    "hi! help pls",
    "hello donation pls working towards smth",
    "hey! donate ty :D",
    "hi can u donate?",
    "heyy pls help out any amount works",
    "hey donate pls :)",
    "hi! any donations? been grinding all day",
    "hello robux pls",
    "hey! pls donate"
}

-- Typo variations (3 per message, realistic keyboard mistakes)
local MESSAGE_TYPOS = {
    {"hry! donate pls? :)", "hey! dinate pls? :)", "hey! donate pld? :)"},
    {"hi! csn u donate?", "hi! can u dknate?", "hi! can u donatw?"},
    {"hrllo! donation? :D", "hello! donatiob? :D", "hello! donatipn? :D"},
    {"heu donate maybe?", "hey dontae maybe?", "hey donate maybr?"},
    {"hi! pks donate im trying to save up", "hi! pls donsre im trying to save up", "hi! pls donate im tryinf to save up"},
    {"heyy anu donations?", "heyy any donatiins?", "heyy any donatuons?"},
    {"hrllo donate pls", "hello dinate pls", "hello donate pld"},
    {"hi! hwlp me out? any robux appreciated", "hi! help me oit? any robux appreciated", "hi! help me out? any robix appreciated"},
    {"hry! donate? :)", "hey! dinate? :)", "hey! donatr? :)"},
    {"hii pks donate ty", "hii pls dknate ty", "hii pls donate ry"},
    {"hry can u donate im close to my goal", "hey csn u donate im close to my goal", "hey can u donsre im close to my goal"},
    {"hrllo! robux pls?", "hello! robix pls?", "hello! robux pld?"},
    {"hi dinate pls :D", "hi donate pld :D", "hi donate pla :D"},
    {"heyy donatiom? would mean a lot", "heyy donation? woulf mean a lot", "heyy donatiin? would mean a lot"},
    {"hry! pls help", "hey! pld help", "hey! pls hwlp"},
    {"hi! any robix? trying to get something cool", "hi! any robux? tryinf to get something cool", "hi! any robux? trying to grt something cool"},
    {"hrllo donate ty", "hello dknate ty", "hello donate ry"},
    {"hry! can u help? even small amount helps", "hey! csn u help? even small amount helps", "hey! can u hwlp? even small amount helps"},
    {"hi pld donate :)", "hi pls dknate :)", "hi pls donate :0"},
    {"heyy robix pls", "hryy robux pls", "heyy robux pld"},
    {"hry donate? ty appreciate it", "hey dknate? ty appreciate it", "hey donate? ty apprexiate it"},
    {"hi! hwlp pls", "hi! help pld", "hi! gelp pls"},
    {"hrllo donation pls working towards smth", "hello donatiom pls working towards smth", "hello donation pls workibg towards smth"},
    {"hry! donate ty :D", "hey! dknate ty :D", "hey! donate ry :D"},
    {"hi csn u donate?", "hi can u dinate?", "hi can u donatw?"},
    {"heyy pld help out any amount works", "hryy pls help out any amount works", "heyy pls hwlp out any amount works"},
    {"hry donate pls :)", "hey dknate pls :)", "hey donate pld :)"},
    {"hi! any donatioms? been grinding all day", "hi! any donations? bren grinding all day", "hi! any donations? been grindibg all day"},
    {"hrllo robux pls", "hello robix pls", "hello robux pld"},
    {"hry! pls donate", "hey! pld donate", "hey! pls dknate"}
}

local WAIT_FOR_ANSWER_TIME = 7        -- seconds to wait for reply
local MAX_WAIT_DISTANCE = 10              -- max distance before following player while waiting
-- YES: full words or substrings for longer phrases
local YES_LIST = {
    "yes", "yeah", "yep", "yea", "ya", "yh", "sure", "ok", "okay", "k",
    "bet", "aight", "alright", "fine", "of course", "why not", "ight", "ig",
    "follow", "come", "lead", "lets go", "go", "show me", "where", "lets",
    "ill donate", "im donating", "sure thing", "no problem",
}
-- NO: full words or substrings
local NO_LIST = {
    "no", "nope", "nah", "naur", "n", "pass", "busy", "not now", "not rn",
    "no ty", "no thx", "no thanks", "no thank", "nty", "nah ty",
    "leave", "stop", "go away", "gtfo", "dont", "don't", "never",
    "no way", "im good", "i'm good", "leave me",
}

local MSG_FOLLOW_ME = "follow me!"
local MSG_HERE_IS_HOUSE = "here is my booth!"
local MSG_OK_FINE_POOL = {"ok fine :(", "aw ok :(", "dang ok lol", "oh ok :(", "ok :("}

local SECOND_ATTEMPT_CHANCE = 0.30
local FRUSTRATION_THRESHOLD = 5

local NO_RESPONSE_MSGS = {
    "okay no response...",
    "alright moving on lol",
    "probably afk okay",
    "no answer guess moving on",
    "silence... alright then",
    "not responding, next!",
    "guess they busy okay",
    "okay bye then lol",
}

-- Guilt-trip second message (sent after refusal, no wait for response)
local MSGS_SECOND = {
    "aw ok no worries i guess",
    "oh ok ill keep trying",
    "damn okay maybe next time",
    "np i understand just tryna get some",
    "ok fine sorry for asking lol",
    "alright :( maybe someone else",
}

-- Contextual message pools by target's Raised amount
local MSGS_EMPTY = {
    "hey can u donate? tryna save up",
    "hi donate pls i have nothing yet",
    "anyone donate? literally anything helps",
    "plss donate im so close to my goal",
    "hey could u donate? saving up for something",
    "umm hi could u spare some robux",
    "donate pls im just starting out",
    "hey! help me out? even a little is fine",
}
local MSGS_LOW = {
    "hey we both grinding, support each other?",
    "donate? even like 5 would help fr",
    "hi small donation? any amount is fine",
    "hey could u help me out a bit",
    "we both starting out, donate pls?",
    "bro donate pls i need robux",
    "hey spare some? tryna catch up",
}
local MSGS_MID = {
    "yo ur doing well, spare some for me?",
    "hey nice booth! could u donate?",
    "hi donate pls u seem generous lol",
    "hey looks like ur doing good, help me out?",
    "u got donations u know how it feels, donate?",
    "damn nice raised, share some? lol",
}
local MSGS_RICH = {
    "yo ur rich donate pls",
    "hey ur clearly generous, help me out?",
    "bro u got so much help me lol",
    "ok ur booth doing great mine isnt, donate?",
    "hey big numbers on ur booth share some?",
    "ur doing amazing, spare a lil for me?",
}
local MSGS_LEAVING = {
    "leaving this server soon if anyone wants to donate",
    "bout to hop, anyone wanna donate quick",
    "last chance before i leave lol",
    "changing server soon quick donate?",
}
local COMPLIMENTS = {
    "nice outfit",
    "ur booth looks nice",
    "cool avatar ngl",
    "ur style is fire",
    "love the fit",
    "cute avatar lol",
    "ur booth setup is clean",
    "nice look fr",
}
local MSGS_GOODBYE = {
    "no worries gl with ur booth",
    "all good have fun",
    "np good luck today",
    "ok no worries enjoy the game",
    "all g have a good one",
    "its fine gl",
}
local MSGS_THANKS = {
    "hey just wanted to say thank u for the donation!! that was really nice",
    "bro i had to come back and say THANK YOU means a lot",
    "omg thank you so much!! u made my day fr",
    "seriously thank you ur the best",
    "hey ty so much for the donation!! really appreciate it",
}

-- Dream item goal (chosen once at script start, used in getFirstMsg)
local DREAM_ITEMS = {
    {name = "Headless Horseman", price = 31000},
    {name = "Korblox",           price = 17000},
    {name = "a domino crown",    price = 10300},
    {name = "my dream gamepass", price = 1000},
    {name = "a limited item",    price = 5000},
    {name = "my fav ugc hat",    price = 800},
}
local dreamItem = DREAM_ITEMS[math.random(#DREAM_ITEMS)]
-- NOTE: getNeeded() is defined later (after Stats) to avoid upvalue bug

local FRUSTRATION_MSGS = {
    "today is not my day...",
    "everyone saying no today :(",
    "nobody wants to help today",
    "tough crowd today",
    "sad times...",
    "where are all the kind people?",
    "having bad luck today lol",
    "why everyone say no :(",
}

local JUMP_TIME         = 5
local CIRCLE_COOLDOWN   = 4
local NORMAL_COOLDOWN   = 5
local CIRCLE_STEP_TIME  = 0.1
local TARGET_DISTANCE   = 12
local STUCK_THRESHOLD   = 3
local STUCK_CHECK_TIME  = 4
local MAX_JUMP_TRIES    = 3
local JUMP_DURATION     = 0.8
local MAX_RANDOM_TRIES  = 5
local MAX_STUCK_BEFORE_HOP = 3                         -- Server hop if stuck 3 times in a row
local SPRINT_KEY        = Enum.KeyCode.LeftShift

-- Track consecutive stuck failures
local consecutiveStuckCount = 0
local lastActivityTime      = tick()  -- watchdog: time of last meaningful action
local lastBeggingTime       = tick()  -- watchdog: time of last actual donation request sent
-- Track refusal/no-response streak for frustration messages
local refusalStreak = 0
-- Leaving-soon flag (set ~90s before watchdog-triggered server hop)
local leavingSoon   = false
-- Congrats cooldown: don't spam when many donations fire at once
local lastCongratTs = 0
-- Donors to thank after 2-3 min: { [name] = {ts, thanked} }
local recentDonors  = {}

-- ==================== STATISTICS ====================
local Stats = {
    approached      = 0,
    agreed          = 0,
    refused         = 0,
    no_response     = 0,
    hops            = 0,
    donations       = 0,   -- number of donation events (each time Raised grew)
    robux_gross     = 0,   -- total R$ raised (before Roblox 40% cut)
    raised_current  = 0,   -- current absolute Raised value shown on our booth
}
local sessionStart = os.time()  -- Unix epoch so dashboard timestamps are correct

-- getNeeded() must be AFTER Stats (upvalue lookup at definition time in Lua)
local function getNeeded()
    return math.max(dreamItem.price - Stats.robux_gross, 50)
end

-- ==================== INTERACTION LOG ====================
-- Buffer of per-player conversations; flushed to dashboard every report cycle.
local interactionLog = {}

local function logInteraction(targetName, botMsg, playerReply, outcome)
    table.insert(interactionLog, {
        ts      = os.time(),
        name    = targetName,
        bot     = botMsg,
        reply   = playerReply or "",
        outcome = outcome,    -- "agreed" | "refused" | "no_response" | "left" | "chase_fail"
    })
end

-- ==================== FILE LOGGING SET  ====================
local logLines = {}
local function log(msg)
    local timestamp = os.date("[%Y-%m-%d %H:%M:%S]")
    local logMsg = timestamp .. " " .. msg
    print(logMsg)  -- Still print to console for debugging
    table.insert(logLines, logMsg)
end

local function saveLog()
    local content = table.concat(logLines, "\n")
    writefile("donation_bot.log", content)
end

-- Auto-save log every 30 seconds
task.spawn(function()
    while true do
        task.wait(30)
        saveLog()
    end
end)

-- ==================== SERVICES & HTTP SETUP ====================
local Players               = game:GetService("Players")
local PathfindingService    = game:GetService("PathfindingService")
local TextChatService       = game:GetService("TextChatService")
local ReplicatedStorage     = game:GetService("ReplicatedStorage")
local VirtualInputManager   = game:GetService("VirtualInputManager")
local VirtualUser           = game:GetService("VirtualUser")
local TeleportService       = game:GetService("TeleportService")
local HttpService           = game:GetService("HttpService")
local player                = Players.LocalPlayer
local ignoreList = {}

-- Bot accounts to always ignore
local BOT_ACCOUNTS = {
    ["ExplorerCrusher292"] = true,
    ["ColorCrusher292"] = true,
    ["AquaCrusher292"] = true,
    ["PillageCrusher292"] = true,
    ["BeeCrusher292"] = true,
    ["NetherCrusher292"] = true,
    ["CaveCrusher292"] = true,
    ["CliffCrusher292"] = true,
    ["WildCrusher292"] = true,
    ["TrailCrusher292"] = true,
}

local httprequest = (syn and syn.request) or http and http.request or http_request or (fluxus and fluxus.request) or request
local queueFunc = queueonteleport or queue_on_teleport or (syn and syn.queue_on_teleport) or function() log("[HOP] Queue not supported!") end

-- ==================== SINGLETON GUARD ====================
-- Root cause of duplicates: queueFunc() was called multiple times per hop
-- (from main loop + watchdog firing simultaneously), so N hops = N scripts on next server.
-- Fix:
--   1. queueFunc is only allowed ONCE per Roblox session (PD_HAS_QUEUED flag)
--   2. Singleton with stagger so simultaneous starts resolve to exactly 1 winner
local myInstanceId = tick()

-- Wrap queueFunc so it can only fire ONCE per Roblox session
local _rawQueueFunc = queueFunc
queueFunc = function(code)
    if getgenv and getgenv().PD_HAS_QUEUED then
        log("[SINGLETON] queueFunc already called this session — skipping duplicate")
        return
    end
    if getgenv then getgenv().PD_HAS_QUEUED = true end
    _rawQueueFunc(code)
end

if getgenv then
    -- Reset queue flag for this new server session
    getgenv().PD_HAS_QUEUED = false

    local prevId = getgenv().PD_RUNNING_ID
    if prevId and prevId ~= 0 then
        log("[SINGLETON] Replacing previous instance " .. tostring(prevId))
    end
    getgenv().PD_RUNNING_ID = myInstanceId

    -- Stagger: give other simultaneous instances a moment to also set their ID,
    -- then re-check — the last one to set wins and all others exit their loops
    task.wait(0.05 + math.random() * 0.15)
    if getgenv().PD_RUNNING_ID ~= myInstanceId then
        -- Lost the race — another instance started after us, let it run
        log("[SINGLETON] Lost startup race — exiting (another instance is running)")
        return  -- stops this script execution entirely
    end
    log("[SINGLETON] Won startup race — this is the active instance (id=" .. myInstanceId .. ")")
end

local function isActiveInstance()
    if not getgenv then return true end
    return getgenv().PD_RUNNING_ID == myInstanceId
end

-- ==================== VISITED SERVERS (persistent across hops) ====================
local VISITED_FOLDER = "ServerHop"
local VISITED_FILE   = VISITED_FOLDER .. "/pd_visited_" .. tostring(PLACE_ID) .. ".json"

local function loadVisited()
    pcall(function() if not isfolder(VISITED_FOLDER) then makefolder(VISITED_FOLDER) end end)
    if pcall(function() return isfile(VISITED_FILE) end) and isfile(VISITED_FILE) then
        local ok, data = pcall(function() return HttpService:JSONDecode(readfile(VISITED_FILE)) end)
        if ok and type(data) == "table" then return data end
    end
    return {}
end

local function saveVisited(data)
    pcall(function() writefile(VISITED_FILE, HttpService:JSONEncode(data)) end)
end

local function pruneVisited(data, cooldownMins)
    local cutoff = tick() - (cooldownMins * 60)
    local pruned = {}
    for jobId, ts in pairs(data) do
        if ts > cutoff then pruned[jobId] = ts end
    end
    return pruned
end

local function wasVisited(data, jobId, cooldownMins)
    local ts = data[jobId]
    return ts ~= nil and (tick() - ts) < (cooldownMins * 60)
end

-- ==================== DASHBOARD CONFIG FETCH ====================
local function fetchDashConfig()
    if DASH_URL == "" then return end
    local ok, resp = pcall(function()
        return httprequest({ Url = DASH_URL .. "/pd_config/" .. tostring(player.UserId) })
    end)
    if ok and resp and resp.StatusCode == 200 and resp.Body then
        local parseOk, cfg = pcall(function() return HttpService:JSONDecode(resp.Body) end)
        if parseOk and type(cfg) == "table" then
            if type(cfg.min_players) == "number" then MIN_PLAYERS = cfg.min_players end
            if type(cfg.max_players) == "number" then MAX_PLAYERS_ALLOWED = cfg.max_players end
            if type(cfg.server_cooldown) == "number" then SERVER_COOLDOWN_MINS = cfg.server_cooldown end
            if cfg.clear_history then
                saveVisited({})
                log("[CONFIG] Server visit history cleared from dashboard")
            end
            log(string.format("[CONFIG] Loaded from dashboard: min=%d max=%d cooldown=%dmin",
                MIN_PLAYERS, MAX_PLAYERS_ALLOWED, SERVER_COOLDOWN_MINS))
        end
    end
end

-- Fetch config at startup
fetchDashConfig()

-- Wait for character to fully load
if not player.Character then
    log("Waiting for character to load...")
    player.CharacterAdded:Wait()
end
player.Character:WaitForChild("HumanoidRootPart")
log("Character loaded!")

-- ==================== ANTI-AFK: Error 278 prevention ====================
-- Error 278 = "Disconnected for being idle 20 minutes"
-- VirtualUser simulates controller input so Roblox never considers the bot idle.
player.Idled:Connect(function()
    VirtualUser:CaptureController()
    VirtualUser:ClickButton2(Vector2.new())
    log("[AFK] Anti-AFK fired — idle kick prevented (Error 278)")
end)

-- Backup: click every 10 minutes regardless (belt + suspenders)
task.spawn(function()
    while true do
        task.wait(600)
        pcall(function()
            VirtualUser:CaptureController()
            VirtualUser:ClickButton2(Vector2.new())
        end)
    end
end)
log("[AFK] Anti-AFK running (VirtualUser)")

-- ==================== AUTO-RECONNECT QUEUE: Error 277 recovery ====================
-- Error 277 = lost connection / network drop.
-- queueonteleport queues a script to run after ANY next join/teleport,
-- including when the player clicks "Reconnect" on the 277 screen.
-- So pressing Reconnect automatically restarts the bot — no manual reinjection needed.
local _reconnectScript = [[
local _req = (syn and syn.request) or http and http.request or http_request or (fluxus and fluxus.request) or request
local _ok, _res = pcall(_req, {Url = "]] .. SCRIPT_URL .. [["})
if _ok and _res and _res.Body and _res.Body ~= "" then
    loadstring(_res.Body)()
else
    pcall(function() loadstring(game:HttpGet("]] .. SCRIPT_URL .. [[", true))() end)
end
]]
pcall(function() queueFunc(_reconnectScript) end)
log("[RECONNECT] Script queued — clicking Reconnect on 277 screen will auto-restart bot")

-- ==================== AUTO-RECONNECT: Error 267 (Kick) recovery ====================
-- Error 267 = "You have been kicked by this experience or its moderators"
-- Unlike Error 277 (has "Reconnect" button), Error 267 only has a "Leave" button.
-- Strategy: detect the kick dialog via CoreGui the moment it appears,
-- immediately call TeleportService:Teleport() to "escape" before the kick
-- fully closes the connection — this fires queueonteleport so the script
-- auto-restarts on the new server without any manual action.
local function startKickRecovery()
    task.spawn(function()
        local recovering = false
        while true do
            task.wait(1.5)
            if recovering then continue end
            pcall(function()
                local cg = game:GetService("CoreGui")
                -- Scan all GUI text for Error 267 / kicked indicators
                local kicked267 = false
                for _, elem in pairs(cg:GetDescendants()) do
                    if elem:IsA("TextLabel") or elem:IsA("TextBox") then
                        local t = string.lower(tostring(elem.Text or ""))
                        if string.find(t, "267")
                        or string.find(t, "kicked by this experience")
                        or string.find(t, "kicked by its moderators") then
                            kicked267 = true
                            break
                        end
                    end
                end
                if not kicked267 then return end

                recovering = true
                log("[267] Kick detected — attempting teleport escape before disconnect...")

                -- Re-queue script in case prior queue was consumed (singleton guard
                -- resets PD_HAS_QUEUED each new server, but we force it here just in case)
                if getgenv then getgenv().PD_HAS_QUEUED = false end
                pcall(function() queueFunc(_reconnectScript) end)

                -- Immediately teleport — if this fires before Roblox closes the
                -- connection it behaves like a normal server hop and the queued
                -- script will auto-execute on the next server.
                pcall(function() TeleportService:Teleport(PLACE_ID, player) end)
                task.wait(3)

                -- Fallback: if teleport didn't fire in 3s, click the Leave button.
                -- The queued script won't fire via queueonteleport in this case,
                -- but the user will return to Roblox home and can manually rejoin.
                for _, btn in pairs(cg:GetDescendants()) do
                    if btn:IsA("TextButton") then
                        local bt = string.lower(tostring(btn.Text or ""))
                        if bt == "leave" or bt == "ok" or bt == "okay" then
                            btn.MouseButton1Click:Fire()
                            pcall(function() btn:Activate() end)
                            log("[267] Fallback: clicked Leave button")
                            break
                        end
                    end
                end
            end)
        end
    end)
end

startKickRecovery()
log("[267] Kick recovery monitor started (Error 267 auto-teleport)")

-- ==================== BOOTH CLAIMER ====================
local function getBoothLocation()
    local boothLocation = nil
    pcall(function()
        boothLocation = player:WaitForChild('PlayerGui', 5)
            :WaitForChild('MapUIContainer', 5)
            :WaitForChild('MapUI', 5)
    end)
    if not boothLocation then
        boothLocation = workspace:WaitForChild('MapUI', 5)
    end
    return boothLocation
end

local function findUnclaimedBooths(boothLocation)
    local unclaimed = {}
    local boothUI = boothLocation:WaitForChild("BoothUI", 5)
    local interactions = workspace:WaitForChild("BoothInteractions", 5)
    if not boothUI or not interactions then return unclaimed end
    local mainPos2D = Vector3.new(BOOTH_CHECK_POSITION.X, 0, BOOTH_CHECK_POSITION.Z)
    for _, uiFrame in ipairs(boothUI:GetChildren()) do
        if uiFrame:FindFirstChild("Details") and uiFrame.Details:FindFirstChild("Owner") then
            if uiFrame.Details.Owner.Text == "unclaimed" then
                local boothNum = tonumber(uiFrame.Name:match("%d+"))
                if boothNum then
                    for _, interact in ipairs(interactions:GetChildren()) do
                        if interact:GetAttribute("BoothSlot") == boothNum then
                            local pos2D = Vector3.new(interact.Position.X, 0, interact.Position.Z)
                            local distance = (pos2D - mainPos2D).Magnitude
                            if distance < MAX_BOOTH_DISTANCE then
                                table.insert(unclaimed, {
                                    number = boothNum,
                                    position = interact.Position,
                                    cframe = interact.CFrame,
                                    distance = distance
                                })
                            end
                            break
                        end
                    end
                end
            end
        end
    end
    table.sort(unclaimed, function(a, b) return a.distance < b.distance end)
    return unclaimed
end

local function teleportTo(cframe)
    local root = player.Character:FindFirstChild("HumanoidRootPart")
    if root then
        root.CFrame = cframe
        task.wait(0.1)
    end
end

local function verifyClaim(boothLocation, boothNum)
    local boothUI = boothLocation.BoothUI or boothLocation:FindFirstChild("BoothUI")
    if not boothUI then return false end
    local boothFrame = boothUI:FindFirstChild("BoothUI" .. boothNum)
    if not boothFrame then return false end
    local details = boothFrame:FindFirstChild("Details")
    if not details then return false end
    local owner = details:FindFirstChild("Owner")
    if not owner then return false end
    local ownerText = owner.Text
    return string.find(ownerText, player.DisplayName) ~= nil or string.find(ownerText, player.Name) ~= nil
end

local function walkRandomDirection(studs, waitTime)
    local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
    local humanoid = player.Character and player.Character:FindFirstChild("Humanoid")
    if root and humanoid then
        local angle = math.random() * math.pi * 2
        local movePos = root.Position + Vector3.new(math.cos(angle)*studs, 0, math.sin(angle)*studs)
        humanoid:MoveTo(movePos)
        task.wait(waitTime)
    end
end

local claimedBoothNum = nil  -- set once per script session when booth is claimed

-- Safely get the world position of a booth interaction object (Part or Model)
local function getInteractPos(interact)
    local ok, pos = pcall(function()
        if interact:IsA("BasePart") then
            return interact.Position
        elseif interact.PrimaryPart then
            return interact.PrimaryPart.Position
        else
            return interact:GetPivot().Position
        end
    end)
    return ok and pos or nil
end

-- Check BoothUI to see if this player already owns a booth; returns position or nil
local function findOwnedBooth(boothLocation)
    local boothUI = boothLocation and (boothLocation.BoothUI or boothLocation:FindFirstChild("BoothUI"))
    if not boothUI then return nil end
    local interactions = workspace:FindFirstChild("BoothInteractions")
    if not interactions then return nil end
    local myName    = tostring(player.Name)
    local myDisplay = tostring(player.DisplayName)
    for _, uiFrame in ipairs(boothUI:GetChildren()) do
        if uiFrame:IsA("Frame") then
            local details = uiFrame:FindFirstChild("Details")
            local owner   = details and details:FindFirstChild("Owner")
            if owner then
                local txt = tostring(owner.Text or "")
                -- plain=true: no Lua pattern issues with special chars in names
                local isOwner = string.find(txt, myName, 1, true)
                               or string.find(txt, myDisplay, 1, true)
                if isOwner then
                    local boothNum = tonumber(uiFrame.Name:match("%d+"))
                    if boothNum then
                        for _, interact in ipairs(interactions:GetChildren()) do
                            if interact:GetAttribute("BoothSlot") == boothNum then
                                local pos = getInteractPos(interact)
                                if pos then
                                    log("[BOOTH] Already own booth #" .. boothNum .. " — reusing")
                                    claimedBoothNum = boothNum
                                    return Vector3.new(pos.X, pos.Y, pos.Z)
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    return nil
end

local BOOTH_CLAIM_DEADLINE = nil  -- set on first call

local function claimBooth(retryCount)
    retryCount = retryCount or 0
    -- Global deadline: max 90s total for booth claiming across all retries
    if retryCount == 0 then BOOTH_CLAIM_DEADLINE = tick() + 90 end
    if BOOTH_CLAIM_DEADLINE and tick() > BOOTH_CLAIM_DEADLINE then
        log("[BOOTH] ⏰ 90s deadline exceeded — skipping booth, using fallback")
        return nil
    end
    log("=== BOOTH CLAIMER ===")

    -- Fast path: booth already claimed in this Lua session
    if claimedBoothNum then
        log("[BOOTH] Booth #" .. claimedBoothNum .. " already claimed this session — skipping")
        local boothLocation = getBoothLocation()
        if boothLocation then
            local existing = findOwnedBooth(boothLocation)
            if existing then return existing end
            -- claim was lost somehow (edge case) — fall through to re-claim
            claimedBoothNum = nil
            log("[BOOTH] Booth was lost — re-claiming...")
        end
    end

    local boothLocation = getBoothLocation()
    if not boothLocation then
        log("[BOOTH] ERROR: Could not find booth UI!")
        return nil
    end

    -- Double-check via UI scan
    local existing = findOwnedBooth(boothLocation)
    if existing then
        log("[BOOTH] Already own a booth — reusing it")
        return existing
    end

    local unclaimed = findUnclaimedBooths(boothLocation)
    log("[BOOTH] Found " .. #unclaimed .. " unclaimed booth(s)")
    
    if #unclaimed == 0 then
        log("[BOOTH] ERROR: No booths available!")
        return nil
    end
    
    -- Get BoothInteractions reference
    local boothInteractions = workspace:FindFirstChild("BoothInteractions")
    if not boothInteractions then
        log("[BOOTH] ERROR: BoothInteractions not found in Workspace!")
        return nil
    end
    
    -- Try each booth one by one
    for i, booth in ipairs(unclaimed) do
        -- Check deadline on every booth attempt
        if BOOTH_CLAIM_DEADLINE and tick() > BOOTH_CLAIM_DEADLINE then
            log("[BOOTH] ⏰ Deadline hit mid-loop — aborting, using fallback")
            return nil
        end
        log("═══════════════════════════════════════")
        log("[BOOTH] Attempt " .. i .. "/" .. #unclaimed .. " - Trying Booth #" .. booth.number)
        
        -- Find the ProximityPrompt for THIS specific booth
        local myBoothInteraction = nil
        for _, interact in ipairs(boothInteractions:GetChildren()) do
            if interact:GetAttribute("BoothSlot") == booth.number then
                myBoothInteraction = interact
                break
            end
        end
        
        if not myBoothInteraction then
            log("[BOOTH] ERROR: Couldn't find interaction object for booth #" .. booth.number)
            continue
        end
        
        -- Find ProximityPrompt in this booth's interaction
        local claimPrompt = nil
        for _, child in ipairs(myBoothInteraction:GetChildren()) do
            if child:IsA("ProximityPrompt") and child.Name == "Claim" then
                claimPrompt = child
                break
            end
        end
        
        if not claimPrompt then
            log("[BOOTH] ERROR: No Claim ProximityPrompt found for booth #" .. booth.number)
            continue
        end
        
        -- Try claiming this booth up to 3 times
        local claimed = false
        for attempt = 1, 3 do
            -- Teleport closer to the ProximityPrompt's parent
            local targetCFrame = myBoothInteraction.CFrame * CFrame.new(0, 0, 2)
            teleportTo(targetCFrame)
            task.wait(0.5)
            
            -- Trigger ProximityPrompt
            local success, err = pcall(function()
                fireproximityprompt(claimPrompt)
            end)
            
            if not success then
                log("[BOOTH] ProximityPrompt trigger failed: " .. tostring(err))
            end
            
            -- Wait for server to process
            task.wait(2)
            
            -- Verify claim
            claimed = verifyClaim(boothLocation, booth.number)
            if claimed then
                claimedBoothNum = booth.number  -- remember: don't claim again this session
                log("╔═══════════════════════════════════════")
                log("║ [SUCCESS] CLAIMED BOOTH #" .. booth.number .. "!")
                log("║ Position: " .. tostring(booth.position))
                log("╚═══════════════════════════════════════")
                saveLog()
                return booth.position
            else
                if attempt < 3 then
                    log("[BOOTH] Claim didn't register, retrying...")
                end
            end
        end
        
        log("[BOOTH] Failed after 3 attempts, moving away from booth...")
        walkRandomDirection(20, 2)
        log("[BOOTH] Moving to next booth...")
    end
    
    log("[BOOTH] All booths tried, moving away before retrying...")
    walkRandomDirection(30, 3)
    retryCount = (retryCount or 0) + 1
    if retryCount >= 3 then
        log("[BOOTH] ⚠️ Failed after 3 full cycles — using fallback position and continuing")
        return nil
    end
    log("[BOOTH] Retrying from start (cycle " .. retryCount .. "/3)...")
    return claimBooth(retryCount)
end

-- ── Startup server viability check ───────────────────────────────────────────
-- Skip booth claim entirely if the server has too few players.
-- This prevents wasting 90s on an empty server arrived via matchmaking.
do
    task.wait(3)  -- give PlayerList a moment to populate after join
    local startupCount = #Players:GetPlayers()
    local currentJobId = tostring(game.JobId)
    if startupCount < MIN_PLAYERS then
        log(string.format("[STARTUP] Only %d players (min=%d) — server too empty, hopping now!", startupCount, MIN_PLAYERS))
        local RELOAD = [[
local httprequest = (syn and syn.request) or http and http.request or http_request or (fluxus and fluxus.request) or request
local response = httprequest({Url = "]] .. SCRIPT_URL .. [["})
if response and response.Body then loadstring(response.Body)()
else loadstring(game:HttpGet("]] .. SCRIPT_URL .. [["))() end
]]
        queueFunc(RELOAD)
        pcall(function() TeleportService:Teleport(PLACE_ID, player) end)
        task.wait(5)
        pcall(function() player:Kick("Joining better server...") end)
        task.wait(60)
    end
    log(string.format("[STARTUP] Server OK: %d players — proceeding", startupCount))
end

-- CLAIM BOOTH AND SET HOME POSITION
local HOME_POSITION = claimBooth()
if not HOME_POSITION then
    log("[BOOTH] Failed to claim booth! Using default position.")
    HOME_POSITION = Vector3.new(94, 4, 281)  -- Fallback position
end
log("=== HOME SET TO: " .. tostring(HOME_POSITION) .. " ===")
saveLog()

-- ==================== BOOTH FADE MONITOR ====================
-- "YourBooth is fading out" = game unclaims booth when bot walks away.
-- Checks every 20s; requires 2 CONSECUTIVE misses before re-claiming
-- to avoid false positives from BoothUI temporarily not loading.
local boothMissStreak = 0  -- consecutive checks where booth wasn't found

task.spawn(function()
    task.wait(25)  -- Give initial claim + BoothUI time to settle
    while isActiveInstance() do
        task.wait(20)
        if not isActiveInstance() then break end
        pcall(function()
            local boothLocation = getBoothLocation()
            if not boothLocation then return end  -- UI not loaded, skip
            local existing = findOwnedBooth(boothLocation)
            if existing then
                -- Booth alive — update position and reset streak
                HOME_POSITION = existing
                boothMissStreak = 0
            else
                boothMissStreak = boothMissStreak + 1
                log("[BOOTH-MONITOR] Booth not found (miss #" .. boothMissStreak .. "/2)")
                -- Only re-claim after 2 consecutive misses (~40s) to avoid false triggers
                if boothMissStreak >= 2 then
                    boothMissStreak = 0
                    log("[BOOTH-MONITOR] Booth confirmed gone — reclaiming...")
                    claimedBoothNum = nil
                    BOOTH_CLAIM_DEADLINE = nil
                    local newPos = claimBooth()
                    if newPos then
                        HOME_POSITION = newPos
                        log("[BOOTH-MONITOR] Re-claimed OK: " .. tostring(HOME_POSITION))
                    else
                        log("[BOOTH-MONITOR] Re-claim failed — will retry next cycle")
                    end
                end
            end
        end)
    end
end)

-- ==================== SOCIAL BOT LOGIC ====================
-- ========= CHAT LOGGER + RESPONSE DETECTION =========
local lastSpeaker = nil
local lastMessage = nil
local responseReceived = false

local function resetResponse()
    lastSpeaker = nil
    lastMessage = nil
    responseReceived = false
end

-- Shared handler: runs on every chat message from any player
local function onAnyChat(speakerName, msgLower)
    if speakerName == player.Name then return end
    -- Response detection (for active waitForResponse)
    lastSpeaker      = speakerName
    lastMessage      = msgLower
    responseReceived = true
    -- Mention detection: did they write our name?
    local myNameLow     = string.lower(player.Name)
    local myDisplayLow  = string.lower(player.DisplayName)
    if string.find(msgLower, myNameLow, 1, true)
    or (myDisplayLow ~= myNameLow and string.find(msgLower, myDisplayLow, 1, true)) then
        onMentioned(speakerName)
    end
end

-- Hook Legacy Chat
spawn(function()
    local legacy = ReplicatedStorage:WaitForChild("DefaultChatSystemChatEvents", 5)
    if legacy then
        local ev = legacy:FindFirstChild("OnMessageDoneFiltering")
        if ev then
            ev.OnClientEvent:Connect(function(data)
                local speaker = data.FromSpeaker
                local msg = (data.Message or data.OriginalMessage or ""):lower()
                log(speaker .. ": " .. msg)
                onAnyChat(speaker, msg)
            end)
        end
    end
end)

-- Hook TextChatService
spawn(function()
    if TextChatService.ChatVersion == Enum.ChatVersion.TextChatService then
        local channels = TextChatService:WaitForChild("TextChannels", 10)
        if channels then
            local function hook(ch)
                if ch:IsA("TextChannel") then
                    ch.MessageReceived:Connect(function(msgObj)
                        local source = msgObj.TextSource
                        if source then
                            local speaker = source.Name
                            local text = (msgObj.Text or ""):lower()
                            log(speaker .. ": " .. text)
                            onAnyChat(speaker, text)
                        end
                    end)
                end
            end
            for _, ch in pairs(channels:GetChildren()) do hook(ch) end
            channels.ChildAdded:Connect(hook)
        end
    end
end)

-- Your own chat (just in case)
player.Chatted:Connect(function(msg)
    log(player.Name .. ": " .. msg)
end)

-- ========= MOVEMENT & DANCE =========
local DIRECTION_KEYS = {
    {Enum.KeyCode.W}, {Enum.KeyCode.W, Enum.KeyCode.D}, {Enum.KeyCode.D},
    {Enum.KeyCode.D, Enum.KeyCode.S}, {Enum.KeyCode.S}, {Enum.KeyCode.S, Enum.KeyCode.A},
    {Enum.KeyCode.A}, {Enum.KeyCode.A, Enum.KeyCode.W},
}

local function startCircleDance(duration)
    log("[CIRCLE] Starting circle dance...")
    VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Space, false, game)
    local startTime = tick()
    local step = 1
    task.spawn(function()
        while tick() - startTime < duration do
            for _, k in DIRECTION_KEYS[step] do VirtualInputManager:SendKeyEvent(true, k, false, game) end
            task.wait(CIRCLE_STEP_TIME)
            for _, k in DIRECTION_KEYS[step] do VirtualInputManager:SendKeyEvent(false, k, false, game) end
            step = step % 8 + 1
        end
        VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Space, false, game)
        log("[CIRCLE] Done")
    end)
end

-- Wait with anti-AFK movement (circle dance every 10 seconds)
local function waitWithMovement(duration)
    local elapsed = 0
    while elapsed < duration do
        local waitTime = math.min(10, duration - elapsed)
        task.wait(waitTime)
        elapsed = elapsed + waitTime
        
        -- Do a quick circle dance if we have more time to wait
        if elapsed < duration then
            startCircleDance(3)
            task.wait(3)
            elapsed = elapsed + 3
        end
    end
end

local isSprinting = false

-- Forward declaration so performMove can call it
local serverHop

local function startSprinting()
    if isSprinting then return end
    VirtualInputManager:SendKeyEvent(true, SPRINT_KEY, false, game)
    isSprinting = true
end

local function stopSprinting()
    if not isSprinting then return end
    VirtualInputManager:SendKeyEvent(false, SPRINT_KEY, false, game)
    isSprinting = false
end

-- FIXED performMove & chasePlayer to handle target disappearing mid-chase
local function performMove(humanoid, root, getPos, sprint)
    if sprint then startSprinting() end
    local lastPos   = root.Position
    local stuckTime = 0
    local jumpTries = 0
    local randTries = 0
    local moveStart = tick()  -- total move timeout

    while true do
        task.wait(0.1)
        -- Hard timeout: give up chasing after 60 seconds to avoid infinite loops
        if tick() - moveStart > 60 then
            log("[MOVE] Chase timeout (60s) — giving up on target")
            if sprint then stopSprinting() end
            return false
        end
        local pos = getPos()
        if not pos then  -- Target lost mid-move
            log("[MOVE] Target lost mid-chase! Stopping movement.")
            if sprint then stopSprinting() end
            return false
        end
        if (root.Position - pos).Magnitude <= TARGET_DISTANCE then
            if sprint then stopSprinting() end
            -- Reset stuck counter on successful movement
            consecutiveStuckCount = 0
            return true
        end

        humanoid:MoveTo(pos)
        local moved = (root.Position - lastPos).Magnitude
        if moved < STUCK_THRESHOLD then 
            stuckTime += 0.1 
        else 
            stuckTime = 0
            lastPos = root.Position 
        end

        if stuckTime >= STUCK_CHECK_TIME then
            if jumpTries < MAX_JUMP_TRIES then
                jumpTries += 1
                log("[ANTI-STUCK] Jump unstuck #"..jumpTries)
                VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Space, false, game)
                task.wait(JUMP_DURATION)
                VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Space, false, game)
                task.wait(0.5)
            else
                randTries += 1
                log("[ANTI-STUCK] Random dodge #"..randTries)
                local a = math.random() * math.pi * 2
                local dodge = pos + Vector3.new(math.cos(a)*80, 0, math.sin(a)*80)
                humanoid:MoveTo(dodge)
                task.wait(3)
                if randTries >= MAX_RANDOM_TRIES then
                    log("[ANTI-STUCK] Failed to unstuck after all attempts!")
                    consecutiveStuckCount = consecutiveStuckCount + 1
                    log("[ANTI-STUCK] Consecutive stuck count: " .. consecutiveStuckCount .. "/" .. MAX_STUCK_BEFORE_HOP)
                    
                    if consecutiveStuckCount >= MAX_STUCK_BEFORE_HOP then
                        log("[ANTI-STUCK] Too many stuck failures! Initiating server hop...")
                        log("[ANTI-STUCK] Saving log before hop...")
                        pcall(saveLog)  -- Use pcall in case it errors
                        log("[ANTI-STUCK] Stopping sprint...")
                        if sprint then stopSprinting() end
                        log("[ANTI-STUCK] Calling serverHop(true) now...")
                        -- Don't return! Let serverHop's infinite loop take over
                        serverHop(true)
                        -- Should never reach here since serverHop never returns
                        log("[ANTI-STUCK] ERROR: serverHop returned unexpectedly!")
                        return false
                    end
                    
                    if sprint then stopSprinting() end
                    return false
                end
            end
            stuckTime = 0
            lastPos = root.Position
        end
    end
end

local function chasePlayer(t)
    if not t.Character or not t.Character:FindFirstChild("HumanoidRootPart") then return false end
    if not player.Character then player.CharacterAdded:Wait(); task.wait(2) end
    local h = player.Character:FindFirstChild("Humanoid")
    local r = player.Character:FindFirstChild("HumanoidRootPart")
    if not h or not r then return false end
    log("[CHASE] Going to " .. t.Name .. " (approaching from front)")

    local function safeGetPos()
        local targetHRP = t.Character and t.Character:FindFirstChild("HumanoidRootPart")
        if not targetHRP then return nil end
        -- Aim for a position 4 studs in front of the target's face
        return targetHRP.Position + targetHRP.CFrame.LookVector * 4
    end

    return performMove(h, r, safeGetPos, true)
end

local function returnHome()
    if not player.Character then player.CharacterAdded:Wait(); task.wait(2) end
    local h = player.Character:FindFirstChild("Humanoid")
    local r = player.Character:FindFirstChild("HumanoidRootPart")
    if not h or not r then return false end
    log("[HOME] Returning home...")
    return performMove(h, r, function() return HOME_POSITION end, false)
end

local function faceTargetBriefly(t)
    if not player.Character or not t.Character or not t.Character:FindFirstChild("HumanoidRootPart") then return end
    local hrp = player.Character:FindFirstChild("HumanoidRootPart")
    if not hrp then return end
    local p = t.Character.HumanoidRootPart.Position
    local look = Vector3.new(p.X, hrp.Position.Y, p.Z)
    hrp.CFrame = CFrame.new(hrp.Position, look)
end

local function sendChat(msg)
    -- Make chat non-blocking to prevent hangs from SendAsync
    task.spawn(function()
        if TextChatService.ChatVersion == Enum.ChatVersion.TextChatService then
            local ch = TextChatService.TextChannels.RBXGeneral
            if ch then pcall(function() ch:SendAsync(msg) end) end
        end
        local say = ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents")
                    and ReplicatedStorage.DefaultChatSystemChatEvents:FindFirstChild("SayMessageRequest")
        if say then pcall(function() say:FireServer(msg, "All") end) end
    end)
end

-- Count words in a string
local function countWords(s)
    local count = 1
    for _ in s:gmatch("%s+") do count = count + 1 end
    return count
end

-- Send chat with typing delay (simulates human typing speed)
local function sendChatTyped(msg)
    local words = countWords(msg)
    local delay
    if words <= 3 then
        delay = math.random() * 0.3 + 0.5   -- 0.5–0.8s
    elseif words <= 8 then
        delay = math.random() * 0.8 + 1.0   -- 1.0–1.8s
    else
        delay = math.random() * 1.0 + 2.0   -- 2.0–3.0s
    end
    task.wait(delay)
    sendChat(msg)
end

-- Occasional natural movement between targets (no dance)
local function doIdleAction()
    local roll = math.random()
    if roll < 0.12 then
        -- short jump
        VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Space, false, game)
        task.wait(0.3)
        VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Space, false, game)
    elseif roll < 0.18 then
        -- brief pause
        task.wait(math.random() * 0.8 + 0.3)
    end
end

-- ========= MENTION SYSTEM =========
-- If someone writes the bot's name in chat, bot replies quickly and approaches them
local mentionQueue   = {}  -- { [userId] = true }
local mentionReplyCd = {}  -- { [userId] = tick() } per-player cooldown

local MENTION_REPLIES = {
    "yeah?",
    "hi!",
    "yes?",
    "hey!",
    "what's up",
    "yea?",
    "u called?",
    "yeah what's up",
    "oh hey!",
}

local function onMentioned(speakerName)
    if speakerName == player.Name then return end
    local mentioned = nil
    for _, p in ipairs(Players:GetPlayers()) do
        if p.Name == speakerName then mentioned = p; break end
    end
    if not mentioned then return end
    local uid = mentioned.UserId
    -- 30s per-player cooldown so bot doesn't spam replies
    local now = tick()
    if mentionReplyCd[uid] and now - mentionReplyCd[uid] < 30 then return end
    mentionReplyCd[uid] = now
    -- Prioritise this player for next approach
    mentionQueue[uid] = true
    ignoreList[uid]   = nil  -- remove from ignore if they were there
    log("[MENTION] " .. speakerName .. " mentioned bot — queued for priority approach")
    -- Quick natural reply with short random delay (looks human)
    task.spawn(function()
        task.wait(math.random() * 1.0 + 0.4)
        sendChat(MENTION_REPLIES[math.random(#MENTION_REPLIES)])
    end)
end

local function findClosest()
    if not player.Character then return nil end
    local root = player.Character:FindFirstChild("HumanoidRootPart")
    if not root then return nil end
    local allPlayers = Players:GetPlayers()
    if not allPlayers then return nil end

    -- Priority: players who mentioned the bot by name
    for uid, _ in pairs(mentionQueue) do
        for _, p in ipairs(allPlayers) do
            if p.UserId == uid and p ~= player and not BOT_ACCOUNTS[p.Name]
               and p.Character and p.Character:FindFirstChild("HumanoidRootPart") then
                mentionQueue[uid] = nil
                log(string.format("[FIND] Priority target (mentioned bot): %s", p.Name))
                return p
            end
        end
        mentionQueue[uid] = nil  -- player left, clean up
    end

    -- Normal: closest player not in ignoreList
    local best, bestDist = nil, math.huge
    for _, p in ipairs(allPlayers) do
        if p ~= player
            and p.UserId
            and not ignoreList[p.UserId]
            and not BOT_ACCOUNTS[p.Name]
            and p.Character
        then
            local hrp = p.Character:FindFirstChild("HumanoidRootPart")
            if hrp then
                local dist = (hrp.Position - root.Position).Magnitude
                if dist < bestDist then
                    bestDist = dist
                    best = p
                end
            end
        end
    end
    if best then
        log(string.format("[FIND] Closest: %s (%.1f studs)", best.Name, bestDist))
    end
    return best
end

-- ========= MESSAGE WITH TYPO CHANCE =========
local function getRandomMessage()
    local msgIndex = math.random(#MESSAGES)
    if math.random() < TYPO_CHANCE then
        return MESSAGE_TYPOS[msgIndex][math.random(3)]
    else
        return MESSAGES[msgIndex]
    end
end

-- ========= CONTEXT-AWARE FIRST MESSAGE =========

-- Read the Raised amount from a target player's booth (from our own PlayerGui copy of the BoothUI)
local function getPlayerRaised(t)
    local ok, result = pcall(function()
        local gui = player.PlayerGui
        local mc = gui:FindFirstChild("MapUIContainer") or workspace:FindFirstChild("MapUIContainer")
        if not mc then return nil end
        local mapUI = mc:FindFirstChild("MapUI")
        if not mapUI then return nil end
        local bui = mapUI:FindFirstChild("BoothUI")
        if not bui then return nil end
        local tName    = tostring(t.Name)
        local tDisplay = tostring(t.DisplayName)
        for _, frame in ipairs(bui:GetChildren()) do
            local det   = frame:FindFirstChild("Details")
            local owner = det and det:FindFirstChild("Owner")
            if owner then
                local txt = tostring(owner.Text or "")
                if string.find(txt, tName, 1, true) or string.find(txt, tDisplay, 1, true) then
                    local raised = det:FindFirstChild("Raised")
                    if raised then
                        local num = tostring(raised.Text or "0"):split(" ")[1]:gsub(",", "")
                        return tonumber(num) or 0
                    end
                end
            end
        end
        return nil
    end)
    return ok and result or nil
end

local function getMsgCategory(raised)
    if raised == nil or raised == 0 then return "empty" end
    if raised <= 500  then return "low"   end
    if raised <= 2000 then return "mid"   end
    return "rich"
end

-- 35% chance to include player's name in message (varied prefixes)
local function addName(msg, t)
    if math.random(20) <= 7 then
        local prefixes = {"hey " .. t.Name .. " ", t.Name .. " ", "yo " .. t.Name .. " "}
        return prefixes[math.random(#prefixes)] .. msg
    end
    return msg
end

-- Build the opening donation request (context-aware pool + optional dream-item line)
local function getFirstMsg(t)
    local raised = getPlayerRaised(t)
    local cat    = getMsgCategory(raised)

    -- Dream-item line appears ~25% of the time instead of pool message
    local useDreamLine = math.random(4) == 1
    local pool
    if cat == "empty" then pool = MSGS_EMPTY
    elseif cat == "low" then pool = MSGS_LOW
    elseif cat == "mid" then pool = MSGS_MID
    else                     pool = MSGS_RICH
    end

    local base
    if leavingSoon and math.random(2) == 1 then
        base = MSGS_LEAVING[math.random(#MSGS_LEAVING)]
    elseif useDreamLine then
        local dreamLines = {
            "saving up for " .. dreamItem.name .. " donate pls",
            "trying to get " .. dreamItem.name .. " any help appreciated",
            "so close to getting " .. dreamItem.name .. " help me out?",
            "want " .. dreamItem.name .. " so bad, any donation helps",
        }
        base = dreamLines[math.random(#dreamLines)]
    else
        base = pool[math.random(#pool)]
    end

    return addName(base, t)
end

-- ========= MAIN LOGIC WITH CHAT RESPONSE =========
local function nextPlayer()
    local target = findClosest()
    if not target then
        log("[MAIN] Everyone greeted — going home")
        returnHome()
        return false
    end

    log("[MAIN] Target → " .. target.Name)
    lastActivityTime = tick()  -- bot is actively working

    doIdleAction()

    if chasePlayer(target) then
        -- Compliment first (reciprocity principle), then donation request
        local compliment = COMPLIMENTS[math.random(#COMPLIMENTS)]
        sendChatTyped(compliment)
        task.wait(math.random() * 0.5 + 1.5)   -- 1.5–2.0s pause

        local openingMsg = getFirstMsg(target)  -- context-aware pool + optional name + leavingSoon
        sendChatTyped(openingMsg)
        Stats.approached += 1
        lastBeggingTime = tick()
        leavingSoon = false
        -- Brief pause after sending message: just stand close and face the player
        do
            local elapsed = 0
            while elapsed < 2 do
                task.wait(0.2)
                elapsed += 0.2
                faceTargetBriefly(target)
                local r = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
                local tr = target.Character and target.Character:FindFirstChild("HumanoidRootPart")
                local h = player.Character and player.Character:FindFirstChild("Humanoid")
                if r and tr and h then
                    local fp = Vector3.new(
                        (tr.Position + tr.CFrame.LookVector * 2).X,
                        tr.Position.Y,
                        (tr.Position + tr.CFrame.LookVector * 2).Z)
                    if (r.Position - fp).Magnitude > 3 then h:MoveTo(fp) end
                end
            end
        end

        -- ── Wait for response helper ──────────────────────────────
        -- Returns outcome ("yes"|"no"|"timeout"|"left"), player's reply text
        local function waitForResponse(waitTime)
            resetResponse()
            local start = tick()
            while tick() - start < waitTime do
                if not target.Character or not target.Character:FindFirstChild("HumanoidRootPart") then
                    log("[WAIT] Target left")
                    return "left", ""
                end
                local root       = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
                local targetRoot = target.Character:FindFirstChild("HumanoidRootPart")
                if root and targetRoot then
                    local targetPos = targetRoot.Position
                    -- If player ran more than 20 studs away — treat as left
                    if (root.Position - targetPos).Magnitude > 20 then
                        log("[WAIT] Target moved >20 studs — treating as left")
                        return "left", ""
                    end
                    -- Always stay 2 studs in front of player's face
                    local frontPos = Vector3.new(
                        (targetRoot.Position + targetRoot.CFrame.LookVector * 2).X,
                        targetRoot.Position.Y,
                        (targetRoot.Position + targetRoot.CFrame.LookVector * 2).Z)
                    local humanoid = player.Character:FindFirstChild("Humanoid")
                    if humanoid and (root.Position - frontPos).Magnitude > 2 then
                        humanoid:MoveTo(frontPos)
                    end
                    faceTargetBriefly(target)
                end
                if responseReceived and lastSpeaker == target.Name then
                    local msg = lastMessage
                    lastActivityTime = tick()
                    log("[RESPONSE] " .. target.Name .. " said: " .. msg)
                    -- Smart match: single-char words must be entire message; longer = substring
                    local function matches(text, word)
                        if #word <= 1 then
                            return text:match("^%s*" .. word .. "%s*$") ~= nil
                        end
                        return text:find(word, 1, true) ~= nil
                    end
                    local saidYes = false
                    for _, word in ipairs(YES_LIST) do
                        if matches(msg, word) then saidYes = true; break end
                    end
                    local saidNo = false
                    for _, word in ipairs(NO_LIST) do
                        if matches(msg, word) then saidNo = true; break end
                    end
                    if saidYes then return "yes", msg end
                    if saidNo  then return "no",  msg end
                end
                task.wait(0.2)
            end
            return "timeout", ""
        end
        -- ─────────────────────────────────────────────────────────

        log("[WAIT] Waiting " .. WAIT_FOR_ANSWER_TIME .. "s for " .. target.Name .. "'s reply...")
        local result, playerReply = waitForResponse(WAIT_FOR_ANSWER_TIME)

        if result == "yes" then
            -- ── Agreed ──
            sendChat(MSG_FOLLOW_ME)
            -- Sync HOME_POSITION with the actual booth position before guiding.
            -- Only re-claim if the booth is CONFIRMED gone (claimedBoothNum already nil).
            pcall(function()
                local boothLocation = getBoothLocation()
                if not boothLocation then return end
                local existing = findOwnedBooth(boothLocation)
                if existing then
                    HOME_POSITION = existing  -- keep position accurate
                elseif not claimedBoothNum then
                    -- Monitor already cleared claimedBoothNum — safe to re-claim
                    log("[BOOTH-GUIDE] No booth and claimedBoothNum=nil — reclaiming before guide")
                    BOOTH_CLAIM_DEADLINE = nil
                    local newPos = claimBooth()
                    if newPos then HOME_POSITION = newPos end
                end
            end)
            returnHome()
            sendChat(MSG_HERE_IS_HOUSE)
            ignoreList[target.UserId] = true
            Stats.agreed += 1
            refusalStreak = 0
            logInteraction(target.Name, openingMsg, playerReply, "agreed")
            task.wait(2)
            return true

        elseif result == "no" then
            -- ── Refused ──
            sendChat(MSG_OK_FINE_POOL[math.random(#MSG_OK_FINE_POOL)])
            task.wait(math.random() * 0.7 + 0.8)

            -- 30% chance: guilt-trip second message (no wait — just write and walk away)
            if math.random() < SECOND_ATTEMPT_CHANCE then
                local attempt2 = MSGS_SECOND[math.random(#MSGS_SECOND)]
                sendChatTyped(attempt2)
                log("[RETRY] Guilt-trip: " .. attempt2)
                task.wait(0.5)
                logInteraction(target.Name,
                    openingMsg .. " → [refused] → " .. attempt2,
                    playerReply, "refused")
            else
                logInteraction(target.Name, openingMsg, playerReply, "refused")
            end

            -- 60% chance: dignified goodbye
            if math.random() < 0.60 then
                task.wait(0.5)
                sendChatTyped(MSGS_GOODBYE[math.random(#MSGS_GOODBYE)])
            end

            ignoreList[target.UserId] = true
            Stats.refused += 1
            refusalStreak += 1
            if refusalStreak >= FRUSTRATION_THRESHOLD then
                task.wait(1)
                sendChat(FRUSTRATION_MSGS[math.random(#FRUSTRATION_MSGS)])
                log("[FRUSTRATION] " .. refusalStreak .. " refusals in a row!")
            end
            task.wait(1)
            return true

        else
            -- ── No response / left ──
            local noRespMsg = NO_RESPONSE_MSGS[math.random(#NO_RESPONSE_MSGS)]
            sendChatTyped(noRespMsg)
            -- 60% chance: goodbye (only if they didn't physically leave)
            if result ~= "left" and math.random() < 0.60 then
                task.wait(0.5)
                sendChatTyped(MSGS_GOODBYE[math.random(#MSGS_GOODBYE)])
            end
            log("[WAIT] No valid reply from " .. target.Name .. " — moving on")
            ignoreList[target.UserId] = true
            Stats.no_response += 1
            refusalStreak += 1
            logInteraction(target.Name, openingMsg, "",
                result == "left" and "left" or "no_response")
            if refusalStreak >= FRUSTRATION_THRESHOLD then
                task.wait(1)
                sendChat(FRUSTRATION_MSGS[math.random(#FRUSTRATION_MSGS)])
                log("[FRUSTRATION] " .. refusalStreak .. " refusals/no-responses in a row!")
            end
        end
    else
        -- Chase failed (player moved away / unreachable)
        logInteraction(target.Name, "", "", "chase_fail")
        ignoreList[target.UserId] = true
    end

    task.wait(1)
    return true
end

-- ==================== SERVER HOP FUNCTION ====================
function serverHop(skipReturnHome)
    lastActivityTime = tick()
    lastBeggingTime  = tick()
    Stats.hops += 1
    log("[HOP] Starting server hop...")

    -- Pre-queue the script so it auto-starts after rejoin/teleport
    local RELOAD_CODE = [[
local httprequest = (syn and syn.request) or http and http.request or http_request or (fluxus and fluxus.request) or request
local response = httprequest({Url = "]] .. SCRIPT_URL .. [["})
if response and response.Body then loadstring(response.Body)()
else loadstring(game:HttpGet("]] .. SCRIPT_URL .. [["))() end
]]
    queueFunc(RELOAD_CODE)

    -- Go home if not stuck
    if not skipReturnHome then
        pcall(returnHome)
        task.wait(1)
    end

    -- Stagger so multiple bots on same IP don't hit API at the exact same time
    local stagger = math.random(2, 8)
    log("[HOP] Stagger " .. stagger .. "s...")
    waitWithMovement(stagger)

    -- Re-fetch config (cooldown/min/max may have changed from dashboard)
    fetchDashConfig()

    -- Load visited servers list and mark current server as visited
    local visited = loadVisited()
    visited = pruneVisited(visited, SERVER_COOLDOWN_MINS)
    visited[tostring(game.JobId)] = tick()  -- mark current as visited
    saveVisited(visited)
    log(string.format("[HOP] Visited server list: %d entries (cooldown=%dmin)",
        (function() local n=0 for _ in pairs(visited) do n=n+1 end return n end)(),
        SERVER_COOLDOWN_MINS))

    -- ── Step 1: ONE API call to find a populated server ──────────────────────
    -- No retry loop, no pagination — if it fails for any reason, skip to Step 2
    local foundServer = nil
    local apiOk, apiResp = pcall(function()
        return httprequest({
            Url = string.format(
                "https://games.roblox.com/v1/games/%d/servers/Public?sortOrder=Desc&limit=100&excludeFullGames=true",
                PLACE_ID
            )
        })
    end)

    if apiOk and apiResp and apiResp.StatusCode == 200 and apiResp.Body then
        local parseOk, body = pcall(function() return HttpService:JSONDecode(apiResp.Body) end)
        if parseOk and body and body.data then
            local candidates = {}
            for _, s in ipairs(body.data) do
                if type(s) == "table" and s.id
                   and s.id ~= tostring(game.JobId)                    -- not current
                   and not wasVisited(visited, s.id, SERVER_COOLDOWN_MINS)  -- not recently visited
                   and tonumber(s.playing) and tonumber(s.playing) >= MIN_PLAYERS
                   and tonumber(s.playing) <= MAX_PLAYERS_ALLOWED then
                    table.insert(candidates, s)
                end
            end
            if #candidates > 0 then
                table.sort(candidates, function(a, b) return (a.playing or 0) > (b.playing or 0) end)
                foundServer = candidates[1]
                log(string.format("[HOP] API found %d candidates, picked server with %d players",
                    #candidates, foundServer.playing or 0))
            else
                log("[HOP] API: no new unvisited suitable servers found")
            end
        end
    elseif apiOk and apiResp then
        log("[HOP] API status " .. tostring(apiResp.StatusCode) .. " — skipping to direct teleport")
    else
        log("[HOP] API call failed — skipping to direct teleport")
    end

    -- ── Step 2: Teleport ─────────────────────────────────────────────────────
    local teleported = false

    if foundServer then
        -- Try TeleportToPlaceInstance (specific populated server)
        local tpOk = pcall(function()
            TeleportService:TeleportToPlaceInstance(PLACE_ID, foundServer.id, player)
        end)
        if tpOk then
            log("[HOP] TeleportToPlaceInstance initiated — waiting 45s...")
            waitWithMovement(45)
            -- If still here, teleport didn't fire — fall through to direct
            log("[HOP] TeleportToPlaceInstance didn't fire, using direct teleport")
        else
            log("[HOP] TeleportToPlaceInstance failed, using direct teleport")
        end
    end

    -- Direct teleport (Roblox matchmaking picks server — always works, no API needed)
    log("[HOP] ⚡ Direct teleport to random server via matchmaking...")
    pcall(function() TeleportService:Teleport(PLACE_ID, player) end)
    task.wait(5)

    -- Final fallback: kick self (script restarts via queueFunc on rejoin)
    log("[HOP] Kicking self to force rejoin...")
    pcall(function() player:Kick("Rejoining server...") end)
    task.wait(60)  -- script should be dead by now; this only runs if kick also failed
end

-- ==================== DONATION MONITOR ====================
-- Tries three methods in order, uses the first one that works.
-- No double-counting: only one method runs at a time.
--
-- Method 1 (best): leaderstats.Raised.Changed  — event-driven, instant, exact delta
-- Method 2 (good): ChatDonationAlert RemoteEvent — event-driven, gives tipper info
-- Method 3 (fallback): BoothUI Raised text polling — works even without leaderstats

local function onDonation(delta, source)
    if delta <= 0 then return end
    Stats.donations   += 1
    Stats.robux_gross += delta
    log(string.format(
        "[DONATE/%s] +R$%d | Session total: R$%d gross / R$%d net | %d donations",
        source, delta, Stats.robux_gross, math.floor(Stats.robux_gross * 0.6), Stats.donations))
end

local function monitorDonations()
    task.spawn(function()
        local tracked = false

        -- ── METHOD 1: leaderstats.Raised (WaitForChild, best) ─────────────
        -- Sets Stats.raised_current immediately at startup (e.g. 85 R$)
        -- and updates it on every donation. No FindFirstChild races.
        pcall(function()
            local ls = player:WaitForChild("leaderstats", 25)
            if not ls then log("[DONATE] leaderstats missing"); return end
            local rs = ls:WaitForChild("Raised", 15)
            if not rs then log("[DONATE] leaderstats.Raised missing"); return end

            -- ★ Set the absolute current value right away
            Stats.raised_current = tonumber(rs.Value) or 0
            log(string.format("[DONATE] Method 1 active: leaderstats.Raised = R$%d", Stats.raised_current))

            local last = rs.Value
            rs.Changed:Connect(function(newVal)
                Stats.raised_current = tonumber(newVal) or 0  -- keep in sync
                onDonation(newVal - last, "LS")
                last = newVal
            end)
            tracked = true
        end)
        if tracked then return end

        -- ── METHOD 2: ChatDonationAlert RemoteEvent ────────────────────────
        -- Doesn't give us starting balance, but catches new donations.
        -- Also reads initial balance from BoothUI text as fallback for raised_current.
        pcall(function()
            local Events = ReplicatedStorage:WaitForChild("Events", 15)
            if not Events then return end
            local alertEvent = Events:WaitForChild("ChatDonationAlert", 10)
            if not alertEvent then return end
            alertEvent.OnClientEvent:Connect(function(tipper, receiver, amount)
                local isUs = (type(receiver) == "string")
                    and (receiver == player.Name or receiver == player.DisplayName)
                    or (receiver == player)
                local tipName = (type(tipper) == "string" and tipper)
                             or (typeof(tipper) == "Instance" and tipper.Name) or "?"
                if isUs then
                    local amt = tonumber(amount) or 0
                    Stats.raised_current += amt
                    onDonation(amt, "CDA:" .. tipName)
                    -- Queue for deferred thank-you approach (2–3 min later)
                    recentDonors[tipName] = {ts = os.time(), thanked = false}
                else
                    -- Someone else received a donation — react with congrats (max once/30s)
                    local now = os.time()
                    if now - lastCongratTs >= 30 then
                        lastCongratTs = now
                        local CONGRATS = {
                            "omg congrats!! 🎉",
                            "yoo nice donation!! 🎉",
                            "aww that's so sweet 💙",
                            "goals fr 🔥",
                            "love to see it!! 🎉",
                        }
                        task.spawn(function()
                            task.wait(math.random(5, 20) / 10)
                            sendChat(CONGRATS[math.random(#CONGRATS)])
                        end)
                    end
                end
            end)
            tracked = true
            log("[DONATE] Method 2: ChatDonationAlert RemoteEvent")
        end)
        -- Method 2 doesn't stop fallback — also launch BoothUI for initial value
        -- (even if ChatDonationAlert works we still need the starting balance)
        task.spawn(function()
            pcall(function()
                local boothUI = player.PlayerGui
                    :WaitForChild("MapUIContainer", 20)
                    :WaitForChild("MapUI", 15)
                    :WaitForChild("BoothUI", 15)
                if not boothUI then return end
                local ourBooth
                for _ = 1, 40 do
                    for _, v in ipairs(boothUI:GetChildren()) do
                        local det = v:FindFirstChild("Details")
                        if det and det:FindFirstChild("Owner") then
                            local ownerName = det.Owner.Text:split("'")[1]
                            if ownerName == player.DisplayName or ownerName == player.Name then
                                ourBooth = v; break
                            end
                        end
                    end
                    if ourBooth then break end
                    task.wait(1)
                end
                if not ourBooth then log("[DONATE] BoothUI: our booth not found"); return end

                local function readRaised()
                    local txt = ourBooth.Details.Raised.Text or "0"
                    return tonumber(txt:split(" ")[1]:gsub(",", "")) or 0
                end

                -- ★ Capture starting balance from BoothUI right away
                local initVal = readRaised()
                if Stats.raised_current == 0 and initVal > 0 then
                    Stats.raised_current = initVal
                    log(string.format("[DONATE] raised_current from BoothUI: R$%d", initVal))
                end

                if not tracked then
                    -- Use BoothUI polling as primary donation detection
                    local last = initVal
                    tracked = true
                    log(string.format("[DONATE] Method 3: BoothUI polling (current: R$%d)", last))
                    while true do
                        task.wait(5)
                        local ok, cur = pcall(readRaised)
                        if ok then
                            Stats.raised_current = cur
                            onDonation(cur - last, "UI")
                            last = cur
                        end
                    end
                else
                    -- Method 1 or 2 already active — just keep raised_current synced from UI
                    while true do
                        task.wait(10)
                        local ok, cur = pcall(readRaised)
                        if ok and cur > Stats.raised_current then
                            Stats.raised_current = cur
                        end
                    end
                end
            end)
        end)

        if not tracked then
            log("[DONATE] All methods failed — donation tracking disabled")
        end
    end)
end

-- ==================== DASHBOARD REPORTING ====================
local function startReporting()
    if DASH_URL == "" then return end
    task.spawn(function()
        local consecutiveFails = 0
        while true do
            local logSnapshot = interactionLog
            interactionLog = {}

            local ok, err = pcall(function()
                local body = HttpService:JSONEncode({
                    id              = tostring(player.UserId),
                    name            = player.Name,
                    approached      = Stats.approached,
                    agreed          = Stats.agreed,
                    refused         = Stats.refused,
                    no_response     = Stats.no_response,
                    hops            = Stats.hops,
                    donations       = Stats.donations,
                    robux_gross     = Stats.robux_gross,
                    raised_current  = Stats.raised_current,
                    status          = "Active",
                    job_id          = tostring(game.JobId),
                    session_start   = sessionStart,
                    interactions    = logSnapshot,
                })
                local resp = request({
                    Url     = DASH_URL .. "/pd_update",
                    Method  = "POST",
                    Headers = {["Content-Type"] = "application/json"},
                    Body    = body,
                })
                -- Treat non-2xx as failure so we know the server rejected it
                if resp and resp.StatusCode and resp.StatusCode >= 300 then
                    error("HTTP " .. tostring(resp.StatusCode))
                end
            end)

            if ok then
                if consecutiveFails > 0 then
                    log("[REPORT] ✅ Dashboard reconnected after " .. consecutiveFails .. " failed reports")
                end
                consecutiveFails = 0
            else
                consecutiveFails += 1
                -- Log every 6th fail (~30 seconds) so console isn't spammed
                if consecutiveFails == 1 or consecutiveFails % 6 == 0 then
                    log("[REPORT] ⚠️ Dashboard unreachable (x" .. consecutiveFails .. "): " .. tostring(err))
                    log("[REPORT] URL: " .. DASH_URL)
                end
                -- Return undelivered interactions to buffer so they're not lost
                for _, entry in ipairs(logSnapshot) do
                    table.insert(interactionLog, entry)
                end
            end

            task.wait(5)
        end
    end)
end

-- ========= NEW PLAYER DETECTION =========
-- When a new player joins mid-session, remove them from ignoreList so the bot
-- will approach them in the next nextPlayer() cycle.
Players.PlayerAdded:Connect(function(newPlayer)
    task.wait(3)  -- Wait for character to load
    if ignoreList[newPlayer.UserId] then
        ignoreList[newPlayer.UserId] = nil
        log("[NEW] Removed " .. newPlayer.Name .. " from ignoreList (new arrival)")
    else
        log("[NEW] Player joined: " .. newPlayer.Name)
    end
end)

-- ========= START =========
log("=== SOCIAL GREETER BOT – ULTIMATE EDITION ===")
log("=== AUTO BOOTH CLAIM + SERVER HOP ===")
if not player.Character or not player.Character:FindFirstChild("HumanoidRootPart") then
    player.CharacterAdded:Wait()
    task.wait(2)
end

monitorDonations()
startReporting()

-- ── Watchdog: if bot hasn't actually begged in 3 minutes, force server hop ──
-- At 90s idle → enable leavingSoon messages; at 180s → force hop.
task.spawn(function()
    local BEG_IDLE_LIMIT = 180
    task.wait(60)
    while isActiveInstance() do
        task.wait(30)
        if not isActiveInstance() then break end
        local sinceLastBeg = tick() - lastBeggingTime
        if sinceLastBeg > 90 and not leavingSoon then
            leavingSoon = true
            log("[WATCHDOG] Idle 90s — leavingSoon enabled")
        end
        if sinceLastBeg > BEG_IDLE_LIMIT then
            leavingSoon = false
            log(string.format("[WATCHDOG] No begging for %.0fs — force hopping!", sinceLastBeg))
            serverHop(true)
        end
    end
    log("[SINGLETON] Watchdog exiting (new instance took over)")
end)

-- ── Thank-you loop: approach donors 2–3 min after they donated ──
task.spawn(function()
    while isActiveInstance() do
        task.wait(30)
        if not isActiveInstance() then break end
        local now = os.time()
        for tipName, info in pairs(recentDonors) do
            if not info.thanked and (now - info.ts) >= math.random(120, 180) then
                -- Find the donor on this server
                local donor = nil
                for _, p in ipairs(Players:GetPlayers()) do
                    if p.Name == tipName or p.DisplayName == tipName then
                        donor = p; break
                    end
                end
                if donor and donor.Character and donor.Character:FindFirstChild("HumanoidRootPart") then
                    info.thanked = true
                    task.spawn(function()
                        log("[THANKS] Going to thank " .. tipName)
                        if chasePlayer(donor) then
                            local msg = MSGS_THANKS[math.random(#MSGS_THANKS)]
                            sendChatTyped(msg)
                            logInteraction(tipName, msg, "", "thanked")
                        end
                    end)
                elseif (now - info.ts) > 300 then
                    recentDonors[tipName] = nil  -- donor left or 5min passed
                end
            end
        end
    end
end)

-- Main loop: greet everyone, then wait for new arrivals before hopping
while isActiveInstance() do
    while isActiveInstance() and nextPlayer() do end

    if not isActiveInstance() then
        log("[SINGLETON] New instance detected — this instance is exiting")
        break
    end

    -- Everyone greeted — wait 2s in case new players just joined before hopping
    log("[MAIN] Everyone greeted! Waiting 2s for new arrivals...")
    returnHome()
    local waitStart = tick()
    local gotNewPlayer = false
    while tick() - waitStart < 2 do
        if not isActiveInstance() then break end
        if findClosest() then
            gotNewPlayer = true
            break
        end
        task.wait(0.5)
    end

    if not isActiveInstance() then
        log("[SINGLETON] New instance detected — this instance is exiting")
        break
    end

    if gotNewPlayer then
        log("[MAIN] New players found, continuing greeting loop...")
    else
        log("[MAIN] No new players in 20s — initiating server hop...")
        serverHop()
        -- serverHop loops forever; this line never runs
    end
end