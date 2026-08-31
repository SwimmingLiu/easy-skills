#!/usr/bin/env python3
"""
Download Douyin (抖音) videos using yt-dlp.

Usage: python3 download_douyin.py <douyin_url> [output_dir] [proxy]

Examples:
    # Basic download
    python3 download_douyin.py 'https://www.douyin.com/video/7530216143047363891'

    # With custom output directory
    python3 download_douyin.py 'https://www.douyin.com/video/...' ~/Downloads/tmp/video/douyin

    # With proxy (for users outside China)
    python3 download_douyin.py 'https://www.douyin.com/video/...' ~/Downloads/tmp/video/douyin "http://127.0.0.1:7897"
"""

import os
import subprocess
import sys
from pathlib import Path


def find_available_proxy():
    """
    Try to find an available Clash proxy by checking common ports.
    Returns proxy URL if found, None otherwise.
    """
    common_ports = [7890, 7891, 7897, 1080, 10808]

    for port in common_ports:
        proxy = f"http://127.0.0.1:{port}"
        try:
            # Test if proxy is available
            result = subprocess.run(
                [
                    "curl",
                    "-x",
                    proxy,
                    "-I",
                    "--connect-timeout",
                    "2",
                    "https://www.douyin.com",
                ],
                capture_output=True,
                timeout=3,
            )
            if result.returncode == 0:
                print(f"✅ Found available proxy: {proxy}")
                return proxy
        except (subprocess.TimeoutExpired, Exception):
            continue

    return None


def download_douyin(url: str, output_dir: str = None, proxy: str = None):
    """
    Download a Douyin video using yt-dlp.

    Args:
        url: Douyin video URL (e.g., https://www.douyin.com/video/...)
        output_dir: Output directory (defaults to ~/Downloads/tmp/video/douyin)
        proxy: Proxy URL (e.g., http://127.0.0.1:7897) or "auto" for auto-detection
    """
    if output_dir is None:
        output_dir = os.path.expanduser("~/Downloads/tmp/video/douyin")

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Auto-detect proxy if not specified
    if proxy is None or proxy == "auto":
        detected_proxy = find_available_proxy()
        if detected_proxy:
            proxy = detected_proxy
        else:
            print("⚠️  No proxy detected. Continuing without proxy...")
            print("    (If download fails, try specifying a proxy manually)")

    # Build yt-dlp command for Douyin
    cmd = [
        "yt-dlp",
        "--cookies-from-browser",
        "chrome",  # Try to use cookies for authenticated content
        "-f",
        "best",  # Download best quality
        "--merge-output-format",
        "mp4",  # Merge to mp4
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "all",
        "-o",
        os.path.join(output_dir, "%(uploader)s_%(id)s.%(ext)s"),  # Output template
    ]

    # Add proxy if specified
    if proxy:
        cmd.extend(["--proxy", proxy])
        print(f"🔄 Using proxy: {proxy}")

    # Add referer to bypass anti-crawler measures
    cmd.extend(
        [
            "--referer",
            "https://www.douyin.com/",
            "--user-agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    )

    cmd.append(url)

    print(f"📥 Downloading from Douyin: {url}")
    print(f"📁 Output directory: {output_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("✅ Download completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   ⚠️  IMPORTANT: Douyin requires valid login cookies!")
        print("   1. Open Chrome and log in to https://www.douyin.com")
        print("   2. After logging in, try the download again")
        print("   3. Make sure yt-dlp is up to date: brew upgrade yt-dlp")
        print("   4. For users outside China, make sure proxy is working:")
        print("      curl -x http://127.0.0.1:7897 -I https://www.douyin.com")
        print("\n📌 Note: Without valid Douyin cookies, downloads will fail.")
        print("   Make sure you're logged in to Douyin in Chrome browser.")
        return False
    except FileNotFoundError:
        print("❌ Error: yt-dlp not found. Please install it:")
        print("   brew install yt-dlp")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_douyin.py <douyin_url> [output_dir] [proxy]")
        print("\nExamples:")
        print("  # Basic download")
        print(
            "  python3 download_douyin.py 'https://www.douyin.com/video/7530216143047363891'"
        )
        print("\n  # With custom output directory")
        print(
            "  python3 download_douyin.py 'https://www.douyin.com/video/...' ~/Downloads/tmp/video/douyin"
        )
        print("\n  # With proxy (auto-detection)")
        print(
            "  python3 download_douyin.py 'https://www.douyin.com/video/...' ~/Downloads/tmp/video/douyin auto"
        )
        print("\n  # With manual proxy")
        print(
            "  python3 download_douyin.py 'https://www.douyin.com/video/...' ~/Downloads/tmp/video/douyin 'http://127.0.0.1:7897'"
        )
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    proxy = sys.argv[3] if len(sys.argv) > 3 else None

    success = download_douyin(url, output_dir, proxy)
    sys.exit(0 if success else 1)
