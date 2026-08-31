---
name: video-downloader
description: 视频下载助手。用于下载或保存 YouTube、Bilibili、抖音、小红书、X/Twitter 视频；当用户说“下载视频”“保存这个链接的视频”“抓取视频内容”“把字幕也下下来”时使用。默认保存到 ~/Downloads/tmp/video，按平台分类到 youtube、bilibili、douyin、x、xiaohongshu 子文件夹；如果源站和 yt-dlp 支持字幕，默认同时下载字幕文件，并支持自动检测 Clash 代理端口。
---

# Video Downloader

## Overview

Download videos from YouTube, Bilibili, Douyin (抖音), Xiaohongshu (小红书), and X (Twitter) to your local machine. Videos are automatically saved to `~/Downloads/tmp/video` directory, organized by platform subfolders.

**Notes**:
- **For China users**: X requires a proxy to access
- **For users outside China**: Douyin may require a proxy to access
- The script can auto-detect Clash proxies on ports 7890, 7891, 7897, 1080, 10808 or use a manually specified proxy
- If the source site and yt-dlp extractor expose subtitles, download sidecar subtitle files by default. YouTube and Bilibili also try to embed subtitles into the MP4.

## Supported Platforms

- **YouTube**: Uses `yt-dlp` with auto proxy detection, subtitle sidecar download, and subtitle embedding
- **Bilibili (B站)**: Uses `yt-dlp` with cookie support for authenticated content, subtitle sidecar download, and subtitle embedding
- **Douyin (抖音)**: Uses `yt-dlp` with cookie support, anti-crawler bypass, and best-effort subtitle download
- **X (Twitter)**: Uses `yt-dlp` with cookie support for authenticated content and best-effort subtitle download (requires proxy in China)
- **Xiaohongshu (小红书)**: Uses `yt-dlp` with auto proxy detection, supports xhslink short URLs, and best-effort subtitle download

## Quick Start

### Download from YouTube

```bash
# Auto-detect proxy with Chrome cookies (recommended)
python3 scripts/download_youtube.py 'https://www.youtube.com/watch?v=xxx'

# Download YouTube Shorts
python3 scripts/download_youtube.py 'https://www.youtube.com/shorts/xxx'

# Without cookies (for public videos that don't require authentication)
python3 scripts/download_youtube.py '<url>' ~/Downloads/tmp/video/youtube auto no_cookies

# With manual proxy
python3 scripts/download_youtube.py '<url>' ~/Downloads/tmp/video/youtube "http://127.0.0.1:7897"
```

### Download from Bilibili

```bash
python3 scripts/download_bilibili.py <bilibili_url>
```

### Download from Douyin (抖音)

```bash
# Basic download (auto proxy detection)
python3 scripts/download_douyin.py <douyin_url>

# Example
python3 scripts/download_douyin.py 'https://www.douyin.com/video/7530216143047363891'

# With custom output directory
python3 scripts/download_douyin.py <douyin_url> ~/Downloads/tmp/video/douyin

# With manual proxy (for users outside China)
python3 scripts/download_douyin.py <douyin_url> ~/Downloads/tmp/video/douyin "http://127.0.0.1:7897"
```

### Download from X/Twitter (with auto proxy detection)

The script automatically detects Clash proxy ports (7890, 7891, 7897, 1080, 10808):

```bash
python3 scripts/download_x.py <x_url>
```

### Download from X/Twitter (without cookies)

For public content that doesn't require authentication:

```bash
python3 scripts/download_x.py <x_url> ~/Downloads/tmp/video/x no_cookies
```

### Download from Xiaohongshu (小红书)

The script supports both regular URLs and short links (xhslink.com):

