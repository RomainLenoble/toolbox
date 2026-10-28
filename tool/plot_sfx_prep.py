#!/usr/bin/env python3
"""
Plot the main fields of a SURFEX PREP (FA) file to check it by eye.

The ISBA fields of a PREP are stored per patch: SFX.<NAME><layer>P<patch> (e.g. SFX.TG1P7) for the
soil profiles, SFX.<NAME>P<patch> for the others (LAIP7, PATCHP7, ASN_VEGP3...).
Written to the output directory (PNG):
  patches.png    the fraction of each patch
  <NAME>.png     fraction-weighted mean over the patches of the first layer of NAME
                 (default TG1 WG1 WGI1 LAI), with the patch-weighted standard deviation across
                 patches in the right panel
  undefined.png  points where a patch is present (fraction > 0) but a field is undefined (1e20),
                 the points that make the model fail at start
  snow.png       the snow reservoir and albedo of the patches that have snow, if any
and a check on the standard output: values outside the usual physical ranges.

Usage:
    plot_sfx_prep.py PREP.fa outdir
    plot_sfx_prep.py PREP.fa outdir --fields TG1 WG1 TG14 LAI --patch 7

--patch N only plots the fields of patch N instead of the weighted mean.

Requires epygram and matplotlib (python3 -I is fine).
"""
import argparse
import os
import sys

import numpy as np
import epygram
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

XUNDEF = 1e19
NPATCH = 12
PATCH_NAMES = ['bare soil', 'rock', 'permanent snow', 'broadleaf', 'needleleaf', 'tropical',
               'C3 crops', 'C4 crops', 'irrigated', 'C3 grass', 'C4 grass', 'irrig. crops']
LIMITS = {'TG': (200., 340.), 'WG': (0., 1.), 'WGI': (0., 1.), 'LAI': (0., 15.),
          'ASN_VEG': (0.3, 1.), 'PATCH': (0., 1.)}


def readfield(res, name, crop):
    """Field as a masked array (undefined points masked), cropped to the C+I zone."""
    data = np.ma.getdata(res.readfield(name).getdata()).astype(float)
    data = data[:crop[0], :crop[1]]
    return np.ma.masked_where((data >= XUNDEF) | np.isnan(data), data)


