#!/bin/bash
# Update frequencies.json with entries for all satellites
cd "$(dirname "$0")"
exec venv/bin/python3 update_frequencies.py "$@"