```bash
# Short link (recommended)
python3 scripts/download_xiaohongshu.py 'http://xhslink.com/xxx'

# Regular URL
python3 scripts/download_xiaohongshu.py 'https://www.xiaohongshu.com/discovery/item/xxx'

# With custom output directory
python3 scripts/download_xiaohongshu.py <url> ~/Downloads/tmp/video/xiaohongshu

# With manual proxy
python3 scripts/download_xiaohongshu.py <url> ~/Downloads/tmp/video/xiaohongshu "http://127.0.0.1:7897"
```

### Custom Output Directory

```bash
python3 scripts/download_youtube.py <url> /path/to/output
python3 scripts/download_bilibili.py <url> /path/to/output
python3 scripts/download_douyin.py <url> /path/to/output
python3 scripts/download_x.py <url> /path/to/output
python3 scripts/download_xiaohongshu.py <url> /path/to/output
```

### Subtitle Files

By default, scripts ask yt-dlp to download available subtitles as sidecar files next to the video.

- YouTube and Bilibili try Chinese and English subtitles, including auto-generated subtitles when available, and also try to embed subtitles into the MP4.
- Douyin, X/Twitter, and Xiaohongshu use best-effort subtitle download. Many videos on these platforms do not expose subtitles through yt-dlp.
- Subtitle files usually appear as `.vtt`, `.srt`, or another yt-dlp-supported subtitle extension, using the same title/id output template as the video.

**Default platform folders:**
- YouTube → `~/Downloads/tmp/video/youtube`
- Bilibili → `~/Downloads/tmp/video/bilibili`
- Douyin → `~/Downloads/tmp/video/douyin`
- X/Twitter → `~/Downloads/tmp/video/x`
- Xiaohongshu → `~/Downloads/tmp/video/xiaohongshu`

## Proxy Support

**Important**: If you cannot access the website or the webpage is blocked, enable proxy support.

### Auto-Detection (Recommended)

The script automatically detects and tries these common Clash proxy ports:
- `7890`, `7891`, `7897` - Clash/Clash Verge default ports
- `1080`, `10808` - Alternative proxy ports

Simply run the download command - if any of these proxies are available, they will be used automatically.

### Manual Proxy

Specify proxy as the third argument:

```bash
python3 scripts/download_x.py <url> ~/Downloads/tmp/video/x "http://127.0.0.1:7897"
```

**Proxy formats:**
- HTTP: `http://127.0.0.1:7897`
- SOCKS5: `socks5://127.0.0.1:1080`

## Scripts

### scripts/download_youtube.py

Downloads YouTube videos using yt-dlp.

**Features:**
- Auto-detects Clash proxy ports (7890, 7891, 7897, 1080, 10808) for users in China
- Downloads best quality available with H.264/AAC for QuickTime compatibility
- Downloads Chinese and English subtitle files if available
- Downloads auto-generated subtitles when available
- Embeds subtitles into the MP4 when supported
- Merges streams into MP4 format
- Saves with video title as filename
- Supports cookies from Chrome browser for authenticated content

**Requirements:**
```bash
brew install yt-dlp
```

**Notes:**
- YouTube requires a proxy in China. The script auto-detects common Clash proxy ports.
- Some videos may require authentication ("Sign in to confirm you're not a bot"). In this case:
  1. Make sure Chrome is running and you're logged into YouTube
  2. The script will automatically use Chrome cookies
  3. Or manually export cookies and use with yt-dlp directly (see [yt-dlp wiki](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies))

### scripts/download_bilibili.py

Downloads Bilibili videos using yt-dlp.

**Features:**
- Attempts to use browser cookies for authenticated content
- Downloads best quality available
- Merges streams into MP4 format
- Downloads Chinese and English subtitle files if available
- Downloads auto-generated subtitles when available
- Embeds subtitles into the MP4 when supported
- Saves with video title as filename

**Requirements:**
```bash
brew install yt-dlp
```

### scripts/download_douyin.py

Downloads Douyin (抖音) videos using yt-dlp.

