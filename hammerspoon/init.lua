local projectDir = os.getenv("HOME") .. "/Desktop/Projects/HotkeyNotes"
local binary = projectDir .. "/bin/hotkey-notes"
local notesFile = projectDir .. "/notes.txt"

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
        title = "HotkeyNotes",
        informativeText = (stdErr ~= "" and stdErr) or "Quick note window failed to open"
      }):send()
    end
  end, { notesFile })

  if not quickNoteTask then
    hs.notify.new({
      title = "HotkeyNotes",
      informativeText = "Could not launch quick note helper"
    }):send()
    return
  end

  quickNoteTask:start()
end

hs.hotkey.bind({ "alt" }, "space", openQuickNote)
