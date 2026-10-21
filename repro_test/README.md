# repro_test

Reproducibility test suite for IAL runs (launched via `param_*` scripts such
as `param_Eclis`). Each *case* is a self-contained copy of a launch config
plus a reference `NODE.001_01` log to diff future runs against.

## Layout

```
repro_test/
├── bin/
│   ├── diff_NODE                 # NODE.001_01 spectral/gridpoint-norm comparator (also standalone)
│   ├── diff_netcdf               # netCDF variable comparator
│   └── diff_fa_grib             # FA / GRIB field comparator (epygram)
├── lib/
│   ├── paths.py                 # where a run's live outputs sit (imported by the scripts)
│   └── common.py                # case-file parsing, running the bin/diff_* tools
├── cases/<name>/
│   ├── case.yaml                 # optional notes/description
│   ├── node_diff_args            # optional: extra diff_NODE flags for this case
│   ├── netcdf_vars               # optional: netCDF field tags to compare
│   ├── fa_grib_files            # optional: FA/GRIB output filenames to compare
│   └── launch/                   # param_Eclis + namelists + xml needed to launch
├── references/<name>/
│   ├── NODE.001_01               # the log this case is checked against
│   ├── netcdf/<tag>.nc           # netCDF fields this case is checked against
│   └── fa_grib/<filename>       # FA/GRIB files this case is checked against
├── results/<run_id>/vs-*_<ts>/    # gitignored: per-compare detail files (SUMMARY.txt, NODE.txt, ...)
└── .runs/<name>/                 # gitignored: scratch working dir used to launch (see run_test.py)
```

`METRIC_NOTES.md` — open design questions for the norm-comparison metric.

Convention: everywhere, `<name>` is the case's folder name (also its
`EXPID` when launched) -- there's no separate ID to keep in sync.

## Adding a case

1. `mkdir -p cases/<name>/launch` and drop in `param_Eclis` + the namelists
   / xml it needs (i.e. everything you'd otherwise put in the directory you
   `cd` into before running `./param_Eclis`).
2. Put the log you want to check future runs against at
   `references/<name>/NODE.001_01`.
3. Optionally write a couple of notes in `cases/<name>/case.yaml`.

## Running a case

```
./run_test.py <name>              # copies cases/<name>/launch -> .runs/<name>, launches param_Eclis
```

This submits the job (an async cluster job via mtool/sbatch), then waits
until the run is done — either a `last_NODE.001_01` marker appears in the
directory above `rundir/` (the reliable signal), or `rundir/NODE.001_01`
stops changing for a few polls — and calls `compare_test.py`. Once the run
has finished, `compare_test.py` reads `last_NODE.001_01` if `rundir/` is
already gone. With `--no-wait` it just submits and prints the command to
run later.

The run's outputs are read **in place** — nothing is copied. `lib/paths.py`
resolves where they are (`<GROUP>` and `<INIDATE>` come from the run's
`param_Eclis`, `<run_id>` = the `EXPID`):

| what | where it's read from |
|---|---|
| NODE.001_01 | `$HOME/relances/<GROUP>/<run_id>/rundir/NODE.001_01` |
| FA/GRIB `<fname>` (per `cases/<name>/fa_grib_files`) | `$HOME/relances/<GROUP>/<run_id>/rundir/<fname>` |
| netCDF `<tag>` (per `cases/<name>/netcdf_vars`) | `$HOME/relances/<GROUP>/<run_id>/iox_keep/<INIDATE>/*_arpsfx_<tag>_*.nc` |

Set `$REPRO_RUN_BASE` to override the `$HOME/relances` prefix (e.g. a
local mount of belenos). Run `compare_test.py` on a host that can see
that tree.

`./run_all.py` does this for every case under `cases/`.

## Testing a new executable (or any single override), keeping everything else fixed

Use `--set KEY=VALUE` to patch one `param_Eclis` variable (e.g. `pack=`,
the executable path) for the run, and `--variant <tag>` so it runs under a
distinct `EXPID` instead of colliding with the baseline:

```
./run_test.py <name> --variant v7.5 --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
```

Nothing in `cases/<name>/launch/` is modified -- the override is applied to
the copy in `.runs/<name>__v7.5/` only. To run this across several/all
cases with the same new executable:

```
./run_all.py --variant v7.5 --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
```

Once the jobs finish:

```
./compare_test.py <name> --variant v7.5      # or: ./compare_all.py --variant v7.5
```

A variant is always compared against its base case's **existing**
reference (`references/<name>/NODE.001_01`) -- the point is checking the
new executable still reproduces the known-good result, not recording a new
one.

### `--repro`: check the executable two ways at once

`--repro` (needs `--variant`) launches a **second, identical** run under
`<name>__<tag>__rep` and, once both finish, does both checks:

```
./run_test.py <name> --variant v7.5 --set pack=/home/.../arome_v7.5.../ --repro
```

