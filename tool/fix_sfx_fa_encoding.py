#!/usr/bin/env python3
"""
Convert the scalar SFX records of a SURFEX v8 FA file to the encoding expected
by SURFEX v9 (integers, logicals and strings stored as int64 instead of float64).

Symptom fixed: PREP aborts with 'GRIDTYPE "" NOT ACCEPTED AS INPUT FILE' or with
a zero-size buffer in FACILE_NOEXTZ when reading a PGD / restart written by v8.

The input file is never modified: it is copied to the output file first.

Usage:
    fix_sfx_fa_encoding.py PGD.fa PGD_fixed.fa
    fix_sfx_fa_encoding.py rst.sfx.fa rst.sfx_fixed.fa --set-bug 0

Requires epygram and falfilfa4py (python3 -I is fine).
"""
import argparse
import os
import shutil
import sys

import numpy as np
import epygram
from falfilfa4py import LFI


def lfi_open(path, state):
    unit = LFI.wlfiouv(path, state)
    return unit[0] if isinstance(unit, tuple) else unit


def lfi_records(unit):
    """Return {record name: (length, position)}."""
    records = {}
    while True:
        res = LFI.wlficas(unit, True)
        name = res[0].strip()
        if not name:
            break
        records[name] = (res[1], res[2])
    return records


def lfi_read(unit, name, length):
    res = LFI.wlfilec(unit, name, length, True)
    return np.asarray(res[0] if isinstance(res, tuple) else res)


def lfi_write(unit, name, values):
    """Replace record `name` by the int64 array `values`."""
    LFI.wlfisup(unit, name)
    LFI.wlfiecr(unit, name, len(values), np.asarray(values, dtype=np.int64))


def classify(path):
    """Return {record: 'int' | 'bool' | 'str'} for the SFX records to convert.

    The type comes from epygram, which knows the SURFEX type of each record name:
    real records (float64) are left untouched. SOILGRID* are reals that epygram
    wrongly reports as integers, so they are excluded.
    """
    resource = epygram.formats.resource(path, 'r')
    conv = {}
    for name in resource.listfields():
        if not name.startswith('SFX.') or name.startswith('SFX.SOILGRID'):
            continue
        try:
            dtype = str(resource.readfield(name).getdata().dtype)
        except (OverflowError, ValueError):
            # float-encoded strings cannot be decoded: OverflowError or
            # ValueError (chr() out of range) depending on the epygram version
            conv[name] = 'str'
            continue
        if dtype == 'int64':
            conv[name] = 'int'
        elif dtype == 'bool':
            conv[name] = 'bool'
    return conv


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('infile')
    parser.add_argument('outfile')
    parser.add_argument('--set-bug', type=int, default=None, metavar='N',
                        help='also set SFX.BUG to N. 0 makes SURFEX read patch fields '
                             'with the old XnnnVAR names (files without SFX.SPLIT_PATCH)')
    args = parser.parse_args()

    if os.path.abspath(args.infile) == os.path.abspath(args.outfile):
        sys.exit('input and output must differ')

    epygram.init_env()
    shutil.copyfile(args.infile, args.outfile)

    conv = classify(args.outfile)
    unit = lfi_open(args.outfile, 'OLD')
    records = lfi_records(unit)

    done = 0
    for name, kind in conv.items():
        if name not in records:
            continue
        words = lfi_read(unit, name, records[name][0])
        values = words.astype(np.int64).view(np.float64)
        if not np.all(np.isfinite(values)) or np.any(np.abs(values - np.round(values)) > 1e-9):
            print('skipped (not integral): %s' % name)
            continue
        new = np.round(values).astype(np.int64)
        if kind == 'bool':
            new = (new != 0).astype(np.int64)
        lfi_write(unit, name, new)
        done += 1

    if args.set_bug is not None:
        lfi_write(unit, 'SFX.BUG', [args.set_bug])

    LFI.wlfifer(unit, 'KEEP')
    print('%s: %d records rewritten%s' % (args.outfile, done,
          ', SFX.BUG=%d' % args.set_bug if args.set_bug is not None else ''))


if __name__ == '__main__':
    main()
