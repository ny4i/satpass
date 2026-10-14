# SatPass - Amateur Radio Satellite Pass Predictor

Predict visible satellite passes over your location, with frequency information and calendar export.

## Features

- Predict passes for amateur radio satellites (ISS, SO-50, AO-73, etc.)
- Filter by minimum elevation angle
- Display times in local timezone or UTC
- Export to ICS calendar files with frequency info in notes
- Optional calendar reminders before each pass

## Quick Start

```bash
# Predict passes for the next 24 hours
./passes.sh --grid EL87pb --min-elev 10

# Export to calendar with 15-minute reminders
./passes.sh --grid EL87pb --min-elev 10 --ics passes.ics --ics-notify 15
```

## Installation

### Prerequisites

You need Python 3.9 or newer installed on your system.

---

### macOS

1. **Check if Python is installed:**
   ```bash
   python3 --version
   ```
   If not installed, install via Homebrew:
   ```bash
   brew install python3
   ```

2. **Download or clone this repository:**
   ```bash
   git clone https://github.com/yourusername/satpass.git
   cd satpass
   ```
   Or download and extract the ZIP file, then open Terminal and navigate to the folder:
   ```bash
   cd ~/Downloads/satpass
   ```

3. **Create the Python virtual environment:**
   ```bash
   python3 -m venv venv
   ```

4. **Install the required library:**
   ```bash
   venv/bin/pip install ephem
   ```

5. **Make the scripts executable:**
   ```bash
   chmod +x passes.sh update_frequencies.sh
   ```

6. **Test it:**
   ```bash
   ./passes.sh --grid EL87pb --min-elev 10
   ```

---

### Linux (Ubuntu/Debian)

1. **Install Python and venv:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-pip
   ```

2. **Download or clone this repository:**
   ```bash
   git clone https://github.com/yourusername/satpass.git
   cd satpass
   ```

3. **Create the Python virtual environment:**
   ```bash
   python3 -m venv venv
   ```

4. **Install the required library:**
   ```bash
   venv/bin/pip install ephem
   ```

5. **Make the scripts executable:**
   ```bash
   chmod +x passes.sh update_frequencies.sh
   ```

6. **Test it:**
   ```bash
   ./passes.sh --grid EL87pb --min-elev 10
   ```

---

### Windows

1. **Install Python:**
   - Download Python from https://www.python.org/downloads/
   - Run the installer
   - **IMPORTANT:** Check the box "Add Python to PATH" at the bottom of the installer
   - Click "Install Now"

2. **Download this repository:**
   - Click the green "Code" button on GitHub and select "Download ZIP"
   - Extract the ZIP file to a folder (e.g., `C:\Users\YourName\satpass`)

3. **Open Command Prompt:**
   - Press `Win + R`, type `cmd`, press Enter
   - Navigate to the satpass folder:
     ```cmd
     cd C:\Users\YourName\satpass
     ```

4. **Create the Python virtual environment:**
   ```cmd
   python -m venv venv
   ```

5. **Install the required library:**
   ```cmd
   venv\Scripts\pip install ephem
   ```

6. **Test it:**
   ```cmd
   venv\Scripts\python passes.py --grid EL87pb --min-elev 10
   ```

#### Windows Usage Notes

On Windows, instead of `./passes.sh`, run:
```cmd
venv\Scripts\python passes.py --grid EL87pb --min-elev 10
```

You can create a batch file `passes.bat` for convenience:
```batch
@echo off
%~dp0venv\Scripts\python %~dp0passes.py %*
```

Then run:
```cmd
passes.bat --grid EL87pb --min-elev 10
```

---

## Usage

### Basic Pass Prediction

```bash
./passes.sh --grid EL87pb --min-elev 10
```

Replace `EL87pb` with your Maidenhead grid square. You can find yours at: https://www.levinecentral.com/ham/grid_square.php

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--grid` | Your Maidenhead grid square (required) | - |
| `--elev` | Your ground elevation in meters | 0 |
| `--min-elev` | Minimum pass elevation in degrees | 10 |
| `--start` | Start time: "YYYY-MM-DD HH:MM" | now |
| `--hours` | Prediction window in hours | 24 |
| `--sats` | Satellite list file | satellites.txt |
| `--utc` | Display times in UTC | local time |
| `--ics FILE` | Export to ICS calendar file | - |
| `--ics-notify MIN` | Add reminder N minutes before pass | - |
| `--all` | Show all tracked satellites, not just active ones | - |
| `--active-hours N` | Lookback window for activity status | 48 |

