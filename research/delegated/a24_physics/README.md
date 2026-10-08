# A24 physics implementation

Owned files: `src/a24/physics.py`, `src/a24/relative_feedback.py`.

The adapter independently names the scalar 2-D TM contract. It imports the unchanged A2 vendor by path, uses the fixed side-1 / k=2π / 8-source / 32-receiver geometry, and preserves mass-normalized current/field and real material coordinates. All native solves use general complex SciPy LU, with a backward-residual audit and no iterative solve, inverse, pseudoinverse, jitter, or fallback.

`ReferenceCache` keeps the background factorization, field/data and exact receiver adjoint cache. `prepare_lowrank` returns balanced factors `Ug,Vg` and a `LocalBlocks` operator, obtained by zero-power randomized SVD from counted background primal/adjoint actions. Optional disjoint 2×2-cell blocks use `G_loc (I-a_b G_loc)^-1` as an independent exact block primitive; they are not selected blocks of the full background inverse. `to_dense()` is an explicit small-verification helper, not preparation.

`RelativeFeedbackModel` supports L, native-current F, strict-adjoint local-plus-low-rank R, ordinary affine current ROM, and the fixed-background undressed incremental BORN control `y_b + S(h * incident)`. The frozen ROM uses 32 current directions from known-background smooth material-probe tangents and differentiates that fixed basis. Its `w` is `L_b V c`, the relative source associated with its Galerkin current, and generally differs from `h * field` because the constitutive equation is projected. Cache descriptor validation checks geometry, background, frequency, precision and normalization. Reference/basis arrays are immutable; F always assembles and factors the currently supplied material.

RHS counters count actual complex columns. Source-vs-material-direction multiplicity is recorded separately. Failed LU/guard actions are charged by shared spans; default constructors use the parent process's active ledger. Background data-Jacobian assembly is receiver-cache contraction only, in real material mass coordinates.

No numerical execution, physics fixture construction, or experiment was performed by this worker. Parent owns charged verification and scientific interpretation. Static compilation is the only permitted local validation.

## Conditional micro-3D confirmation

`src/a24/confirmation.py` separately wraps the preserved A20 vector DDA on a 6³ side-1.5 grid, k=2, six transverse plane waves and 16 two-channel receivers. It prepares all known-background operators and inline primal/adjoint identities before reserving the four noiseless evaluator labels. L/F/R16 share the same mass-coordinate initialization, 3-D TV, three material blocks and one half-step retry. Every requested relative-current output, candidate full solve and separate evaluator full validation is charged. Protocol, volume arrays, comparable central slices, failure rows and cost summaries are written when the parent conditionally invokes `confirm(config,out,book)`. This worker only compiled the module; the confirmation is NOT_RUN here.
