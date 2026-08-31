#!/usr/bin/env python3
"""
Download YouTube videos using yt-dlp.
Usage: python3 download_youtube.py <youtube_url> [output_dir] [proxy] [no_cookies]
"""

import sys
import subprocess
import os
import socket
from pathlib import Path

def detect_proxy():
    """
    Auto-detect common Clash proxy ports.
    Returns the first available proxy URL or None.
    """
    common_ports = [7890, 7891, 7897, 1080, 10808]

    for port in common_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    return None

def download_youtube(url: str, output_dir: str | None = None, proxy: str | None = None, auto_detect: bool = True, use_cookies: bool = True):
    """
    Download a YouTube video using yt-dlp.

    Args:
        url: YouTube video URL
        output_dir: Output directory (defaults to ~/Downloads/tmp/video/youtube)
        proxy: Optional proxy URL (e.g., "http://127.0.0.1:7897")
        auto_detect: Auto-detect proxy if not specified (default: True)
        use_cookies: Use browser cookies for authentication (default: True)
    """
    if output_dir is None:
        output_dir = os.path.expanduser("~/Downloads/tmp/video/youtube")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Auto-detect proxy if not specified and enabled
    if proxy is None and auto_detect:
        detected_proxy = detect_proxy()
        if detected_proxy:
            proxy = detected_proxy
            print(f"🔍 Auto-detected proxy: {proxy}")

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "-f", "(bestvideo[vcodec~='^avc1']+bestaudio[acodec~='^mp4a'])/(bestvideo[vcodec~='^avc1']+bestaudio)/(bestvideo[ext=mp4]+bestaudio[ext=m4a])/bestvideo+bestaudio/best",  # Prefer H.264/AAC for QuickTime compatibility
        "--merge-output-format", "mp4",     # Merge to mp4
        "--write-subs",                     # Download subtitles if available
        "--write-auto-subs",                # Download auto-generated subtitles if available
        "--embed-subs",                     # Embed subtitles if available
        "--sub-langs", "zh-Hans,zh-Hant,zh,en",  # Prefer Chinese and English subtitles
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),  # Output template
        "--extractor-args", "youtube:player_client=web",  # Use web client to avoid bot detection
        "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Add cookies from browser for authentication
    if use_cookies:
        # Try to find Comet browser cookies first (Comet is based on Chromium)
        # Common Comet data paths on macOS
        comet_paths = [
            os.path.expanduser("~/Library/Application Support/Comet"),
            os.path.expanduser("~/Library/Application Support/comet"),
        ]
        comet_found = False
        for comet_path in comet_paths:
            if os.path.exists(comet_path):
                print(f"🔍 Found Comet browser data at: {comet_path}")
                cmd.extend(["--cookies-from-browser", f"chrome:{comet_path}"])
                comet_found = True
                break
        if not comet_found:
            # Fallback to Chrome
            cmd.extend(["--cookies-from-browser", "chrome"])

    # Add proxy if specified
    if proxy:
        cmd.extend(["--proxy", proxy])
        print(f"🔧 Using proxy: {proxy}")

    cmd.append(url)

    print(f"📥 Downloading from YouTube: {url}")
    print(f"📁 Output directory: {output_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("✅ Download completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
        if not proxy and auto_detect:
            print("\n💡 Tip: YouTube may require a proxy in your region.")
            print("   Try manually specifying a proxy:")
            print(f"   python3 {sys.argv[0]} '{url}' ~/Downloads/tmp/video/youtube 'http://127.0.0.1:7897'")
        return False
    except FileNotFoundError:
        print("❌ Error: yt-dlp not found. Please install it:")
        print("   brew install yt-dlp")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_youtube.py <youtube_url> [output_dir] [proxy] [no_cookies]")
        print("\nExamples:")
        print("  # Auto-detect proxy with cookies (recommended)")
        print("  python3 download_youtube.py 'https://youtube.com/watch?v=xxx'")
        print("\n  # Without cookies (for public videos)")
        print("  python3 download_youtube.py 'https://youtube.com/watch?v=xxx' ~/Downloads/tmp/video/youtube auto no_cookies")
        print("\n  # Manual proxy")
        print("  python3 download_youtube.py 'https://youtube.com/watch?v=xxx' ~/Downloads/tmp/video/youtube 'http://127.0.0.1:7897'")
        print("\n  # No proxy (if not needed)")
        print("  python3 download_youtube.py 'https://youtube.com/watch?v=xxx' ~/Downloads ''")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    proxy = sys.argv[3] if len(sys.argv) > 3 else None
    no_cookies = len(sys.argv) > 4 and sys.argv[4] == "no_cookies"

    # Disable auto-detection if empty string is passed
    auto_detect = proxy != ''
    if proxy == '' or proxy == 'auto':
        proxy = None

    success = download_youtube(url, output_dir, proxy, auto_detect, use_cookies=not no_cookies)
    sys.exit(0 if success else 1)
