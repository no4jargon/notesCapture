local source = debug.getinfo(1, "S").source
local scriptPath = source:sub(1, 1) == "@" and source:sub(2) or source
local scriptDir = scriptPath:match("(.*/)" ) or "./"
local projectDir = scriptDir:gsub("/$", ""):gsub("/hammerspoon$", "")
local binary = projectDir .. "/bin/notesCapture"
local generatedConfig = projectDir .. "/config/generated.lua"

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

local function stopExistingQuickNote()
  hs.execute("pkill -f '" .. binary .. "'", true)
  quickNoteTask = nil
end

local function openQuickNote()
  stopExistingQuickNote()

  quickNoteTask = hs.task.new(binary, function(exitCode, stdOut, stdErr)
    quickNoteTask = nil

    if exitCode ~= 0 and exitCode ~= 15 then
      hs.notify.new({
        title = "notesCapture",
        informativeText = (stdErr ~= "" and stdErr) or "Quick note window failed to open"
      }):send()
    end
  end, { config.dataDir })

  if not quickNoteTask then
    hs.notify.new({
      title = "notesCapture",
      informativeText = "Could not launch quick note helper"
    }):send()
    return
  end

  quickNoteTask:start()
end

hs.hotkey.bind({ "alt" }, "space", openQuickNote)
