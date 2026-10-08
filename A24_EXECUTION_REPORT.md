# A24 execution report

Protocol `A24-NO-NN-20261008-v1`; generated 2026-10-08T12:45:29.558483+00:00.
Report generation is evaluator-only and charged to the caller's B0 ledger.
Gate decisions are copied from saved evidence; no experiment or numerical setting is changed.

## Evidence and failures

| Level | Recorded status | Scope |
| --- | --- | --- |
| 理论 | FORMULAS_AND_COUNTEREXAMPLES_ONLY | 来源 theory/；不产生图像或速度结论 |
| A0/unit | PASS | 离散代数与实现核验；不能替代成像 |
| A1 tiny 2D | COMPLETE | 8×8空间剖析；无材料重建图像 |
| B0 2D imaging | {"OK": 136, "FAILED": 4, "COMMON_INITIALIZATION_FAILED": 84} | 四个已公开合成parent，失败条件全部保留 |
| 3D dyadic DDA | NOT_RUN | 有条件最多4状态；不能将2D解释成3D |
| 时间/成本 | QUALITY_TARGET_NOT_REACHED | 实测warm与组成计费；N=10/100未实际重复部署 |
| NN训练 | NOT_RUN_TRAINING_DISABLED | C/D保持关闭 |

Condition records: 224; statuses `{'OK': 136, 'FAILED': 4, 'COMMON_INITIALIZATION_FAILED': 84}`. All 88 non-OK
conditions are retained. COMMON_INITIALIZATION_FAILED identifies the frozen TV-prox
KKT cap at the shared initializer; it does not override the passing Maxwell identity tests.
Four exposed synthetic parents are the statistical units. Official parent means require
all eight conditions, and unavailable metrics remain null.

| Gate | Status | Frozen threshold |
| --- | --- | --- |
| G1 | PASS | 1e-10 |
| G2 | FAIL | {"task_max": 0.05, "cosine_min": 0.99, "image_degradation_max": 0.05} |
| G3 | HOLD | {"F_improvement": 0.1, "R_gain_retention": 0.8, "rho_closure_max": 0.5} |
| G4 | NOT_RUN_TRAINING_DISABLED | — |
| G5 | QUALITY_TARGET_NOT_REACHED | 0.2 |

G2 observed-task counterexamples are failures of the frozen universal R16 task
criterion, even with missing image conditions. G3 image/headroom coverage remains
separate. Missing observations cannot erase an observed valid counterexample;
passing G1 identities cannot substitute for G2 accuracy.

| Observed counterexample | Transfer error | Adjoint error | Gradient cosine |
| --- | --- | --- | --- |
| weak_2402_1.2_zero | 0.0506979 | 0.0510996 | 0.997589 |
| weak_2402_1.2_snr20 | 0.0507192 | 0.0512131 | 0.997621 |
| weak_2403_1.2_zero | 0.0516552 | 0.0490487 | 0.995264 |
| weak_2403_1.2_snr20 | 0.0514967 | 0.0488278 | 0.995353 |
| weak_2404_1.2_zero | 0.0535177 | 0.0537776 | 0.996696 |
| weak_2404_1.2_snr20 | 0.0532317 | 0.0534903 | 0.996768 |

Descriptive paired background subgroups (not full-eight official parent means):

| 背景 | parent | 成对条件 | 应有 | L NRMSE | F NRMSE | R16 NRMSE | F改善% | R改善% | R保留比 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weak | 2401 | 4 | 4 | 0.54949 | 0.53842 | 0.539026 | 2.0146 | 1.90434 | 0.945271 |
| weak | 2402 | 4 | 4 | 0.598533 | 0.577653 | 0.578101 | 3.48854 | 3.41372 | 0.978554 |
| weak | 2403 | 4 | 4 | 0.536332 | 0.502102 | 0.504533 | 6.38222 | 5.92905 | 0.928996 |
| weak | 2404 | 4 | 4 | 0.601231 | 0.576989 | 0.578866 | 4.03209 | 3.71988 | 0.922567 |
| ring | 2401 | 2 | 4 | 0.0752007 | 0.0751887 | 0.0751889 | 0.0160139 | 0.0158025 | 0.986796 |
| ring | 2402 | 2 | 4 | 0.0895988 | 0.0894996 | 0.0895012 | 0.110712 | 0.108926 | 0.983869 |
| ring | 2403 | 0 | 4 | — | — | — | — | — | — |
| ring | 2404 | 0 | 4 | — | — | — | — | — | — |

| Background | Complete parents | Equal-parent F gain % | Equal-parent R gain % | Scope |
| --- | --- | --- | --- | --- |
| weak | 4 | 3.97936 | 3.74175 | COMPLETE_WEAK_SUBGROUP_DESCRIPTION |
| ring | 0 | — | — | NO_EQUAL_PARENT_SUBGROUP_AGGREGATE |

Available legal-estimate R16 task ranges; missing conditions remain missing:

