#!/bin/bash
# Wrapper used by cron on your Mac: go to the project, activate the venv, run.
cd "$(dirname "$0")/.." || exit 1
source venv/bin/activate
mkdir -p logs
python -m pipelines.run_pipeline >> logs/cron.log 2>&1
