#!/bin/bash
# Satellite pass predictor wrapper
cd "$(dirname "$0")"
exec venv/bin/python3 passes.py "$@"