| Metric | Available | Expected | Min | Median | Max |
| --- | --- | --- | --- | --- | --- |
| independent_transfer_error | 20 | 32 | 0.00552293 | 0.0163242 | 0.0535177 |
| independent_adjoint_error | 20 | 32 | 0.00524809 | 0.0154174 | 0.0537776 |
| gradient_cosine | 20 | 32 | 0.995264 | 0.999474 | 0.999992 |
| independent_state_data_error | 20 | 32 | 3.21638e-05 | 0.00151497 | 0.00918908 |

## Actual inclusive costs and provenance

| Job | Command | Stage | Status | Wall s | CPU s | New labels | Geometry s | Source commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a24-a-001 | anatomy | A | COMPLETE | 1.373 | 0.835901 | 0 | 0.0127114 | 4d6fedcbc603b562e1aa0d6d57655174276170c7 |
| a24-b0-001 | no-nn | B0 | FAILED | 37.9147 | 36.2311 | 10 | 0.184766 | 4d6fedcbc603b562e1aa0d6d57655174276170c7 |
| a24-b0-002 | no-nn | B0 | COMPLETE | 9.27904 | 9.00676 | 6 | 0.18076 | 84b7f73fcb4a52e4edb9a23f55da9a1cc5e38d11 |
| a24-report-gates-001 | report | B0 | HOLD_INCOMPLETE | 0.0124234 | 0.012417 | 0 | — | 84b7f73fcb4a52e4edb9a23f55da9a1cc5e38d11 |
| a24-a-002 | anatomy | A | COMPLETE | 0.913488 | 0.822025 | 0 | 0.0118471 | ddd91a05cd67607164270ffe757e24cfba75ba1f |
| a24-report-002 | report | B0 | HOLD_INCOMPLETE | 4.40437 | 4.13139 | 0 | — | 2f97fd1c0860696c7f08fea2d7963ade32ba417a |
| a24-a-003 | anatomy | A | COMPLETE | 0.926891 | 0.829025 | 0 | 0.012246 | b4c146b93a575433eebb8a4ec9bc279ae5ee3200 |
| a24-report-003 | report | B0 | ACTIVE_SNAPSHOT | 0.479119 | 0.470043 | — | — | 6d597a34ada767a0c473447e4825dabbebd41655 |

Both failed and resumed jobs are charged. Sum inclusive job receipts, never nested span
walls. The current report job snapshot ends before this report's final export; its final
job_receipt.json is authoritative for total reporting cost.

Cold accounting adds the actual per-job tm2d_geometry_setup omitted by the driver's
original cold_image_s: cold_in_memory_image_s = raw cold_image_s + source-job geometry.
The recorded recovery boundary assigns all weak conditions plus ring2401/.3 zero/20dB
to job001 and successful remaining checkpoint images to job002. Actual image shared
and method setup components are used; unresolved/failed associations stay null.
Archive cache export is science I/O in full job wall, not mandatory in-memory setup.
Disk-loaded-cache deployment cold is NOT_RUN. Remaining unsegmented cache/data I/O
stays in full job wall overhead. N=10/100 values are accounting
projections from a single setup and measured warm medians, not measured N deployments.
No time-to-image superiority is asserted outside the joint quality region.

