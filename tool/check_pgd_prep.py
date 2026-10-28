#!/usr/bin/env python3
"""
Check that a SURFEX PGD file and a PREP file describe the same tiles.

The model reads the PREP fields of a tile on the points where the PGD has that tile. A PREP made
with another PGD leaves fields undefined (1e20) on the points the PGD has and the PREP does not,
which makes the model fail (NaN, "Incoherent grid point albedo"...).

For each tile, the points where its fraction is > 0 in the PGD are compared with the points where
a PREP field of that tile is defined:
    nature  any SFX.PATCHP<n>         town   SFX.TROOF1
    water   SFX.TS_WATER              sea    SFX.SST

Usage:
    check_pgd_prep.py PGD.fa PREP.fa

Requires epygram (python3 -I is fine). Exit status 1 if a tile does not match.
"""
import sys

import numpy as np
import epygram

XUNDEF = 1e19


def read(res, name):
    return np.ma.getdata(res.readfield(name).getdata()).astype(float)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    epygram.init_env()
    pgd = epygram.formats.resource(sys.argv[1], 'r')
    prep = epygram.formats.resource(sys.argv[2], 'r')
    names = set(prep.listfields())

    nature = np.zeros(read(pgd, 'SFX.FRAC_NATURE').shape, bool)
    for p in range(1, 13):
        if 'SFX.PATCHP%d' % p in names:
            nature |= read(prep, 'SFX.PATCHP%d' % p) < XUNDEF
    tiles = [('nature', 'SFX.FRAC_NATURE', nature),
             ('town', 'SFX.FRAC_TOWN', read(prep, 'SFX.TROOF1') < XUNDEF),
             ('water', 'SFX.FRAC_WATER', read(prep, 'SFX.TS_WATER') < XUNDEF),
             ('sea', 'SFX.FRAC_SEA', read(prep, 'SFX.SST') < XUNDEF)]

    status = 0
    for tile, frac_name, in_prep in tiles:
        frac = read(pgd, frac_name)
        in_pgd = (frac < XUNDEF) & (frac > 0)
        missing = int((in_pgd & ~in_prep).sum())
        extra = int((~in_pgd & in_prep).sum())
        print('%-7s PGD %7d points, PREP %7d points, in PGD but not in PREP: %d, in PREP but not in PGD: %d' %
              (tile, in_pgd.sum(), in_prep.sum(), missing, extra))
        if missing or extra:
            status = 1
    print('OK: same tiles' if status == 0 else 'MISMATCH: the PREP was not made with this PGD')
    sys.exit(status)


if __name__ == '__main__':
    main()