Exemple, test the bit-repro of the default executable with different number of tasks. 
```
 ./run_test.py 07_NFR25_full_new_nml  --variant bit_repro --repro --repro-set NODE_ARP=4
```


| check | what | tolerance |
|---|---|---|
| **[1/2] bit-reproducible** | `<tag>` vs `<tag>__rep` — does the executable give the same answer run-to-run? | bit-exact (`--rtol 0 --atol 0 --atol-frac 0 --gpnorms '*'`, netCDF/FA-GRIB `--rel-max-diff 0`) |
| **[2/2] vs reference** | `<tag>` vs `references/<name>/` — does it still match the known-good result? | the case's normal tolerances (`node_diff_args`, `--rel-max-diff` default) |

Before comparing, both runs are checked for their **completion marker**
(`last_NODE.001_01`, the directory above `rundir/` — see `lib/paths.py`):
this confirms each one actually reached the end of the forecast, rather
than `wait_for_node()`'s fallback inference ("`NODE.001_01` stopped
changing for a while", which a crashed or stalled run can also produce). A
missing marker prints `reached end : v7.5=yes   v7.5__rep=NO` in the
summary and downgrades a would-be `PASS` to `???` (never hides a real
`FAIL`).

`run_test.py` exits `0` only if both pass, `1` if either FAILs, `2` if
either could not run (including: a run's completion marker is missing).
Add `--repro-set KEY=VALUE` to also vary something in the `__rep` run
(e.g. `--repro-set NODE_ARP=3` for a different MPI decomposition — a
stronger reproducibility test). `--no-compare` submits and waits without
comparing; `--no-wait` just submits and prints the two `compare_test.py`
commands.

Standalone, against an already-finished pair:

```
./compare_test.py <name> --variant v7.5 --against v7.5__rep    # [1/2]
./compare_test.py <name> --variant v7.5                        # [2/2]
```

`--against <tag2>` also works on `compare_netcdf.py` / `compare_fa_grib.py`
/ `compare_all.py`.

## Comparing

```
./compare_test.py <name>          # NODE.001_01 + (if configured) netCDF + FA/GRIB
```

Always runs `bin/diff_NODE` (the run's live `NODE.001_01` vs the
reference); then, when the case has a `cases/<name>/netcdf_vars` and/or
`cases/<name>/fa_grib_files` list, it also runs `compare_netcdf.py` /
`compare_fa_grib.py`. Overall exit code: `0` → `PASS`, `1` → `FAIL` (out of
tolerance / structural mismatch), `2` → `???` (some comparison couldn't
run — missing file, nothing to compare).

**Output.** The terminal shows one `PASS`/`FAIL`/`???` line per thing, then
a short per-section breakdown; on a failure the offending rows (flagged
values, `WARNING`, structural mismatch) are echoed inline. `-v` / `--verbose`
streams the full diff tables too. Every invocation writes one directory of
detail files:

```
results/<run_id>/vs-reference_<ts>/        # normal run
results/<run_id>/vs-<against>_<ts>/        # --against / --repro
    SUMMARY.txt        verdict + section breakdown
    NODE.txt           full diff_NODE report
    netcdf/<entry>.txt
    fa_grib/<file>.txt
```

So a `--repro` run leaves two clearly-named dirs side by side:
`vs-<tag>__rep_<ts>/` (the bit-repro check) and `vs-reference_<ts>/`.

Extra flags after `--` go to `diff_NODE` only, e.g.:

```
./compare_test.py <name> -- --rtol 1e-8 --max-nstep 12
```

Flags you always want for a case can live in `cases/<name>/node_diff_args`
(whitespace-separated, `#` comments, quotes respected), e.g. a line
`--rtol 1e-10` or `--preset arome-lam`.

`./compare_all.py` runs this for every case whose run has produced a
NODE.001_01, skipping the rest, and prints a summary.

### FA / GRIB output

```
./compare_fa_grib.py <name> [--variant <tag>] [--maps] [-- diff_fa_grib options]
```

(standalone `compare_fa_grib.py` needs `--maps` to draw maps; via
`compare_test.py` / `run_test.py` they are **on by default** — `--no-maps`
to skip.)

Files to compare are listed one per line in `cases/<name>/fa_grib_files`
(`#` comments ok). Each entry is a whole FA or GRIB file; `bin/diff_fa_grib`
opens it with epygram and iterates over **every field inside**, reporting
the same metrics as `diff_netcdf` (max abs diff, RMS abs diff, RMS diff
relative to the reference field's own RMS; spectral fields are converted to
gridpoint space first). Reference at `references/<name>/fa_grib/<filename>`;
the run's file is read in place from its rundir (see `lib/paths.py`).
Exit codes as elsewhere: `0` PASS, `1` FAIL (a field's relative RMS diff
exceeds `--rel-max-diff`, default `1e-4`), other → `???`. Also usable
standalone: `bin/diff_fa_grib ref.fa exp.fa [--fields A,B] [--rel-max-diff 1e-4]`.

**Difference maps.** For every flagged field an **`exp − ref` map** PNG is
written to `results/<run_id>/vs-*/fa_grib/<filename>.maps/` — automatically
when run via `compare_test.py` / `run_test.py` (`--no-maps` to skip), or
with `compare_fa_grib.py --maps` / `bin/diff_fa_grib --plot-dir DIR`
standalone. One map per field by default (`--plot-layout diff`: projected
map with coastlines via cartopy, diverging colours centred on 0, clipped at
the 99.5th percentile of |Δ| with an `×` on the worst cell);
`--plot-layout panels` gives a `ref | exp | exp−ref` triptych. `--plot-when
all` maps every compared field; `--plot-max N` caps the count (default 50).
Needs matplotlib (warns + skips if absent); cartopy optional.

## `bin/diff_NODE` (also usable standalone)

Reworked comparator -- run it directly on any two NODE files, no test suite
involved:

```
bin/diff_NODE a/NODE.001_01 b/NODE.001_01           # per-field summary + verdict
bin/diff_NODE a b --by-step                          # one row per (field, step)
bin/diff_NODE a b --full --flagged-only              # every out-of-tolerance value
bin/diff_NODE a b --json                             # machine-readable
bin/diff_NODE a b --growth --plot growth.png         # chaos-aware verdict + plot (B1)
```

- Compares **SPECTRAL NORMS** (`LOG(PREHYDS)` + `VORTICITY` / `DIVERGENCE`
  / `TEMPERATURE` / `KINETIC ENERGY`, AVE row by default, per-level with
  `--levels`), each tied to its forecast step and predictor/corrector
  half. Add gridpoint norms with `--gpnorms 'TKE,HUMI.SPECIFI'` or
  `--gpnorms '*'`. **SURFEX surface norms** (`SFX.<NAME> : AVERAGE MINIMUM
  MAXIMUM`, dumped at each surface-history write) are compared by default
  (`--sfx '*'`); narrow with `--sfx 'SFX.TS_WATER,SFX.T2M'` or turn off
  with `--sfx ''`.
- Matches values by `(field, step, half, level)`, not by file position --
  if the two runs produced a different number of norm blocks (one crashed
  / diverged early) that's a **STRUCTURAL MISMATCH → FAIL**, not a silent
  truncation.
- Flags a value when
  `|exp-ref| > max(--atol, --atol-frac·peak|ref|_field) + --rtol·|ref|`.
  The per-field absolute floor (`--atol-frac`, default `1e-9` of the
  field's own peak) keeps near-zero fields from tripping on noise.
- Exit `0` within tolerance, `1` out of tolerance / structural mismatch,
  `2` on error / nothing to compare.
- `--preset arome-lam|global`, `--fields-from FILE`, `--max-nstep N`.

### `--growth` — chaos-aware verdict (METRIC_NOTES.md B1)

For builds that are **not** meant to be bit-reproducible (new compiler,
`-O2`→`-O3`, new node type), a fixed `--rtol` on the last step fails every
legitimate build. `--growth` instead tracks, per spectral field, the
**digits of agreement** `d(n) = -log10( |Δ| / (|ref| + floor) )` across
forecast steps and judges the *shape*:

| flag | meaning |
|---|---|
| `d1<dmin` | diverges immediately → a real bug (wrong init, uninit memory, wrong constant), not chaos |
| `cliff` | digits fall off a cliff between two prints → a discrete event (branch taken differently) |
| `steep` | agreement decays faster than chaotic growth → instability / blow-up |

Knobs: `--growth-dmin` (default 8), `--growth-cliff` (4),
`--growth-slope-min` (−8 digits/decade); restrict the meaningful window
with `--max-nstep`. `--plot PATH` writes a PNG of `d(n)` vs step (needs
matplotlib; skipped with a warning if absent). Put `--growth` in a case's
`node_diff_args` and `compare_test.py` runs it that way and drops
`NODE_growth.png` next to `NODE.txt` in the report dir.

Still open (see `METRIC_NOTES.md`): the `--growth-slope-min` threshold
wants calibration against real past compiler bumps; B2 (a perturbed second
reference run as the noise envelope) is the principled successor.

## Current cases

- **NFR25_standard_namelist** -- ALADIN 49t1_clim1 with SURFEX, grid
  ALPX12, ERA5 LBCs, `INIDATE=ENDDATE=20200102`. Also tracks
  `hour_zg`/`hour_wap` netCDF fields.
  - NOTE: the current `references/.../NODE.001_01` (from `37_NFR_tuto_2`)
    has **no SPECTRAL NORMS** section, so `diff_NODE` finds nothing to
    compare against it. Replace it (via `save_reference.py` on a fresh run,
    or by hand) with a NODE from a config that prints spectral norms.
