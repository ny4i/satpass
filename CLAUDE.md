# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Amateur radio satellite pass predictor. Predicts visible passes over a location, displays frequency information, and exports to ICS calendar files.

## Usage

```bash
./passes.sh --grid EL87pb --elev 10 --min-elev 10

# Export to calendar file with 15-minute reminder
./passes.sh --grid EL87pb --min-elev 10 --ics passes.ics --ics-notify 15

# Use UTC times
./passes.sh --grid EL87pb --min-elev 10 --utc

# Show all tracked satellites regardless of recent reported activity
./passes.sh --grid EL87pb --min-elev 10 --all

# Only show FM satellites
./passes.sh --grid EL87pb --min-elev 10 --mode FM
```

Options:
- `--grid` - Maidenhead grid square (required, e.g., EL87pb)
- `--elev` - Ground elevation in meters (default: 0)
- `--min-elev` - Minimum pass elevation in degrees (default: 10)
- `--start` - Start time: "YYYY-MM-DD HH:MM" (default: now)
- `--hours` - Prediction window in hours (default: 24)
- `--sats` - Satellite list file (default: satellites.txt)
- `--utc` - Display times in UTC (default: local time)
- `--ics FILE` - Export passes to ICS calendar file
- `--ics-notify MIN` - Add calendar reminder N minutes before each pass
- `--all` - Show all tracked satellites, not just ones with recent reported AMSAT activity (default: active only)
- `--active-hours N` - Lookback window in hours for AMSAT activity status (default: 48)
- `--mode MODE` - Only show satellites with this mode from `frequencies.json` (e.g. `FM`, `SSB`, `CW`, `SSB/CW` — SSB and CW are treated as interchangeable since linear transponders carry both). Default: all modes

## Activity Filtering

By default, `passes.py` only predicts passes for satellites in `satellites.txt`
that have been reported "Heard" on the [AMSAT Live OSCAR Satellite Status
page](https://www.amsat.org/status/) within the last 48 hours (`--active-hours`
to change the window). This queries the status page's public JSON API
(`amsat_status.py`, see https://www.amsat.org/status/api/docs.php) rather than
scraping the page. Use `--all` to predict passes for every tracked satellite
regardless of reported activity. If the status API can't be reached, the
script warns and falls back to showing all satellites.

This only filters among satellites already in `satellites.txt` — it does not
add or remove entries from the file. A satellite newly active on the status
page still needs to be added to `satellites.txt` (and `frequencies.json` via
`update_frequencies.py`) manually before it will show up here.

## Managing Frequency Data

When adding new satellites to `satellites.txt`, update the frequency database:

```bash
./update_frequencies.sh
```

This will:
- Create template entries for any satellites missing from `frequencies.json`
- Report which satellites need frequency data filled in
- Warn about orphaned entries no longer in satellites.txt

The main script warns if `frequencies.json` is missing or incomplete.

## Files

- `satellites.txt` - Satellites to track (one per line, AMSAT designations)
- `frequencies.json` - Uplink/downlink frequencies and modes for each satellite
- `passes.py` - Main Python script
- `passes.sh` - Wrapper to run with venv
- `amsat_status.py` - Queries the AMSAT status API for recent satellite activity
- `sat_naming.py` - Shared designation-parsing helpers (base name + mode suffix)
- `update_frequencies.py` - Script to manage frequencies.json
- `update_frequencies.sh` - Wrapper to run update script
- `venv/` - Python virtual environment with pyephem

## Dependencies

- Python 3
- pyephem (installed in venv)

## Name Mapping

AMSAT designations mapped to Celestrak names in `passes.py`:
- `ISS-FM` → `ISS`
- `AO-7[B]` → `AO-7`
- `SO-124` → `HADES-R`
- `SO-125` → `HADES-ICM`

## Data Sources

- TLE data: https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle
- Frequency info: Stored locally in `frequencies.json`
- Activity status: https://www.amsat.org/status/api/v1/ (see `amsat_status.py`)
