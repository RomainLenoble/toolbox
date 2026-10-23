#!/usr/bin/env python3
"""
Fill nearly empty patches of a SURFEX restart (FA) from donor patches.

SURFEX stores the patch fields of a restart as X<patch><name><layer> (e.g. X006TG3).
A patch that is almost absent on the source grid forces PREP to extrapolate it from
a handful of points over every target point, which is extremely slow. This copies,
for every field of each patch, the donor patch values at the points where the patch
is undefined and the donor is defined.

X<patch>PATCH (the patch fraction itself) is never modified.

The input file is never modified: it is copied to the output file first.

Usage:
    fill_sfx_patch.py rst.sfx_fixed.fa rst.sfx_filled.fa --fill 6:4 --fill 3:2
    fill_sfx_patch.py rst.sfx_filled.fa rst.sfx_vfilled.fa --vertical WG --vertical WGI

--constant NAME=VALUE: for every patch, where X<patch>NAME is undefined set VALUE (for
fields that only matter where something exists, e.g. the snow albedo ASN_VEG where
there is no snow). Fully undefined fields (e.g. LAI of bare soil) are left alone.

--vertical NAME: for every patch, where layer k of NAME (X<patch>NAME<k>) is undefined
and layer k-1 is defined, copy layer k-1. Deep soil layers are only defined where the
source soil is deep enough; a target with deeper soil would otherwise need them
extrapolated horizontally from far-away points.

Requires epygram (python3 -I is fine).
"""
import argparse
import os
import re
import shutil
import sys

import numpy as np
import epygram


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('infile')
    parser.add_argument('outfile')
    parser.add_argument('--fill', action='append', default=[], metavar='PATCH:DONOR',
                        help='patch to fill and the patch to copy from; can be repeated')
    parser.add_argument('--vertical', action='append', default=[], metavar='NAME',
                        help='fill undefined deep layers from the layer above; can be repeated')
    parser.add_argument('--constant', action='append', default=[], metavar='NAME=VALUE',
                        help='set VALUE where X<patch>NAME is undefined; can be repeated')
    parser.add_argument('--limit', type=int, default=None, help='only treat the first N fields (test)')
    args = parser.parse_args()

    if os.path.abspath(args.infile) == os.path.abspath(args.outfile):
        sys.exit('input and output must differ')

    epygram.init_env()
    shutil.copyfile(args.infile, args.outfile)

    resource = epygram.formats.resource(args.outfile, 'a')
    for pair in args.fill:
        patch, donor = (int(i) for i in pair.split(':'))
        prefix = 'X%03d' % patch
        names = [n for n in resource.listfields()
                 if n.startswith(prefix) and not n.startswith(prefix + 'PATCH')]
        if args.limit:
            names = names[:args.limit]

        filled = 0
        for name in names:
            donor_name = 'X%03d%s' % (donor, name[len(prefix):])
            field = resource.readfield(name)
            donor_field = resource.readfield(donor_name)
            data = np.ma.masked_greater(np.ma.filled(field.getdata(), 1e20), 1e19)
            donor_data = np.ma.masked_greater(np.ma.filled(donor_field.getdata(), 1e20), 1e19)
            todo = data.mask & ~np.ma.getmaskarray(donor_data)
            if not todo.any():
                continue
            new = np.ma.filled(data, 1e20)
            new[todo] = np.ma.filled(donor_data, 1e20)[todo]
            # plain array, not masked: undefined points must stay exactly XUNDEF (1e20)
            field.setdata(new)
            resource.delfield(name)
            resource.writefield(field)
            filled += 1
        print('patch %d from patch %d: %d/%d fields filled' % (patch, donor, filled, len(names)))
    for name in args.vertical:
        for patch in range(1, 13):
            prefix = 'X%03d%s' % (patch, name)
            layers = sorted(int(n[len(prefix):]) for n in resource.listfields()
                            if re.fullmatch(re.escape(prefix) + r'\d+', n))
            filled = 0
            previous = None
            for layer in layers:
                field = resource.readfield('%s%d' % (prefix, layer))
                data = np.asarray(np.ma.filled(field.getdata(), 1e20))
                if previous is not None:
                    todo = (data > 1e19) & (previous < 1e19)
                    if todo.any():
                        data = data.copy()
                        data[todo] = previous[todo]
                        field.setdata(data)
                        resource.delfield('%s%d' % (prefix, layer))
                        resource.writefield(field)
                        filled += 1
                previous = data
            print('%s: %d/%d layers filled from the layer above' % (prefix, filled, len(layers)))
    for item in args.constant:
        name, value = item.split('=')
        for patch in range(1, 13):
            fname = 'X%03d%s' % (patch, name)
            field = resource.readfield(fname)
            data = np.asarray(np.ma.filled(field.getdata(), 1e20))
            undefined = data > 1e19
            if undefined.all() or not undefined.any():
                print('%s: left alone (%d valid)' % (fname, int((~undefined).sum())))
                continue
            data = data.copy()
            data[undefined] = float(value)
            field.setdata(data)
            resource.delfield(fname)
            resource.writefield(field)
            print('%s: %d points set to %s' % (fname, int(undefined.sum()), value))
    resource.close()
    print(args.outfile)


if __name__ == '__main__':
    main()
