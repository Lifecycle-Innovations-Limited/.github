"""Verify every self-hosted runs-on carries an org fleet label.

The org's ephemeral AWS fleet is dispatched by a webhook matcher keyed on the
labels listed below. A self-hosted job that omits the fleet label matches no
scale-up queue, so it never creates its own runner: it can only land on an
instance another job happened to spawn, and otherwise sits queued until the
24-hour timeout. That is how the org-wide main-source-gate stalled.

This check makes the label contract explicit instead of assumed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Fleet labels that route to a real scale-up queue. Keep in sync with
# /github-action-runners/ghr-ephemeral/webhook/runner-matcher-config.
FLEET_LABELS = {"aws", "aws-large", "aws-od", "aws-arm", "aws-win"}

# The AWS ephemeral fleet is Linux only. A self-hosted job that names another
# operating system (macOS, Windows) runs on a different runner and is out of
# scope for this contract, so it is skipped rather than flagged.
NON_FLEET_OS_LABELS = {"macos", "windows"}

WORKFLOW_GLOBS = ("*.yml", "*.yaml")


def label_set(runs_on: object) -> set[str] | None:
    """Return the label set for a runs-on value, or None if it is dynamic.

    A ${{ ... }} expression is resolved at runtime, so it cannot be checked
    statically and is skipped rather than guessed at.
    """
    if isinstance(runs_on, str):
        if "${{" in runs_on:
            return None
        return {runs_on}
    if isinstance(runs_on, list):
        labels: set[str] = set()
        for item in runs_on:
            if not isinstance(item, str):
                return None
            if "${{" in item:
                return None
            labels.add(item)
        return labels
    return None


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # actionlint owns syntax errors; stay quiet here to avoid double reports.
        return [f"{path}: unreadable YAML ({exc.__class__.__name__})"]

    if not isinstance(data, dict):
        return problems

    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return problems

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        runs_on = job.get("runs-on")
        labels = label_set(runs_on)
        if labels is None:
            continue
        lowered = {str(lbl).lower() for lbl in labels}
        if "self-hosted" not in lowered:
            continue
        if lowered & NON_FLEET_OS_LABELS:
            continue
        if not (lowered & FLEET_LABELS):
            problems.append(
                f"{path}: job '{job_id}' runs on self-hosted without a fleet label "
                f"({sorted(labels)}). Add one of {sorted(FLEET_LABELS)}."
            )
    return problems


def main() -> int:
    roots = []
    for arg in sys.argv[1:]:
        roots.append(Path(arg))
    if not roots:
        roots = [Path(".github/workflows")]

    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            for glob in WORKFLOW_GLOBS:
                files.extend(sorted(root.glob(glob)))
        elif root.is_file():
            files.append(root)

    if not files:
        print("::notice::No workflow files to check.")
        return 0

    all_problems: list[str] = []
    for path in files:
        all_problems.extend(check_file(path))

    print(f"Checked {len(files)} workflow file(s) for the fleet label contract.")
    if all_problems:
        for problem in all_problems:
            print(f"::error::{problem}")
        return 1
    print("OK: every self-hosted runs-on carries a fleet label.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
