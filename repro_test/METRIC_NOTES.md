# A chaos-aware metric for NODE norm comparison — design prompt

## The problem

`diff_NODE` currently flags a norm value when

```
|exp - ref| > eff_atol + rtol·|ref|          eff_atol = max(atol, atol_frac·peak|ref|_field)
```

The per-field absolute floor (`--atol-frac`, default `1e-9` of the field's
own peak) already stops genuinely near-zero values from tripping on noise.
But two things are still unresolved:

1. **Small-magnitude fields with real signal.** `DIVERGENCE` and
   `VORTICITY` spectral AVE norms are ~`1e-4`–`1e-5` while `TEMPERATURE`
   and `KINETIC ENERGY` are ~`1e+2`. A relative tolerance that's right for
   temperature is either far too loose or far too tight for divergence,
   and the absolute floor is a blunt instrument (it either kills the field
   entirely or doesn't).

2. **Chaotic growth.** For a change that is *not* expected to be
   bit-reproducible (new compiler, new optimisation flags, different MPI
   decomposition, different hardware), a rounding-level perturbation at
   step 0 grows ~exponentially. By step 360 the spectral norms can differ
   by whole percent — **not a bug, just the atmosphere**. A single
   `rtol` applied to the last step will fail every non-bit-repro build.

We want a metric that says "this build is fine" vs "this build is broken"
without hand-tuning per field and per forecast length.

## Regimes (the user should say which one each case is in)

- **A — bit-reproducible expected.** Refactor, same toolchain/flags/decomp.
  Any difference above rounding (`rel > ~1e-12`, or a handful of ULPs) is a
  regression. Metric is almost trivial: near-exact equality. This is the
  strongest test and should be the default where achievable.

- **B — numerically close expected, not bit-identical.** New compiler
  version, `-O2`→`-O3`, new node type. Early steps must still agree to
  many digits; later divergence must look like *chaos*, not *instability*
  or a *systematic drift*.

- **C — physics changed.** Not a reproducibility test — out of scope here.

## Candidate metrics for regime B

### B1. Early-step agreement + growth-rate check  *(recommended primary)*

Track, per field, the **digits of agreement**
`d(n) = -log10(rel_diff)` as a function of forecast step `n`, using
`rel_diff = |exp-ref| / (|ref| + floor_field)`.

Healthy non-bit-repro run:
- `d(1)` is high (≈ 12–15 — one or two roundings, not more).
- `d(n)` decreases roughly linearly in `n` (or in `log n`), slope set by
  the flow's Lyapunov time.

Flag if:
- `d(1) < D_MIN` (immediate divergence ⇒ real bug: wrong init, uninit
  memory, broken I/O, wrong constant), **or**
- the fitted slope of `d(n)` is steeper than `SLOPE_MAX` (blow-up /
  instability rather than chaos), **or**
- `d(n)` is flat-then-cliff (a discrete event — a branch taken
  differently), detectable as a large single-step drop `d(n)-d(n+1)`.

Knobs: `D_MIN` (~8–10), `SLOPE_MAX`, `--max-nstep` to restrict to the
regime where the check is meaningful. Cheap: we already parse per-step
values.

### B2. Perturbation-growth envelope  *(gold standard, heavier)*

Run the reference **twice**, once with the last bit of the initial state
perturbed (or with a different decomposition). The spread between those
two runs *is* the chaotic-noise envelope `E(n)` for each field. Flag the
experiment only where `|exp-ref|(n)` exceeds `k·E(n)`.

Pros: no hand-tuned thresholds, directly separates chaos from bug.
Cons: needs an extra reference run per case (store `E(n)` alongside the
reference NODE); the perturbation recipe has to be defined.

### B3. Scale-normalised difference

Replace `|ref|` in the denominator with a fixed physical scale per field
(e.g. divergence and vorticity both normalised by a vorticity scale
`~1e-4 s⁻¹`, temperature by `~1 K`, KE by its own AVE). Removes the
small-magnitude asymmetry of B-with-plain-rtol, but still needs a
chaos-growth allowance on top.

### B4. Compare a robust functional, not the raw norm

Instead of the norm at each step, compare something that's less
chaos-sensitive: time-mean of the norm over the run, the norm of the
*difference* field if available, or energy spectra slopes. More work,
weaker link to "did the model change".

## Recommendation

- Default every case to **regime A** (exact-ish) unless told otherwise —
  `--rtol 1e-12 --atol-frac 0`, verdict on any real difference.
- Add **B1** as an opt-in mode (`--mode chaos` or per-case
  `node_diff_args`): needs only `D_MIN`, `SLOPE_MAX`, `--max-nstep`, all
  with defaults; reuses the per-step data we already have.
- Offer **B2** later for cases where B1's thresholds prove fiddly — it's
  the only approach that's actually principled, and the infrastructure
  (a second reference run, an `E(n)` file) fits the existing
  `save_reference.sh` pattern.

## Questions for you

1. For the executable-version tests you're doing now — is the new build
   meant to be bit-reproducible with the old one (regime A), or not
   (regime B)?
2. If B: do you already have a feel for acceptable `d(1)` /
   digits-of-agreement at step 1 for a "good" build? (From past
   compiler bumps.)
3. Is a second, perturbed reference run per case acceptable cost (B2), or
   should we stay with threshold-based B1?
4. Which fields matter most for the verdict — all five spectral norms
   equally, or is `LOG(PREHYDS)` / `KINETIC ENERGY` the one you trust?
5. Restrict the verdict to the first N steps by default (where the signal
   is cleanest), and treat later steps as informational?
