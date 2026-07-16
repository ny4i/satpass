#!/usr/bin/env python3
"""
Satellite pass predictor for amateur radio.
Reads satellite list from satellites.txt, fetches TLE data, predicts passes.
Optionally exports to ICS calendar files with frequency information.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ephem

# AMSAT name -> Celestrak name mapping
NAME_MAP = {
    "SO-124": "HADES-R",
    "SO-125": "HADES-ICM",
}


def grid_to_latlon(grid: str) -> tuple[float, float]:
    """Convert Maidenhead grid square to lat/lon."""
    grid = grid.upper()
    if len(grid) < 4:
        raise ValueError(f"Grid must be at least 4 characters: {grid}")

    lon = (ord(grid[0]) - ord('A')) * 20 - 180
    lat = (ord(grid[1]) - ord('A')) * 10 - 90
    lon += (ord(grid[2]) - ord('0')) * 2
    lat += (ord(grid[3]) - ord('0'))

    if len(grid) >= 6:
        lon += (ord(grid[4].upper()) - ord('A')) * (2 / 24)
        lat += (ord(grid[5].upper()) - ord('A')) * (1 / 24)
        lon += 1 / 24  # Center of subsquare
        lat += 0.5 / 24
    else:
        lon += 1  # Center of square
        lat += 0.5

    return lat, lon


def fetch_tle_data() -> str:
    """Fetch amateur satellite TLE data from Celestrak."""
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode('utf-8')


def parse_tle_data(tle_text: str) -> dict[str, tuple[str, str, str]]:
    """Parse TLE text into dict of name -> (line0, line1, line2)."""
    lines = [l.strip() for l in tle_text.strip().split('\n') if l.strip()]
    satellites = {}
    i = 0
    while i < len(lines) - 2:
        if lines[i+1].startswith('1 ') and lines[i+2].startswith('2 '):
            name = lines[i].strip()
            satellites[name] = (lines[i], lines[i+1], lines[i+2])
            i += 3
        else:
            i += 1
    return satellites


def find_satellite(name: str, tle_dict: dict) -> tuple[str, str, str] | None:
    """Find satellite TLE by AMSAT name, handling name variations."""
    search_name = NAME_MAP.get(name, name)
    search_name = search_name.replace("-FM", "").split("[")[0]

    for tle_name, tle_data in tle_dict.items():
        tle_upper = tle_name.upper()
        search_upper = search_name.upper()
        if tle_upper.startswith(search_upper) or f"({search_upper})" in tle_upper:
            return tle_data
    return None


def predict_passes(sat: ephem.EarthSatellite, observer: ephem.Observer,
                   start: datetime, end: datetime, min_elev: float) -> list[dict]:
    """Predict satellite passes between start and end times."""
    passes = []
    observer.date = ephem.Date(start)
    end_ephem = ephem.Date(end)

    while observer.date < end_ephem:
        try:
            info = observer.next_pass(sat)
            if info[0] is None:
                break

            rise_time, rise_az, max_time, max_elev, set_time, set_az = info

            if rise_time > end_ephem:
                break

            max_elev_deg = float(max_elev) * 180 / 3.14159
            if max_elev_deg >= min_elev:
                passes.append({
                    'rise_time': ephem.Date(rise_time).datetime(),
                    'rise_az': float(rise_az) * 180 / 3.14159,
                    'max_time': ephem.Date(max_time).datetime(),
                    'max_elev': max_elev_deg,
                    'set_time': ephem.Date(set_time).datetime(),
                    'set_az': float(set_az) * 180 / 3.14159,
                })

            observer.date = set_time + ephem.minute
        except Exception:
            break

    return passes


def az_to_dir(az: float) -> str:
    """Convert azimuth to compass direction."""
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = int((az + 11.25) / 22.5) % 16
    return dirs[idx]


def load_frequencies(script_dir: Path) -> tuple[dict, bool]:
    """Load satellite frequency data from JSON file. Returns (data, file_exists)."""
    freq_file = script_dir / "frequencies.json"
    if freq_file.exists():
        with open(freq_file) as f:
            return json.load(f), True
    return {}, False


def validate_frequencies(sat_names: list[str], freq_data: dict) -> list[str]:
    """Check which satellites are missing frequency data. Returns list of missing satellites."""
    missing = []
    for sat in sat_names:
        entry = freq_data.get(sat, {})
        if not entry.get("uplink") or not entry.get("downlink"):
            missing.append(sat)
    return missing


def format_freq_info(sat_name: str, freq_data: dict) -> str:
    """Format frequency information for calendar notes."""
    info = freq_data.get(sat_name, {})
    if not info:
        return ""

    lines = []
    if info.get("name"):
        lines.append(f"Name: {info['name']}")
    if info.get("mode"):
        lines.append(f"Mode: {info['mode']}")
    if info.get("uplink"):
        lines.append(f"Uplink: {info['uplink']} MHz")
    if info.get("downlink"):
        lines.append(f"Downlink: {info['downlink']} MHz")
    if info.get("tone"):
        lines.append(f"Tone: {info['tone']}")
    if info.get("notes"):
        lines.append(f"Notes: {info['notes']}")

    return "\n".join(lines)


def fold_ics_line(line: str, max_octets: int = 75) -> str:
    """Fold ICS line to max_octets bytes per RFC 5545."""
    line_bytes = line.encode('utf-8')
    if len(line_bytes) <= max_octets:
        return line

    result = []
    # First line: up to max_octets bytes
    pos = 0
    while pos < max_octets and pos < len(line):
        # Don't split in middle of multi-byte character
        char_bytes = len(line[pos].encode('utf-8'))
        if len(line[:pos + 1].encode('utf-8')) > max_octets:
            break
        pos += 1
    result.append(line[:pos])
    line = line[pos:]

    # Continuation lines: space + up to (max_octets - 1) bytes
    while line:
        pos = 0
        # Account for the leading space (1 byte)
        while pos < len(line):
            chunk = " " + line[:pos + 1]
            if len(chunk.encode('utf-8')) > max_octets:
                break
            pos += 1
        if pos == 0:
            pos = 1  # At least one character
        result.append(" " + line[:pos])
        line = line[pos:]

    return "\r\n".join(result)


def generate_ics(passes: list[dict], freq_data: dict, grid: str, tz_offset: timedelta, notify_minutes: int = None) -> str:
    """Generate ICS calendar content for all passes."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SatPass//Amateur Radio Satellite Passes//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for p in passes:
        sat = p['satellite']
        freq_info = format_freq_info(sat, freq_data)

        # Build description
        desc_parts = [
            f"Satellite: {sat}",
            f"Max Elevation: {p['max_elev']:.1f}°",
            f"AOS: {az_to_dir(p['rise_az'])} ({p['rise_az']:.0f}°)",
            f"LOS: {az_to_dir(p['set_az'])} ({p['set_az']:.0f}°)",
            f"Grid: {grid}",
            "",
        ]
        if freq_info:
            desc_parts.append("--- FREQUENCIES ---")
            desc_parts.extend(freq_info.split("\n"))

        description = "\\n".join(desc_parts)

        # Times in UTC for ICS
        dtstart = p['rise_time'].strftime("%Y%m%dT%H%M%SZ")
        dtend = p['set_time'].strftime("%Y%m%dT%H%M%SZ")
        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        # Unique ID
        uid = f"{dtstart}-{sat.replace(' ', '')}@satpass"

        # Summary with local time for readability
        local_time = p['rise_time'] + tz_offset
        summary = f"{sat} Pass ({p['max_elev']:.0f}° max)"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
        ])

        # Add reminder alarm if requested
        if notify_minutes:
            lines.extend([
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Satellite pass: {sat}",
                f"TRIGGER:-PT{notify_minutes}M",
                "END:VALARM",
            ])

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    # Fold long lines per RFC 5545
    return "\r\n".join(fold_ics_line(line) for line in lines)


