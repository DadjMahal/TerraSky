#!/usr/bin/env bash
# SkyDash unit-test runner (§115). Runs every test suite that does NOT need
# Flask/cloud creds (pure stdlib + cryptography). Usage: scripts/run_tests.sh
set -euo pipefail
cd "$(dirname "$0")/../skydash"
fail=0
for f in tests/test_*.py; do
  echo "== $f =="
  python3 "$f" || fail=1
done
echo ""
if [ "$fail" -eq 0 ]; then echo "ALL TEST SUITES PASSED"; else echo "SOME TEST SUITES FAILED"; fi
exit "$fail"
