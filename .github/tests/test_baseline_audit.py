"""Tests for the gate detector in organization-pr-baseline.yml.

The audit runs as an inline `shell: python` step so the reusable workflow
carries no dependency on files in this repository. That makes it easy for a
test to drift from what actually ships, so these tests do not re-implement the
logic: they extract the exact script out of the workflow YAML and execute it.
Change the workflow and these tests exercise the change.

Run: python3 .github/tests/test_baseline_audit.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/organization-pr-baseline.yml"
AUDIT_STEP = "Audit workflow structure"
# A detector regression should fail fast and point at the subprocess, not
# hang until the CI job timeout.
AUDIT_TIMEOUT_SECONDS = 60


def audit_source() -> str:
    """The exact script shipped in the workflow, not a copy of it."""
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for step in doc["jobs"]["validate"]["steps"]:
        if step.get("name") == AUDIT_STEP:
            return step["run"]
    raise AssertionError(f"step {AUDIT_STEP!r} not found in {WORKFLOW}")


class AuditResult:
    def __init__(self, exit_code, stdout, stderr, summary):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.summary = summary

    @property
    def blocking(self):
        return [x for x in self.stdout.splitlines() if x.startswith("::error")]

    @property
    def advisory(self):
        return [x for x in self.stdout.splitlines() if x.startswith("::warning")]


def run_audit(workflows, strict=False):
    """Execute the shipped audit against a synthetic .github/workflows tree."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp, ".github", "workflows")
        target.mkdir(parents=True)
        for name, body in workflows.items():
            (target / name).write_text(body, encoding="utf-8")
        summary = Path(tmp, "summary.md")
        summary.touch()
        # Deliberately not the inherited environment: the script under test is
        # read out of a workflow file that a pull request can modify, so it gets
        # only the two variables it reads and nothing else to disclose.
        env = {
            "STRICT": "true" if strict else "false",
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        proc = subprocess.run(
            [sys.executable, "-c", audit_source()],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
            timeout=AUDIT_TIMEOUT_SECONDS,
        )
        return AuditResult(
            proc.returncode,
            proc.stdout,
            proc.stderr,
            summary.read_text(encoding="utf-8"),
        )


def gate(steps, name="CI Summary", needs=""):
    """A minimal workflow whose single job is a merge gate."""
    return (
        "name: t\n"
        "on: [pull_request]\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  s:\n"
        f"    name: {name}\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 5\n"
        + (f"    {needs}\n" if needs else "")
        + "    steps:\n"
        + textwrap.indent(textwrap.dedent(steps), " " * 6)
    )


class FakeGatesAreBlocked(unittest.TestCase):
    """A required gate that cannot fail must be reported."""

    def assert_blocked(self, steps, msg):
        result = run_audit({"ci.yml": gate(steps)})
        self.assertTrue(result.blocking, f"{msg}\nstdout:\n{result.stdout}")
        self.assertEqual(result.exit_code, 1, msg)

    def test_inline_echo(self):
        self.assert_blocked('- run: echo "CI checks passed"\n', "inline echo placeholder")

    def test_block_scalar_echo(self):
        self.assert_blocked('- run: |\n    echo "CI checks passed"\n', "block scalar echo")

    def test_set_e_then_echo(self):
        # Defeated the previous literal-string matcher.
        self.assert_blocked('- run: |\n    set -e\n    echo "CI checks passed"\n', "set -e then echo")

    def test_any_other_phrase(self):
        self.assert_blocked('- run: echo "all good"\n', "phrase-independent")

    def test_exit_zero(self):
        self.assert_blocked("- run: exit 0\n", "exit 0")

    def test_true(self):
        self.assert_blocked("- run: 'true'\n", "true")

    def test_chained_inert_commands(self):
        self.assert_blocked("- run: echo a && echo b\n", "every segment inert")

    def test_multiline_all_inert(self):
        self.assert_blocked("- run: |\n    set -e\n    true\n    exit 0\n", "all lines inert")

    def test_setup_action_plus_echo(self):
        # The shape found in meditation-service and healify-org: a checkout step
        # does not make a gate meaningful.
        self.assert_blocked(
            '- uses: actions/checkout@v4\n- run: echo "CI checks passed"\n',
            "setup action plus echo is still fake",
        )


class RealGatesArePermitted(unittest.TestCase):
    """A false positive here red-lines a compliant repository, so these matter most."""

    def assert_clean(self, steps, msg, needs=""):
        result = run_audit({"ci.yml": gate(steps, needs=needs)})
        self.assertEqual(result.blocking, [], f"{msg}\nstdout:\n{result.stdout}")
        self.assertEqual(result.exit_code, 0, msg)

    def test_real_command(self):
        self.assert_clean("- run: npm test\n", "a real command is a real gate")

    def test_compound_command_after_echo(self):
        # Prefix matching used to read this whole line as inert.
        self.assert_clean('- run: echo "verifying" && make verify\n', "echo && make verify")

    def test_command_prefixed_by_inert_word(self):
        self.assert_clean("- run: truncate_logs --check\n", "'truncate_logs' is not 'true'")

    def test_semicolon_separated(self):
        self.assert_clean("- run: cd app; pytest\n", "cd then pytest")

    def test_piped_into_real_command(self):
        self.assert_clean("- run: echo x | grep -q ok\n", "piped into grep")

    def test_exit_nonzero_guard(self):
        self.assert_clean('- run: |\n    if [ -z "$X" ]; then exit 1; fi\n', "exit 1 can fail")

    def test_aggregator_via_needs(self):
        self.assert_clean(
            '- run: |\n    if [ "${{ needs.build.result }}" != "success" ]; then exit 1; fi\n',
            "aggregates through needs",
            needs="needs: [build]",
        )

    def test_unrelated_job_mentioning_the_phrase(self):
        """The old matcher was file-scoped and fired on this."""
        body = (
            "name: t\n"
            "on: [pull_request]\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  other:\n"
            "    name: Other\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 5\n"
            "    steps:\n"
            '      - run: echo "CI checks passed"\n'
            "  s:\n"
            "    name: CI Summary\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 5\n"
            "    steps:\n"
            "      - run: ./scripts/aggregate.sh\n"
        )
        result = run_audit({"ci.yml": body})
        self.assertEqual(result.blocking, [], f"job-scoped, not file-scoped\n{result.stdout}")

    def test_non_gate_job_is_never_blocking(self):
        result = run_audit({"ci.yml": gate('- run: echo "hi"\n', name="Build")})
        self.assertEqual(result.blocking, [], "only gate jobs are judged")


class AdvisoryTier(unittest.TestCase):
    """Advisory findings annotate by default and fail only under strict."""

    MUTABLE = (
        "name: t\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  b:\n"
        "    runs-on: ubuntu-24.04\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        '      - run: echo "${{ secrets.TOKEN }}"\n'
    )

    def test_advisory_does_not_fail_by_default(self):
        result = run_audit({"ci.yml": self.MUTABLE})
        self.assertEqual(result.exit_code, 0, "advisory must not fail the default run")
        self.assertTrue(result.advisory, "expected advisory findings")

    def test_advisory_fails_under_strict(self):
        result = run_audit({"ci.yml": self.MUTABLE}, strict=True)
        self.assertEqual(result.exit_code, 1, "strict must fail on advisory findings")

    def test_detects_each_advisory_class(self):
        joined = "\n".join(run_audit({"ci.yml": self.MUTABLE}).advisory)
        for expected in (
            "mutable ref",
            "permissions block",
            "timeout-minutes",
            "interpolates a secret",
        ):
            self.assertIn(expected, joined, f"missing advisory: {expected}")

    def test_sha_pinned_action_is_not_flagged(self):
        body = self.MUTABLE.replace(
            "actions/checkout@v4",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        )
        joined = "\n".join(run_audit({"ci.yml": body}).advisory)
        self.assertNotIn("mutable ref", joined, "a full SHA must not be reported as mutable")

    def test_local_action_is_not_flagged(self):
        body = self.MUTABLE.replace("actions/checkout@v4", "./.github/actions/setup")
        joined = "\n".join(run_audit({"ci.yml": body}).advisory)
        self.assertNotIn("mutable ref", joined, "local actions have no ref to pin")


class Robustness(unittest.TestCase):
    def test_unparsable_workflow_is_blocking(self):
        result = run_audit({"broken.yml": "jobs:\n  - this: [is\n   not: valid\n"})
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(any("Unable to parse" in x for x in result.blocking))

    def test_empty_workflow_directory_is_clean(self):
        result = run_audit({})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.blocking, [])

    def test_step_summary_is_written(self):
        result = run_audit({"ci.yml": gate("- run: npm test\n")})
        self.assertIn("Organization PR Baseline", result.summary)
        self.assertIn("Workflows audited", result.summary)

    def test_script_writes_nothing_to_stderr(self):
        result = run_audit({"ci.yml": gate("- run: npm test\n")})
        self.assertEqual(result.stderr, "", f"unexpected stderr: {result.stderr}")


class ShippedWorkflowIsSelfConsistent(unittest.TestCase):
    def test_audit_step_parses_as_python(self):
        ast.parse(audit_source())

    def test_this_repository_passes_its_own_blocking_tier(self):
        workflows = {
            p.name: p.read_text(encoding="utf-8")
            for p in (REPO_ROOT / ".github/workflows").glob("*.y*ml")
        }
        result = run_audit(workflows)
        self.assertEqual(
            result.blocking, [], f"this repo must pass its own blocking tier\n{result.stdout}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