def main():
    parser = argparse.ArgumentParser(description='Predict amateur satellite passes')
    parser.add_argument('--grid', required=True, help='Maidenhead grid square (e.g., EL87pb)')
    parser.add_argument('--elev', type=float, default=0, help='Ground elevation in meters')
    parser.add_argument('--min-elev', type=float, default=10, help='Minimum pass elevation in degrees')
    parser.add_argument('--start', help='Start time (YYYY-MM-DD HH:MM), default: now')
    parser.add_argument('--hours', type=float, default=24, help='Hours to predict (default: 24)')
    parser.add_argument('--sats', default='satellites.txt', help='Satellite list file')
    parser.add_argument('--utc', action='store_true', help='Display times in UTC (default: local time)')
    parser.add_argument('--ics', metavar='FILE', help='Export passes to ICS calendar file')
    parser.add_argument('--ics-notify', type=int, metavar='MIN', help='Add calendar reminder N minutes before each pass')
    parser.add_argument('--json', action='store_true', help='Output passes as JSON to stdout (diagnostics go to stderr)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent

    # In JSON mode, keep stdout clean for the JSON array; send diagnostics to stderr
    info = sys.stderr if args.json else sys.stdout

    # Parse location
    try:
        lat, lon = grid_to_latlon(args.grid)
        print(f"Location: {args.grid} ({lat:.4f}°N, {lon:.4f}°W)", file=info)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine timezone for display
    if args.utc:
        tz_offset = timedelta(0)
        tz_name = "UTC"
    else:
        tz_offset = datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)
        tz_hours = tz_offset.total_seconds() / 3600
        tz_name = f"LOCAL (UTC{tz_hours:+.0f})"

    # Parse times
    if args.start:
        start_local = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
        start_utc = start_local - tz_offset
    else:
        start_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        start_local = start_utc + tz_offset
    end_utc = start_utc + timedelta(hours=args.hours)
    end_local = start_local + timedelta(hours=args.hours)

    print(f"Window: {start_local.strftime('%Y-%m-%d %H:%M')} to {end_local.strftime('%Y-%m-%d %H:%M')} {tz_name}", file=info)
    print(f"Min elevation: {args.min_elev}°", file=info)
    print(file=info)

    # Setup observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = args.elev

    # Load satellite list
    sats_file = script_dir / args.sats if not os.path.isabs(args.sats) else Path(args.sats)
    try:
        with open(sats_file) as f:
            sat_names = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"ERROR: {sats_file} not found", file=sys.stderr)
        sys.exit(1)

    # Load frequency data
    freq_data, freq_file_exists = load_frequencies(script_dir)
    if not freq_file_exists:
        print("WARNING: frequencies.json not found - ICS notes will lack frequency data", file=info)
        print("         Run: ./venv/bin/python3 update_frequencies.py", file=info)
        print(file=info)
    else:
        missing_freq = validate_frequencies(sat_names, freq_data)
        if missing_freq:
            print(f"WARNING: {len(missing_freq)} satellite(s) missing frequency data:", file=info)
            for sat in missing_freq:
                print(f"         - {sat}", file=info)
            print("         Run: ./venv/bin/python3 update_frequencies.py", file=info)
            print(file=info)

    # Fetch TLE data
    print("Fetching TLE data...", file=info)
    try:
        tle_text = fetch_tle_data()
        tle_dict = parse_tle_data(tle_text)
    except Exception as e:
        print(f"ERROR: Failed to fetch TLE data: {e}", file=sys.stderr)
        sys.exit(1)

    # Predict passes for each satellite
    all_passes = []
    for sat_name in sat_names:
        tle = find_satellite(sat_name, tle_dict)
        if not tle:
            print(f"  NOT FOUND: {sat_name}", file=info)
            continue

        try:
            sat = ephem.readtle(*tle)
            passes = predict_passes(sat, observer, start_utc, end_utc, args.min_elev)
            for p in passes:
                p['satellite'] = sat_name
            all_passes.extend(passes)
            print(f"  {sat_name}: {len(passes)} passes", file=info)
        except Exception as e:
            print(f"  ERROR {sat_name}: {e}", file=info)

    # Sort by rise time
    all_passes.sort(key=lambda p: p['rise_time'])

    # Output results
    if args.json:
        records = []
        for p in all_passes:
            duration = (p['set_time'] - p['rise_time']).seconds // 60
            display_time = p['rise_time'] + tz_offset
            records.append({
                "datetime": display_time.strftime('%Y-%m-%d %H:%M'),
                "sat": p['satellite'],
                "aos": az_to_dir(p['rise_az']),
                "max_el": round(p['max_elev'], 1),
                "los": az_to_dir(p['set_az']),
                "dur_min": duration,
            })
        print(json.dumps(records, indent=2))
    else:
        print()
        print("=" * 70)
        tz_label = "UTC" if args.utc else "LOCAL"
        print(f"{'TIME (' + tz_label + ')':<18} {'SAT':<10} {'AOS':<5} {'MAX EL':>6} {'LOS':<5} {'DUR':>5}")
        print("=" * 70)

        for p in all_passes:
            duration = (p['set_time'] - p['rise_time']).seconds // 60
            display_time = p['rise_time'] + tz_offset
            print(f"{display_time.strftime('%Y-%m-%d %H:%M'):<18} "
                  f"{p['satellite']:<10} "
                  f"{az_to_dir(p['rise_az']):<5} "
                  f"{p['max_elev']:>5.1f}° "
                  f"{az_to_dir(p['set_az']):<5} "
                  f"{duration:>4}m")

        print("=" * 70)
        print(f"Total: {len(all_passes)} passes")

    # Export to ICS if requested
    if args.ics:
        ics_content = generate_ics(all_passes, freq_data, args.grid, tz_offset, args.ics_notify)
        with open(args.ics, 'w') as f:
            f.write(ics_content)
        print(f"\nExported to: {args.ics}", file=info)


if __name__ == '__main__':
    main()
