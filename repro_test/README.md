# repro_test

Reproducibility test suite for IAL runs (launched via `param_*` scripts such
as `param_Eclis`). Each *case* is a self-contained copy of a launch config
plus a reference `NODE.001_01` log to diff future runs against.

## Layout

```
repro_test/
├── bin/diff_NODE                 # the norms/Jo comparator (yours, copied in)
├── cases/<name>/
│   ├── case.yaml                 # optional notes/description
│   └── launch/                   # param_Eclis + namelists + xml needed to launch
├── references/<name>/NODE.001_01 # the log this case is checked against
├── results/<name>/               # gitignored: fresh NODE.001_01 + diff reports land here
└── .runs/<name>/                 # gitignored: scratch working dir used to launch (see run_test.sh)
```

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
it doesn't wait for completion. Once the run has finished, fetch its
`NODE.001_01` and put it at `results/<name>/NODE.001_01` (however you
already fetch results back locally, e.g. the `last_NODE.001_01` your sync
step drops next to the run).

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

Once the jobs finish, put each run's `NODE.001_01` at
`results/<name>__v7.5/NODE.001_01`, then:

```
./compare_test.sh <name> --variant v7.5      # or: ./compare_all.sh --variant v7.5
```

A variant is always compared against its base case's **existing**
reference (`references/<name>/NODE.001_01`) -- the point is checking the
new executable still reproduces the known-good result, not recording a new
one.

## Comparing

```
./compare_test.sh <name>          # diffs results/<name>/NODE.001_01 vs references/<name>/NODE.001_01
```

Prints `diff_NODE`'s norms/Jo report, saves it to
`results/<name>/diff_<timestamp>.txt`, and prints `PASS`/`FAIL`. Note that
`diff_NODE` itself always exits 0 -- pass/fail here is decided by whether
its report contains a `WARNING` line (a norm or Jo diff outside the allowed
relative threshold, `--norm-max-diff`/`--jo-max-diff`, default 5%/3%). Pass
extra `diff_NODE` flags after `--`, e.g.:

```
./compare_test.sh <name> -- --norm-max-diff 0.10
```

`./compare_all.sh` runs this for every case that already has a
`results/<name>/NODE.001_01`, skipping the rest, and prints a summary.

## Note on `--gpnorms '*'`

AROME LAM `GPNORM` fields (this NODE file has `TKE`, `SNOW`, `RAIN`,
`GRAUPEL`, `CLOUD_WATER`, `ICE_CRYSTAL`, `HUMI.SPECIFI`, `CLOUD_FRACTI`,
`SRC`, `MF_LIQUID_WATER`, `MF_ICE_WATER`, `MF_CLOUD_FRACTI`,
`RAD_LIQUID_WATER`, `RAD_SOLID_WATER`, `EZDIAG01-03`) don't match
`diff_NODE`'s built-in defaults (`VORTICITY`, `U VELOCITY`,
`SURFACE PRESSURE`, ... -- global IFS/ARPEGE names), so `compare_test.sh`
passes `--gpnorms '*'` to match everything instead. That's thorough but
verbose (tens of thousands of lines, several MB) since these fields recur
at every output step. Narrow it down once you know which fields you
actually care about, e.g.:

```
./compare_test.sh <name> -- --gpnorms "TKE,HUMI.SPECIFI,CLOUD_WATER"
```

## Current cases

- **NFR25_standard_namelist** -- ALADIN 49t1_clim1 with SURFEX, grid
  ALPX12, ERA5 LBCs, `INIDATE=ENDDATE=20200102`. Reference log copied from
  the `37_NFR_tuto_2` run.
