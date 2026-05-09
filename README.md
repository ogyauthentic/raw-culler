# RAW Culler 📷

A fast RAW photo culling tool for Windows 10 — inspired by Ogy.
Instantly extract camera-embedded JPEG thumbnails without full RAW rendering, so you can keep, reject, and flag photos at full speed.

## Supported Formats

`.raf` `.arw` `.cr3` `.nef` `.dng` `.orf` `.rw2` `.pef`

## Features

- ⚡ **Fast preview** — extracts camera-embedded thumbnail, no full RAW render
- 🖼️ **Thumbnail strip** — scrollable panel with color-coded status indicators
- ✓ **Keep / Reject / Flag** — one keypress culling
- 💾 **Export** — copy all Keep photos to a destination folder
- 🌑 **Dark UI** — easy on the eyes during long culling sessions

## Screenshot

> *(Add a screenshot here after first run)*

## Installation

### Option A — Standalone EXE *(no Python required)*
1. Go to [Releases](../../releases)
2. Download `RAW_Culler.exe`
3. Double-click — done ✅

### Option B — Run from source
```bash
pip install rawpy imageio Pillow
python raw_culler.py
```

## Build the Installer Yourself

Requirements: Python 3.10+, [Inno Setup 6](https://jrsoftware.org/isdl.php) *(optional)*

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/raw-culler.git
cd raw-culler

# 2. Double-click build_installer.bat
#    or run from terminal:
build_installer.bat
```

Output:
- `dist\RAW_Culler.exe` — standalone portable EXE
- `Output\RAW_Culler_Setup.exe` — full installer with Start Menu shortcut & uninstaller *(requires Inno Setup)*

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `← →` | Navigate photos |
| `K` | Mark as Keep |
| `X` / `Del` | Mark as Reject |
| `F` | Mark as Flagged |
| `U` | Clear status |
| `Ctrl+O` | Open folder |
| `Ctrl+S` | Export all Keep photos |

## Project Structure

```
raw-culler/
├── raw_culler.py       # Main application
├── raw_culler.spec     # PyInstaller build spec
├── installer.iss       # Inno Setup installer script
├── build_installer.bat # One-click build script
├── requirements.txt    # Python dependencies
└── README.md
```

## License
GPL v3 — see [LICENSE](LICENSE) for details.