#!/usr/bin/env python3
"""
Update frequencies.json with entries for all satellites in satellites.txt.
Creates template entries for satellites not already in the file.
"""

import json
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    sats_file = script_dir / "satellites.txt"
    freq_file = script_dir / "frequencies.json"

    # Load satellite list
    if not sats_file.exists():
        print(f"ERROR: {sats_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(sats_file) as f:
        satellites = [line.strip() for line in f if line.strip()]

    if not satellites:
        print("ERROR: No satellites in satellites.txt", file=sys.stderr)
        sys.exit(1)

    # Load existing frequency data
    if freq_file.exists():
        with open(freq_file) as f:
            freq_data = json.load(f)
        print(f"Loaded {len(freq_data)} existing entries from frequencies.json")
    else:
        freq_data = {}
        print("Creating new frequencies.json")

    # Check for missing entries and add templates
    added = []
    for sat in satellites:
        if sat not in freq_data:
            freq_data[sat] = {
                "name": "",
                "mode": "",
                "uplink": "",
                "downlink": "",
                "tone": None,
                "notes": ""
            }
            added.append(sat)

    # Check for orphaned entries (in freq_data but not in satellites.txt)
    orphaned = [sat for sat in freq_data if sat not in satellites]

    # Write updated file
    with open(freq_file, 'w') as f:
        json.dump(freq_data, f, indent=2)
        f.write('\n')

    # Report results
    print(f"\nSatellites in list: {len(satellites)}")
    print(f"Entries in frequencies.json: {len(freq_data)}")

    if added:
        print(f"\nAdded {len(added)} new template entries:")
        for sat in added:
            print(f"  - {sat}")
        print("\nPlease edit frequencies.json to fill in the frequency data.")

    if orphaned:
        print(f"\nOrphaned entries (not in satellites.txt):")
        for sat in orphaned:
            print(f"  - {sat}")
        print("Consider removing these or adding them to satellites.txt")

    # Validate existing entries
    incomplete = []
    for sat in satellites:
        entry = freq_data.get(sat, {})
        if not entry.get("uplink") or not entry.get("downlink"):
            incomplete.append(sat)

    if incomplete:
        print(f"\nIncomplete entries (missing uplink/downlink):")
        for sat in incomplete:
            print(f"  - {sat}")


if __name__ == '__main__':
    main()
