# iPhone setup for notesCapture

notesCapture uses a simple cross-device contract:

- Mac capture writes to `ingress/local/`
- mobile capture should drop plain text files into `ingress/dropbox/`
- the Mac importer turns ingress files into canonical entries and rebuilds `notes.txt`
- `inbox/` is still supported only as a deprecated legacy path

## Recommended Apple setup

Use:
- **Dropbox** for shared storage
- **Apple Shortcuts** for note capture

After running `./setup.sh` on your Mac, open the generated file:

```txt
mobile/ios/SHORTCUT_SETUP.txt
```

That file contains the exact Dropbox ingress path for your machine.

## Shortcut shape

A minimal Shortcut should:
1. ask for text input
2. optionally use dictation instead of typing
3. save the text as a `.txt` file into the notesCapture Dropbox `ingress/dropbox/` folder

Once the file lands in Dropbox, the Mac sync agent imports it into canonical entries and updates `notes.txt` automatically.

## Why this design

This keeps mobile capture very lightweight and platform-friendly:
- iPhone does not need the repo
- Android can later do the same thing with Dropbox or another shared folder
- Windows can later drop files into the same ingress folder or another transport adapter
- the durable memory remains plain files, not a proprietary database

Legacy note:
- if you already have an older Shortcut writing to `inbox/`, it will still work for now
- new Shortcut setups should use `ingress/dropbox/`
