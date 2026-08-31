#!/usr/bin/env python3
"""
glm-eyes — 当主模型 (如 GLM-5.2) 无法读图时，用任意一个多模态模型兜底读图。

设计为**模型无关**：不写死 Kimi。它只是"当前在 CC-Switch 里被识别为
具备多模态能力的 Claude 路由"之一。以后加新的视觉模型，只要在 CC-Switch 里
加一个 Claude provider（Anthropic 兼容端点），本脚本就能自动用上。

选择哪个多模态 provider 的优先级：
  1. 环境变量 GLM_EYES_PROVIDER 指定的 provider（按 CC-Switch providers.name）
  2. 命令行 --provider <name> 指定
  3. 自动：在 CC-Switch Claude providers 里，挑选一个 model 名命中
     "已知多模态模型清单" 的 provider；若当前激活路由本身是多模态的则用它。
  4. 找不到时回退环境变量 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / model。

凭据从 CC-Switch 的数据库 (~/.cc-switch/cc-switch.db) 动态读取，不硬编码密钥。

用法:
    uv run ~/.claude/skills/glm-eyes/scripts/glm_eyes.py <image_path> [prompt] [--provider <name>]

示例:
    # 自动选一个多模态 provider
    glm_eyes.py ./shot.png "描述这张截图"
    # 指定 provider
    glm_eyes.py ./shot.png "描述布局" --provider Kimi-flik

退出码:
    0  成功，图像描述输出到 stdout
    1  参数 / 文件错误
    2  找不到任何多模态 provider / 接口调用失败
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

CC_SWITCH_DB = Path.home() / ".cc-switch" / "cc-switch.db"
DEFAULT_TIMEOUT = 120

DEFAULT_PROMPT = (
    "请仔细观察这张图片，详细描述其中的全部内容。"
    "如果是 UI / 截图，请按布局层级描述：整体布局、区域的标题/文字、"
    "控件类型（按钮/输入框/列表/弹窗等）、颜色、图标，以及任何可见的文字。"
    "如果是实物 / 场景 / 图表，请如实描述其内容与关键数据。"
    "最后用一句话给出图片的整体主旨。"
)

# 已知具备多模态/视觉能力的模型名碎片（小写匹配）。新增视觉模型时往这里加即可。
# 命中其中任一即视为"多模态 provider"。
VISION_MODEL_HINTS = (
    "kimi",                      # Kimi kimi-for-coding (多模态)
    "claude",                    # Claude 官方 / 兼容代理 (sonnet/opus/haiku 都支持视觉)
    "gpt-4o", "gpt-5", "chatgpt",  # OpenAI 视觉系列（经 Anthropic 兼容代理亦同）
    "qwen-vl", "qwen2-vl", "qwen2.5-vl", "qwen3-vl",  # 通义千问视觉
    "glm-4v", "glm-v",          # 智谱 GLM 视觉版（注意：glm-5.2 裸文字模型不在此列）
    "gemini",                    # Gemini 全系视觉
    "llava", "vision", "vl",
)


@dataclass
class Provider:
    name: str
    base_url: str
    token: str
    model: str

    @property
    def is_vision(self) -> bool:
        m = (self.model or "").lower()
        return any(h in m for h in VISION_MODEL_HINTS)


def die(code: int, msg: str) -> None:
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def _parse_provider_config(cfg_json: str) -> Provider | None:
    try:
        cfg = json.loads(cfg_json)
    except json.JSONDecodeError:
        return None
    env = cfg.get("env", {}) or {}
    token = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")
    base_url = env.get("ANTHROPIC_BASE_URL")
    if not token or not base_url:
        return None
    # opus 优先（CC-Switch 里通常所有档位都映射到同一真实模型），其次 ANTHROPIC_MODEL
    model = (
        env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
        or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or env.get("ANTHROPIC_MODEL")
        or ""
    )
    base_url = base_url.rstrip("/")
    return Provider(name="", base_url=base_url, token=token, model=model)


def _open_db_readonly() -> sqlite3.Connection:
    """以只读方式打开 CC-Switch db，对锁做短重试。"""
    last = None
    for _ in range(5):
        try:
            return sqlite3.connect(f"file:{CC_SWITCH_DB}?mode=ro", uri=True, timeout=2.0)
        except Exception as e:  # noqa: BLE001
            last = e
            import time
            time.sleep(0.2)
    raise last  # type: ignore[misc]


def load_all_providers() -> list[Provider]:
    """从 CC-Switch db 读所有 Claude providers。"""
    out: list[Provider] = []
    if not CC_SWITCH_DB.exists():
        return out
    try:
        con = _open_db_readonly()
        rows = con.execute(
            "SELECT name, settings_config, is_current FROM providers "
            "WHERE app_type='claude'"
        ).fetchall()
        con.close()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"WARN: 读取 CC-Switch db 失败 ({e})。\n")
        return out
    for name, cfg_json, _is_current in rows:
        p = _parse_provider_config(cfg_json)
        if p:
            p.name = name
            out.append(p)
    return out


def pick_providers_candidates(explicit: str | None) -> list[Provider]:
    """返回按优先级排序的候选 provider 列表（用于失败 fallback）。

    - 显式指定：只返回该一个（若非多模态已在 pick_provider 报错；此处不再二重判断）。
    - 自动：[当前激活且多模态] ++ [其余多模态] ++ [环境变量兜底]。
    """
    providers = load_all_providers()
    by_name = {p.name: p for p in providers}

    wanted = explicit or os.environ.get("GLM_EYES_PROVIDER")
    if wanted:
        if wanted not in by_name:
            die(2, f"CC-Switch 中找不到名为 '{wanted}' 的 Claude provider。")
        p = by_name[wanted]
        if not p.is_vision:
            die(2, f"provider '{wanted}' 的模型 '{p.model}' 未命中已知多模态清单，"
                  f"它大概率读不了图。给 glm-eyes 换一个多模态 provider，"
                  f"或编辑 VISION_MODEL_HINTS 加入该模型。")
        return [p]

    candidates: list[Provider] = []
    seen_names: set[str] = set()

    current = load_current_provider()
    if current and current.is_vision:
        candidates.append(current)
        seen_names.add(current.name)

    for p in providers:
        if p.is_vision and p.name not in seen_names:
            candidates.append(p)
            seen_names.add(p.name)

    # 环境变量兜底
    env_tok = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    env_url = os.environ.get("ANTHROPIC_BASE_URL")
    if env_tok and env_url:
        env_model = os.environ.get("GLM_EYES_MODEL") or os.environ.get("ANTHROPIC_MODEL") or ""
        candidates.append(Provider(name="<env>", base_url=env_url.rstrip("/"),
                                   token=env_tok, model=env_model))

    return candidates


def pick_provider(explicit: str | None) -> Provider:
    cands = pick_providers_candidates(explicit)
    if cands:
        return cands[0]
    die(2, "找不到任何多模态 provider：CC-Switch 的 Claude providers 都未命中多模态清单，"
          "且未设置环境变量 ANTHROPIC_AUTH_TOKEN/ANTHROPIC_BASE_URL。"
          "可用 --provider <CC-Switch里某个provider名> 指定，或设置 GLM_EYES_PROVIDER。")
    raise RuntimeError("unreachable")


def load_current_provider() -> Provider | None:
    try:
        con = _open_db_readonly()
        row = con.execute(
            "SELECT name, settings_config FROM providers "
            "WHERE app_type='claude' AND is_current=1 LIMIT 1"
        ).fetchone()
        con.close()
    except Exception:  # noqa: BLE001
        return None
    if not row:
        return None
    name, cfg_json = row
    p = _parse_provider_config(cfg_json)
    if p:
        p.name = f"{name} (current)"
    return p


def encode_image(path: Path) -> tuple[str, str]:
    mime, _ = mimetypes.guess_type(str(path))
    if not mime or not mime.startswith("image/"):
        ext = path.suffix.lower()
        guess = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
        mime = guess.get(ext, "image/png")
    data = path.read_bytes()
    if len(data) > 20 * 1024 * 1024:
        die(1, f"图片过大 ({len(data)} bytes)，单图上限约 20MB。")
    return mime, base64.b64encode(data).decode("ascii")


def call_vision(p: Provider, media_type: str, b64: str,
                prompt: str, max_tokens: int = 4096) -> str:
    if not p.model:
        raise VisionError(p, "未配置 model")
    url = p.base_url.rstrip("/") + "/v1/messages"
    payload = {
        "model": p.model,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": p.token,
        "anthropic-version": "2023-06-01",
        "Authorization": f"Bearer {p.token}",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        snippet = e.read().decode("utf-8", "ignore")[:400]
        raise VisionError(p, f"HTTP {e.code}: {snippet}") from e
    except urllib.error.URLError as e:
        raise VisionError(p, f"网络错误: {e.reason}") from e
    except Exception as e:  # noqa: BLE001
        raise VisionError(p, f"调用异常: {e}") from e
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise VisionError(p, f"返回非 JSON: {body[:400]}")
    blocks = data.get("content", [])
    parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    text = "\n".join(x for x in parts if x).strip()
    if not text:
        raise VisionError(p, f"未返回文本。原始响应: {body[:400]}")
    return text


class VisionError(Exception):
    def __init__(self, provider: Provider, reason: str):
        super().__init__(reason)
        self.provider = provider
        self.reason = reason


def main() -> int:
    ap = argparse.ArgumentParser(description="用多模态模型兜底读图 (模型无关)。")
    ap.add_argument("image", help="图片本地路径")
    ap.add_argument("prompt", nargs="?", default=None, help="读图指令，缺省为详细描述 UI/图表")
    ap.add_argument("--provider", default=None, help="CC-Switch 里的 Claude provider 名")
    ap.add_argument("--max-tokens", type=int, default=4096)
    args = ap.parse_args()

    img = Path(args.image).expanduser()
    prompt = args.prompt.strip() if args.prompt and args.prompt.strip() else DEFAULT_PROMPT
    if not img.exists():
        die(1, f"图片不存在: {img}")
    if not img.is_file():
        die(1, f"不是文件: {img}")

    candidates = pick_providers_candidates(args.provider)
    if not candidates:
        die(2, "找不到任何多模态 provider：CC-Switch 的 Claude providers 都未命中多模态清单，"
              "且未设置环境变量 ANTHROPIC_AUTH_TOKEN/ANTHROPIC_BASE_URL。"
              "可用 --provider <CC-Switch里某个provider名> 指定，或设置 GLM_EYES_PROVIDER。")

    media, b64 = encode_image(img)

    errors: list[str] = []
    last_text: str | None = None
    for p in candidates:
        sys.stderr.write(f"INFO: 尝试 provider={p.name} model={p.model} file={img.name}\n")
        if not p.model:
            errors.append(f"  - {p.name}: 未配置 model")
            continue
        try:
            text = call_vision(p, media, b64, prompt, max_tokens=args.max_tokens)
            if errors:
                sys.stderr.write(
                    f"WARN: 之前的尝试失败，最终由 {p.name} 成功:\n"
                    + "\n".join(errors) + "\n"
                )
            last_text = text
            break
        except VisionError as e:
            errors.append(f"  - {p.name} ({p.model}): {e.reason}")
            sys.stderr.write(f"WARN: {p.name} 失败 -> {e.reason}\n")
            continue

    if last_text is None:
        die(2, "所有多模态 provider 都失败：\n" + "\n".join(errors))
    sys.stdout.write(last_text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())