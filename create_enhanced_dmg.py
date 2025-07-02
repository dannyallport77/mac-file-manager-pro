#!/usr/bin/env python3
"""
Script to create a professional DMG with custom background
"""
import os
import subprocess
import tempfile
import shutil

def create_enhanced_dmg():
    """Create DMG with custom background and proper layout"""
    
    # DMG settings
    dmg_title = "MAC File Manager Pro"
    dmg_name = "File Manager Pro"
    app_name = "MAC File Manager Pro.app"
    
    # Temporary directory for DMG contents
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Create DMG staging directory
        dmg_staging = os.path.join(temp_dir, "dmg_staging")
        os.makedirs(dmg_staging, exist_ok=True)
        
        # Copy app to staging
        print("Copying app to staging directory...")
        if os.path.exists(f"dist/{app_name}"):
            shutil.copytree(f"dist/{app_name}", os.path.join(dmg_staging, app_name))
        else:
            print(f"❌ App not found: dist/{app_name}")
            return False
        
        # Create Applications symlink
        print("Creating Applications symlink...")
        os.symlink("/Applications", os.path.join(dmg_staging, "Applications"))
        
        # Copy background image to .background folder
        background_dir = os.path.join(dmg_staging, ".background")
        os.makedirs(background_dir, exist_ok=True)
        if os.path.exists("dmg_background.png"):
            shutil.copy2("dmg_background.png", os.path.join(background_dir, "background.png"))
        
        # Create DS_Store file for custom layout
        ds_store_content = create_ds_store_script()
        
        # Write AppleScript to set DMG appearance
        applescript_path = os.path.join(temp_dir, "set_dmg_layout.applescript")
        with open(applescript_path, 'w') as f:
            f.write(f'''
tell application "Finder"
    tell disk "{dmg_title}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {{100, 100, 700, 500}}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 128
        set background picture of viewOptions to file ".background:background.png"
        set position of item "{app_name}" of container window to {{120, 200}}
        set position of item "Applications" of container window to {{480, 200}}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
''')
        
        # Create initial DMG
        print("Creating initial DMG...")
        initial_dmg = os.path.join(temp_dir, "temp.dmg")
        
        # Calculate size needed (app size + buffer)
        app_size = get_directory_size(f"dist/{app_name}")
        dmg_size = max(50, (app_size // (1024*1024)) + 20)  # At least 50MB
        
        cmd = [
            "hdiutil", "create",
            "-srcfolder", dmg_staging,
            "-volname", dmg_title,
            "-fs", "HFS+",
            "-fsargs", "-c c=64,a=16,e=16",
            "-format", "UDRW",
            "-size", f"{dmg_size}m",
            initial_dmg
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error creating initial DMG: {result.stderr}")
            return False
        
        # Mount the DMG
        print("Mounting DMG for customization...")
        mount_result = subprocess.run([
            "hdiutil", "attach", initial_dmg, "-readwrite", "-noverify", "-noautoopen"
        ], capture_output=True, text=True)
        
        if mount_result.returncode != 0:
            print(f"❌ Error mounting DMG: {mount_result.stderr}")
            return False
        
        # Extract mount point
        mount_point = None
        for line in mount_result.stdout.split('\n'):
            if dmg_title in line and '/Volumes/' in line:
                mount_point = line.split('\t')[-1].strip()
                break
        
        if not mount_point:
            print("❌ Could not find mount point")
            return False
        
        print(f"DMG mounted at: {mount_point}")
        
        try:
            # Wait a moment for mount to complete
            import time
            time.sleep(2)
            
            # Run AppleScript to set layout
            print("Setting DMG layout...")
            subprocess.run(["osascript", applescript_path], check=False)
            
            # Wait for changes to apply
            time.sleep(3)
            
        finally:
            # Unmount the DMG
            print("Unmounting DMG...")
            subprocess.run(["hdiutil", "detach", mount_point], check=False)
            time.sleep(2)
        
        # Convert to final compressed DMG
        print("Creating final compressed DMG...")
        final_dmg = f"{dmg_name}.dmg"
        
        cmd = [
            "hdiutil", "convert", initial_dmg,
            "-format", "UDZO",
            "-imagekey", "zlib-level=9",
            "-o", final_dmg
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error creating final DMG: {result.stderr}")
            return False
        
        print(f"✅ DMG created successfully: {final_dmg}")
        return True

def get_directory_size(path):
    """Get directory size in bytes"""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.isfile(filepath):
                    total += os.path.getsize(filepath)
    except:
        pass
    return total

def create_ds_store_script():
    """Create DS_Store configuration"""
    return """
# DS_Store configuration for DMG layout
# This would typically require more complex binary manipulation
# For now, we rely on AppleScript to set the layout
"""

if __name__ == "__main__":
    success = create_enhanced_dmg()
    if success:
        print("🎉 Enhanced DMG created successfully!")
    else:
        print("❌ Failed to create enhanced DMG")
