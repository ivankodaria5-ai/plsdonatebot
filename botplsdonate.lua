-- ==================== CONSTANTS & CONFIGURATION ====================
local PLACE_ID = 8737602449                            -- Please Donate place ID
local MIN_PLAYERS = 4                                  -- Minimum players in server
local MAX_PLAYERS_ALLOWED = 24                         -- Maximum players in server
local TELEPORT_RETRY_DELAY = 8                         -- Delay between teleport attempts (increased from 4)
local TELEPORT_COOLDOWN = 30                           -- Cooldown between failed servers to avoid rate limit detection
local SCRIPT_URL = "https://cdn.jsdelivr.net/gh/ivankodaria5-ai/plsdonatebot@main/botplsdonate.lua"
local DASH_URL   = "https://export-petition-your-jul.trycloudflare.com"

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
local YES_LIST = {"yes", "yeah", "yep", "sure", "ok", "okay", "y", "follow", "come", "lets go", "go"}
local NO_LIST = {"no", "nope", "nah", "don't", "dont", "n", "stop", "leave", "no thanks"}

local MSG_FOLLOW_ME = "Follow me!"
local MSG_HERE_IS_HOUSE = "Here is my booth!"
local MSG_OK_FINE = "Ok fine :("

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

local SECOND_ATTEMPT_MSGS = {
    "maybe just 5 robux? :(",
    "pleeeease? just a tiny bit?",
    "are you sure? even just a little?",
    "can u reconsider? any amount helps :)",
    "even 1 robux would help :(",
    "pretty please? :c",
    "last chance pls? :(",
}

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
local sessionStart = tick()

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

-- CLAIM BOOTH AND SET HOME POSITION
local HOME_POSITION = claimBooth()
if not HOME_POSITION then
    log("[BOOTH] Failed to claim booth! Using default position.")
    HOME_POSITION = Vector3.new(94, 4, 281)  -- Fallback position
end
log("=== HOME SET TO: " .. tostring(HOME_POSITION) .. " ===")
saveLog()

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
                if speaker and speaker ~= player.Name then
                    lastSpeaker = speaker
                    lastMessage = msg
                    responseReceived = true
                end
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
                            if speaker ~= player.Name then
                                lastSpeaker = speaker
                                lastMessage = text
                                responseReceived = true
                            end
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

-- Random idle action between players (looks human)
local function doIdleAction()
    local roll = math.random()
    if roll < 0.05 then
        -- 5% chance: random jump
        log("[IDLE] Random jump")
        VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Space, false, game)
        task.wait(0.35)
        VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Space, false, game)
    elseif roll < 0.08 then
        -- 3% chance: spin around
        log("[IDLE] Random spin")
        local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
        if hrp then
            for _ = 1, 8 do
                hrp.CFrame = hrp.CFrame * CFrame.Angles(0, math.pi / 4, 0)
                task.wait(0.05)
            end
        end
    elseif roll < 0.10 then
        -- 2% chance: pause briefly
        log("[IDLE] Random pause")
        task.wait(math.random() * 1.0 + 0.5)
    end
end

