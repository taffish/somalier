#!/usr/bin/env python3
"""故障注入只使用私有临时目录，不运行真实分析或修改宿主环境。"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SMOKE = Path(__file__).resolve().parents[1] / "docker/somalier-smoke.sh"
COMMANDS = ["extract", "relate", "ancestry", "AB_plot", "contamination", "find-sites", "pedrel"]


class Diagnostics(unittest.TestCase):
    def test_each_help_failure_retains_status_and_bounded_log(self):
        for index, command in enumerate(["main"] + COMMANDS):
            with self.subTest(command=command), tempfile.TemporaryDirectory(prefix="somalier-diagnostics-") as tmp:
                root = Path(tmp)
                scratch = root / "scratch"
                scratch.mkdir()
                fake = root / "somalier"
                fake.write_text("#!/bin/sh\n"
                    'case "$1" in --help) phase=main ;; *) phase=$1 ;; esac\n'
                    'if [ "$phase" = "$FAIL_PHASE" ]; then\n'
                    '  i=1; while [ "$i" -le 240 ]; do printf "injected-line-%03d\\n" "$i"; i=$((i+1)); done\n'
                    '  echo "INJECTED_HELP_FAILURE_$FAIL_PHASE" >&2\n'
                    '  exit "$FAIL_CODE"\n'
                    'fi\n'
                    "printf '%s\\n' 'somalier version: 0.3.4' " +
                    " ".join(repr("  " + c) for c in COMMANDS) + "\n")
                fake.chmod(0o700)
                env = dict(os.environ, PATH=str(root)+os.pathsep+os.environ["PATH"],
                           TMPDIR=str(scratch), FAIL_PHASE=command, FAIL_CODE=str(42+index))
                result = subprocess.run(["sh", str(SMOKE), "identity"], env=env,
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 42+index)
                self.assertIn(f"smoke-stage=identity-{command}-help exit={42+index}", result.stderr)
                self.assertIn(f"INJECTED_HELP_FAILURE_{command}", result.stderr)
                self.assertIn("injected-line-240", result.stderr)
                self.assertNotIn("injected-line-001", result.stderr)
                self.assertEqual(sum(line.startswith("injected-line-") for line in result.stderr.splitlines()), 79)
                self.assertEqual(list(scratch.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
