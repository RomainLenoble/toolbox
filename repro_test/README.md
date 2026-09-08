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
├── cases/<name>/
│   ├── case.yaml                 # optional notes/description
│   ├── node_diff_args            # optional: extra diff_NODE flags for this case
│   ├── netcdf_vars               # optional: netCDF field tags to fetch/compare
│   ├── fa_grib_files            # optional: FA/GRIB output filenames to compare
│   └── launch/                   # param_Eclis + namelists + xml needed to launch
├── references/<name>/
│   ├── NODE.001_01               # the log this case is checked against
│   ├── netcdf/<tag>.nc           # netCDF fields this case is checked against
│   └── fa_grib/<filename>       # FA/GRIB files this case is checked against
├── results/<name>/               # gitignored: fresh NODE.001_01, netcdf/, diff reports, launch.log
└── .runs/<name>/                 # gitignored: scratch working dir used to launch (see run_test.sh)
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
./run_test.sh <name>              # copies cases/<name>/launch -> .runs/<name>, launches param_Eclis
```

This only *submits* the job (it's an async cluster job via mtool/sbatch) --
it doesn't wait for completion. Once the run has finished, fetch
`~/relance/TEST_SUITE/<name>/NODE.001_01` from the cluster (`TEST_SUITE` is
the `GROUP` set in every case's `param_Eclis`, `<name>` is the `EXPID`) and
put it at `results/<name>/NODE.001_01` locally.

`./run_all.sh` does this for every case under `cases/`.

## Testing a new executable (or any single override), keeping everything else fixed

Use `--set KEY=VALUE` to patch one `param_Eclis` variable (e.g. `pack=`,
the executable path) for the run, and `--variant <tag>` so it runs under a
distinct `EXPID` instead of colliding with the baseline:

```
./run_test.sh <name> --variant v7.5 --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
```

Nothing in `cases/<name>/launch/` is modified -- the override is applied to
the copy in `.runs/<name>__v7.5/` only. To run this across several/all
cases with the same new executable:

```
./run_all.sh --variant v7.5 --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
```

Once the jobs finish, fetch each run's
`~/relance/TEST_SUITE/<name>__v7.5/NODE.001_01` from the cluster and put it
at `results/<name>__v7.5/NODE.001_01` locally, then:

```
./compare_test.sh <name> --variant v7.5      # or: ./compare_all.sh --variant v7.5
```

A variant is always compared against its base case's **existing**
reference (`references/<name>/NODE.001_01`) -- the point is checking the
new executable still reproduces the known-good result, not recording a new
one.

## Comparing

```
./compare_test.sh <name>          # NODE.001_01 + (if configured) netCDF + FA/GRIB
```

Always runs `bin/diff_NODE` (results vs references `NODE.001_01`), saving
its report to `results/<name>/diff_<timestamp>.txt`. Then, when the case
has a `cases/<name>/netcdf_vars` and/or `cases/<name>/fa_grib_files` list,
it also runs `compare_netcdf.sh` / `compare_fa_grib.sh` for that case (with
their defaults). Overall exit code: `0` → `PASS` (everything within
tolerance), `1` → `FAIL` (some comparison out of tolerance / structural
mismatch), anything else → `???` (some comparison couldn't run).

Extra flags after `--` go to `diff_NODE` only, e.g.:

```
./compare_test.sh <name> -- --rtol 1e-8 --max-nstep 12
```

Flags you always want for a case can live in `cases/<name>/node_diff_args`
(whitespace-separated, `#` comments, quotes respected), e.g. a line
`--rtol 1e-10` or `--preset arome-lam`.

`./compare_all.sh` runs this for every case that already has a
`results/<name>/NODE.001_01`, skipping the rest, and prints a summary.

### FA / GRIB output

```
./compare_fa_grib.sh <name> [--variant <tag>] [-- diff_fa_grib options]
```

Files to compare are listed one per line in `cases/<name>/fa_grib_files`
(`#` comments ok). Each entry is a whole FA or GRIB file; `bin/diff_fa_grib`
opens it with epygram and iterates over **every field inside**, reporting
the same metrics as `diff_netcdf` (max abs diff, RMS abs diff, RMS diff
relative to the reference field's own RMS; spectral fields are converted to
gridpoint space first). Reference at `references/<name>/fa_grib/<filename>`,
fresh copy at `results/<run_id>/fa_grib/<filename>`. Exit codes as
elsewhere: `0` PASS, `1` FAIL (a field's relative RMS diff exceeds
`--rel-max-diff`, default `1e-4`), other → `???`. Also usable standalone:
`bin/diff_fa_grib ref.fa exp.fa [--fields A,B] [--rel-max-diff 1e-4]`.

## `bin/diff_NODE` (also usable standalone)

Reworked comparator -- run it directly on any two NODE files, no test suite
involved:

```
bin/diff_NODE a/NODE.001_01 b/NODE.001_01           # per-field summary + verdict
bin/diff_NODE a b --by-step                          # one row per (field, step)
bin/diff_NODE a b --full --flagged-only              # every out-of-tolerance value
bin/diff_NODE a b --json                             # machine-readable
```

- Compares **SPECTRAL NORMS** (`LOG(PREHYDS)` + `VORTICITY` / `DIVERGENCE`
  / `TEMPERATURE` / `KINETIC ENERGY`, AVE row by default, per-level with
  `--levels`), each tied to its forecast step and predictor/corrector
  half. Add gridpoint norms with `--gpnorms 'TKE,HUMI.SPECIFI'` or
  `--gpnorms '*'`; global observation Jo is compared when present.
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

**The relative-diff metric is still a work in progress** for the
not-bit-reproducible case (chaotic growth makes late-step relative diffs
large for legitimate builds). See `METRIC_NOTES.md` for the options and
open questions.

## Current cases

- **NFR25_standard_namelist** -- ALADIN 49t1_clim1 with SURFEX, grid
  ALPX12, ERA5 LBCs, `INIDATE=ENDDATE=20200102`. Also tracks
  `hour_zg`/`hour_wap` netCDF fields.
  - NOTE: the current `references/.../NODE.001_01` (from `37_NFR_tuto_2`)
    has **no SPECTRAL NORMS** section, so `diff_NODE` finds nothing to
    compare against it. Replace it (via `save_reference.sh` on a fresh run,
    or by hand) with a NODE from a config that prints spectral norms.
