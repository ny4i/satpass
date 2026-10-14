#!/usr/bin/env python3
"""Shared satellite designation parsing helpers."""

import re

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
