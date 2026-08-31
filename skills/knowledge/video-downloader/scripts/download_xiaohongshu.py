#!/usr/bin/env python3
"""
Xiaohongshu (小红书) Video Downloader
Download videos from Xiaohongshu using yt-dlp with auto proxy detection.

Usage:
    python3 download_xiaohongshu.py <url> [output_dir] [proxy]

Examples:
    python3 download_xiaohongshu.py 'http://xhslink.com/xxx'
    python3 download_xiaohongshu.py 'https://www.xiaohongshu.com/discovery/item/xxx'
    python3 download_xiaohongshu.py '<url>' ~/Downloads/tmp/video/xiaohongshu
    python3 download_xiaohongshu.py '<url>' ~/Downloads/tmp/video/xiaohongshu "http://127.0.0.1:7897"
"""

import subprocess
import sys
import os
import requests
from pathlib import Path

# Default output directory
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/Downloads/tmp/video/xiaohongshu")

# Common Clash proxy ports to try
PROXY_PORTS = [7890, 7891, 7897, 1080, 10808]


def find_available_proxy():
    """Find an available Clash proxy port."""
    for port in PROXY_PORTS:
        proxy_url = f"http://127.0.0.1:{port}"
        try:
            response = requests.get(
                "http://www.google.com",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=2
            )
            if response.status_code == 200:
                print(f"✅ Found available proxy: {proxy_url}")
                return proxy_url
        except:
            continue
    return None


def download_xiaohongshu(url, output_dir=DEFAULT_OUTPUT_DIR, proxy=None):
    """Download Xiaohongshu video using yt-dlp."""

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "-f", "best",
        "--merge-output-format", "mp4",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "all",
        "-o", os.path.join(output_dir, "%(id)s.%(ext)s"),
        url
    ]

    # Add proxy if specified or auto-detect
    if proxy:
        if proxy.lower() == "auto" or proxy.lower() == "none":
            # Auto-detect proxy
            detected_proxy = find_available_proxy()
            if detected_proxy:
                cmd.extend(["--proxy", detected_proxy])
                print(f"🔄 Using proxy: {detected_proxy}")
        else:
            cmd.extend(["--proxy", proxy])
            print(f"🔄 Using proxy: {proxy}")
    else:
        # Auto-detect proxy by default
        detected_proxy = find_available_proxy()
        if detected_proxy:
            cmd.extend(["--proxy", detected_proxy])
            print(f"🔄 Using proxy: {detected_proxy}")

    print(f"📥 Downloading from Xiaohongshu: {url}")
    print(f"📁 Output directory: {output_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("✅ Download completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ yt-dlp not found. Please install it: brew install yt-dlp")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 download_xiaohongshu.py <url> [output_dir] [proxy]")
        print("\nExamples:")
        print("  python3 download_xiaohongshu.py 'http://xhslink.com/xxx'")
        print("  python3 download_xiaohongshu.py 'https://www.xiaohongshu.com/discovery/item/xxx'")
        print("  python3 download_xiaohongshu.py '<url>' ~/Downloads/tmp/video/xiaohongshu")
        print("  python3 download_xiaohongshu.py '<url>' ~/Downloads/tmp/video/xiaohongshu 'http://127.0.0.1:7897'")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR
    proxy = sys.argv[3] if len(sys.argv) > 3 else None

    # Handle "no_cookies" as no proxy override
    if proxy and proxy.lower() == "no_cookies":
        proxy = None

    success = download_xiaohongshu(url, output_dir, proxy)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
