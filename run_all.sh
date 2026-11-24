#!/usr/bin/env bash
# Reproduce the full project: clean -> analyse -> build PDFs -> verify
set -euo pipefail
python3 scripts/clean.py
python3 scripts/analysis.py > outputs/tables/analysis_stdout.txt
python3 scripts/build_reports.py
python3 scripts/verify.py
