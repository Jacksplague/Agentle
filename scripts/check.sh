#!/usr/bin/env bash
set -euo pipefail
python -m ruff check .
python -m mypy src
python -m pytest