| condition | method | N | 有效重复 | geometry s | 一次setup s | warm median s | 实测组成cold s | 摊销/image s | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weak_2401_0.3_snr20 | L | 1 | 5 | 0.184766 | 0.202276 | 0.151254 | 0.354778 | 0.353531 | COMPLETE |
| weak_2401_0.3_snr20 | L | 10 | 5 | 0.184766 | 0.202276 | 0.151254 | 0.354778 | 0.171482 | COMPLETE |
| weak_2401_0.3_snr20 | L | 100 | 5 | 0.184766 | 0.202276 | 0.151254 | 0.354778 | 0.153277 | COMPLETE |
| weak_2401_0.3_snr20 | F | 1 | 5 | 0.184766 | 0.202235 | 0.17352 | 0.375873 | 0.375755 | COMPLETE |
| weak_2401_0.3_snr20 | F | 10 | 5 | 0.184766 | 0.202235 | 0.17352 | 0.375873 | 0.193744 | COMPLETE |
| weak_2401_0.3_snr20 | F | 100 | 5 | 0.184766 | 0.202235 | 0.17352 | 0.375873 | 0.175543 | COMPLETE |
| weak_2401_0.3_snr20 | R16 | 1 | 5 | 0.184766 | 0.20618 | 0.150655 | 0.356738 | 0.356835 | COMPLETE |
| weak_2401_0.3_snr20 | R16 | 10 | 5 | 0.184766 | 0.20618 | 0.150655 | 0.356738 | 0.171273 | COMPLETE |
| weak_2401_0.3_snr20 | R16 | 100 | 5 | 0.184766 | 0.20618 | 0.150655 | 0.356738 | 0.152717 | COMPLETE |
| weak_2403_0.3_snr20 | L | 1 | 5 | 0.184766 | 0.202276 | 0.0577324 | 0.26021 | 0.260009 | COMPLETE |
| weak_2403_0.3_snr20 | L | 10 | 5 | 0.184766 | 0.202276 | 0.0577324 | 0.26021 | 0.07796 | COMPLETE |
| weak_2403_0.3_snr20 | L | 100 | 5 | 0.184766 | 0.202276 | 0.0577324 | 0.26021 | 0.0597551 | COMPLETE |
| weak_2403_0.3_snr20 | F | 1 | 5 | 0.184766 | 0.202235 | 0.0967811 | 0.299385 | 0.299016 | COMPLETE |
| weak_2403_0.3_snr20 | F | 10 | 5 | 0.184766 | 0.202235 | 0.0967811 | 0.299385 | 0.117005 | COMPLETE |
| weak_2403_0.3_snr20 | F | 100 | 5 | 0.184766 | 0.202235 | 0.0967811 | 0.299385 | 0.0988034 | COMPLETE |
| weak_2403_0.3_snr20 | R16 | 1 | 5 | 0.184766 | 0.20618 | 0.0716844 | 0.27774 | 0.277864 | COMPLETE |
| weak_2403_0.3_snr20 | R16 | 10 | 5 | 0.184766 | 0.20618 | 0.0716844 | 0.27774 | 0.0923024 | COMPLETE |
| weak_2403_0.3_snr20 | R16 | 100 | 5 | 0.184766 | 0.20618 | 0.0716844 | 0.27774 | 0.0737462 | COMPLETE |
| ring_2401_0.3_snr20 | L | 1 | 5 | 0.184766 | 0.200019 | 0.427261 | 0.624411 | 0.62728 | COMPLETE |
| ring_2401_0.3_snr20 | L | 10 | 5 | 0.184766 | 0.200019 | 0.427261 | 0.624411 | 0.447263 | COMPLETE |
| ring_2401_0.3_snr20 | L | 100 | 5 | 0.184766 | 0.200019 | 0.427261 | 0.624411 | 0.429261 | COMPLETE |
| ring_2401_0.3_snr20 | F | 1 | 5 | 0.184766 | 0.199984 | 0.441242 | 0.639806 | 0.641225 | COMPLETE |
| ring_2401_0.3_snr20 | F | 10 | 5 | 0.184766 | 0.199984 | 0.441242 | 0.639806 | 0.46124 | COMPLETE |
| ring_2401_0.3_snr20 | F | 100 | 5 | 0.184766 | 0.199984 | 0.441242 | 0.639806 | 0.443242 | COMPLETE |
| ring_2401_0.3_snr20 | R16 | 1 | 5 | 0.184766 | 0.203512 | 0.420382 | 0.631816 | 0.623894 | COMPLETE |
| ring_2401_0.3_snr20 | R16 | 10 | 5 | 0.184766 | 0.203512 | 0.420382 | 0.631816 | 0.440733 | COMPLETE |
| ring_2401_0.3_snr20 | R16 | 100 | 5 | 0.184766 | 0.203512 | 0.420382 | 0.631816 | 0.422417 | COMPLETE |
| ring_2403_0.3_snr20 | L | 1 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | L | 10 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | L | 100 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | F | 1 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | F | 10 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | F | 100 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | R16 | 1 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | R16 | 10 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |
| ring_2403_0.3_snr20 | R16 | 100 | 0 | — | — | — | — | — | INCOMPLETE_OR_FAILED |

## Preserved missing baselines and condition failures

| Baseline | Status or equivalence |
| --- | --- |
| DRESSED_LINEAR_CHI | L |
| LINEAR_A_EXACT_CONVERSION_2D | L |
| ORDINARY_ADJOINT_TV | F |
| SOM_FFT_TSOM | NOT_COMPARABLE: existing Gaussian-parameter fit changes material prior and optimizer |
| CIE_I_WT_TSOM | NOT_IMPLEMENTED |

| Condition | Method | Failure/missing status | Recorded reason |
| --- | --- | --- | --- |
| ring_2401_0.3_zero | BORN_TV | FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_0.3_snr20 | BORN_TV | FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2401_1.2_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_0.3_zero | BORN_TV | FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_0.3_snr20 | BORN_TV | FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2402_1.2_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_0.3_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2403_1.2_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_0.3_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_zero | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | L | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | F | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | R16 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | R32_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | R16_LOCAL_DIAGNOSTIC | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | AFFINE_ROM32 | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |
| ring_2404_1.2_snr20 | BORN_TV | COMMON_INITIALIZATION_FAILED | NumericalFailure('TV_PROX_NOT_CONVERGED:2000') |

## Deliverables and reproduction

- [Chinese research report](A24_RESEARCH_REPORT_ZH.md)
- [Report manifest](results/report/REPORT_MANIFEST.json)
- `results/report/figures/`: scientific PNG and PDF exports.
- `results/report/plot_data/`: all plotted condition, parent, task, timing, preparation,
  anatomy, failure and image-pixel data, with nulls/failure statuses retained.
- Frozen sources: [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json),
  [config](configs/a24_frozen.json), job manifests and receipts under `results/jobs/`.

Parent invocation: `build_report(config, repo_root, book)` within the active B0 ledger.
Report generation reads recorded evaluator outputs only; it does not invoke a physical
adapter, generate clean labels, run tests, train, recompute gates or publish anything.
Scientific interpretation and any public release remain with the parent reviewer.
