#!/usr/bin/env python3
"""
Download Bilibili videos using yt-dlp (with bilibili support).
Note: yt-dlp is the recommended tool for Bilibili as ffmpeg alone cannot
directly download from Bilibili due to the need for authentication and
API interactions.

Usage: python3 download_bilibili.py <bilibili_url> [output_dir]
"""

import sys
import subprocess
import os
from pathlib import Path

def download_bilibili(url: str, output_dir: str = None):
    """
    Download a Bilibili video using yt-dlp.

    Args:
        url: Bilibili video URL
        output_dir: Output directory (defaults to ~/Downloads/tmp/video/bilibili)
    """
    if output_dir is None:
        output_dir = os.path.expanduser("~/Downloads/tmp/video/bilibili")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Build yt-dlp command for Bilibili
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "chrome",  # Try to use cookies for authenticated content
        "-f", "(bestvideo[vcodec~='^avc1']+bestaudio[acodec~='^mp4a'])/(bestvideo[vcodec~='^avc1']+bestaudio)/(bestvideo[ext=mp4]+bestaudio[ext=m4a])/bestvideo+bestaudio/best",  # Prefer H.264/AAC for QuickTime compatibility
        "--merge-output-format", "mp4",       # Merge to mp4
        "--write-subs",                       # Download subtitles if available
        "--write-auto-subs",                  # Download auto-generated subtitles if available
        "--embed-subs",                       # Embed subtitles if available
        "--sub-langs", "zh-Hans,zh-Hant,zh,en",  # Prefer Chinese and English subtitles
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),  # Output template
        url
    ]

    print(f"📥 Downloading from Bilibili: {url}")
    print(f"📁 Output directory: {output_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("✅ Download completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
        print("\n💡 Tip: Bilibili may require cookies for some content.")
        print("   Make sure Chrome is running and you're logged in to Bilibili.")
        print("   Or try without cookies:")
        print(f"   yt-dlp -f 'bestvideo+bestaudio/best' '{url}'")
        return False
    except FileNotFoundError:
        print("❌ Error: yt-dlp not found. Please install it:")
        print("   brew install yt-dlp")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_bilibili.py <bilibili_url> [output_dir]")
        print("\nExamples:")
        print("  python3 download_bilibili.py 'https://www.bilibili.com/video/BV...'")
        print("  python3 download_bilibili.py 'https://www.bilibili.com/video/BV...' ~/Downloads")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    success = download_bilibili(url, output_dir)
    sys.exit(0 if success else 1)
