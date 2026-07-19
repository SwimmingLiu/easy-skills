#!/usr/bin/env python3
"""Aggregate paired baseline/candidate Skill evaluations and apply regression gates."""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path


EXIT_REJECTED = 1
EXIT_VALIDATION = 2
EXIT_RUNTIME = 3
VARIANTS = ("baseline", "candidate")


class ValidationError(ValueError):
    """Raised when evaluation data or thresholds violate the input contract."""


def _finite_number(value, label, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{label} must be finite")
    if minimum is not None and number < minimum:
        raise ValidationError(f"{label} must be at least {minimum}")
    return number


def _assertion_result(assertion, label):
    if isinstance(assertion, bool):
        return assertion, False
    if not isinstance(assertion, dict):
        raise ValidationError(f"{label} must be a boolean or object")
    passed = assertion.get("passed")
    if not isinstance(passed, bool):
        raise ValidationError(f"{label}.passed must be a boolean")
    prohibited = assertion.get("prohibited_action", False)
    if not isinstance(prohibited, bool):
        raise ValidationError(f"{label}.prohibited_action must be a boolean")
    return passed, prohibited


def _normalize_record(record, index):
    label = f"record {index}"
    if not isinstance(record, dict):
        raise ValidationError(f"{label} must be an object")
    case_id = record.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValidationError(f"{label}.case_id must be a non-empty string")
    variant = record.get("variant")
    if variant not in VARIANTS:
        raise ValidationError(f"{label}.variant must be candidate or baseline")
    assertions = record.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise ValidationError(f"{label}.assertions must be a non-empty list")
    results = [
        _assertion_result(assertion, f"{label}.assertions[{offset}]")
        for offset, assertion in enumerate(assertions)
    ]
    duration = _finite_number(record.get("duration_ms"), f"{label}.duration_ms", minimum=0)
    tokens = _finite_number(record.get("total_tokens"), f"{label}.total_tokens", minimum=0)
    passed = sum(result for result, _ in results)
    prohibited_failures = sum(
        1 for result, prohibited in results if prohibited and not result
    )
    return {
        "case_id": case_id,
        "variant": variant,
        "pass_rate": passed / len(results),
        "duration_ms": duration,
        "total_tokens": tokens,
        "assertions_passed": passed,
        "assertions_total": len(results),
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


def _load_records(path):
    try:
        with Path(path).open(encoding="utf-8") as handle:
            document = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValidationError(f"invalid JSON: {error.msg}") from error
    except UnicodeDecodeError as error:
        raise ValidationError("input must be UTF-8 JSON") from error
    if isinstance(document, dict):
        if set(document) != {"records"}:
            raise ValidationError("input object must contain only records")
        document = document["records"]
    return document


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
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
        if arguments.json_output:
            Path(arguments.json_output).write_text(json_text, encoding="utf-8")
        if arguments.markdown_output:
            Path(arguments.markdown_output).write_text(
                render_markdown(report), encoding="utf-8"
            )
        sys.stdout.write(json_text)
        return 0 if report["decision"]["accepted"] else EXIT_REJECTED
    except ValidationError as error:
        print(f"validation error: {error}", file=sys.stderr)
        return EXIT_VALIDATION
    except OSError as error:
        print(f"runtime error: {error}", file=sys.stderr)
        return EXIT_RUNTIME


if __name__ == "__main__":
    raise SystemExit(main())
