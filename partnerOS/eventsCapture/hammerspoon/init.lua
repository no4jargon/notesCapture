local source = debug.getinfo(1, "S").source
local scriptPath = source:sub(1, 1) == "@" and source:sub(2) or source
local scriptDir = scriptPath:match("(.*/)" ) or "./"
local projectDir = scriptDir:gsub("/$", ""):gsub("/hammerspoon$", "")
local binary = projectDir .. "/bin/notesCapture"
local generatedConfig = projectDir .. "/config/generated.lua"
local processInboxScript = projectDir .. "/scripts/process_inbox.sh"

local config = {
  dataDir = projectDir
}

if hs.fs.attributes(generatedConfig) then
  local ok, loaded = pcall(dofile, generatedConfig)
  if ok and type(loaded) == "table" and type(loaded.dataDir) == "string" and loaded.dataDir ~= "" then
    config = loaded
  end
end

local quickNoteTask = nil
local processInboxTask = nil

local function stopExistingQuickNote()
  hs.execute("pkill -f '" .. binary .. "'", true)
  quickNoteTask = nil
end

local function notifyError(message)
  hs.notify.new({
    title = "notesCapture",
    informativeText = message
  }):send()
end

local function processInbox()
  if processInboxTask then
    return
  end

  processInboxTask = hs.task.new("/bin/bash", function(exitCode, stdOut, stdErr)
    processInboxTask = nil

    if exitCode ~= 0 then
      notifyError((stdErr ~= "" and stdErr) or "Inbox sync failed")
    end
  end, { processInboxScript, config.dataDir })

  if not processInboxTask then
    notifyError("Could not start inbox sync")
    return
  end

  processInboxTask:start()
end

local function openQuickNote()
  stopExistingQuickNote()

  quickNoteTask = hs.task.new(binary, function(exitCode, stdOut, stdErr)
    quickNoteTask = nil

    if exitCode ~= 0 and exitCode ~= 15 then
      notifyError((stdErr ~= "" and stdErr) or "Quick note window failed to open")
    else
      processInbox()
    end
  end, { config.dataDir })

  if not quickNoteTask then
    notifyError("Could not launch quick note helper")
    return
  end

  quickNoteTask:start()
end

hs.hotkey.bind({ "alt" }, "space", openQuickNote)
hs.timer.doEvery(20, processInbox)
hs.timer.doAfter(3, processInbox)

hs.caffeinate.watcher.new(function(event)
  if event == hs.caffeinate.watcher.systemDidWake then
    hs.timer.doAfter(5, processInbox)
  end
end):start()
