#!/bin/bash

# Script to fix macOS security warning for MAC File Manager Pro
# This removes the quarantine attribute that causes the security warning

APP_PATH="/Applications/MAC File Manager Pro.app"

echo "🔧 MAC File Manager Pro - Security Fix"
echo "======================================="
echo ""

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: MAC File Manager Pro.app not found in Applications folder"
    echo "   Please install the app first by dragging it from the DMG to Applications"
    exit 1
fi

echo "📍 Found app at: $APP_PATH"
echo ""

# Check current quarantine status
echo "🔍 Checking quarantine status..."
if xattr -l "$APP_PATH" | grep -q "com.apple.quarantine"; then
    echo "⚠️  App is quarantined (this causes the security warning)"
    echo ""
    echo "🔓 Removing quarantine attribute..."
    
    # Remove quarantine attribute
    if sudo xattr -rd com.apple.quarantine "$APP_PATH"; then
        echo "✅ Successfully removed quarantine attribute"
        echo "🎉 MAC File Manager Pro should now open without security warnings"
    else
        echo "❌ Failed to remove quarantine attribute"
        echo "   Try running with: sudo xattr -rd com.apple.quarantine '$APP_PATH'"
    fi
else
    echo "✅ App is not quarantined - no security warning should occur"
fi

echo ""
echo "📝 Alternative methods:"
echo "   1. Right-click the app and select 'Open'"
echo "   2. System Preferences → Security & Privacy → 'Open Anyway'"
echo ""
echo "ℹ️  For more help, see: INSTALLATION_GUIDE.md"
