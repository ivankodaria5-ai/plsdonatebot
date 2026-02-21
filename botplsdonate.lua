-- ==================== CONSTANTS & CONFIGURATION ====================
local PLACE_ID = 8737602449                            -- Please Donate place ID
local MIN_PLAYERS = 4                                  -- Minimum players in server
local MAX_PLAYERS_ALLOWED = 24                         -- Maximum players in server
local TELEPORT_RETRY_DELAY = 8                         -- Delay between teleport attempts (increased from 4)
local TELEPORT_COOLDOWN = 30                           -- Cooldown between failed servers to avoid rate limit detection
local SCRIPT_URL = "https://cdn.jsdelivr.net/gh/ivankodaria5-ai/plsdonatebot@main/botplsdonate.lua"
local DASH_URL   = "https://around-replied-extra-carrier.trycloudflare.com"

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

local function claimBooth()
    log("=== BOOTH CLAIMER ===")
    local boothLocation = getBoothLocation()
    if not boothLocation then
        log("[BOOTH] ERROR: Could not find booth UI!")
        return nil
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
    log("[BOOTH] Retrying from start...")
    return claimBooth()  -- Recursively retry until success
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
    local lastPos = root.Position
    local stuckTime = 0
    local jumpTries = 0
    local randTries = 0

    while true do
        task.wait(0.1)
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
    local best, bestT = nil, math.huge
    local allPlayers = Players:GetPlayers()
    if not allPlayers then
        log("[DEBUG] Players:GetPlayers() returned nil!")
        return nil
    end
    for _, p in ipairs(allPlayers) do
        if p and p ~= player and p.UserId and not ignoreList[p.UserId] and not BOT_ACCOUNTS[p.Name] and p.Character and p.Character:FindFirstChild("HumanoidRootPart") then
            local path = PathfindingService:CreatePath()
            path:ComputeAsync(root.Position, p.Character.HumanoidRootPart.Position)
            if path.Status == Enum.PathStatus.Success then
                local dist = 0
                local wp = path:GetWaypoints()
                for i = 2, #wp do dist += (wp[i].Position - wp[i-1].Position).Magnitude end
                local t = dist / 16
                if t < bestT then bestT, best = t, p end
            end
        end
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

    -- Random idle action before approaching (looks more human)
    doIdleAction()

    if chasePlayer(target) then
        sendChatTyped(string.lower(target.Name) .. " " .. getRandomMessage())
        Stats.approached += 1
        startCircleDance(CIRCLE_COOLDOWN)
        task.wait(CIRCLE_COOLDOWN)
        local normElapsed = 0
        while normElapsed < NORMAL_COOLDOWN do
            task.wait(0.1)
            normElapsed += 0.1
            faceTargetBriefly(target)
        end

        -- ── Wait for response helper ──────────────────────────────
        -- Returns: "yes" | "no" | "timeout" | "left"
        local function waitForResponse(waitTime)
            resetResponse()
            local start = tick()
            while tick() - start < waitTime do
                if not target.Character or not target.Character:FindFirstChild("HumanoidRootPart") then
                    log("[WAIT] Target left")
                    return "left"
                end
                local root       = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
                local targetRoot = target.Character:FindFirstChild("HumanoidRootPart")
                if root and targetRoot then
                    if (root.Position - targetRoot.Position).Magnitude > MAX_WAIT_DISTANCE then
                        log("[WAIT] Target moving away, following...")
                        local humanoid = player.Character:FindFirstChild("Humanoid")
                        if humanoid then humanoid:MoveTo(targetRoot.Position) end
                    end
                    faceTargetBriefly(target)
                end
                if responseReceived and lastSpeaker == target.Name then
                    local msg = lastMessage
                    log("[RESPONSE] " .. target.Name .. " said: " .. msg)
                    local saidYes = false
                    for _, word in ipairs(YES_LIST) do
                        if msg:find(word) then saidYes = true; break end
                    end
                    local saidNo = false
                    for _, word in ipairs(NO_LIST) do
                        if msg:find(word) then saidNo = true; break end
                    end
                    if saidYes then return "yes" end
                    if saidNo  then return "no"  end
                end
                task.wait(0.1)
            end
            return "timeout"
        end
        -- ─────────────────────────────────────────────────────────

        log("[WAIT] Waiting " .. WAIT_FOR_ANSWER_TIME .. "s for " .. target.Name .. "'s reply...")
        local result = waitForResponse(WAIT_FOR_ANSWER_TIME)

        if result == "yes" then
            -- ── Agreed ──
            sendChat(MSG_FOLLOW_ME)
            returnHome()
            sendChat(MSG_HERE_IS_HOUSE)
            ignoreList[target.UserId] = true
            Stats.agreed += 1
            refusalStreak = 0
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
                local result2 = waitForResponse(5)
                if result2 == "yes" then
                    sendChat(MSG_FOLLOW_ME)
                    returnHome()
                    sendChat(MSG_HERE_IS_HOUSE)
                    ignoreList[target.UserId] = true
                    Stats.agreed += 1
                    refusalStreak = 0
                    task.wait(2)
                    return true
                end
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
            if refusalStreak >= FRUSTRATION_THRESHOLD then
                task.wait(1)
                sendChat(FRUSTRATION_MSGS[math.random(#FRUSTRATION_MSGS)])
                log("[FRUSTRATION] " .. refusalStreak .. " refusals/no-responses in a row!")
            end
        end
    else
        ignoreList[target.UserId] = true
    end

    task.wait(1)
    return true
end

-- ==================== SERVER HOP FUNCTION ====================
function serverHop(skipReturnHome)
    Stats.hops += 1
    log("[HOP] Starting server hop...")
    
    -- Return home before hopping (unless we're stuck and can't move)
    if not skipReturnHome then
        local success = returnHome()
        if not success then
            log("[HOP] returnHome failed, continuing anyway...")
        end
        task.wait(1)
    else
        log("[HOP] Skipping returnHome due to stuck state, doing keyboard movement")
        -- Use keyboard input instead of MoveTo since we're stuck
        task.spawn(function()
            for i = 1, 20 do
                VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.W, false, game)
                task.wait(0.1)
                VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.W, false, game)
                task.wait(0.1)
            end
        end)
        task.wait(2)
    end
    
    log("[HOP] Beginning server search...")
    
    local cursor = ""
    
    while true do
        -- Simple 5 second delay between requests
        waitWithMovement(5)
        
        local url = string.format(
            "https://games.roblox.com/v1/games/%d/servers/Public?sortOrder=Asc&limit=100%s",
            PLACE_ID,
            cursor ~= "" and "&cursor=" .. cursor or ""
        )
        
        local success, response = pcall(function()
            return httprequest({Url = url})
        end)
        
        if not success or not response then
            log("[HOP] HTTP request failed, retrying...")
            if not success then
                log("[HOP DEBUG] Request error: " .. tostring(response))
            end
            waitWithMovement(10)
            continue
        end
        
        -- Check for 429 Too Many Requests
        if response.StatusCode == 429 then
            log("[HOP] ⚠️ 429 Too Many Requests! Cooling down for 30s...")
            waitWithMovement(30)
            cursor = ""
            continue
        end
        
        if not response.Body then
            log("[HOP] Response has no Body field! Likely rate-limited by Roblox.")
            log("[HOP] Waiting 30 seconds before retrying...")
            waitWithMovement(30)
            cursor = ""
            continue
        end
        
        local bodySuccess, body = pcall(function() 
            return HttpService:JSONDecode(response.Body) 
        end)
        
        if not bodySuccess or not body or not body.data then
            log("[HOP] Failed to parse response, retrying in 5s...")
            log("[HOP DEBUG] Parse error: " .. tostring(body))
            if response then
                log("[HOP DEBUG] Response status: " .. tostring(response.StatusCode or "N/A"))
                log("[HOP DEBUG] Response body type: " .. type(response.Body))
            end
            waitWithMovement(5)
            continue
        end
        
        -- Collect all valid servers (not current server)
        local servers = {}
        for _, server in pairs(body.data) do
            if server.id ~= game.JobId 
                and server.playing >= MIN_PLAYERS 
                and server.playing <= MAX_PLAYERS_ALLOWED then
                table.insert(servers, server)
            end
        end
        
        if #servers > 0 then
            -- Sort by player count (more players = more donation potential)
            table.sort(servers, function(a, b) return (a.playing or 0) > (b.playing or 0) end)
            
            log("[HOP] Found " .. #servers .. " suitable servers on this page")
            
            -- Try only 1 server per page to reduce API spam and avoid rate limiting
            local selected = servers[1]
            local playing = selected.playing or "?"
            local maxP = selected.maxPlayers or "?"
            log("[HOP] Trying server: " .. selected.id .. " (" .. playing .. "/" .. maxP .. ")")
            
            -- Queue script for next server (use httprequest since game:HttpGet returns nil on some executors)
            queueFunc([[
local httprequest = (syn and syn.request) or http and http.request or http_request or (fluxus and fluxus.request) or request
local response = httprequest({Url = "]] .. SCRIPT_URL .. [["})
if response and response.Body then
    loadstring(response.Body)()
else
    -- Fallback to game:HttpGet
    loadstring(game:HttpGet("]] .. SCRIPT_URL .. [["))()
end
]])
            
            -- Attempt teleport
            local teleportOptions = Instance.new("TeleportOptions")
            teleportOptions.ShouldReserveServer = false
            
            local tpOk, err = pcall(function()
                TeleportService:TeleportToPlaceInstance(PLACE_ID, selected.id, player, teleportOptions)
            end)
            
            if tpOk then
                log("[HOP] Teleport initiated! Waiting up to 3 minutes with anti-AFK movement...")
                -- Wait up to 3 minutes for teleport to complete
                local waitStart = tick()
                local maxWaitTime = 180  -- 3 minutes
                
                while tick() - waitStart < maxWaitTime do
                    waitWithMovement(30)
                    local elapsed = math.floor(tick() - waitStart)
                    log("[HOP] Still waiting for teleport... (" .. elapsed .. "s/" .. maxWaitTime .. "s)")
                end
                
                -- If we're still here after 3 minutes, this server isn't working
                log("[HOP] Teleport timed out after 3 minutes")
                log("[HOP] Cooling down for " .. TELEPORT_COOLDOWN .. "s to avoid rate limiting...")
                waitWithMovement(TELEPORT_COOLDOWN)
            else
                log("[HOP] Teleport call failed: " .. tostring(err))
                log("[HOP] Cooling down for " .. TELEPORT_COOLDOWN .. "s...")
                waitWithMovement(TELEPORT_COOLDOWN)
            end
            
            -- Move to next page after trying one server
            if body.nextPageCursor then
                cursor = body.nextPageCursor
                log("[HOP] Moving to next page...")
            else
                log("[HOP] Exhausted all pages, starting over from page 1 after cooldown...")
                waitWithMovement(TELEPORT_COOLDOWN)
                cursor = ""
            end
        else
            -- No suitable servers on this page, check if there's a next page
            if body.nextPageCursor then
                cursor = body.nextPageCursor
                log("[HOP] No suitable servers on this page, checking next page...")
            else
                -- Exhausted all pages, start over from beginning
                log("[HOP] Exhausted all pages with no suitable servers. Starting over from page 1 in 10s...")
                waitWithMovement(10)
                cursor = ""
            end
        end
    end
end

-- ==================== DONATION MONITOR ====================
-- Reads the "Raised" counter directly from our booth UI.
-- When the value grows, we calculate the delta and record it as a donation.
-- This is the same method used by all serious PD bots (no chat parsing needed).
local function monitorDonations()
    task.spawn(function()
        -- Find the BoothUI container
        local boothUI
        pcall(function()
            boothUI = player:WaitForChild("PlayerGui", 10)
                :WaitForChild("MapUIContainer", 10)
                :WaitForChild("MapUI", 10)
                :WaitForChild("BoothUI", 10)
        end)
        if not boothUI then
            log("[DONATE] BoothUI not found — donation tracking disabled")
            return
        end

        -- Wait until a booth owned by us appears (up to 30 sec)
        local ourBooth = nil
        for _ = 1, 30 do
            for _, frame in ipairs(boothUI:GetChildren()) do
                local details = frame:FindFirstChild("Details")
                if details then
                    local ownerLabel = details:FindFirstChild("Owner")
                    if ownerLabel then
                        local t = ownerLabel.Text
                        if t:find(player.DisplayName, 1, true) or t:find(player.Name, 1, true) then
                            ourBooth = frame
                            break
                        end
                    end
                end
            end
            if ourBooth then break end
            task.wait(1)
        end

        if not ourBooth then
            log("[DONATE] Our booth not found in BoothUI — donation tracking disabled")
            return
        end

        local raisedLabel = ourBooth.Details:FindFirstChild("Raised")
        if not raisedLabel then
            log("[DONATE] No 'Raised' label in booth — donation tracking disabled")
            return
        end

        -- Parse "1,234 Raised" → 1234
        local function readRaised()
            local numStr = (raisedLabel.Text or "0"):match("^([%d,]+)")
            return tonumber((numStr or "0"):gsub(",", "")) or 0
        end

        local lastRaised = readRaised()
        log(string.format("[DONATE] Monitoring booth %s — current Raised: %d R$", ourBooth.Name, lastRaised))

        while true do
            task.wait(5)
            local ok, current = pcall(readRaised)
            if ok and current > lastRaised then
                local delta = current - lastRaised
                Stats.donations     += 1
                Stats.robux_gross   += delta
                Stats.raised_current = current
                local net = math.floor(delta * 0.6)
                log(string.format(
                    "[DONATE] +%d R$ raised (+%d net after 40%% fee) | Total: %d gross / %d net | %d donations",
                    delta, net, Stats.robux_gross, math.floor(Stats.robux_gross * 0.6), Stats.donations))
                lastRaised = current
            elseif ok then
                Stats.raised_current = current
                lastRaised = current
            end
        end
    end)
end

-- ==================== DASHBOARD REPORTING ====================
local function startReporting()
    if DASH_URL == "" then return end
    task.spawn(function()
        while true do
            pcall(function()
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
                })
                request({
                    Url     = DASH_URL .. "/pd_update",
                    Method  = "POST",
                    Headers = {["Content-Type"] = "application/json"},
                    Body    = body,
                })
            end)
            task.wait(15)
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