### Examples

```bash
# Predict passes for next 48 hours
./passes.sh --grid EL87pb --min-elev 10 --hours 48

# Show only high-elevation passes (easier to work)
./passes.sh --grid EL87pb --min-elev 30

# Export to calendar with 10-minute reminders
./passes.sh --grid EL87pb --min-elev 10 --ics passes.ics --ics-notify 10

# Display times in UTC
./passes.sh --grid EL87pb --min-elev 10 --utc

# Start from a specific date/time
./passes.sh --grid EL87pb --min-elev 10 --start "2024-03-15 08:00"

# Show all tracked satellites, even ones with no recent activity
./passes.sh --grid EL87pb --min-elev 10 --all
```

### Activity Filtering

By default, only satellites with recent reported activity on the [AMSAT Live
OSCAR Satellite Status page](https://www.amsat.org/status/) are included —
the same blue "Sat/Mode Active" cells you'd otherwise check manually before
an event. This queries AMSAT's public status API directly (no scraping) and
looks back 48 hours by default (`--active-hours` to change). Pass `--all` to
predict passes for every satellite in `satellites.txt` regardless of recent
activity. If the status API is unreachable, the script warns and falls back
to showing everything.

### Understanding the Output

```
TIME (LOCAL)       SAT        AOS   MAX EL LOS     DUR
======================================================================
2024-03-15 09:28   SO-50      SSW    59.1° NNE     13m
```

- **TIME**: When the satellite rises above your horizon (AOS time)
- **SAT**: Satellite name
- **AOS**: Direction where satellite appears (Acquisition of Signal)
- **MAX EL**: Maximum elevation angle (higher = better)
- **LOS**: Direction where satellite sets (Loss of Signal)
- **DUR**: Pass duration in minutes

---

## Customizing Satellites

### Edit the Satellite List

Edit `satellites.txt` to add or remove satellites (one per line):

```
ISS-FM
AO-73
SO-50
```

Use AMSAT designations. Common satellites:
- `ISS-FM` - International Space Station FM repeater
- `SO-50` - Easy FM satellite for beginners
- `AO-73` - FUNcube-1, SSB/CW transponder
- `AO-7[B]` - Classic OSCAR 7, Mode B
- `RS-44` - Russian linear transponder
- `SO-124` - HADES-R FM repeater
- `SO-125` - HADES-ICM FM repeater

### Update Frequency Data

After adding satellites, update the frequency database:

```bash
./update_frequencies.sh
```

Then edit `frequencies.json` to fill in the frequency data for new satellites.

---

## Calendar Integration

### Export to ICS

```bash
./passes.sh --grid EL87pb --min-elev 10 --ics passes.ics --ics-notify 15
```

### Import the Calendar

- **Google Calendar**: Go to Settings → Import & Export → Import, select the .ics file
- **Apple Calendar**: Double-click the .ics file or File → Import
- **Outlook**: File → Open & Export → Import/Export → Import an iCalendar file

Each calendar event includes:
- Pass start and end times
- Maximum elevation
- AOS/LOS directions
- Frequency information (uplink, downlink, mode, tone)

---

## Troubleshooting

### "python3: command not found"

Python is not installed or not in your PATH. See installation instructions above.

### "No module named 'ephem'"

The virtual environment wasn't set up correctly. Run:
```bash
venv/bin/pip install ephem      # macOS/Linux
venv\Scripts\pip install ephem  # Windows
```

### "Permission denied" (macOS/Linux)

Make the scripts executable:
```bash
chmod +x passes.sh update_frequencies.sh
```

### "frequencies.json not found"

Run the frequency update script:
```bash
./update_frequencies.sh
```

### Satellite not found in TLE data

The satellite name in `satellites.txt` doesn't match Celestrak's naming. Check the name mapping in `passes.py` or use the exact Celestrak name.

---

## How It Works

1. Reads satellite list from `satellites.txt`
2. Fetches current TLE (orbital) data from Celestrak
3. Uses PyEphem to calculate when satellites are visible from your location
4. Filters passes by minimum elevation
5. Displays results and optionally exports to ICS

---

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE) for details.

## Credits

- TLE data from [Celestrak](https://celestrak.org/)
- Satellite status from [AMSAT](https://www.amsat.org/status/)
- Pass prediction using [PyEphem](https://rhodesmill.org/pyephem/)
