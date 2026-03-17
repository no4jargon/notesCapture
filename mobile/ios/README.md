# iPhone setup for notesCapture

Current mobile contract:
- Mac capture writes to `ingress/local/`
- mobile capture writes plain text files into `ingress/dropbox/`
- the Mac importer turns ingress files into canonical entries and rebuilds `notes.txt`

## Setup

1. run `./setup.sh` on your Mac
2. open:

```txt
mobile/ios/SHORTCUT_SETUP.txt
```

That generated file contains the exact Dropbox ingress path for your machine.

## Shortcut shape

A minimal Shortcut should:
1. ask for text input or dictation
2. save one `.txt` file into `ingress/dropbox/`

Once the file lands in Dropbox, the Mac importer moves it into canonical storage and updates `notes.txt` automatically.

## Why this stays lightweight

- iPhone does not need the repo
- Dropbox is enough for shared transport
- future Android or Windows clients can use the same ingress pattern
