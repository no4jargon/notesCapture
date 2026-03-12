# notesCapture

A lightweight macOS quick-capture note tool triggered by `Option + Space`.

It uses:
- **Hammerspoon** for the global hotkey
- a tiny **Swift/AppKit helper** for the popup note window

## What it does

- Press `Option + Space` from anywhere to open the note window
- Type a quick note in a small popup
- Press `Command + Enter` to save
- Notes are **appended** to `notes.txt` with a timestamp
- `Enter` inserts a new line
- `Command + Shift + 7` toggles bullet formatting
- `Esc` closes the window

## Save format

Each note is appended like this:

```txt
[2026-03-12 03:51:59]
A quick thought goes here

[2026-03-12 03:55:10]
- Another note
- Saved later
```

## Project structure

```txt
notesCapture/
├── hammerspoon/
│   └── init.lua
├── quicknote.swift
├── LICENSE
└── README.md
```

Generated locally at runtime, but not tracked in git:
- `notes.txt`
- `bin/hotkey-notes`
- `.DS_Store`

## Setup

### 1. Install Hammerspoon

```bash
brew install --cask hammerspoon
```

### 2. Point Hammerspoon at this repo config

Create or update `~/.hammerspoon/init.lua` with:

```lua
dofile(os.getenv("HOME") .. "/Desktop/Projects/notesCapture/hammerspoon/init.lua")
```

### 3. Build the helper

```bash
mkdir -p ~/Desktop/Projects/notesCapture/bin
swiftc ~/Desktop/Projects/notesCapture/quicknote.swift -o ~/Desktop/Projects/notesCapture/bin/hotkey-notes
```

### 4. Launch Hammerspoon

```bash
open -a Hammerspoon
```

### 5. Grant permissions

macOS may ask you to allow Hammerspoon in:
- **Privacy & Security → Accessibility**
- **Privacy & Security → Input Monitoring**

## Usage

- `Option + Space` → open quick note window
- `Command + Enter` → save note
- `Command + Shift + 7` → toggle bullets
- `Esc` → close window

Notes are saved to:

```txt
~/Desktop/Projects/notesCapture/notes.txt
```

## How it works

- `hammerspoon/init.lua` binds `Option + Space`
- Hammerspoon launches the compiled helper binary
- the Swift helper shows a floating note window
- saving appends a timestamped entry to `notes.txt` using append mode

## Rebuild after code changes

```bash
swiftc ~/Desktop/Projects/notesCapture/quicknote.swift -o ~/Desktop/Projects/notesCapture/bin/hotkey-notes
killall Hammerspoon || true
open -a Hammerspoon
```

## License

MIT