local function findClosest()
    if not player.Character then return nil end
    local root = player.Character:FindFirstChild("HumanoidRootPart")
    if not root then return nil end
    local best, bestDist = nil, math.huge
    local allPlayers = Players:GetPlayers()
    if not allPlayers then
        log("[DEBUG] Players:GetPlayers() returned nil!")
        return nil
    end
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
    
    -- Roll for typo chance
    if math.random() < TYPO_CHANCE then
        -- Pick a random typo variant (1-3)
        local typoVariant = math.random(3)
        return MESSAGE_TYPOS[msgIndex][typoVariant]
    else
        return MESSAGES[msgIndex]
    end
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

    -- Random idle action before approaching (looks more human)
    doIdleAction()

    if chasePlayer(target) then
        local openingMsg = string.lower(target.Name) .. " " .. getRandomMessage()
        sendChatTyped(openingMsg)
        Stats.approached += 1
        lastBeggingTime = tick()  -- bot actually sent a begging message
        startCircleDance(CIRCLE_COOLDOWN)
        task.wait(CIRCLE_COOLDOWN)
        local normElapsed = 0
        while normElapsed < NORMAL_COOLDOWN do
            task.wait(0.1)
            normElapsed += 0.1
            faceTargetBriefly(target)
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
                    -- Always position bot 3 studs in front of the player's face
                    local frontPos = targetRoot.Position + targetRoot.CFrame.LookVector * 3
                    frontPos = Vector3.new(frontPos.X, targetRoot.Position.Y, frontPos.Z)
                    local distToIdeal = (root.Position - frontPos).Magnitude
                    local humanoid = player.Character:FindFirstChild("Humanoid")
                    if humanoid then
                        if distToIdeal > 1.5 then
                            humanoid:MoveTo(frontPos)
                        end
                    end
                    faceTargetBriefly(target)
                end
                if responseReceived and lastSpeaker == target.Name then
                    local msg = lastMessage
                    lastActivityTime = tick()  -- got a reply — bot is active
                    log("[RESPONSE] " .. target.Name .. " said: " .. msg)
                    local saidYes = false
                    for _, word in ipairs(YES_LIST) do
                        if msg:find(word) then saidYes = true; break end
                    end
                    local saidNo = false
                    for _, word in ipairs(NO_LIST) do
                        if msg:find(word) then saidNo = true; break end
                    end
                    if saidYes then return "yes", msg end
                    if saidNo  then return "no",  msg end
                end
                task.wait(0.1)
            end
            return "timeout", ""
        end
        -- ─────────────────────────────────────────────────────────

        log("[WAIT] Waiting " .. WAIT_FOR_ANSWER_TIME .. "s for " .. target.Name .. "'s reply...")
        local result, playerReply = waitForResponse(WAIT_FOR_ANSWER_TIME)

        if result == "yes" then
            -- ── Agreed ──
            sendChat(MSG_FOLLOW_ME)
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
            sendChat(MSG_OK_FINE)
            task.wait(math.random() * 0.7 + 0.8)

            -- 30% chance: second attempt
            if math.random() < SECOND_ATTEMPT_CHANCE then
                local attempt2 = SECOND_ATTEMPT_MSGS[math.random(#SECOND_ATTEMPT_MSGS)]
                sendChatTyped(attempt2)
                log("[RETRY] Second attempt: " .. attempt2)
                local result2, reply2 = waitForResponse(5)
                if result2 == "yes" then
                    sendChat(MSG_FOLLOW_ME)
                    returnHome()
                    sendChat(MSG_HERE_IS_HOUSE)
                    ignoreList[target.UserId] = true
                    Stats.agreed += 1
                    refusalStreak = 0
                    -- log both attempts in one record
                    logInteraction(target.Name,
                        openingMsg .. " → [refused] → " .. attempt2,
                        playerReply .. " / " .. reply2,
                        "agreed_2nd")
                    task.wait(2)
                    return true
                end
                -- second attempt also failed
                logInteraction(target.Name,
                    openingMsg .. " → [refused] → " .. attempt2,
                    playerReply .. " / " .. reply2,
                    "refused")
            else
                logInteraction(target.Name, openingMsg, playerReply, "refused")
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
                if type(s) == "table" and s.id and s.id ~= tostring(game.JobId)
                   and tonumber(s.playing) and tonumber(s.playing) >= MIN_PLAYERS
                   and tonumber(s.playing) <= MAX_PLAYERS_ALLOWED then
                    table.insert(candidates, s)
                end
            end
            if #candidates > 0 then
                -- Pick highest player count (most donation potential)
                table.sort(candidates, function(a, b) return (a.playing or 0) > (b.playing or 0) end)
                foundServer = candidates[1]
                log(string.format("[HOP] API found server with %d players", foundServer.playing or 0))
            else
                log("[HOP] API returned no suitable servers")
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
                if not isUs then return end
                local amt = tonumber(amount) or 0
                Stats.raised_current += amt
                local tipName = (type(tipper) == "string" and tipper)
                             or (typeof(tipper) == "Instance" and tipper.Name) or "?"
                onDonation(amt, "CDA:" .. tipName)
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
        while true do
            pcall(function()
                -- Stats.raised_current is kept live by monitorDonations()
                -- (set at startup from leaderstats.Raised, then updated on every change)
                -- Flush interaction log: snapshot current buffer then clear it
                local logSnapshot = interactionLog
                interactionLog = {}

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
                request({
                    Url     = DASH_URL .. "/pd_update",
                    Method  = "POST",
                    Headers = {["Content-Type"] = "application/json"},
                    Body    = body,
                })
            end)
            task.wait(5)  -- report every 5s (was 10s) — keeps dashboard alive during long hops
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
-- (bot moving/chasing without begging doesn't count — we track lastBeggingTime)
task.spawn(function()
    local BEG_IDLE_LIMIT = 180  -- 3 minutes without sending a single donation request
    task.wait(60)               -- grace period at script start
    while true do
        task.wait(30)
        local sinceLastBeg = tick() - lastBeggingTime
        if sinceLastBeg > BEG_IDLE_LIMIT then
            log(string.format("[WATCHDOG] No begging for %.0fs — bot is stuck, force hopping!", sinceLastBeg))
            serverHop(true)
        end
    end
end)

-- Main loop: greet everyone, then wait for new arrivals before hopping
while true do
    while nextPlayer() do end

    -- Everyone greeted — wait 2s in case new players just joined before hopping
    log("[MAIN] Everyone greeted! Waiting 2s for new arrivals...")
    returnHome()
    local waitStart = tick()
    local gotNewPlayer = false
    while tick() - waitStart < 2 do
        if findClosest() then
            gotNewPlayer = true
            break
        end
        task.wait(0.5)
    end

    if gotNewPlayer then
        log("[MAIN] New players found, continuing greeting loop...")
    else
        log("[MAIN] No new players in 20s — initiating server hop...")
        serverHop()
        -- serverHop loops forever; this line never runs
    end
end