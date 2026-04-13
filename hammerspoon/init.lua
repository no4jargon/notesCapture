local source = debug.getinfo(1, "S").source
local scriptPath = source:sub(1, 1) == "@" and source:sub(2) or source
local scriptDir = scriptPath:match("(.*/)" ) or "./"
local repoRoot = scriptDir:gsub("/$", ""):gsub("/hammerspoon$", "")
local nestedInit = repoRoot .. "/partnerOS/eventsCapture/hammerspoon/init.lua"
dofile(nestedInit)
