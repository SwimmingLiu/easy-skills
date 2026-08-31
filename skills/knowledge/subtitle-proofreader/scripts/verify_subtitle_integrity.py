#!/usr/bin/env python3
"""Verify that proofreading kept subtitle structure and timing unchanged.

Supports SRT and WebVTT-style cues. The script intentionally compares the
structural signature only: cue count, optional cue identifiers, timing lines,
start/end timestamps, per-cue duration, and total duration.

When a proofread file only changed cue timings, ``--fix`` can safely restore
the original timing lines while preserving proofread text. This repairs common
time-unit mistakes such as millisecond/second scale drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TIMING_RE = re.compile(
    r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})(?P<settings>.*)$"
)


@dataclass(frozen=True)
class CueSignature:
    ordinal: int
    timing_index: int
    identifier: str | None
    timing_line: str
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(frozen=True)
class SubtitleDocument:
    path: Path
    lines: list[str]
    cues: list[CueSignature]


def parse_timestamp(value: str) -> int:
    normalized = value.replace(",", ".")
    parts = normalized.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Unsupported timestamp: {value}")

    second_value, millisecond_value = seconds.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(second_value) * 1_000
        + int(millisecond_value)
    )


def split_blocks(lines: list[str]) -> Iterable[list[tuple[int, str]]]:
    current: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines):
        if line.strip():
            current.append((line_number, line))
        elif current:
            yield current
            current = []
    if current:
        yield current


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def parse_document(path: Path) -> SubtitleDocument:
    lines = read_lines(path)
    cues: list[CueSignature] = []

    for block in split_blocks(lines):
        block_lines = [line for _, line in block]
        if block_lines[0].strip().upper().startswith("WEBVTT"):
            continue
        if block_lines[0].strip().upper().startswith(("NOTE", "STYLE", "REGION")):
            continue

        timing_index = None
        timing_match = None
        timing_line_number = None
        for index, (line_number, line) in enumerate(block):
            match = TIMING_RE.match(line.strip())
            if match:
                timing_index = index
                timing_line_number = line_number
                timing_match = match
                break

        if timing_index is None or timing_line_number is None or timing_match is None:
            continue

        identifier_lines = block_lines[:timing_index]
        identifier = "\n".join(identifier_lines) if identifier_lines else None
        start_text = timing_match.group("start")
        end_text = timing_match.group("end")
        cues.append(
            CueSignature(
                ordinal=len(cues) + 1,
                timing_index=timing_line_number,
                identifier=identifier,
                timing_line=block_lines[timing_index].strip(),
                start_ms=parse_timestamp(start_text),
                end_ms=parse_timestamp(end_text),
            )
        )

    return SubtitleDocument(path=path, lines=lines, cues=cues)


def summarize(cues: list[CueSignature]) -> dict[str, int | None]:
    if not cues:
        return {
            "cue_count": 0,
            "first_start_ms": None,
            "last_end_ms": None,
            "total_duration_ms": 0,
        }
    return {
        "cue_count": len(cues),
        "first_start_ms": cues[0].start_ms,
        "last_end_ms": cues[-1].end_ms,
        "total_duration_ms": sum(cue.duration_ms for cue in cues),
    }


def calculate_overlap_metrics(
    original: list[CueSignature], proofread: list[CueSignature]
) -> dict[str, float | int | None]:
    if not original or not proofread or len(original) != len(proofread):
        return {
            "matched_cues": 0,
            "overlap_ms": 0,
            "original_duration_ms": sum(cue.duration_ms for cue in original),
            "proofread_duration_ms": sum(cue.duration_ms for cue in proofread),
            "overlap_ratio": None,
            "coverage_ratio": None,
            "duration_ratio": None,
            "detected_time_scale": None,
        }

    overlap_ms = 0
    matched_cues = 0
    original_duration_ms = sum(cue.duration_ms for cue in original)
    proofread_duration_ms = sum(cue.duration_ms for cue in proofread)

    for left, right in zip(original, proofread):
        intersection = max(0, min(left.end_ms, right.end_ms) - max(left.start_ms, right.start_ms))
        if intersection:
            matched_cues += 1
        overlap_ms += intersection

    overlap_denominator = max(original_duration_ms, proofread_duration_ms)
    coverage_denominator = original_duration_ms
    duration_ratio = (
        proofread_duration_ms / original_duration_ms if original_duration_ms else None
    )

    return {
        "matched_cues": matched_cues,
        "overlap_ms": overlap_ms,
        "original_duration_ms": original_duration_ms,
        "proofread_duration_ms": proofread_duration_ms,
        "overlap_ratio": overlap_ms / overlap_denominator if overlap_denominator else None,
        "coverage_ratio": overlap_ms / coverage_denominator if coverage_denominator else None,
        "duration_ratio": duration_ratio,
        "detected_time_scale": detect_time_scale(original, proofread),
    }


def detect_time_scale(original: list[CueSignature], proofread: list[CueSignature]) -> float | None:
    if not original or not proofread or len(original) != len(proofread):
        return None

    ratios: list[float] = []
    for left, right in zip(original, proofread):
        for original_value, proofread_value in (
            (left.start_ms, right.start_ms),
            (left.end_ms, right.end_ms),
            (left.duration_ms, right.duration_ms),
        ):
            if original_value > 0 and proofread_value > 0:
                ratios.append(proofread_value / original_value)

    if not ratios:
        return None

    ratios.sort()
    median = ratios[len(ratios) // 2]
    for expected in (0.001, 0.01, 0.1, 10.0, 100.0, 1000.0):
        tolerance = expected * 0.05
        if abs(median - expected) <= tolerance:
            return expected
    return None


def compare(original: list[CueSignature], proofread: list[CueSignature]) -> list[str]:
    errors: list[str] = []

    if not original:
        errors.append("no subtitle cues found in original file")
    if not proofread:
        errors.append("no subtitle cues found in proofread file")
    if errors:
        return errors

    if len(original) != len(proofread):
        errors.append(f"cue count changed: original={len(original)}, proofread={len(proofread)}")
        return errors

    for left, right in zip(original, proofread):
        prefix = f"cue {left.ordinal}"
        if left.identifier != right.identifier:
            errors.append(f"{prefix}: identifier changed")
        if left.timing_line != right.timing_line:
            errors.append(f"{prefix}: timing line changed")
        if left.start_ms != right.start_ms:
            errors.append(f"{prefix}: start time changed")
        if left.end_ms != right.end_ms:
            errors.append(f"{prefix}: end time changed")
        if left.duration_ms != right.duration_ms:
            errors.append(f"{prefix}: duration changed")

    left_summary = summarize(original)
    right_summary = summarize(proofread)
    for key in ("first_start_ms", "last_end_ms", "total_duration_ms"):
        if left_summary[key] != right_summary[key]:
            errors.append(f"{key} changed: original={left_summary[key]}, proofread={right_summary[key]}")

    return errors


def can_restore_timing(original: list[CueSignature], proofread: list[CueSignature]) -> tuple[bool, str]:
    if not original or not proofread:
        return False, "cannot repair because one file has no subtitle cues"
    if len(original) != len(proofread):
        return False, "cannot repair because cue count changed"
    for left, right in zip(original, proofread):
        if left.identifier != right.identifier:
            return False, f"cannot repair because cue {left.ordinal} identifier changed"
    return True, "timing lines can be restored from the original file"


def restore_timing_lines(original: SubtitleDocument, proofread: SubtitleDocument) -> None:
    fixed_lines = list(proofread.lines)
    for left, right in zip(original.cues, proofread.cues):
        fixed_lines[right.timing_index] = left.timing_line
    proofread.path.write_text("\n".join(fixed_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify subtitle cue count and timing invariants after proofreading."
    )
    parser.add_argument("original", type=Path)
    parser.add_argument("proofread", type=Path)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Restore proofread timing lines from the original file when cue structure still matches.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    args = parser.parse_args()

    original_document = parse_document(args.original)
    proofread_document = parse_document(args.proofread)
    original = original_document.cues
    proofread = proofread_document.cues
    errors = compare(original, proofread)
    overlap_metrics = calculate_overlap_metrics(original, proofread)
    pre_repair_overlap_metrics = None
    repaired = False
    repair_reason = None

    if errors and args.fix:
        pre_repair_overlap_metrics = overlap_metrics
        can_fix, repair_reason = can_restore_timing(original, proofread)
        if can_fix:
            restore_timing_lines(original_document, proofread_document)
            proofread_document = parse_document(args.proofread)
            proofread = proofread_document.cues
            errors = compare(original, proofread)
            overlap_metrics = calculate_overlap_metrics(original, proofread)
            repaired = not errors

    payload = {
        "ok": not errors,
        "repaired": repaired,
        "repair_reason": repair_reason,
        "original": summarize(original),
        "proofread": summarize(proofread),
        "overlap_metrics": overlap_metrics,
        "pre_repair_overlap_metrics": pre_repair_overlap_metrics,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif errors:
        print("Subtitle integrity check failed:")
        for error in errors:
            print(f"- {error}")
        print("Overlap metrics:")
        print(f"- overlap_ms: {overlap_metrics['overlap_ms']}")
        print(f"- overlap_ratio: {overlap_metrics['overlap_ratio']}")
        print(f"- coverage_ratio: {overlap_metrics['coverage_ratio']}")
        print(f"- duration_ratio: {overlap_metrics['duration_ratio']}")
        print(f"- detected_time_scale: {overlap_metrics['detected_time_scale']}")
        if not args.fix:
            print("- repair_hint: rerun with --fix if only timing units/lines changed")
        elif repair_reason:
            print(f"- repair_status: {repair_reason}")
    else:
        print("Subtitle integrity check passed.")
        if repaired:
            print("- repaired: proofread timing lines restored from original file")
            if pre_repair_overlap_metrics:
                print(
                    "- pre_repair_detected_time_scale: "
                    f"{pre_repair_overlap_metrics['detected_time_scale']}"
                )
        print(f"- cue_count: {payload['original']['cue_count']}")
        print(f"- total_duration_ms: {payload['original']['total_duration_ms']}")
        print(f"- overlap_ratio: {overlap_metrics['overlap_ratio']}")
        print(f"- coverage_ratio: {overlap_metrics['coverage_ratio']}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
