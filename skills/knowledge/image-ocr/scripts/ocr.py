#!/usr/bin/env python3
"""Local OCR wrapper for RapidOCR and PaddleOCR PP-StructureV3."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from statistics import fmean
from typing import Any

SCHEMA_VERSION = 1
IMAGE_SUFFIXES = {
    ".bmp",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | {".pdf"}
VALID_FORMATS = {"txt", "md", "json"}


class OCRError(RuntimeError):
    """An actionable OCR failure."""


class DependencyError(OCRError):
    """A required local OCR dependency is unavailable."""


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    return str(value)


def parse_formats(raw: str) -> list[str]:
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("--formats cannot be empty")
    if "all" in values:
        return ["txt", "md", "json"]
    unknown = sorted(set(values) - VALID_FORMATS)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown format(s): {', '.join(unknown)}; choose txt,md,json or all"
        )
    return list(dict.fromkeys(values))


def validate_input(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise OCRError(f"input does not exist: {path}")
    if not path.is_file():
        raise OCRError(f"input is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise OCRError(
            f"unsupported input type {path.suffix!r}; supported: {supported}"
        )
    return path


def choose_engine(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    return "paddle" if path.suffix.lower() == ".pdf" else "rapid"


def normalize_bbox(value: Any) -> list[list[float | int]] | None:
    if value is None:
        return None
    data = json_safe(value)
    if not isinstance(data, list):
        return None
    normalized: list[list[float | int]] = []
    for point in data:
        if not isinstance(point, list) or len(point) < 2:
            return None
        coords: list[float | int] = []
        for coordinate in point[:2]:
            number = float(coordinate)
            coords.append(int(number) if number.is_integer() else round(number, 3))
        normalized.append(coords)
    return normalized


def rapid_lines_from_result(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "txts"):
        raw_texts = getattr(result, "txts", None)
        raw_scores = getattr(result, "scores", None)
        raw_boxes = getattr(result, "boxes", None)
        texts = [] if raw_texts is None else list(raw_texts)
        scores = [] if raw_scores is None else list(raw_scores)
        boxes = [] if raw_boxes is None else list(raw_boxes)
        lines = []
        for index, text in enumerate(texts):
            score = float(scores[index]) if index < len(scores) else None
            bbox = normalize_bbox(boxes[index]) if index < len(boxes) else None
            lines.append({"text": str(text).strip(), "confidence": score, "bbox": bbox})
        return lines

    # RapidOCR releases before the RapidOCROutput dataclass returned
    # (items, elapsed), where each item was [box, text, score].
    items = result[0] if isinstance(result, tuple) and len(result) == 2 else result
    if not isinstance(items, (list, tuple)):
        raise OCRError("RapidOCR returned an unsupported result shape")

    lines = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        lines.append(
            {
                "text": str(item[1]).strip(),
                "confidence": float(item[2]),
                "bbox": normalize_bbox(item[0]),
            }
        )
    return lines


def build_rapid_engine() -> Any:
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:
        raise DependencyError(
            "rapidocr is not installed; run: uv pip install --python "
            "~/.cache/image-ocr/venv/bin/python rapidocr onnxruntime"
        ) from exc

    try:
        return RapidOCR()
    except Exception as exc:
        raise OCRError(f"RapidOCR initialization failed: {exc}") from exc


def run_rapid(
    path: Path, engine: Any, fallback_threshold: float, line_threshold: float
) -> dict[str, Any]:
    if path.suffix.lower() == ".pdf":
        raise OCRError(
            "RapidOCR mode accepts raster images only; use --engine paddle for PDF"
        )
    started = time.perf_counter()
    try:
        result = engine(str(path))
    except Exception as exc:
        raise OCRError(f"RapidOCR failed for {path.name}: {exc}") from exc

    lines = rapid_lines_from_result(result)
    lines = [line for line in lines if line["text"]]
    text = "\n".join(line["text"] for line in lines)
    scores = [line["confidence"] for line in lines if line["confidence"] is not None]
    average_confidence = fmean(scores) if scores else None
    minimum_confidence = min(scores) if scores else None
    low_confidence_lines = [
        index + 1
        for index, line in enumerate(lines)
        if line["confidence"] is not None and line["confidence"] < line_threshold
    ]

    reasons: list[str] = []
    if not text.strip():
        reasons.append("no_text_detected")
    if average_confidence is not None and average_confidence < fallback_threshold:
        reasons.append("average_confidence_below_threshold")
    if low_confidence_lines:
        reasons.append("low_confidence_lines")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "source": str(path),
        "engine": "rapidocr",
        "text": text,
        "markdown": text,
        "line_count": len(lines),
        "average_confidence": average_confidence,
        "minimum_confidence": minimum_confidence,
        "low_confidence_lines": low_confidence_lines,
        "needs_vision_fallback": bool(reasons),
        "fallback_reasons": reasons,
        "lines": lines,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def extract_markdown(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        preferred = value.get("markdown_texts")
        if preferred is not None:
            return extract_markdown(preferred)
        for key in ("markdown", "text", "content"):
            if key in value:
                extracted = extract_markdown(value[key])
                if extracted:
                    return extracted
        return ""
    if isinstance(value, (list, tuple)):
        parts = [extract_markdown(item) for item in value]
        return "\n\n".join(part for part in parts if part)
    return ""


def markdown_to_text(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`]", "", text)
    return text.strip()


def build_paddle_pipeline(args: argparse.Namespace) -> Any:
    cache_dir = Path.home() / ".cache" / "image-ocr" / "paddlex"
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))

    try:
        from paddleocr import PPStructureV3
    except (ImportError, ModuleNotFoundError) as exc:
        raise DependencyError(
            "paddleocr document parser is not installed; install "
            "'paddleocr[doc-parser]' and a supported inference engine"
        ) from exc

    options: dict[str, Any] = {
        "engine": args.paddle_engine,
        "use_doc_orientation_classify": not args.no_doc_orientation,
        "use_doc_unwarping": not args.no_unwarp,
        "use_textline_orientation": not args.no_textline_orientation,
        "use_formula_recognition": not args.disable_formula,
        "use_table_recognition": not args.disable_table,
        "use_seal_recognition": not args.disable_seal,
    }
    if args.language:
        options["lang"] = args.language
    if args.device:
        options["device"] = args.device

    try:
        return PPStructureV3(**options)
    except Exception as exc:
        raise OCRError(
            f"PaddleOCR PP-StructureV3 initialization failed: {exc}"
        ) from exc


def run_paddle(path: Path, pipeline: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        results = list(pipeline.predict(str(path)))
    except Exception as exc:
        raise OCRError(f"PaddleOCR failed for {path.name}: {exc}") from exc

    pages: list[dict[str, Any]] = []
    markdown_pages: list[str] = []
    for page_number, result in enumerate(results, start=1):
        page_markdown = extract_markdown(getattr(result, "markdown", None))
        if page_markdown:
            markdown_pages.append(page_markdown)
        pages.append(
            {
                "page": page_number,
                "markdown": page_markdown,
                "result": json_safe(getattr(result, "json", None)),
            }
        )

    merged_markdown = "\n\n---\n\n".join(markdown_pages).strip()
    warnings: list[str] = []
    if results and hasattr(pipeline, "concatenate_markdown_pages"):
        try:
            concatenated = pipeline.concatenate_markdown_pages(results)
            official_markdown = extract_markdown(concatenated)
            if official_markdown:
                merged_markdown = official_markdown
        except Exception as exc:  # noqa: BLE001 - optional cross-version API
            # Per-page Markdown is still valid when this release cannot merge
            # the specific input type.
            warnings.append(f"page_merge_failed: {exc}")

    text = markdown_to_text(merged_markdown)
    reasons = [] if text else ["no_text_detected"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "source": str(path),
        "engine": "paddleocr-ppstructurev3",
        "text": text,
        "markdown": merged_markdown,
        "page_count": len(pages),
        "average_confidence": None,
        "minimum_confidence": None,
        "needs_vision_fallback": bool(reasons),
        "fallback_reasons": reasons,
        "warnings": warnings,
        "pages": pages,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def artifact_stem(path: Path, seen: set[str]) -> str:
    stem = re.sub(r"[^0-9A-Za-z._-]+", "-", path.stem).strip("-.") or "ocr"
    if stem not in seen:
        seen.add(stem)
        return stem
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    base = f"{stem}-{digest}"
    unique = base
    counter = 2
    while unique in seen:
        unique = f"{base}-{counter}"
        counter += 1
    seen.add(unique)
    return unique


def write_artifacts(
    payload: dict[str, Any], output_dir: Path, formats: Iterable[str], stem: str
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    requested = set(formats)
    if "txt" in requested:
        path = (output_dir / f"{stem}.ocr.txt").resolve()
        path.write_text(payload.get("text", "").rstrip() + "\n", encoding="utf-8")
        artifacts["txt"] = str(path)
    if "md" in requested:
        path = (output_dir / f"{stem}.ocr.md").resolve()
        markdown = payload.get("markdown") or payload.get("text", "")
        path.write_text(str(markdown).rstrip() + "\n", encoding="utf-8")
        artifacts["md"] = str(path)
    if "json" in requested:
        path = (output_dir / f"{stem}.ocr.json").resolve()
        artifacts["json"] = str(path)
        payload["artifacts"] = artifacts
        path.write_text(
            json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    payload["artifacts"] = artifacts
    return artifacts


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract local image/PDF text with RapidOCR by default or "
            "PaddleOCR PP-StructureV3 for complex documents."
        )
    )
    parser.add_argument("inputs", nargs="+", help="local image or PDF paths")
    parser.add_argument(
        "--engine",
        choices=("auto", "rapid", "paddle"),
        default="auto",
        help="auto selects PaddleOCR for PDF and RapidOCR for images (default: auto)",
    )
    parser.add_argument(
        "--output-dir",
        default="ocr-output",
        help="artifact directory (default: ./ocr-output)",
    )
    parser.add_argument(
        "--formats",
        type=parse_formats,
        default=parse_formats("txt,json"),
        help="comma-separated txt,md,json or all (default: txt,json)",
    )
    parser.add_argument(
        "--fallback-threshold",
        type=float,
        default=0.72,
        help="RapidOCR average confidence below this requests vision fallback",
    )
    parser.add_argument(
        "--line-threshold",
        type=float,
        default=0.45,
        help="RapidOCR line confidence below this requests vision fallback",
    )
    parser.add_argument(
        "--print-text", action="store_true", help="print extracted text"
    )
    parser.add_argument(
        "--json-stdout", action="store_true", help="print all results as JSON"
    )

    paddle = parser.add_argument_group("PaddleOCR PP-StructureV3")
    paddle.add_argument(
        "--language", help="recognition language, e.g. en; default is Chinese/English"
    )
    paddle.add_argument("--device", help="PaddleOCR device string, e.g. cpu or gpu:0")
    paddle.add_argument(
        "--paddle-engine",
        default="paddle",
        help="PaddleOCR inference engine (default: paddle)",
    )
    paddle.add_argument("--disable-formula", action="store_true")
    paddle.add_argument("--disable-table", action="store_true")
    paddle.add_argument("--disable-seal", action="store_true")
    paddle.add_argument("--no-doc-orientation", action="store_true")
    paddle.add_argument("--no-unwarp", action="store_true")
    paddle.add_argument("--no-textline-orientation", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if not 0 <= args.fallback_threshold <= 1:
        parser.error("--fallback-threshold must be between 0 and 1")
    if not 0 <= args.line_threshold <= 1:
        parser.error("--line-threshold must be between 0 and 1")

    output_dir = Path(args.output_dir).expanduser().resolve()
    payloads: list[dict[str, Any]] = []
    seen_stems: set[str] = set()
    rapid_engine = None
    paddle_pipeline = None
    failures = 0

    for raw_path in args.inputs:
        try:
            path = validate_input(raw_path)
            engine = choose_engine(path, args.engine)
            if engine == "rapid":
                if rapid_engine is None:
                    rapid_engine = build_rapid_engine()
                payload = run_rapid(
                    path, rapid_engine, args.fallback_threshold, args.line_threshold
                )
            else:
                if paddle_pipeline is None:
                    paddle_pipeline = build_paddle_pipeline(args)
                payload = run_paddle(path, paddle_pipeline)
            stem = artifact_stem(path, seen_stems)
            write_artifacts(payload, output_dir, args.formats, stem)
            payloads.append(payload)
        except OCRError as exc:
            failures += 1
            payloads.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "source": str(Path(raw_path).expanduser()),
                    "error": str(exc),
                    "needs_vision_fallback": True,
                    "fallback_reasons": ["engine_error"],
                }
            )

    if args.json_stdout:
        print(json.dumps(json_safe(payloads), ensure_ascii=False, indent=2))
    else:
        for payload in payloads:
            if payload["status"] == "error":
                print(
                    f"ERROR\t{payload['source']}\t{payload['error']}", file=sys.stderr
                )
                continue
            confidence = payload.get("average_confidence")
            confidence_text = "n/a" if confidence is None else f"{confidence:.3f}"
            fallback = "yes" if payload["needs_vision_fallback"] else "no"
            print(
                f"OK\t{payload['source']}\tengine={payload['engine']}\t"
                f"confidence={confidence_text}\tvision_fallback={fallback}"
            )
            for format_name, artifact in payload.get("artifacts", {}).items():
                print(f"  {format_name}: {artifact}")

    if args.print_text and not args.json_stdout:
        successful = [item for item in payloads if item["status"] == "ok"]
        for payload in successful:
            if len(successful) > 1:
                print(f"\n===== {Path(payload['source']).name} =====")
            print(payload.get("text", ""))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
