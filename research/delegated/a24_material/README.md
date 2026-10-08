# A24 constrained material TV update

Status: implemented; numerical tests **NOT_RUN** by this worker. The parent
must execute the tests inside its charged A0/A1 120-second stage ledger.
No Maxwell, reconstruction-quality, or scientific gate is claimed here.

## Files and API

- `src/a24/material_updates.py`: `tv_value`, real Neumann
  `material_gradient`/`material_gradient_adjoint`, `prox_tv_box`, and an
  optional one-shot `normalized_backprojection` helper.
- `tests/test_material_updates.py`: 12 unittest cases. Test setup calls
  `contracts.get_ledger()`; direct standalone execution refuses to run.

All materials use `[sqrt(volume) Re chi, sqrt(volume) Im chi]` in C grid
ordering. The TV input is **delta material mass**, normally `x-background`.
For dimension d, TV is
`volume**((d-1)/d)/sqrt(volume) * sum_cells ||D(delta_mass)||_2`,
with one joint norm across the d outgoing differences and both channels.
The final edge in every direction is zero. This is the cubical-cell physical
TV integral with the declared cell volume, without an extra spacing factor.

## Convex solve and acceptance

The solver minimizes
`0.5 ||x-v||^2 + weight TV(x-background) + indicator_physical_box(x)`.
It uses fixed Chambolle--Pock steps
`tau=sigma=.99/(2*sqrt(d))`, `theta=1` and dual ball radius
`weight*volume**((d-1)/d)/sqrt(volume)`.
Each primal step is the exact proximal map of the quadratic plus the box.
Default physical bounds are real `[-.5,4]`, imaginary `[0,.5]`; frozen
`real_lower`, `real_upper`, `imag_lower`, `imag_upper` configuration keys are
supported. There is no ridge, jitter, hidden line search, or clipping after
an unconstrained solve. Box projections in initialization, primal updates,
and diagnostic certificates are counted separately from physical actions.

Default `prox_max_iter=1000`; a frozen parent configuration may choose up
to 2000. `prox_tolerance=1e-6`, `prox_check_every=10`, and normalized
physical feasibility tolerance is `1e-10`. `prox_raise_on_failure=True`
raises `NumericalFailure` with `.meta`; False returns `NOT_CONVERGED`
metadata. Exhausting the cap is never acceptance.

Acceptance requires finite, small box-normal-cone stationarity, primal and
dual fixed-point residuals, dual feasibility, TV complementarity, box
complementarity, and primal-dual gap. Residual norms use the declared mass
scale `material_scale*sqrt(N*volume)` (physical material scale defaults to
1); gap/complementarity use its square. The dual minimizer is the analytic
constrained quadratic minimizer `clip(v-D*dual)`, evaluated only as a
certificate. The gap is computed by a stable sum of quadratic, box-normal,
and TV-complementarity terms. Metadata includes all residual components,
objective, gap, TV, feasibility, iteration count, fixed steps, array-byte
estimate, and elapsed wall time. Ledger spans charge failed solves too.

The BP helper expects a fixed real whitened linear forward/adjoint pair in
mass coordinates. Its standard normalization is `||J*r||^2/||J J*r||^2`.
The callbacks remain responsible for physical action accounting; the wrapper
also counts callback calls. At present its `weight` is the supplied proximal
weight, matching `prox_tv_box`; it does not freeze a new lambda or data model.

## Tests prepared

Tests cover D/D* in 2D/3D with arbitrary boundary loads; constant-field TV;
joint Re/Im TV and physical-volume scaling; analytic zero-weight/single-cell
box prox; closed-form two-cell unfused/fused solutions; an active-bound
solution constructed from its exact joint-TV KKT certificate; mass scaling;
reported/raised nonconvergence; normalized BP and zero-adjoint action counts.

Static AST parsing passed for both Python files, measured wall
`0.003218875 seconds`. This check imported no numerical modules and ran no
numerical tests. Parent numerical execution and gate decisions remain pending.

## Conservatism and uncertainties

`2*sqrt(d)` is a safe bound even on short/degenerate axes, so the fixed
steps can be conservative. Small TV features or large penalties can make the
dual converge slowly. The 1000/2000 iteration caps may therefore reject
otherwise useful approximations at tolerance `1e-6`; failures must be kept,
and the frozen cap/tolerance must not change after observing B0 results.
The declared fixed physical mass scale prevents a large objective or iterate
from making a relative convergence test artificially lenient. Numerical
convergence, wall cost, and conditioning are unverified until the parent run.
