#!/usr/bin/env python3
"""
Set a constant value in some fields of a SURFEX FA file, on the points where they are defined.

Undefined points (1e20) stay undefined. The input file is never modified: it is copied to the
output file first. Used to test which field of a PREP makes the model fail, by giving it the
value the previous (working) PREP had.

Usage:
    set_sfx_field.py PREP.fa PREP_test.fa SFX.QCANYON=0.0015
    set_sfx_field.py PREP.fa PREP_test.fa SFX.QCANYON=0.0015 SFX.PSOLD=101325

Requires epygram (python3 -I is fine).
"""
import os
import shutil
import sys

import numpy as np
import epygram


def main():
    if len(sys.argv) < 4 or not all('=' in a for a in sys.argv[3:]):
        sys.exit(__doc__)
    infile, outfile = sys.argv[1:3]
    if os.path.abspath(infile) == os.path.abspath(outfile):
        sys.exit('input and output must differ')

    epygram.init_env()
    shutil.copyfile(infile, outfile)
    resource = epygram.formats.resource(outfile, 'a')
    for item in sys.argv[3:]:
        name, value = item.split('=')
        field = resource.readfield(name)
        data = np.asarray(np.ma.filled(field.getdata(), 1e20)).astype(float)
        defined = data < 1e19
        before = (float(data[defined].min()), float(data[defined].max())) if defined.any() else None
        data[defined] = float(value)
        # plain array, not masked: undefined points must stay exactly 1e20
        field.setdata(data)
        resource.delfield(name)
        resource.writefield(field)
        print('%s: %d points set to %s (was %s)' % (name, defined.sum(), value, before))
    resource.close()
    print(outfile)


if __name__ == '__main__':
    main()
