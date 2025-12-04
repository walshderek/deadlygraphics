import os
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageOps

def get_valid_path():
    """Prompts the user for a path and validates it."""
    while True:
        print("\nPlease paste the full path to your dataset folder.")
        print("(e.g., C:\\Users\\seanf\\... or /home/seanf/...)")
        user_input = input("Enter path: ").strip()
        
        # Remove quotes if the user pasted them
        user_input = user_input.strip('"').strip("'")
        
        # Expand ~ to user home (Linux/WSL specific)
        expanded_path = os.path.expanduser(user_input)
        path_obj = Path(expanded_path)
        
        if path_obj.exists() and path_obj.is_dir():
            return path_obj
        else:
            print(f"❌ Error: Directory not found at: {path_obj}")
            print("Please try again.")

def resize_and_pad(image_path, output_path, size=(512, 512)):
    """Resizes an image to fit within size, padding with black to keep aspect ratio."""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB to handle PNGs with transparency or CMYK
            img = img.convert("RGB")
            
            # Resize maintaining aspect ratio (thumbnail is in-place)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create a new black background image
            new_img = Image.new("RGB", size, (0, 0, 0))
            
            # Paste the resized image into the center
            left = (size[0] - img.width) // 2
            top = (size[1] - img.height) // 2
            new_img.paste(img, (left, top))
            
            # Save
            new_img.save(output_path, quality=95)
            return True
    except Exception as e:
        print(f"❌ Error processing {image_path.name}: {e}")
        return False

def main():
    print("=== DG Dataset Collector ===")
    print("This script will backup your originals and create a 512x512 dataset.")
    
    # 1. Get directory
    input_dir = get_valid_path()
    
    # 2. Setup output folders
    source_dir = input_dir / "source"
    resized_dir = input_dir / "512"
    
    print(f"\nProcessing folder: {input_dir}")
    
    if not source_dir.exists():
        source_dir.mkdir()
    if not resized_dir.exists():
        resized_dir.mkdir()
        
    # 3. Process files
    valid_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    processed_count = 0
    txt_count = 0
    
    # List files (excluding directories)
    files = [f for f in input_dir.iterdir() if f.is_file()]
    
    print(f"Found {len(files)} files. Starting processing...\n")
    
    for file_path in files:
        # A. Handle Text Files
        if file_path.suffix.lower() == '.txt':
            # Copy to source (backup)
            shutil.copy2(file_path, source_dir / file_path.name)
            # Copy to 512 (training)
            shutil.copy2(file_path, resized_dir / file_path.name)
            print(f"📄 Copied caption: {file_path.name}")
            txt_count += 1
            
        # B. Handle Image Files
        elif file_path.suffix.lower() in valid_extensions:
            # Copy original to source (backup)
            shutil.copy2(file_path, source_dir / file_path.name)
            
            # Resize and save to 512
            target_path = resized_dir / file_path.name
            success = resize_and_pad(file_path, target_path, size=(512, 512))
            
            if success:
                print(f"🖼️  Resized image: {file_path.name}")
                processed_count += 1
                
    print("\n" + "="*30)
    print("✅ Processing Complete!")
    print("="*30)
    print(f"Images Resized: {processed_count}")
    print(f"Captions Copied: {txt_count}")
    print(f"Originals backed up to: {source_dir}")
    print(f"Training set created at: {resized_dir}")
    print("\nREMINDER: Update your .toml configuration:")
    print(f'image_directory = "{resized_dir.as_posix()}"')
    print('resolution = [512, 512]')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")