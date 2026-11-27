"""
surfex_emission_records.py

Write into a SURFEX FA PGD file the metadata records that SURFEX needs to
switch its chemical emissions on (CCH_EMIS = 'AGGR').

Why this is needed
------------------
`create_emission_date.py` only appends the raw 2D fields `X001E_<name>`.
SURFEX (`init_surf_atmn.F90`) only calls `CH_INIT_EMISSION_n` when the
record `SFX.CH_EMIS` is true, and `CH_INIT_EMISSION_n` then reads:

    SFX.CH_EMIS         logical   must be .TRUE.
    SFX.CH_EMIS_OPT     string    'AGGR'
    SFX.EMISFILE_NBR    integer   total number of 2D emission fields
    SFX.EMISPEC_NBR     integer   number of emitted species
    SFX.EMISNAMEnnn     string    species name (matches the AGREGATION names
                                  of ChemAeroSURFEX.nam)
    SFX.EMISAREAnnn     string    'ALL' / 'LAN' / 'SEA'
    SFX.EMISNBTnnn      integer   number of emission times
    SFX.EMISTIMESnnn    integer() emission times in seconds (>= 0)

These are what the SURFEX PGD program writes (`writesurf_ch_emisn.F90`,
`write_pgd_surf_atmn.F90`).  In a SURFEX FA file with LFAGMAP they are plain
int64 LFI articles with no header: integer and logical = 1 word, string =
NCAR_FILES = 40 ASCII codes padded with blanks.  The 2D fields are read with
FACILE_NOEXTZ, so the (compressed) fields written by epygram are fine.

Usage
-----
    python3 surfex_emission_records.py PGD_aer.fa BC_em BC_bb OC_em OC_bb SO2_bb SO2_em
    python3 surfex_emission_records.py PGD_aer.fa --check        # list what is there

or from Python:  write_emission_records(path, ['BC_em', ...])

Needs the epygram LFI interface (LFI4py).
"""
import sys
import numpy as np
import epygram

NCAR_FILES = 40            # length of SURFEX character records (modd_data_cover_par)
PREFIX = 'SFX.'            # CPREFIX1D of the SURFEX FA driver
PREFIX2D = 'X'             # CPREFIX2D: 2D field 'X' + 'NNN' (time index) + name


def _lfi4py():
    try:
        from epygram.formats.LFI import LFI4py
        return LFI4py
    except Exception:
        import LFI4py  # noqa
        return LFI4py


def _words_int(values):
    return np.atleast_1d(np.asarray(values, dtype=np.int64))


def _words_str(text):
    text = str(text)[:NCAR_FILES].ljust(NCAR_FILES)
    return np.array([ord(c) for c in text], dtype=np.int64)


def _open(path, mode):
    return epygram.open(path, mode, fmt='LFI')


def _names(r):
    return set(str(y[0] if isinstance(y, tuple) else y) for y in r.listfields())


def _put(r, LF, name, words, existing):
    """Write (or replace) one plain int64 article."""
    if name in existing:
        LF.wlfisup(r._unit, name)
    LF.wlfiecr(r._unit, name, len(words), words)
    existing.add(name)


def read_record(r, name):
    LF = _lfi4py()
    length = LF.wlfinfo(r._unit, name)[0]
    return np.asarray(LF.wlfilec(r._unit, name, length, True)).astype('int64')


def check_records(path, species=None):
    """Print the emission records found in `path` and return True if they are consistent."""
    r = _open(path, 'r')
    try:
        names = _names(r)
        ok = True

        def show(n, as_str=False):
            nonlocal ok
            if PREFIX + n not in names:
                print('  %-18s ABSENT' % n)
                ok = False
                return None
            w = read_record(r, PREFIX + n)
            val = ''.join(chr(c) for c in w).strip() if as_str else w.tolist()
            print('  %-18s %s' % (n, val))
            return val

        print('Emission records in', path)
        flag = show('CH_EMIS')
        ok &= bool(flag and flag[0] == 1)
        opt = show('CH_EMIS_OPT', True)
        ok &= (opt == 'AGGR')
        nfile = show('EMISFILE_NBR')
        nspec = show('EMISPEC_NBR')
        if nspec:
            for j in range(1, nspec[0] + 1):
                nm = show('EMISNAME%03d' % j, True)
                show('EMISAREA%03d' % j, True)
                nbt = show('EMISNBT%03d' % j)
                show('EMISTIMES%03d' % j)
                if nm:
                    nt = nbt[0] if nbt else 0
                    for t in range(1, nt + 1):
                        f = '%s%03dE_%s' % (PREFIX2D, t, nm)
                        if f not in names:
                            print('  %-18s ABSENT (2D field)' % f)
                            ok = False
        if species:
            for s in species:
                if 'X001E_' + s not in names:
                    print('  X001E_%s ABSENT (2D field)' % s)
                    ok = False
        print('=> consistent' if ok else '=> INCOMPLETE')
        return ok
    finally:
        r.close()


def write_emission_records(path, species, area='ALL', times=None, option='AGGR'):
    """
    Add the SURFEX emission metadata records to `path` (modified in place).

    species : list of species names; the 2D fields 'X00<t>E_<name>' must already be in the file.
    area    : 'ALL' (default), 'LAN' or 'SEA' (same for all species).
    times   : dict name -> list of emission times in seconds (default: one time, 0 s).
    """
    LF = _lfi4py()
    times = times or {}
    r = _open(path, 'a')
    try:
        names = _names(r)
        existing = set(names)
        missing = ['X%03dE_%s' % (t, s) for s in species
                   for t in range(1, len(times.get(s, [0])) + 1)
                   if 'X%03dE_%s' % (t, s) not in names]
        if missing:
            raise RuntimeError('2D emission fields missing in %s: %s' % (path, missing))
        if len(set(species)) != len(species):
            raise RuntimeError('duplicate species names: %s' % species)
        if max(len(s) for s in species) > 12:
            raise RuntimeError('species names are truncated to 12 characters by SURFEX')

        ntot = sum(len(times.get(s, [0])) for s in species)
        _put(r, LF, PREFIX + 'CH_EMIS', _words_int(1), existing)
        _put(r, LF, PREFIX + 'CH_EMIS_OPT', _words_str(option), existing)
        _put(r, LF, PREFIX + 'EMISFILE_NBR', _words_int(ntot), existing)
        _put(r, LF, PREFIX + 'EMISPEC_NBR', _words_int(len(species)), existing)
        for j, s in enumerate(species, 1):
            tt = times.get(s, [0])
            _put(r, LF, '%sEMISNAME%03d' % (PREFIX, j), _words_str(s), existing)
            _put(r, LF, '%sEMISAREA%03d' % (PREFIX, j), _words_str(area), existing)
            _put(r, LF, '%sEMISNBT%03d' % (PREFIX, j), _words_int(len(tt)), existing)
            _put(r, LF, '%sEMISTIMES%03d' % (PREFIX, j), _words_int(tt), existing)
    finally:
        r.close()
    return check_records(path, species)


if __name__ == '__main__':
    epygram.init_env()
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    if sys.argv[2] == '--check':
        sys.exit(0 if check_records(sys.argv[1]) else 1)
    sys.exit(0 if write_emission_records(sys.argv[1], sys.argv[2:]) else 1)
