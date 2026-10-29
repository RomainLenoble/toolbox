#!/usr/bin/env python3
"""
Fill nearly empty patches of a SURFEX restart (FA) from donor patches.

SURFEX stores the patch fields of a restart as X<patch><name><layer> (e.g. X006TG3) or,
in other versions, as SFX.<name><layer>P<patch> (e.g. SFX.TG3P6); the scheme is detected
from the file. In the text below X<patch>NAME stands for either.
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


class Names:
    """Field names of the patch fields, whatever the naming scheme of the restart."""

    def __init__(self, listfields):
        self.all = listfields
        self.sfx = any(re.fullmatch(r'SFX\.TG1P\d+', n) for n in listfields)

    def field(self, patch, name):
        return 'SFX.%sP%d' % (name, patch) if self.sfx else 'X%03d%s' % (patch, name)

    def of_patch(self, patch):
        """All the fields of a patch, except its fraction, as {suffix: field name}."""
        if self.sfx:
            out = {}
            for n in self.all:
                m = re.fullmatch(r'SFX\.(.+)P%d' % patch, n)
                if m and not m.group(1).startswith('PATCH'):
                    out[m.group(1)] = n
            return out
        prefix = 'X%03d' % patch
        return {n[len(prefix):]: n for n in self.all
                if n.startswith(prefix) and not n.startswith(prefix + 'PATCH')}

    def layers(self, patch, name):
        """Names of the layers of NAME for a patch, in layer order."""
        found = []
        for n in self.all:
            if self.sfx:
                m = re.fullmatch(r'SFX\.%s(\d+)P%d' % (re.escape(name), patch), n)
            else:
                m = re.fullmatch(r'X%03d%s(\d+)' % (patch, re.escape(name)), n)
            if m:
                found.append((int(m.group(1)), n))
        return [n for _, n in sorted(found)]


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
    names_of = Names(resource.listfields())
    print('naming scheme: %s' % ('SFX.<name>P<patch>' if names_of.sfx else 'X<patch><name>'))
    for pair in args.fill:
        patch, donor = (int(i) for i in pair.split(':'))
        donor_fields = names_of.of_patch(donor)
        names = names_of.of_patch(patch)
        if args.limit:
            names = dict(list(names.items())[:args.limit])

        filled = 0
        for suffix, name in names.items():
            donor_name = donor_fields.get(suffix)
            if donor_name is None:
                continue
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
            prefix = names_of.field(patch, name)
            layers = names_of.layers(patch, name)
            filled = 0
            previous = None
            for fname in layers:
                field = resource.readfield(fname)
                data = np.asarray(np.ma.filled(field.getdata(), 1e20))
                if previous is not None:
                    todo = (data > 1e19) & (previous < 1e19)
                    if todo.any():
                        data = data.copy()
                        data[todo] = previous[todo]
                        field.setdata(data)
                        resource.delfield(fname)
                        resource.writefield(field)
                        filled += 1
                previous = data
            print('%s: %d/%d layers filled from the layer above' % (prefix, filled, len(layers)))
    for item in args.constant:
        name, value = item.split('=')
        for patch in range(1, 13):
            fname = names_of.field(patch, name)
            if fname not in names_of.all:
                print('%s: not in the file' % fname)
                continue
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
