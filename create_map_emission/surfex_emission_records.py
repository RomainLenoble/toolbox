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

In AROME, SURFEX does not read the file record by record: the I/O layer
(`modd_io_surf_aro.F90`, SURFEX_FIELD_BUF_READ_MISC1) first reads an INDEX made of
the records SFX._FBUF_SIZE / _FBUF_DIM1 / _FBUF_DIM2 / _FBUF_NAME (32 chars per
entry) / _FBUF_TYPE (2 chars) / _FBUF_MASK (16 chars), entries sorted by name,
and only the fields listed there exist for it (otherwise: "SURFEX FIELD
CACHE:<name> WAS NOT FOUND").  Every record written here is therefore also
registered in that index (scalars N0/L0/C0, EMISTIMES N1, 2D fields E_<name> as
type X2 with mask FULL, DIM1 = number of grid points, DIM2 = number of times).

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


IDX_NAME, IDX_TYPE, IDX_MASK = 32, 2, 16


def _str_from_words(w):
    return ''.join(chr(c) for c in w)


def read_index(r):
    """Return the SURFEX field index as a list of dicts (name, type, mask, d1, d2)."""
    n = int(read_record(r, PREFIX + '_FBUF_SIZE')[0])
    d1 = read_record(r, PREFIX + '_FBUF_DIM1')
    d2 = read_record(r, PREFIX + '_FBUF_DIM2')
    nm = read_record(r, PREFIX + '_FBUF_NAME')
    ty = read_record(r, PREFIX + '_FBUF_TYPE')
    mk = read_record(r, PREFIX + '_FBUF_MASK')
    out = []
    for i in range(n):
        out.append(dict(name=_str_from_words(nm[i * IDX_NAME:(i + 1) * IDX_NAME]).strip(),
                        type=_str_from_words(ty[i * IDX_TYPE:(i + 1) * IDX_TYPE]),
                        mask=_str_from_words(mk[i * IDX_MASK:(i + 1) * IDX_MASK]).strip(),
                        d1=int(d1[i]), d2=int(d2[i])))
    return out


def write_index(r, LF, entries, existing):
    """Rewrite the index records from `entries` (sorted by name, like SURFEX's QSORTC)."""
    entries = sorted(entries, key=lambda e: e['name'].ljust(IDX_NAME))
    names = [e['name'] for e in entries]
    if len(set(names)) != len(names):
        raise RuntimeError('duplicate names in the SURFEX index')
    cat = lambda f, w: np.array([ord(c) for e in entries for c in f(e).ljust(w)[:w]], dtype=np.int64)
    _put(r, LF, PREFIX + '_FBUF_DIM1', _words_int([e['d1'] for e in entries]), existing)
    _put(r, LF, PREFIX + '_FBUF_DIM2', _words_int([e['d2'] for e in entries]), existing)
    _put(r, LF, PREFIX + '_FBUF_NAME', cat(lambda e: e['name'], IDX_NAME), existing)
    _put(r, LF, PREFIX + '_FBUF_TYPE', cat(lambda e: e['type'], IDX_TYPE), existing)
    _put(r, LF, PREFIX + '_FBUF_MASK', cat(lambda e: e['mask'], IDX_MASK), existing)
    _put(r, LF, PREFIX + '_FBUF_SIZE', _words_int(len(entries)), existing)


def check_index(r, expected):
    """Check that the expected {name: type} entries are in the index; print and return ok."""
    idx = {e['name']: e for e in read_index(r)}
    ok = True
    for n, t in expected.items():
        if n not in idx or idx[n]['type'] != t:
            print('  index: %-18s MISSING or wrong type (%s)' % (n, idx.get(n, {}).get('type')))
            ok = False
    return ok


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
        # the AROME I/O layer only sees what is in the index
        expected = {'CH_EMIS': 'L0', 'CH_EMIS_OPT': 'C0', 'EMISFILE_NBR': 'N0', 'EMISPEC_NBR': 'N0'}
        if nspec:
            for j in range(1, nspec[0] + 1):
                expected.update({'EMISNAME%03d' % j: 'C0', 'EMISAREA%03d' % j: 'C0',
                                 'EMISNBT%03d' % j: 'N0', 'EMISTIMES%03d' % j: 'N1'})
                nm = read_record(r, '%sEMISNAME%03d' % (PREFIX, j)) if '%sEMISNAME%03d' % (PREFIX, j) in names else None
                if nm is not None:
                    expected['E_' + _str_from_words(nm).strip()] = 'X2'
        if PREFIX + '_FBUF_SIZE' in names:
            ok &= check_index(r, expected)
        else:
            print('  index records (_FBUF_*) ABSENT')
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

        npoints = [e['d1'] for e in read_index(r) if e['type'] == 'X1' and e['mask'] == 'FULL'][0]
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

        # register everything in the SURFEX field index
        entries = read_index(r)
        mine = {'CH_EMIS_OPT': ('C0', -1, -1), 'EMISFILE_NBR': ('N0', -1, -1), 'EMISPEC_NBR': ('N0', -1, -1)}
        for j, s in enumerate(species, 1):
            nt = len(times.get(s, [0]))
            mine.update({'EMISNAME%03d' % j: ('C0', -1, -1), 'EMISAREA%03d' % j: ('C0', -1, -1),
                         'EMISNBT%03d' % j: ('N0', -1, -1), 'EMISTIMES%03d' % j: ('N1', nt, -1),
                         'E_' + s: ('X2', npoints, nt)})
        entries = [e for e in entries if e['name'] not in mine]
        for n, (t, d1, d2) in mine.items():
            entries.append(dict(name=n, type=t, mask='FULL' if t == 'X2' else '', d1=d1, d2=d2))
        write_index(r, LF, entries, existing)
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
