#!/usr/bin/env python3
"""CLI adapter for RightAPI's asynchronous image-generation protocol."""

from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1:1"
DEFAULT_OUTPUT = "output/imagegen/output.png"
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_POLL_TIMEOUT = 300.0
DEFAULT_REQUEST_TIMEOUT = 60.0
MAX_IMAGE_BYTES = 50 * 1024 * 1024
RIGHTAPI_USER_AGENT = "curl/8.7.1"
ACTIVE_STATUSES = {"queued", "in_progress", "processing"}
SUCCESS_STATUSES = {"completed", "complete", "succeeded", "success", "done"}
FAILED_STATUSES = {"failed", "failure", "error", "cancelled", "canceled"}


class RightAPIError(RuntimeError):
    """An actionable error returned by the adapter or RightAPI."""

    def __init__(self, message: str, *, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _die(message: str, code: int = 2) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _redact_text(value: str) -> str:
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer <redacted>", value)
    value = re.sub(r"(?i)sk-[A-Za-z0-9_-]+", "<redacted-key>", value)
    value = re.sub(r"https?://[^\s\"']+", "<redacted-url>", value)
    return value


def _error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("message", "detail", "type", "code"):
                if error.get(key):
                    return _redact_text(str(error[key]))
        for key in ("message", "detail", "error", "code"):
            value = payload.get(key)
            if isinstance(value, (str, int, float)) and value:
                return _redact_text(str(value))
    if payload:
        return _redact_text(str(payload)[:500])
    return "empty response"


def _parse_json(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RightAPIError("RightAPI returned invalid JSON") from exc


def _endpoint_urls(base_url: str) -> tuple[str, str]:
    """Return (submit_url, task_url_prefix) for a /draw base URL."""

    parsed = urlsplit(base_url.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RightAPIError(
            "OPENAI_SUB_BASE_URL must be an absolute http(s) URL, for example "
            "https://www.rightapi.ai/draw"
        )

    base = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    submit_url = f"{base}/v1/images/generations"

    site_path = parsed.path.rstrip("/")
    if site_path.endswith("/draw"):
        site_path = site_path[: -len("/draw")]
    task_prefix = urlunsplit((parsed.scheme, parsed.netloc, f"{site_path}/v1/tasks", "", ""))
    return submit_url, task_prefix.rstrip("/")


class RightAPIClient:
    """Small stdlib HTTP client with injectable transport for unit tests."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        opener: Callable[..., Any] = urlopen,
    ):
        self.submit_url, self.task_url_prefix = _endpoint_urls(base_url)
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.opener = opener

    def _request(self, request: Request) -> Any:
        try:
            response = self.opener(request, timeout=self.request_timeout)
            try:
                return _parse_json(response.read())
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
        except HTTPError as exc:
            try:
                detail = _error_message(_parse_json(exc.read()))
            except RightAPIError:
                detail = f"HTTP {exc.code}"
            raise RightAPIError(
                f"RightAPI request failed ({exc.code}): {detail}", status_code=exc.code
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RightAPIError(f"RightAPI request failed: {_redact_text(str(exc))}") from exc

    def submit(self, payload: dict[str, Any]) -> str:
        request = Request(
            self.submit_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": RIGHTAPI_USER_AGENT,
            },
            method="POST",
        )
        response = self._request(request)
        task_id = response.get("task_id") if isinstance(response, dict) else None
        if not task_id:
            raise RightAPIError(
                "RightAPI submission did not return task_id: "
                f"{_error_message(response)}"
            )
        return str(task_id)

    def get_task(self, task_id: str) -> Any:
        url = f"{self.task_url_prefix}/{quote(task_id, safe='')}"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": RIGHTAPI_USER_AGENT,
            },
            method="GET",
        )
        return self._request(request)

    def download(self, image_url: str) -> bytes:
        request = Request(image_url, headers={"User-Agent": RIGHTAPI_USER_AGENT})
        try:
            response = self.opener(request, timeout=self.request_timeout)
            try:
                return response.read()
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
        except HTTPError as exc:
            raise RightAPIError(
                f"Image download failed ({exc.code})", status_code=exc.code
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RightAPIError(f"Image download failed: {_redact_text(str(exc))}") from exc


def _read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> str:
    if prompt and prompt_file:
        _die("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        path = Path(prompt_file)
        if not path.is_file():
            _die(f"Prompt file not found: {path}")
        value = path.read_text(encoding="utf-8").strip()
    else:
        value = (prompt or "").strip()
    if not value:
        _die("Missing prompt. Use --prompt or --prompt-file.")
    return value


def _check_image_paths(raw_paths: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_file():
            _die(f"Image file not found: {path}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            _die(f"Image exceeds the 50MB limit: {path}")
        paths.append(path)
    return paths


def _image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _augment_prompt(prompt: str, args: argparse.Namespace) -> str:
    if not args.augment:
        return prompt
    fields = (
        ("Use case", args.use_case),
        ("Scene/background", args.scene),
        ("Subject", args.subject),
        ("Style/medium", args.style),
        ("Composition/framing", args.composition),
        ("Lighting/mood", args.lighting),
        ("Color palette", args.palette),
        ("Materials/textures", args.materials),
        ("Text (verbatim)", f'"{args.text}"' if args.text else None),
        ("Constraints", args.constraints),
        ("Avoid", args.negative),
    )
    sections = [f"Primary request: {prompt}"]
    sections.extend(f"{label}: {value}" for label, value in fields if value)
    return "\n".join(sections)


def _validate_size(size: Optional[str]) -> None:
    if not size or size == "auto":
        return
    if size in {"1:1", "16:9", "9:16", "4:3"}:
        return
    if re.fullmatch(r"[1-9][0-9]*x[1-9][0-9]*", size):
        return
    _die("size must be 1:1, 16:9, 9:16, 4:3, auto, or WIDTHxHEIGHT.")


def _resolve_model(model: Optional[str], *, dry_run: bool) -> str:
    value = model or os.environ.get("OPENAI_SUB_IMAGE_MODEL")
    if value:
        return value
    if dry_run:
        return DEFAULT_MODEL
    _die("OPENAI_SUB_IMAGE_MODEL is missing; source ~/.zshrc first.", code=64)
    return DEFAULT_MODEL


def _build_payload(
    *,
    prompt: str,
    model: str,
    n: int,
    size: Optional[str],
    image_size: Optional[str],
    image_data: Sequence[str],
) -> dict[str, Any]:
    if n < 1 or n > 10:
        _die("n must be between 1 and 10.")
    _validate_size(size)
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "async": True,
    }
    if size and size != "auto":
        payload["size"] = size
    if image_size:
        payload["imageSize"] = image_size
    if image_data:
        payload["image"] = list(image_data)
    return payload


def _status(response: Any) -> str:
    if not isinstance(response, dict):
        return ""
    value = response.get("status")
    if isinstance(value, dict):
        value = value.get("status") or value.get("state")
    return str(value or "").strip().lower()


def _iter_image_values(value: Any) -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key in ("url", "image_url"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                yield ("url", candidate)
                return
        for key in ("b64_json", "b64Json", "base64"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                yield ("b64", candidate)
                return
        for key in ("data", "images", "output", "result", "candidates"):
            if key in value:
                yield from _iter_image_values(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from _iter_image_values(item)
    elif isinstance(value, str) and value:
        if value.startswith("data:"):
            yield ("b64", value)
        elif value.startswith(("http://", "https://")):
            yield ("url", value)


def _extract_images(response: Any) -> list[tuple[str, str]]:
    if not isinstance(response, dict):
        return []
    values: list[tuple[str, str]] = []
    for key in ("data", "images", "output", "result", "candidates"):
        if key in response:
            values.extend(_iter_image_values(response[key]))
    return values


def _failure_detail(response: Any) -> str:
    if isinstance(response, dict):
        error = response.get("error")
        if isinstance(error, dict) and error.get("message"):
            return _redact_text(str(error["message"]))
        if error:
            return _redact_text(str(error))
    return "RightAPI marked the task as failed"


def _poll_task(
    client: RightAPIClient,
    task_id: str,
    *,
    expected_count: int,
    poll_interval: float,
    poll_timeout: float,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> list[tuple[str, str]]:
    if poll_timeout <= 0:
        raise RightAPIError("poll timeout must be greater than zero")
    deadline = monotonic_fn() + poll_timeout
    while True:
        try:
            response = client.get_task(task_id)
        except RightAPIError as exc:
            retryable = exc.status_code is None or exc.status_code in {408, 429} or (
                exc.status_code is not None and exc.status_code >= 500
            )
            if not retryable or monotonic_fn() >= deadline:
                raise
            wait_for = min(max(poll_interval, 0.5), max(0.0, deadline - monotonic_fn()))
            sleep_fn(wait_for)
            continue

        state = _status(response)
        images = _extract_images(response)
        if state in FAILED_STATUSES:
            raise RightAPIError(f"RightAPI task failed: {_failure_detail(response)}")
        if state in SUCCESS_STATUSES:
            if not images:
                raise RightAPIError("RightAPI task completed without an image result")
            return images
        if not state and images:
            # Some compatible gateways omit status in the final response.
            return images
        if state not in ACTIVE_STATUSES:
            detail = _error_message(response)
            raise RightAPIError(
                f"RightAPI task response has no supported status or image result: {detail}"
            )

        remaining = deadline - monotonic_fn()
        if remaining <= 0:
            raise RightAPIError(f"RightAPI task timed out after {poll_timeout:.0f}s")
        sleep_fn(min(max(poll_interval, 0.0), remaining))


def _decode_base64(value: str) -> bytes:
    if value.startswith("data:"):
        try:
            value = value.split(",", 1)[1]
        except IndexError as exc:
            raise RightAPIError("RightAPI returned an invalid data URL") from exc
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RightAPIError("RightAPI returned invalid base64 image data") from exc


def _output_paths(
    out: Optional[str], out_dir: Optional[str], output_format: str, n: int
) -> list[Path]:
    extension = ".jpeg" if output_format == "jpeg" else f".{output_format}"
    if out_dir:
        directory = Path(out_dir)
        if out:
            path = Path(out)
            if path.suffix == "":
                path = path.with_suffix(extension)
            path = directory / path.name
            if n == 1:
                return [path]
            return [
                path.with_name(f"{path.stem}-{index}{path.suffix}")
                for index in range(1, n + 1)
            ]
        return [directory / f"image_{index}{extension}" for index in range(1, n + 1)]

    path = Path(out or DEFAULT_OUTPUT)
    if path.suffix == "":
        path = path.with_suffix(extension)
    if n == 1:
        return [path]
    return [path.with_name(f"{path.stem}-{index}{path.suffix}") for index in range(1, n + 1)]


def _write_images(
    client: RightAPIClient,
    images: Sequence[tuple[str, str]],
    outputs: Sequence[Path],
    *,
    force: bool,
) -> None:
    if len(images) < len(outputs):
        raise RightAPIError(
            f"RightAPI returned {len(images)} image(s), expected {len(outputs)}"
        )
    for (kind, value), path in zip(images, outputs):
        if path.exists() and not force:
            _die(f"Output already exists: {path} (use --force to overwrite)")
        raw = _decode_base64(value) if kind == "b64" else client.download(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        print(f"Wrote {path}")


@dataclass
class Job:
    prompt: str
    model: str
    n: int
    size: Optional[str]
    image_size: Optional[str]
    images: list[Path]
    output_paths: list[Path]


def _job_from_args(args: argparse.Namespace, *, prompt: str, images: list[Path], out: Optional[str] = None) -> Job:
    model = _resolve_model(args.model, dry_run=args.dry_run)
    n = args.n
    output_format = args.output_format or "png"
    requested_out = out if out is not None else (None if args.out_dir else args.out)
    output_paths = _output_paths(
        requested_out,
        args.out_dir,
        output_format,
        n,
    )
    return Job(
        prompt=_augment_prompt(prompt, args),
        model=model,
        n=n,
        size=args.size,
        image_size=args.image_size,
        images=images,
        output_paths=output_paths,
    )


def _preview_payload(job: Job) -> dict[str, Any]:
    payload = _build_payload(
        prompt=job.prompt,
        model=job.model,
        n=job.n,
        size=job.size,
        image_size=job.image_size,
        image_data=[str(path) for path in job.images],
    )
    return {
        "endpoint": "/v1/images/generations",
        "outputs": [str(path) for path in job.output_paths],
        **payload,
    }


def _live_payload(job: Job) -> dict[str, Any]:
    return _build_payload(
        prompt=job.prompt,
        model=job.model,
        n=job.n,
        size=job.size,
        image_size=job.image_size,
        image_data=[_image_data_url(path) for path in job.images],
    )


def _validate_optional_flags(args: argparse.Namespace) -> None:
    if args.background:
        _die(
            "RightAPI's documented Images endpoint does not expose --background; "
            "native transparency is not available through this adapter."
        )
    if getattr(args, "mask", None):
        _die("RightAPI's documented Images endpoint does not expose --mask.")
    if args.output_compression is not None:
        _die("RightAPI's documented Images endpoint does not expose --output-compression.")
    ignored = []
    if args.quality:
        ignored.append("--quality")
    if args.moderation:
        ignored.append("--moderation")
    if getattr(args, "input_fidelity", None):
        ignored.append("--input-fidelity")
    if ignored:
        print(
            "Warning: RightAPI does not document "
            + ", ".join(ignored)
            + "; the option was ignored.",
            file=sys.stderr,
        )


def _make_client(args: argparse.Namespace) -> RightAPIClient:
    base_url = os.environ.get("OPENAI_SUB_BASE_URL", "")
    api_key = os.environ.get("OPENAI_SUB_KEY", "")
    if not base_url:
        _die("OPENAI_SUB_BASE_URL is missing; source ~/.zshrc first.", code=64)
    if not api_key:
        _die("OPENAI_SUB_KEY is missing; source ~/.zshrc first.", code=64)
    return RightAPIClient(
        base_url,
        api_key,
        request_timeout=args.request_timeout,
    )


def _run_job(args: argparse.Namespace, job: Job, client: Optional[RightAPIClient]) -> None:
    _validate_optional_flags(args)
    if args.dry_run:
        print(json.dumps(_preview_payload(job), ensure_ascii=False, indent=2, sort_keys=True))
        return
    if client is None:
        raise RightAPIError("RightAPI client is not initialized")
    payload = _live_payload(job)
    task_id = client.submit(payload)
    print(f"RightAPI task submitted: {task_id}", file=sys.stderr)
    images = _poll_task(
        client,
        task_id,
        expected_count=job.n,
        poll_interval=args.poll_interval,
        poll_timeout=args.poll_timeout,
    )
    _write_images(client, images, job.output_paths, force=args.force)


def _read_jobs(path: str) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        _die(f"Input file not found: {source}")
    jobs: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            _die(f"Invalid JSON on line {line_number}: {exc}")
        if isinstance(value, str):
            value = {"prompt": value}
        if not isinstance(value, dict) or not str(value.get("prompt", "")).strip():
            _die(f"Job on line {line_number} must contain a non-empty prompt")
        jobs.append(value)
    if not jobs:
        _die("No jobs found in input file")
    return jobs


def _batch_job(args: argparse.Namespace, item: dict[str, Any], index: int) -> Job:
    raw_images = item.get("image", item.get("images", []))
    if isinstance(raw_images, str):
        raw_images = [raw_images]
    images = _check_image_paths(raw_images or [])
    prompt = str(item["prompt"]).strip()
    model = item.get("model") or args.model
    n = int(item.get("n", args.n))
    size = item.get("size", args.size)
    image_size = item.get("imageSize", item.get("image_size", args.image_size))
    output_format = item.get("output_format", args.output_format or "png")
    explicit_out = item.get("out")
    output_paths = _output_paths(
        str(explicit_out or f"image_{index}"),
        args.out_dir,
        output_format,
        n,
    )
    return Job(
        prompt=_augment_prompt(prompt, args),
        model=_resolve_model(model, dry_run=args.dry_run),
        n=n,
        size=size,
        image_size=image_size,
        images=images,
        output_paths=output_paths,
    )


def _run_batch(args: argparse.Namespace) -> int:
    if not args.out_dir:
        _die("generate-batch requires --out-dir")
    items = _read_jobs(args.input)
    client = None if args.dry_run else _make_client(args)
    failures = 0
    for index, item in enumerate(items, 1):
        try:
            job = _batch_job(args, item, index)
            print(f"[job {index}/{len(items)}]", file=sys.stderr)
            _run_job(args, job, client)
        except (RightAPIError, SystemExit) as exc:
            failures += 1
            if isinstance(exc, SystemExit):
                raise
            print(f"[job {index}/{len(items)}] failed: {exc}", file=sys.stderr)
            if args.fail_fast:
                return 1
    return 1 if failures else 0


def _add_prompt_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--use-case")
    parser.add_argument("--scene")
    parser.add_argument("--subject")
    parser.add_argument("--style")
    parser.add_argument("--composition")
    parser.add_argument("--lighting")
    parser.add_argument("--palette")
    parser.add_argument("--materials")
    parser.add_argument("--text")
    parser.add_argument("--constraints")
    parser.add_argument("--negative")
    parser.add_argument("--augment", dest="augment", action="store_true", default=True)
    parser.add_argument("--no-augment", dest="augment", action="store_false")


def _add_common_args(parser: argparse.ArgumentParser, *, prompt_required: bool = True) -> None:
    parser.add_argument("--model")
    prompt_group = parser.add_mutually_exclusive_group(required=prompt_required)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--image-size", choices=("1K", "2K", "4K"))
    parser.add_argument("--quality")
    parser.add_argument("--background")
    parser.add_argument("--output-format", choices=("png", "jpeg", "webp"), default="png")
    parser.add_argument("--output-compression", type=int)
    parser.add_argument("--moderation")
    parser.add_argument("--out", default=DEFAULT_OUTPUT)
    parser.add_argument("--out-dir")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--poll-timeout", type=float, default=DEFAULT_POLL_TIMEOUT)
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    _add_prompt_fields(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RightAPI async image generation and editing CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate an image")
    _add_common_args(generate)
    generate.add_argument("--image", action="append", default=[], help="Reference image")

    edit = subparsers.add_parser("edit", help="Edit an image with a prompt")
    _add_common_args(edit)
    edit.add_argument("--image", action="append", required=True, help="Input image")
    edit.add_argument("--mask")
    edit.add_argument("--input-fidelity")

    batch = subparsers.add_parser("generate-batch", help="Generate jobs from JSONL")
    _add_common_args(batch, prompt_required=False)
    batch.add_argument("--input", required=True)
    batch.add_argument("--concurrency", type=int, default=1)
    batch.add_argument("--max-attempts", type=int, default=1)
    batch.add_argument("--fail-fast", action="store_true")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.n < 1 or args.n > 10:
        _die("n must be between 1 and 10.")
    if args.poll_interval < 0 or args.poll_timeout <= 0 or args.request_timeout <= 0:
        _die("poll-interval must be >= 0; timeouts must be > 0.")
    if args.command == "generate-batch":
        return _run_batch(args)

    images = _check_image_paths(args.image)
    if args.command == "edit" and not images:
        _die("edit requires at least one --image")
    prompt = _read_prompt(args.prompt, args.prompt_file)
    job = _job_from_args(args, prompt=prompt, images=images)
    client = None if args.dry_run else _make_client(args)
    try:
        _run_job(args, job, client)
    except RightAPIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