**Features:**
- Auto-detects Clash proxy ports (7890, 7891, 7897, 1080, 10808) for users outside China
- Attempts to use browser cookies for authenticated content
- Bypasses anti-crawler measures with proper referer and user-agent
- Downloads best quality available
- Downloads subtitles if the source exposes them through yt-dlp
- Merges streams into MP4 format
- Saves with uploader name and video ID as filename

**Requirements:**
```bash
brew install yt-dlp
```

**Notes:**
- Douyin may require a proxy for users outside China
- Make sure yt-dlp is up to date: `brew upgrade yt-dlp`
- For better compatibility, keep Chrome running and logged in to Douyin (optional)

### scripts/download_x.py

Downloads X (Twitter) videos using yt-dlp.

**Features:**
- Auto-detects Clash proxy ports (7890, 7891, 7897, 1080, 10808)
- Attempts to use browser cookies for authenticated content
- Downloads best quality available
- Downloads subtitles if the source exposes them through yt-dlp
- Merges streams into MP4 format
- Saves with username and tweet ID as filename

**Requirements:**
```bash
brew install yt-dlp
```

**Note:** X/Twitter videos usually require authentication. The script tries to use Chrome cookies by default. Make sure Chrome is running and you're logged in to X/Twitter.

### scripts/download_xiaohongshu.py

Downloads Xiaohongshu (小红书) videos using yt-dlp.

**Features:**
- Auto-detects Clash proxy ports (7890, 7891, 7897, 1080, 10808)
- Supports both regular URLs and short links (xhslink.com)
- Downloads best quality available
- Downloads subtitles if the source exposes them through yt-dlp
- Merges streams into MP4 format
- Saves with video ID as filename

**Requirements:**
```bash
brew install yt-dlp
```

**Note:** Xiaohongshu videos may require a proxy. The script auto-detects common Clash proxy ports.

All videos are downloaded to: `~/Downloads/tmp/video`

Platform subfolders are created automatically:
- YouTube videos → `~/Downloads/tmp/video/youtube`
- Bilibili videos → `~/Downloads/tmp/video/bilibili`
- Douyin videos → `~/Downloads/tmp/video/douyin`
- X/Twitter videos → `~/Downloads/tmp/video/x`
- Xiaohongshu videos → `~/Downloads/tmp/video/xiaohongshu`

## Error Handling

### yt-dlp not found
```bash
brew install yt-dlp
```

### Connection errors (X or other blocked sites)

**If the webpage cannot be accessed:**

1. Ensure your proxy software (Clash, Clash Verge, etc.) is running
2. The script will auto-detect common Clash ports: 7890, 7891, 7897, 1080, 10808
3. Verify proxy port is accessible: `curl -x http://127.0.0.1:7897 https://twitter.com`
4. Manually specify proxy if auto-detection fails

### Bilibili authentication issues
The script attempts to use Chrome cookies for authenticated content. If that fails, you may need to provide cookies manually.

### Douyin download issues

**Common problems and solutions:**

1. **Video unavailable or connection timeout**
   - Make sure yt-dlp is up to date: `brew upgrade yt-dlp`
   - For users outside China, use a proxy:
     ```bash
     python3 scripts/download_douyin.py '<url>' ~/Downloads/tmp/video/douyin "http://127.0.0.1:7897"
     ```

2. **Authentication or anti-crawler errors**
   - Keep Chrome running and log in to Douyin
   - The script automatically sets proper referer and user-agent headers

3. **Manual download (without script)**
   ```bash
   yt-dlp --referer "https://www.douyin.com/" '<douyin_url>'
   ```

### X/Twitter authentication issues
- Make sure Chrome is running and you're logged in to X/Twitter
- Try with Firefox cookies if Chrome doesn't work:
  ```bash
  yt-dlp --cookies-from-browser firefox '<x_url>'
  ```
- For public content only, try without cookies:
  ```bash
  python3 scripts/download_x.py '<x_url>' ~/Downloads/tmp/video/x no_cookies
  ```
