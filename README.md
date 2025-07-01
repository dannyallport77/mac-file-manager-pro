# MAC File Manager Pro

[![Build & Release DMG](https://github.com/dannyallport77/mac-file-manager-pro/actions/workflows/build-dmg.yml/badge.svg)](https://github.com/dannyallport77/mac-file-manager-pro/actions/workflows/build-dmg.yml)
[![Latest Release](https://img.shields.io/github/v/release/dannyallport77/mac-file-manager-pro?label=release)](https://github.com/dannyallport77/mac-file-manager-pro/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![codecov](https://codecov.io/gh/dannyallport77/mac-file-manager-pro/branch/main/graph/badge.svg)](https://codecov.io/gh/dannyallport77/mac-file-manager-pro)

A modern, dual-pane, drag-and-drop file manager for macOS with thumbnails, previews, and DMG installer.

## Features
- Dual-pane interface with independent navigation
- Drag-and-drop file operations (move/copy)
- Icon, List, and Column views
- Thumbnails for images, videos, and music
- Sort by name, size, type, or date
- Bookmarks, folder history, and back/forward/up navigation
- Custom DMG installer with background and Applications shortcut

## Installation
- Download the latest DMG from the [Releases](https://github.com/dannyallport77/mac-file-manager-pro/releases) page
- Open the DMG and drag `MAC File Manager Pro` to your Applications folder

## User Instructions
1. **Open the app** from your Applications folder or Launchpad.
2. **Navigate** using the dual-pane interface. Each pane can browse different folders.
3. **Drag and drop** files/folders between panes to move or copy.
4. **Change view** (Icon, List, Column) and sort order using the toolbar.
5. **Resize thumbnails** with the slider in the toolbar.
6. **Preview images, videos, and music** by selecting them.
7. **Use the Back, Forward, and Up buttons** for navigation. Bookmark favorite folders for quick access.

## Build from Source
1. Install Python 3 and [PyQt5](https://pypi.org/project/PyQt5/), [Pillow](https://pypi.org/project/Pillow/), and [PyInstaller](https://pypi.org/project/pyinstaller/):
   ```bash
   pip install PyQt5 Pillow pyinstaller
   ```
2. (Optional) Install ffmpeg for best video thumbnails:
   ```bash
   brew install ffmpeg
   ```
3. Build the app:
   ```bash
   pyinstaller --windowed --icon file_manager_icon.icns "file_manager.py"
   ```

## License
MIT License (see LICENSE file)

## Release Notes
Release notes are auto-generated for each tagged release using [Release Drafter](https://github.com/marketplace/actions/release-drafter). See the [Releases](https://github.com/dannyallport77/mac-file-manager-pro/releases) page for details.

## Screenshot
![screenshot](screenshot.png) 