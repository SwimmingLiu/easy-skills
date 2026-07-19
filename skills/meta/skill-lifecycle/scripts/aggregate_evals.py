#!/usr/bin/env python3
"""Aggregate paired baseline/candidate Skill evaluations and apply regression gates."""

import argparse
import json
import math
import os
import shutil
import statistics
import sys
import tempfile
from pathlib import Path


EXIT_REJECTED = 1
EXIT_VALIDATION = 2
EXIT_RUNTIME = 3
VARIANTS = ("baseline", "candidate")
ASSERTION_FIELDS = frozenset({"id", "passed", "prohibited_action"})
MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_CASES = 1_000
MAX_ASSERTIONS_PER_RECORD = 500
MAX_STRING_LENGTH = 256
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class ValidationError(ValueError):
    """Raised when evaluation data or thresholds violate the input contract."""


def _finite_number(value, label, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValidationError(f"{label} must be a finite number") from error
    if not math.isfinite(number):
        raise ValidationError(f"{label} must be finite")
    if minimum is not None and number < minimum:
        raise ValidationError(f"{label} must be at least {minimum}")
    return number


def _bounded_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    if len(value) > MAX_STRING_LENGTH:
        raise ValidationError(
            f"{label} exceeds string length limit {MAX_STRING_LENGTH}"
        )
    return value


def _assertion_result(assertion, label):
    if not isinstance(assertion, dict):
        raise ValidationError(f"{label} must be an object")
    unknown = set(assertion) - ASSERTION_FIELDS
    missing = {"id", "passed"} - set(assertion)
    if unknown:
        raise ValidationError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValidationError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    assertion_id = _bounded_string(assertion["id"], f"{label}.id")
    passed = assertion.get("passed")
    if not isinstance(passed, bool):
        raise ValidationError(f"{label}.passed must be a boolean")
    prohibited = assertion.get("prohibited_action", False)
    if not isinstance(prohibited, bool):
        raise ValidationError(f"{label}.prohibited_action must be a boolean")
    return assertion_id, passed, prohibited


def _normalize_record(record, index):
    label = f"record {index}"
    if not isinstance(record, dict):
        raise ValidationError(f"{label} must be an object")
    case_id = _bounded_string(record.get("case_id"), f"{label}.case_id")
    if "|" in case_id or "\n" in case_id or "\r" in case_id:
        raise ValidationError(f"{label}.case_id contains Markdown control characters")
    variant = record.get("variant")
    if variant not in VARIANTS:
        raise ValidationError(f"{label}.variant must be candidate or baseline")
    assertions = record.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise ValidationError(f"{label}.assertions must be a non-empty list")
    if len(assertions) > MAX_ASSERTIONS_PER_RECORD:
        raise ValidationError(
            f"{label} exceeds assertions limit {MAX_ASSERTIONS_PER_RECORD}"
        )
    results = [
        _assertion_result(assertion, f"{label}.assertions[{offset}]")
        for offset, assertion in enumerate(assertions)
    ]
    duration = _finite_number(record.get("duration_ms"), f"{label}.duration_ms", minimum=0)
    tokens = _finite_number(record.get("total_tokens"), f"{label}.total_tokens", minimum=0)
    assertion_ids = [assertion_id for assertion_id, _, _ in results]
    if len(set(assertion_ids)) != len(assertion_ids):
        raise ValidationError(f"{label}.assertions contains duplicate ids")
    passed = sum(result for _, result, _ in results)
    prohibited_failures = sum(
        1 for _, result, prohibited in results if prohibited and not result
    )
    return {
        "case_id": case_id,
        "variant": variant,
        "pass_rate": passed / len(results),
        "duration_ms": duration,
        "total_tokens": tokens,
        "assertions_passed": passed,
        "assertions_total": len(results),
        "assertion_ids": sorted(assertion_ids),
        "prohibited_action_failures": prohibited_failures,
    }


def _distribution(values):
    return {
        "mean": statistics.fmean(values),
        "population_stddev": statistics.pstdev(values),
    }


def _variant_summary(records):
    return {
        "case_count": len(records),
        "pass_rate_mean": statistics.fmean(record["pass_rate"] for record in records),
        "duration_ms": _distribution([record["duration_ms"] for record in records]),
        "total_tokens": _distribution([record["total_tokens"] for record in records]),
        "prohibited_action_failures": sum(
            record["prohibited_action_failures"] for record in records
        ),
    }


def _check(actual, limit, operator):
    if operator == "minimum":
        passed = actual >= limit
    else:
        passed = actual <= limit
    return {"actual": actual, "limit": limit, "passed": passed}


def aggregate(
    records,
    *,
    min_pass_rate_delta,
    max_duration_regression_ms=None,
    max_token_regression=None,
):
    """Validate paired records, aggregate metrics, and return a decision report."""
    if not isinstance(records, list) or not records:
        raise ValidationError("records must be a non-empty list")
    if len(records) > MAX_CASES * len(VARIANTS):
        raise ValidationError(f"records exceed case limit {MAX_CASES}")
    min_delta = _finite_number(min_pass_rate_delta, "min_pass_rate_delta")
    max_duration = None
    if max_duration_regression_ms is not None:
        max_duration = _finite_number(
            max_duration_regression_ms, "max_duration_regression_ms"
        )
    max_tokens = None
    if max_token_regression is not None:
        max_tokens = _finite_number(max_token_regression, "max_token_regression")

    pairs = {}
    for index, raw_record in enumerate(records):
        record = _normalize_record(raw_record, index)
        case = pairs.setdefault(record["case_id"], {})
        variant = record["variant"]
        if variant in case:
            raise ValidationError(
                f"duplicate {variant} record for case {record['case_id']}"
            )
        case[variant] = record
    for case_id, pair in sorted(pairs.items()):
        for variant in VARIANTS:
            if variant not in pair:
                raise ValidationError(f"case {case_id} is missing {variant} record")
        if pair["baseline"]["assertion_ids"] != pair["candidate"]["assertion_ids"]:
            raise ValidationError(
                f"case {case_id} baseline/candidate assertion ids do not match"
            )
    if len(pairs) > MAX_CASES:
        raise ValidationError(f"case limit {MAX_CASES} exceeded")

    grouped = {
        variant: [pairs[case_id][variant] for case_id in sorted(pairs)]
        for variant in VARIANTS
    }
    summary = {variant: _variant_summary(grouped[variant]) for variant in VARIANTS}
    cases = []
    for case_id in sorted(pairs):
        baseline = pairs[case_id]["baseline"]
        candidate = pairs[case_id]["candidate"]
        cases.append(
            {
                "case_id": case_id,
                "baseline": baseline,
                "candidate": candidate,
                "delta": {
                    "pass_rate": candidate["pass_rate"] - baseline["pass_rate"],
                    "duration_ms": candidate["duration_ms"] - baseline["duration_ms"],
                    "total_tokens": candidate["total_tokens"] - baseline["total_tokens"],
                },
            }
        )

    pass_delta = (
        summary["candidate"]["pass_rate_mean"]
        - summary["baseline"]["pass_rate_mean"]
    )
    duration_delta = (
        summary["candidate"]["duration_ms"]["mean"]
        - summary["baseline"]["duration_ms"]["mean"]
    )
    token_delta = (
        summary["candidate"]["total_tokens"]["mean"]
        - summary["baseline"]["total_tokens"]["mean"]
    )
    prohibited_failures = summary["candidate"]["prohibited_action_failures"]
    checks = {
        "pass_rate_delta": _check(pass_delta, min_delta, "minimum"),
        "prohibited_actions": _check(prohibited_failures, 0, "maximum"),
    }
    if max_duration is not None:
        checks["duration_regression_ms"] = _check(
            duration_delta, max_duration, "maximum"
        )
    if max_tokens is not None:
        checks["token_regression"] = _check(token_delta, max_tokens, "maximum")

    return {
        "schema_version": 1,
        "thresholds": {
            "min_pass_rate_delta": min_delta,
            "max_duration_regression_ms": max_duration,
            "max_token_regression": max_tokens,
        },
        "summary": summary,
        "comparison": {
            "pass_rate_delta": pass_delta,
            "duration_ms_delta": duration_delta,
            "total_tokens_delta": token_delta,
        },
        "cases": cases,
        "decision": {
            "accepted": all(check["passed"] for check in checks.values()),
            "candidate_prohibited_action_failures": prohibited_failures,
            "checks": checks,
        },
    }


def deterministic_json(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def render_markdown(report):
    decision = report["decision"]
    summary = report["summary"]
    lines = [
        "# Evaluation comparison",
        "",
        f"Decision: **{'accepted' if decision['accepted'] else 'rejected'}**",
        "",
        "## Summary",
        "",
        "| Variant | Pass-rate mean | Duration mean (ms) | Duration population SD | Token mean | Token population SD |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in VARIANTS:
        metrics = summary[variant]
        lines.append(
            f"| {variant} | {metrics['pass_rate_mean']:.6f} | "
            f"{metrics['duration_ms']['mean']:.6f} | "
            f"{metrics['duration_ms']['population_stddev']:.6f} | "
            f"{metrics['total_tokens']['mean']:.6f} | "
            f"{metrics['total_tokens']['population_stddev']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Pass-rate delta | Duration delta (ms) | Token delta |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for case in report["cases"]:
        delta = case["delta"]
        lines.append(
            f"| {case['case_id']} | {delta['pass_rate']:.6f} | "
            f"{delta['duration_ms']:.6f} | {delta['total_tokens']:.6f} |"
        )
    lines.extend(["", "## Gates", "", "| Gate | Actual | Limit | Passed |", "| --- | ---: | ---: | :---: |"])
    for name, check in decision["checks"].items():
        lines.append(
            f"| {name} | {check['actual']:.6f} | {check['limit']:.6f} | "
            f"{'yes' if check['passed'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def _validate_output_budget(*texts):
    estimated_bytes = sum(len(text.encode("utf-8")) for text in texts)
    if estimated_bytes > MAX_OUTPUT_BYTES:
        raise ValidationError(
            f"estimated output exceeds output limit {MAX_OUTPUT_BYTES} bytes"
        )


def _canonical_output_path(path):
    absolute = Path(os.path.abspath(os.fspath(path)))
    return absolute.parent.resolve(strict=False) / absolute.name


def _reject_output_target(path):
    if path.is_symlink():
        raise OSError(f"refusing symlink output path: {path}")
    if path.exists() and not path.is_file():
        raise OSError(f"output path is not a regular file: {path}")


def _write_sibling_file(destination, text, suffix):
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=suffix,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        return Path(temporary_name)
    except BaseException:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        raise


def _backup_destination(destination):
    if not destination.exists():
        return None
    backup_name = None
    try:
        with destination.open("rb") as source, tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".backup",
            delete=False,
        ) as backup:
            backup_name = backup.name
            shutil.copyfileobj(source, backup)
            backup.flush()
            os.fsync(backup.fileno())
        return Path(backup_name)
    except BaseException:
        if backup_name is not None:
            try:
                os.unlink(backup_name)
            except FileNotFoundError:
                pass
        raise


def _fsync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_path(path):
    if path is None:
        return
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def write_reports(json_path, json_text, markdown_path=None, markdown_text=None):
    """Transactionally replace requested reports; return directory durability."""
    requested = []
    if json_path is not None:
        requested.append((_canonical_output_path(json_path), json_text))
    if markdown_path is not None:
        requested.append((_canonical_output_path(markdown_path), markdown_text))
    if not requested:
        return True
    if any(not isinstance(text, str) for _, text in requested):
        raise ValidationError("every requested output requires text")
    destinations = [destination for destination, _ in requested]
    if len(set(destinations)) != len(destinations):
        raise ValidationError("JSON and Markdown output paths must be distinct")

    # Validate every final target before preparing or committing any replacement.
    for destination in destinations:
        _reject_output_target(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

    prepared = []
    backups = {}
    committed = []
    try:
        for destination, text in requested:
            prepared.append(
                (destination, _write_sibling_file(destination, text, ".new"))
            )
        for destination in destinations:
            _reject_output_target(destination)
            backups[destination] = _backup_destination(destination)
        try:
            for destination, temporary in prepared:
                _reject_output_target(destination)
                os.replace(temporary, destination)
                committed.append(destination)
        except BaseException as commit_error:
            rollback_errors = []
            for destination in reversed(committed):
                backup = backups[destination]
                try:
                    if backup is None:
                        os.unlink(destination)
                    else:
                        os.replace(backup, destination)
                        backups[destination] = None
                except OSError as rollback_error:
                    rollback_errors.append(f"{destination}: {rollback_error}")
            if rollback_errors:
                raise OSError(
                    f"output commit failed ({commit_error}); rollback also failed: "
                    + "; ".join(rollback_errors)
                ) from commit_error
            raise

        for backup in backups.values():
            _cleanup_path(backup)
        durable = True
        for directory in sorted({path.parent for path in destinations}, key=str):
            try:
                _fsync_directory(directory)
            except OSError:
                durable = False
        return durable
    finally:
        for _, temporary in prepared:
            _cleanup_path(temporary)
        for backup in backups.values():
            _cleanup_path(backup)


def _reject_json_constant(value):
    raise ValueError(f"non-finite JSON constant {value}")


def _load_records(path):
    source = Path(path)
    try:
        with source.open("rb") as handle:
            raw_document = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw_document) > MAX_INPUT_BYTES:
            raise ValidationError(
                f"input exceeds input limit {MAX_INPUT_BYTES} bytes"
            )
        document = json.loads(
            raw_document.decode("utf-8"), parse_constant=_reject_json_constant
        )
    except ValidationError:
        raise
    except json.JSONDecodeError as error:
        raise ValidationError(f"invalid JSON: {error.msg}") from error
    except UnicodeDecodeError as error:
        raise ValidationError("input must be UTF-8 JSON") from error
    except (ValueError, OverflowError) as error:
        raise ValidationError(f"invalid JSON value: {error}") from error
    if isinstance(document, dict):
        if set(document) != {"records"}:
            raise ValidationError("input object must contain only records")
        document = document["records"]
    return document


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Resource limits:\n"
            f"  input bytes: {MAX_INPUT_BYTES}\n"
            f"  cases: {MAX_CASES}\n"
            f"  assertions per record: {MAX_ASSERTIONS_PER_RECORD}\n"
            f"  string characters: {MAX_STRING_LENGTH}\n"
            f"  estimated output bytes: {MAX_OUTPUT_BYTES}"
        ),
    )
    parser.add_argument("--input", required=True, help="JSON records file")
    parser.add_argument("--min-pass-rate-delta", required=True, type=float)
    parser.add_argument("--max-duration-regression-ms", type=float)
    parser.add_argument("--max-token-regression", type=float)
    parser.add_argument("--json-output", help="optional JSON report path")
    parser.add_argument("--markdown-output", help="optional Markdown report path")
    return parser


def main(argv=None):
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        records = _load_records(arguments.input)
        report = aggregate(
            records,
            min_pass_rate_delta=arguments.min_pass_rate_delta,
            max_duration_regression_ms=arguments.max_duration_regression_ms,
            max_token_regression=arguments.max_token_regression,
        )
        json_text = deterministic_json(report)
        markdown_text = render_markdown(report)
        _validate_output_budget(json_text, markdown_text)
        durable = write_reports(
            arguments.json_output,
            json_text,
            arguments.markdown_output,
            markdown_text,
        )
        if not durable:
            print(
                "warning: outputs committed but directory durability is uncertain",
                file=sys.stderr,
            )
        sys.stdout.write(json_text)
        return 0 if report["decision"]["accepted"] else EXIT_REJECTED
    except ValidationError as error:
        print(f"validation error: {error}", file=sys.stderr)
        return EXIT_VALIDATION
    except (ValueError, OverflowError) as error:
        print(f"validation error: {error}", file=sys.stderr)
        return EXIT_VALIDATION
    except OSError as error:
        print(f"runtime error: {error}", file=sys.stderr)
        return EXIT_RUNTIME
    except Exception as error:
        print(f"runtime error: {error}", file=sys.stderr)
        return EXIT_RUNTIME


if __name__ == "__main__":
    raise SystemExit(main())
