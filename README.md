# 🎬 ReelTransfer

![Version](https://img.shields.io/github/v/release/SecuredNodeDynamics/ReelTransfer)
![License](https://img.shields.io/github/license/SecuredNodeDynamics/ReelTransfer)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

**ReelTransfer** is a Windows desktop app for moving media files and folders using Robocopy with a clean, preview-first workflow.

Built with **Python + PySide6**, ReelTransfer is designed to replace manual drag‑and‑drop or brittle batch scripts with a reliable GUI tool.

---

<p align="center">
	<img src="reeltransfer_app/assets/reeltransfer.png" alt="ReelTransfer" width="300">
	<br>
	<em>Modern dark UI for safe media transfers</em>
</p>

---

## ✨ Key Features

- 📂 Select folders **or individual files** (multi‑select)
- 👀 Preview the exact Robocopy command before running
- 🧪 Dry run mode (/L) to simulate transfers safely
- 📊 Preflight size estimate before transfer
- 💾 Destination free‑space check
- 🧹 Duplicate detection with Skip / Overwrite / Auto‑rename options
- 🔁 Move or copy mode with optional subfolder inclusion
- 🧵 Configurable retries, wait time, and multithread count
- 📝 Live transfer log with clear status feedback
- 💾 Remembers last used paths and settings
- 🌙 Modern dark UI optimized for long sessions
- 🪟 Native Windows installer

---

## 🖥️ Supported Platforms

| Platform | Status |
|---------|--------|
| Windows (x64) | ✅ Installer (.exe) |
| macOS | ❌ Not supported (Robocopy is Windows‑only) |
| Linux | ❌ Not supported (Robocopy is Windows‑only) |

---

## 📦 Installation

### 🔹 Windows (Recommended)
1. Download `ReelTransfer-Setup-1.2.0.exe` from the **Releases** page
2. Double‑click the installer
3. Follow the setup wizard
4. Launch ReelTransfer from the Start Menu

> ⚠️ Windows SmartScreen may warn about an unknown publisher.  
> Click **More info → Run anyway** (normal for unsigned apps).

---

## 🚀 Usage

1. Choose a **Source** folder or click **Browse Files…** to select media files
2. Choose a **Destination** folder
3. Adjust options (move/copy, subfolders, mirror, retries, threads)
4. Click **Preview Command** to verify the Robocopy command
5. Click **Start Transfer** to run

---

## 🛠 Development

### Requirements
- Windows (Robocopy is Windows‑only)
- Python 3.10+

### Install
```
pip install -r requirements.txt
```

### Run (dev)
```
python -m reeltransfer_app.main
```

### Build (PyInstaller)
```
pyinstaller --noconfirm --clean reeltransfer.spec
```

### Installer (Inno Setup)
1. Install Inno Setup.
2. Build with PyInstaller.
3. Open installer.iss and compile.

---

## ⚠️ Notes

- Robocopy is Windows‑only.
- Mirror mode (/MIR) deletes destination files not present in source. Use with care.
