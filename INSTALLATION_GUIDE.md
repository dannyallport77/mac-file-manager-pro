# MAC File Manager Pro - Installation Guide

## 🔒 macOS Security Warning

When you first try to open MAC File Manager Pro, you may see this warning:

> **"Apple could not verify 'MAC File Manager Pro.app' is free of malware that may harm your Mac or compromise your privacy."**

This is normal for unsigned applications and doesn't mean the app is unsafe. Here's how to safely install and run it:

## ✅ Method 1: Right-Click to Open (Recommended)

1. **Download** `File Manager Pro.dmg` from the [Releases page](https://github.com/dannyallport77/mac-file-manager-pro/releases)
2. **Open the DMG** and drag `MAC File Manager Pro.app` to your Applications folder
3. **Go to Applications folder** in Finder
4. **Right-click** on `MAC File Manager Pro.app`
5. **Select "Open"** from the context menu
6. **Click "Open"** in the security dialog that appears
7. The app will now run and be trusted for future launches

## ⚙️ Method 2: System Preferences (Alternative)

If the right-click method doesn't work:

1. Try to open the app normally (it will be blocked)
2. **Open System Preferences** → **Security & Privacy**
3. **Click the "General" tab**
4. You'll see: *"MAC File Manager Pro.app was blocked from use because it is not from an identified developer"*
5. **Click "Open Anyway"**
6. **Click "Open"** in the confirmation dialog

## 🛡️ Method 3: Terminal Command (Advanced Users)

For advanced users, you can remove the quarantine attribute:

```bash
sudo xattr -rd com.apple.quarantine "/Applications/MAC File Manager Pro.app"
```

## 🔐 Why This Happens

- **Code Signing**: The app isn't signed with an Apple Developer Certificate ($99/year)
- **Notarization**: The app hasn't been notarized by Apple's servers
- **Gatekeeper**: macOS security feature that blocks unsigned apps by default
- **Open Source**: This is a free, open-source project without commercial code signing

## ✨ App Features

Once installed, you'll have access to:

- **Dual-pane file browser** - Navigate two directories simultaneously
- **Drag & drop** - Move files between panes easily
- **Multiple view modes** - Icon, List, Column, and Preview views
- **Search functionality** - Find files quickly
- **Media preview** - Preview images, videos, and documents
- **Keyboard shortcuts** - Efficient navigation
- **File operations** - Copy, move, delete, create folders

## 🔍 Source Code

This is an open-source project. You can:
- **View the source code**: [GitHub Repository](https://github.com/dannyallport77/mac-file-manager-pro)
- **Build from source**: Clone the repo and run `python mac_file_manager_pro/file_manager.py`
- **Report issues**: Use the GitHub Issues tab
- **Contribute**: Submit pull requests

## 📞 Support

If you encounter any issues:
1. Check the [GitHub Issues](https://github.com/dannyallport77/mac-file-manager-pro/issues)
2. Create a new issue with details about your problem
3. Include your macOS version and error messages

---

**Note**: This warning is purely about the lack of Apple's commercial code signature, not about the app's safety or functionality.
