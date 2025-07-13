#!/usr/bin/env python3
"""Download TNG computer beep files and find the longest ones"""

import os
import subprocess
import urllib.request
from mutagen.mp3 import MP3
import tempfile

def download_beep_files():
    """Download all TNG computer beep files 1-77"""
    base_url = "https://www.trekcore.com/audio/computer/computerbeep_{}.mp3"
    download_dir = "/tmp/tng_beeps"
    
    # Create download directory
    os.makedirs(download_dir, exist_ok=True)
    
    print("📥 Downloading TNG computer beep files...")
    files_info = []
    
    for i in range(1, 78):  # 1-77
        url = base_url.format(i)
        filename = f"computerbeep_{i}.mp3"
        filepath = os.path.join(download_dir, filename)
        
        try:
            print(f"Downloading {filename}...")
            # Use curl with proper headers to bypass 406 error
            result = subprocess.run([
                'curl', '-L', '-o', filepath, 
                '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                '-H', 'Accept: audio/mpeg,audio/*,*/*',
                url
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"curl failed: {result.stderr}")
            
            # Get file duration
            try:
                audio = MP3(filepath)
                duration = audio.info.length
                files_info.append((filename, filepath, duration))
                print(f"  ✅ {filename}: {duration:.2f}s")
            except Exception as e:
                print(f"  ⚠️ Could not get duration for {filename}: {e}")
                files_info.append((filename, filepath, 0))
                
        except Exception as e:
            print(f"  ❌ Failed to download {filename}: {e}")
    
    return files_info

def find_longest_beeps(files_info, count=20):
    """Find the longest beep files"""
    # Sort by duration (longest first)
    sorted_files = sorted(files_info, key=lambda x: x[2], reverse=True)
    
    print(f"\n🎵 Top {count} longest TNG computer beeps:")
    longest_files = []
    
    for i, (filename, filepath, duration) in enumerate(sorted_files[:count]):
        print(f"{i+1:2d}. {filename}: {duration:.2f}s")
        longest_files.append((filename, filepath, duration))
    
    return longest_files

def copy_to_pi(longest_files):
    """Copy the longest files to the Pi"""
    print(f"\n📤 Copying {len(longest_files)} files to Pi...")
    
    # Create beeps directory on Pi
    subprocess.run([
        'ssh', 'dan@pi5.local', 'mkdir', '-p', '/home/dan/tng_beeps'
    ])
    
    for filename, filepath, duration in longest_files:
        try:
            print(f"Copying {filename}...")
            subprocess.run([
                'scp', filepath, f'dan@pi5.local:/home/dan/tng_beeps/'
            ], check=True)
            print(f"  ✅ Copied {filename}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to copy {filename}: {e}")

def main():
    print("🖖 TNG Computer Beep Downloader")
    print("=" * 40)
    
    # Download all files
    files_info = download_beep_files()
    
    if not files_info:
        print("❌ No files downloaded")
        return
    
    # Find longest files
    longest_files = find_longest_beeps(files_info, 20)
    
    # Copy to Pi
    copy_to_pi(longest_files)
    
    print("\n✅ Complete! Longest TNG computer beeps ready on Pi.")
    print("Files are in: /home/dan/tng_beeps/")

if __name__ == "__main__":
    main()