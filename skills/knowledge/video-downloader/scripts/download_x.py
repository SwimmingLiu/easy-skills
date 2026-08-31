#!/usr/bin/env python3
"""
Download X (Twitter) videos using yt-dlp.
X/Twitter videos require authentication for most content.
This script attempts to use browser cookies for authenticated access.

Usage: python3 download_x.py <x_url> [output_dir] [no_cookies]
"""

import os
import socket
import subprocess
import sys
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
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    return None


def download_x(
    url: str,
    output_dir: str = None,
    use_cookies: bool = True,
    proxy: str = None,
    auto_detect: bool = True,
):
    """
    Download an X (Twitter) video using yt-dlp.

    Args:
        url: X/Twitter video URL (e.g., https://x.com/user/status/123456)
        output_dir: Output directory (defaults to ~/Downloads/tmp/video/x)
        use_cookies: Try to use browser cookies for authentication (default: True)
        proxy: Optional proxy URL (e.g., "http://127.0.0.1:7897")
        auto_detect: Auto-detect proxy if not specified (default: True)
    """
    if output_dir is None:
        output_dir = os.path.expanduser("~/Downloads/tmp/video/x")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Auto-detect proxy if not specified and enabled
    if proxy is None and auto_detect:
        detected_proxy = detect_proxy()
        if detected_proxy:
            proxy = detected_proxy
            print(f"🔍 Auto-detected proxy: {proxy}")

    # Build yt-dlp command for X/Twitter
    cmd = [
        "yt-dlp",
        "-f",
        "(bestvideo[vcodec~='^avc1']+bestaudio[acodec~='^mp4a'])/(bestvideo[vcodec~='^avc1']+bestaudio)/(bestvideo[ext=mp4]+bestaudio[ext=m4a])/bestvideo+bestaudio/best",  # Prefer H.264/AAC for QuickTime compatibility
        "--merge-output-format",
        "mp4",  # Merge to mp4
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "all",
        "-o",
        os.path.join(
            output_dir, "%(uploader)s_%(id)s.%(ext)s"
        ),  # Output template with username and tweet ID
    ]

    # Add cookies if enabled
    if use_cookies:
        cmd.extend(["--cookies-from-browser", "chrome"])
        print("🔐 Using Chrome cookies for authentication")

    # Add proxy if specified
    if proxy:
        cmd.extend(["--proxy", proxy])
        print(f"🔧 Using proxy: {proxy}")

    cmd.append(url)

    print(f"📥 Downloading from X (Twitter): {url}")
    print(f"📁 Output directory: {output_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("✅ Download completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
        if use_cookies:
            print("\n💡 Tips:")
            print("   1. Make sure Chrome is running and you're logged in to X/Twitter")
            print("   2. Try without cookies:")
            print(f"      python3 {sys.argv[0]} '{url}' ~/Downloads/tmp/video/x no_cookies")
            print("   3. Try with Firefox cookies:")
            print(f"      yt-dlp --cookies-from-browser firefox '{url}'")
        return False
    except FileNotFoundError:
        print("❌ Error: yt-dlp not found. Please install it:")
        print("   brew install yt-dlp")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_x.py <x_url> [output_dir] [no_cookies]")
        print("\nExamples:")
        print("  # With Chrome cookies and auto proxy detection (recommended)")
        print("  python3 download_x.py 'https://x.com/user/status/123456'")
        print("\n  # Without cookies (for public content only)")
        print(
            "  python3 download_x.py 'https://x.com/user/status/123456' ~/Downloads no_cookies"
        )
        print("\n  # Custom output directory")
        print(
            "  python3 download_x.py 'https://x.com/user/status/123456' /path/to/output"
        )
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    use_cookies = sys.argv[3].lower() != "no_cookies" if len(sys.argv) > 3 else True

    success = download_x(url, output_dir, use_cookies)
    sys.exit(0 if success else 1)
