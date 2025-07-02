#!/usr/bin/env python3
"""
Script to create app icon and DMG background for MAC File Manager Pro
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon():
    """Create a modern app icon for MAC File Manager Pro"""
    # Create 1024x1024 icon (standard size)
    size = 1024
    icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    # Background gradient (rounded rectangle)
    margin = 60
    corner_radius = 180
    
    # Create gradient background
    for y in range(size):
        ratio = y / size
        r = int(70 + (30 * ratio))
        g = int(130 + (50 * ratio))
        b = int(220 + (35 * ratio))
        color = (r, g, b, 255)
        draw.rectangle([margin, y, size-margin, y+1], fill=color)
    
    # Create rounded corners mask
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([margin, margin, size-margin, size-margin], 
                               radius=corner_radius, fill=255)
    
    # Apply mask
    icon.putalpha(mask)
    
    # Draw folder icons (dual pane representation)
    folder_width = 160
    folder_height = 120
    folder_gap = 40
    
    # Left folder
    left_x = size//2 - folder_width - folder_gap//2
    left_y = size//2 - folder_height//2
    
    # Right folder
    right_x = size//2 + folder_gap//2
    right_y = size//2 - folder_height//2
    
    # Draw folders
    for x, y in [(left_x, left_y), (right_x, right_y)]:
        # Folder shadow
        shadow_offset = 8
        draw.rounded_rectangle([x+shadow_offset, y+shadow_offset, 
                               x+folder_width+shadow_offset, y+folder_height+shadow_offset],
                              radius=15, fill=(0, 0, 0, 60))
        
        # Folder body
        draw.rounded_rectangle([x, y, x+folder_width, y+folder_height],
                              radius=15, fill=(255, 255, 255, 240))
        
        # Folder tab
        tab_width = 60
        tab_height = 20
        draw.rounded_rectangle([x+20, y-tab_height, x+20+tab_width, y+5],
                              radius=8, fill=(255, 255, 255, 240))
        
        # Folder lines (representing files)
        line_color = (100, 100, 100, 180)
        for i in range(3):
            line_y = y + 30 + i * 20
            draw.rectangle([x+20, line_y, x+folder_width-20, line_y+3], fill=line_color)
    
    # Draw arrow between folders
    arrow_y = size//2
    arrow_start_x = left_x + folder_width + 10
    arrow_end_x = right_x - 10
    arrow_color = (255, 200, 0, 255)
    
    # Arrow shaft
    draw.rectangle([arrow_start_x, arrow_y-4, arrow_end_x-15, arrow_y+4], fill=arrow_color)
    
    # Arrow head
    arrow_points = [
        (arrow_end_x-15, arrow_y-12),
        (arrow_end_x, arrow_y),
        (arrow_end_x-15, arrow_y+12)
    ]
    draw.polygon(arrow_points, fill=arrow_color)
    
    return icon

def create_dmg_background():
    """Create DMG background with drag instruction"""
    # Standard DMG background size
    width, height = 600, 400
    bg = Image.new('RGBA', (width, height), (245, 245, 250, 255))
    draw = ImageDraw.Draw(bg)
    
    # Subtle gradient
    for y in range(height):
        ratio = y / height
        r = int(245 - (20 * ratio))
        g = int(245 - (20 * ratio))
        b = int(250 - (30 * ratio))
        color = (r, g, b, 255)
        draw.rectangle([0, y, width, y+1], fill=color)
    
    # App icon position (left side)
    app_icon_x = 120
    app_icon_y = height//2 - 64
    
    # Applications folder position (right side)
    apps_folder_x = 480
    apps_folder_y = height//2 - 64
    
    # Draw app icon placeholder (will be replaced by actual icon)
    app_icon_size = 128
    draw.rounded_rectangle([app_icon_x, app_icon_y, 
                           app_icon_x + app_icon_size, app_icon_y + app_icon_size],
                          radius=25, fill=(70, 130, 220, 255))
    
    # Draw MAC text on app icon
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Text on app icon
    text_color = (255, 255, 255, 255)
    draw.text((app_icon_x + 15, app_icon_y + 35), "MAC", fill=text_color, font=font_large)
    draw.text((app_icon_x + 10, app_icon_y + 55), "File Mgr", fill=text_color, font=font_small)
    draw.text((app_icon_x + 25, app_icon_y + 75), "Pro", fill=text_color, font=font_large)
    
    # Draw Applications folder
    folder_color = (100, 150, 255, 255)
    draw.rounded_rectangle([apps_folder_x, apps_folder_y, 
                           apps_folder_x + app_icon_size, apps_folder_y + app_icon_size],
                          radius=25, fill=folder_color)
    
    # Applications folder icon details
    draw.text((apps_folder_x + 15, apps_folder_y + 50), "Applications", 
              fill=(255, 255, 255, 255), font=font_small)
    
    # Draw curved arrow
    arrow_color = (255, 100, 100, 255)
    arrow_width = 6
    
    # Arrow path (curved)
    start_x = app_icon_x + app_icon_size + 20
    start_y = app_icon_y + app_icon_size//2
    end_x = apps_folder_x - 20
    end_y = apps_folder_y + app_icon_size//2
    
    # Draw arrow shaft (simplified curve)
    mid_x = (start_x + end_x) // 2
    mid_y = start_y - 40  # Curve upward
    
    # Draw curved line segments
    for i in range(50):
        t = i / 49.0
        # Quadratic Bezier curve
        x = (1-t)**2 * start_x + 2*(1-t)*t * mid_x + t**2 * end_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * mid_y + t**2 * end_y
        
        draw.ellipse([x-arrow_width//2, y-arrow_width//2, 
                     x+arrow_width//2, y+arrow_width//2], fill=arrow_color)
    
    # Arrow head
    head_size = 15
    arrow_points = [
        (end_x - head_size, end_y - head_size),
        (end_x + head_size, end_y),
        (end_x - head_size, end_y + head_size)
    ]
    draw.polygon(arrow_points, fill=arrow_color)
    
    # Add "Drag to Install" text
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Main instruction text
    title_text = "Drag to Install"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 50
    
    draw.text((title_x, title_y), title_text, fill=(50, 50, 50, 255), font=title_font)
    
    # Subtitle
    subtitle_text = "Drag MAC File Manager Pro to Applications folder"
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + 40
    
    draw.text((subtitle_x, subtitle_y), subtitle_text, fill=(100, 100, 100, 255), font=subtitle_font)
    
    return bg

def main():
    print("Creating app icon...")
    icon = create_app_icon()
    
    # Save as PNG first
    icon.save("app_icon.png", "PNG")
    print("✅ App icon saved as app_icon.png")
    
    # Convert to ICNS for macOS
    try:
        # Create iconset directory
        iconset_dir = "AppIcon.iconset"
        os.makedirs(iconset_dir, exist_ok=True)
        
        # Create different sizes for iconset
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for size in sizes:
            resized = icon.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(f"{iconset_dir}/icon_{size}x{size}.png")
            if size <= 512:  # Also create @2x versions
                resized.save(f"{iconset_dir}/icon_{size//2}x{size//2}@2x.png")
        
        # Convert to ICNS using iconutil (macOS only)
        os.system(f"iconutil -c icns {iconset_dir} -o new_file_manager_icon.icns")
        print("✅ ICNS file created as new_file_manager_icon.icns")
        
        # Clean up iconset directory
        import shutil
        shutil.rmtree(iconset_dir)
        
    except Exception as e:
        print(f"⚠️  Could not create ICNS file: {e}")
        print("   You can use the PNG file and convert it manually")
    
    print("\nCreating DMG background...")
    dmg_bg = create_dmg_background()
    dmg_bg.save("dmg_background.png", "PNG")
    print("✅ DMG background saved as dmg_background.png")
    
    print("\n🎉 Assets created successfully!")
    print("   - Use new_file_manager_icon.icns for the app")
    print("   - Use dmg_background.png for the DMG installer")

if __name__ == "__main__":
    main()
