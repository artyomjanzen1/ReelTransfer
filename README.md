# ReelTransfer

ReelTransfer is a Windows desktop app that moves media files/folders from one location to another using Robocopy.

## Requirements
- Windows (Robocopy is Windows-only)
- Python 3.10+

## Install
```
pip install -r requirements.txt
```

## Run (dev)
```
python -m reeltransfer_app.main
```

## Build (PyInstaller)
```
pyinstaller --noconfirm --clean reeltransfer.spec
```

## Installer (Inno Setup)
1. Install Inno Setup.
2. Build with PyInstaller.
3. Open installer.iss and compile.

## Notes
- Mirror mode (/MIR) deletes files in destination not present in source. Use with care.