def draw(ax, data, title, vmin=None, vmax=None, cmap='viridis'):
    img = ax.imshow(data, origin='lower', cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(img, ax=ax, shrink=0.8)


def split_name(field):
    """'TG14' -> ('TG', '14'), 'LAI' -> ('LAI', '')"""
    base = field.rstrip('0123456789')
    return base, field[len(base):]


def patch_name(field, patch):
    base, layer = split_name(field)
    return 'SFX.%s%sP%d' % (base, layer, patch)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('prep')
    parser.add_argument('outdir')
    parser.add_argument('--fields', nargs='+', default=['TG1', 'WG1', 'WGI1', 'LAI'])
    parser.add_argument('--patch', type=int, default=None, help='plot this patch instead of the weighted mean')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    epygram.init_env()
    res = epygram.formats.resource(args.prep, 'r')
    names = set(res.listfields())
    nx = int(np.ma.getdata(res.readfield('SFX.IMAX').getdata()))
    ny = int(np.ma.getdata(res.readfield('SFX.JMAX').getdata()))
    crop = (ny, nx)

    # patch fractions
    frac = np.ma.array([readfield(res, 'SFX.PATCHP%d' % p, crop) for p in range(1, NPATCH + 1)])
    fracz = np.ma.filled(frac, 0.)
    total = fracz.sum(0)
    present = total > 0
    print('points with nature: %d, patch fraction sum min %.6f max %.6f' %
          (present.sum(), total[present].min(), total[present].max()))

    fig, axes = plt.subplots(3, 4, figsize=(18, 11))
    for p, ax in enumerate(axes.ravel()):
        draw(ax, frac[p], 'patch %d %s (%d pts)' % (p + 1, PATCH_NAMES[p], (fracz[p] > 0).sum()), 0, 1)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, 'patches.png'), dpi=90)
    plt.close(fig)

    # weighted mean of the requested fields
    problems = []
    for field in args.fields:
        base, _ = split_name(field)
        if args.patch:
            name = patch_name(field, args.patch)
            if name not in names:
                print('%s not in the file' % name)
                continue
            fig, ax = plt.subplots(1, 1, figsize=(8, 7))
            draw(ax, readfield(res, name, crop), name)
        else:
            vals = []
            for p in range(1, NPATCH + 1):
                name = patch_name(field, p)
                vals.append(readfield(res, name, crop) if name in names
                            else np.ma.masked_all((ny, nx)))
            vals = np.ma.array(vals)
            ok = ~np.ma.getmaskarray(vals) & (fracz > 0)
            w = np.where(ok, fracz, 0.)
            wsum = w.sum(0)
            safe = np.where(wsum > 0, wsum, 1.)
            v = np.ma.filled(vals, 0.)
            mean = (w * v).sum(0) / safe
            std = np.sqrt(np.maximum((w * (v - mean) ** 2).sum(0) / safe, 0.))
            mean = np.ma.masked_where(wsum == 0, mean)
            std = np.ma.masked_where(wsum == 0, std)
            fig, axes = plt.subplots(1, 2, figsize=(16, 7))
            draw(axes[0], mean, '%s, weighted mean over patches' % field)
            draw(axes[1], std, '%s, weighted std across patches' % field, cmap='magma')
            # undefined where a patch is present, and out-of-range values
            for p in range(1, NPATCH + 1):
                if patch_name(field, p) not in names or not (fracz[p - 1] > 0).any():
                    continue
                miss = int(((fracz[p - 1] > 0) & np.ma.getmaskarray(vals[p - 1])).sum())
                if miss:
                    problems.append((field, p, miss))
            lim = LIMITS.get(base)
            if lim:
                bad = ok & ((v < lim[0]) | (v > lim[1]))
                if bad.any():
                    print('%s: %d patch values outside [%g, %g], min %.3f max %.3f' %
                          (field, bad.sum(), lim[0], lim[1], v[bad].min(), v[bad].max()))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, '%s.png' % field), dpi=90)
        plt.close(fig)

    print('patch present but field undefined:')
    for field, p, miss in problems:
        # a vegetated field can be legitimately undefined on bare soil, rock and snow (patches 1 to 3)
        flag = '' if p > 3 or split_name(field)[0] not in ('LAI',) else ' (expected)'
        print('  %-6s patch %2d: %d points%s' % (field, p, miss, flag))

    if problems:
        fig, ax = plt.subplots(1, 1, figsize=(9, 7))
        count = np.zeros((ny, nx))
        for field, p, miss in problems:
            if p > 3 or split_name(field)[0] != 'LAI':
                name = patch_name(field, p)
                count += (fracz[p - 1] > 0) & np.ma.getmaskarray(readfield(res, name, crop))
        draw(ax, np.ma.masked_where(count == 0, count), 'fields undefined where a patch is present', cmap='Reds')
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, 'undefined.png'), dpi=90)
        plt.close(fig)

    # snow
    asn = [(p, readfield(res, 'SFX.ASN_VEGP%d' % p, crop)) for p in range(1, NPATCH + 1)
           if 'SFX.ASN_VEGP%d' % p in names]
    snow = [(p, a) for p, a in asn if a.count() > 0]
    if snow:
        fig, axes = plt.subplots(1, len(snow), figsize=(8 * len(snow), 7), squeeze=False)
        for ax, (p, a) in zip(axes[0], snow):
            draw(ax, a, 'ASN_VEG patch %d (%d pts), min %.3f max %.3f' % (p, a.count(), a.min(), a.max()))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, 'snow.png'), dpi=90)
        plt.close(fig)
        for p, a in snow:
            for var in ('WSN_VEG1', 'RSN_VEG1', 'HSN_VEG1', 'SAG_VEG1'):
                name = 'SFX.%sP%d' % (var, p)
                if name in names:
                    x = readfield(res, name, crop)
                    print('patch %d %-9s defined %d min %.3f max %.3f' %
                          (p, var, x.count(), x.min() if x.count() else np.nan, x.max() if x.count() else np.nan))
    print('plots in', args.outdir)


if __name__ == '__main__':
    main()
