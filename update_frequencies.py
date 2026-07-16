#!/usr/bin/env python3
"""
Update frequencies.json with entries for all satellites in satellites.txt.
Creates template entries for satellites not already in the file.

With --fill, attempts to populate blank fields from the local
amateur-satellite-database (palewire) data files. Only blank fields are
written; existing curated values (notably tone and notes) are never
overwritten. A diff is shown and confirmation is required before writing.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path


MODE_SUFFIXES = ('-FM', '-SSB', '-CW', '-DIG', '-SSTV', '-APRS')


def parse_sat_name(sat):
    """Split a designation into (base_name, suffix) for crosswalk lookup.

    AO-7[B]  -> ('AO-7', 'B')
    ISS-FM   -> ('ISS', 'FM')
    SO-125   -> ('SO-125', None)
    """
    m = re.match(r'^(.+?)\[(\w+)\]$', sat)
    if m:
        return m.group(1), m.group(2)
    for suffix in MODE_SUFFIXES:
        if sat.endswith(suffix):
            return sat[:-len(suffix)], suffix[1:]
    return sat, None


def load_satnogs_index(satnogs_csv):
    """Build {alias_upper: norad_id} from satnogs.csv (name + names aliases)."""
    index = {}
    with open(satnogs_csv, newline='') as f:
        for row in csv.DictReader(f):
            try:
                norad = int(float(row['norad_cat_id']))
            except (ValueError, TypeError):
                continue
            aliases = [row['name']]
            if row.get('names'):
                aliases.extend(a.strip() for a in row['names'].split(','))
            for alias in aliases:
                key = alias.strip().upper()
                if key:
                    index.setdefault(key, norad)
    return index


def load_freq_rows(freq_csv):
    """Build {norad_id: [row, ...]} from amsat-active-frequencies.csv."""
    by_norad = {}
    with open(freq_csv, newline='') as f:
        for row in csv.DictReader(f):
            try:
                norad = int(row['norad_id'])
            except (ValueError, TypeError):
                continue
            by_norad.setdefault(norad, []).append(row)
    return by_norad


def filter_by_suffix(rows, suffix):
    if not suffix:
        return rows
    s = suffix.upper()
    out = []
    for r in rows:
        tokens = re.split(r'[\s/]+', r['mode'].upper())
        if s in tokens:
            out.append(r)
    return out


def select_row(rows, base_name, suffix):
    """Pick one frequency row. Returns (row, reason_if_none)."""
    candidates = filter_by_suffix(rows, suffix)
    if not candidates:
        return None, f'no rows matched suffix [{suffix}]' if suffix else 'no rows'
    for r in candidates:
        if r['name'].upper() == base_name.upper():
            return r, None
    if len(candidates) == 1:
        return candidates[0], None
    return None, f'{len(candidates)} candidate rows; manual disambiguation needed'


def extract_tone(mode_str):
    m = re.search(r'CTCSS\s*([\d.]+)\s*Hz', mode_str, re.IGNORECASE)
    return f'{m.group(1)} Hz' if m else None


def propose_fill(existing, csv_row, base_name):
    """Return {field: new_value} for blank fields we'd fill from csv_row."""
    proposed = {}
    if not existing.get('name'):
        proposed['name'] = csv_row['name'] or base_name
    if not existing.get('uplink') and csv_row['uplink']:
        proposed['uplink'] = csv_row['uplink']
    if not existing.get('downlink') and csv_row['downlink']:
        proposed['downlink'] = csv_row['downlink']
    if not existing.get('mode') and csv_row['mode']:
        proposed['mode'] = csv_row['mode']
    if not existing.get('tone'):
        tone = extract_tone(csv_row['mode'])
        if tone:
            proposed['tone'] = tone
    return proposed


def fill_from_palewire(freq_data, satellites, data_dir):
    satnogs_csv = data_dir / 'satnogs.csv'
    freq_csv = data_dir / 'amsat-active-frequencies.csv'
    if not satnogs_csv.exists() or not freq_csv.exists():
        print(f'ERROR: data files not found in {data_dir}', file=sys.stderr)
        print('Expected: satnogs.csv and amsat-active-frequencies.csv', file=sys.stderr)
        print('Clone https://github.com/palewire/amateur-satellite-database '
              'into this directory or pass --data-dir.', file=sys.stderr)
        sys.exit(2)

    satnogs = load_satnogs_index(satnogs_csv)
    by_norad = load_freq_rows(freq_csv)

    proposals = {}
    skipped = []

    for sat in satellites:
        existing = freq_data.get(sat, {})
        if existing.get('uplink') and existing.get('downlink'):
            continue
        base, suffix = parse_sat_name(sat)
        norad = satnogs.get(base.upper())
        if norad is None:
            skipped.append((sat, f'no NORAD ID for "{base}" in satnogs.csv'))
            continue
        rows = by_norad.get(norad, [])
        if not rows:
            skipped.append((sat, f'NORAD {norad} not in frequency CSV'))
            continue
        row, reason = select_row(rows, base, suffix)
        if row is None:
            skipped.append((sat, reason))
            continue
        proposal = propose_fill(existing, row, base)
        if proposal:
            proposals[sat] = (proposal, norad, row)

    return proposals, skipped


def show_diff(proposals):
    for sat, (proposal, norad, row) in proposals.items():
        print(f'\n  {sat}  (NORAD {norad}, source: "{row["name"]}")')
        for field, value in proposal.items():
            print(f'    {field}: "" -> {value!r}')
        if row.get('beacon'):
            print(f'    (FYI palewire beacon column: {row["beacon"]})')


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--fill', action='store_true',
                        help='Fill blank fields from amateur-satellite-database data')
    parser.add_argument('--yes', action='store_true',
                        help='Skip the confirmation prompt when --fill is used')
    parser.add_argument('--data-dir', default='amateur-satellite-database/data',
                        help='Directory containing satnogs.csv and '
                             'amsat-active-frequencies.csv '
                             '(default: amateur-satellite-database/data)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    sats_file = script_dir / 'satellites.txt'
    freq_file = script_dir / 'frequencies.json'
    data_dir = (script_dir / args.data_dir).resolve()

    if not sats_file.exists():
        print(f'ERROR: {sats_file} not found', file=sys.stderr)
        sys.exit(1)

    with open(sats_file) as f:
        satellites = [line.strip() for line in f if line.strip()]
    if not satellites:
        print('ERROR: No satellites in satellites.txt', file=sys.stderr)
        sys.exit(1)

    if freq_file.exists():
        with open(freq_file) as f:
            freq_data = json.load(f)
        print(f'Loaded {len(freq_data)} existing entries from frequencies.json')
    else:
        freq_data = {}
        print('Creating new frequencies.json')

    added = []
    for sat in satellites:
        if sat not in freq_data:
            freq_data[sat] = {
                'name': '', 'mode': '', 'uplink': '', 'downlink': '',
                'tone': None, 'notes': '',
            }
            added.append(sat)

    orphaned = [sat for sat in freq_data if sat not in satellites]

    write_file = True
    if args.fill:
        proposals, skipped = fill_from_palewire(freq_data, satellites, data_dir)
        if not proposals:
            print('\nNo blank fields could be filled from palewire data.')
        else:
            print(f'\nProposed updates for {len(proposals)} satellite(s):')
            show_diff(proposals)
            if not args.yes:
                try:
                    resp = input('\nApply these changes? [y/N] ').strip().lower()
                except EOFError:
                    resp = ''
                if resp != 'y':
                    print('Aborted; no changes written.')
                    write_file = False
            if write_file:
                for sat, (proposal, _, _) in proposals.items():
                    freq_data[sat].update(proposal)
        if skipped:
            print('\nSkipped (could not match):')
            for sat, reason in skipped:
                print(f'  - {sat}: {reason}')

    if write_file:
        with open(freq_file, 'w') as f:
            json.dump(freq_data, f, indent=2)
            f.write('\n')

    print(f'\nSatellites in list: {len(satellites)}')
    print(f'Entries in frequencies.json: {len(freq_data)}')
    if added:
        print(f'\nAdded {len(added)} new template entries:')
        for sat in added:
            print(f'  - {sat}')
        if not args.fill:
            print('\nRun with --fill to auto-populate blanks from '
                  'amateur-satellite-database data.')
    if orphaned:
        print('\nOrphaned entries (not in satellites.txt):')
        for sat in orphaned:
            print(f'  - {sat}')

    incomplete = [s for s in satellites
                  if not freq_data.get(s, {}).get('uplink')
                  or not freq_data.get(s, {}).get('downlink')]
    if incomplete:
        print('\nIncomplete entries (missing uplink/downlink):')
        for s in incomplete:
            print(f'  - {s}')

    needs_review = [s for s in satellites
                    if '*' in (freq_data.get(s, {}).get('mode') or '')]
    if needs_review:
        print('\nEntries with raw palewire mode strings (manual cleanup recommended):')
        for s in needs_review:
            print(f'  - {s}: {freq_data[s]["mode"]!r}')


if __name__ == '__main__':
    main()
