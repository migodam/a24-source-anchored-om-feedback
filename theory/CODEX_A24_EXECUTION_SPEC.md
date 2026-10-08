# A24｜Codex实施规范：先检验机制，再决定是否训练

## 0. 首轮任务与禁止事项

读取 `A24_EXECUTIVE_DECISION.md`、`MINIMAL_EXPERIMENT_SPEC.md`、`RELATIVE_FEEDBACK_OM_ARCHITECTURE.md`、`THEOREMS_AND_COUNTEREXAMPLES.md`，再核对A20/A23后端。首先完成unit/anatomy和无NN B0；本规范**不授权大型训练、GPU campaign、自动rank搜索或扩场景**。学习C/D保持disabled，另行批准后才启动。

不要重做PCG/GMRES加速或GN fidelity研究。不要仅把OPM类名改OM。不要修改既有A17–A23结果、阈值或源码主分支。建立独立a24目录/branch并记录输入commit。运行前可用Plan mode梳理接口、预算和冻结配置，计划完成后实现与小测试；不要用Plan mode无限追加研究路线。

本包已执行的是 `verification/algebra_checks.py`，其它Maxwell/训练结果不存在，不能从报告中填入伪实验CSV。

## 1. 来源与版本

A20/A22读取基线：`migodam/a20-opm-imaging@b85a29a51f4ea7b4d93617e827d88e23933b89df`。重点 `src/a20/backend.py`、`src/a20/opm.py`、vendored A17/A9 DDA实现。A23来源见本包reading ledger；执行时解析并冻结目标commit，不继续追踪浮动main。

沿用原材料L2度量、complex→real packing、白化、polarizability/self-term、3D receiver model。2D TM新adapter需独立命名与测试，不能假装是原3D后端的scalar开关。

## 2. 建议目录

```text
src/a24/
  contracts.py          # typed operators, cache keys, budgets
  source_anchor.py      # affine reference, exact Schur identities
  tsom_audit.py         # intersection / projection / restricted-G
  relative_feedback.py  # local-plus-low-rank closure + exact adjoint
  material_updates.py   # shared-material fit, constraints, TV/prox
  baselines.py          # dressed-linear, ordinary-adjoint, affine ROM
  diagnostics.py        # runtime-safe + evaluator-only metrics
  cli.py
configs/
  a24_anatomy.json
  a24_no_nn_b0.json
  a24_training_disabled.json
tests/
  test_algebra.py
  test_real_adjoint.py
  test_3d_backend_contract.py
results/<job_id>/
  frozen_config.json, source_manifest.json, costs.jsonl,
  cases.csv, failures.jsonl, gate_decision.json, report.md
```

这些是待实现文件名，不声称当前ZIP已经包含上述完整软件；ZIP提供的是研究文档和可运行代数核验脚本。

## 3. 数据合同与权限隔离

Runtime输入：measured y、已知geometry/frequency/material law、noise covariance、reference χ_b与其cache、允许的训练prior/固定probe seed。Runtime不得接触truth χ、truth currents、truth-state Jacobian、full-GN optimum、test-object support mask或依据truth选择的rank。

Evaluator单独拥有truth与完整physical forward，并在runtime结果冻结后计算image/data/state误差。exact-feedback机制臂可以在**当前估计χ**求full state/adjoint，但这些动作全部归其online账本；它不是读取truth state。

强制shape：current/source/field `(n,s)` complex128；receiver `(q,s)` complex128；χ按N个complex或p=2N real mass coordinates规范存放，且转换只由adapter完成。probe bank末维是probe，source维不可悄悄与cell/components混排。

## 4. 必需接口

```python
class PhysicsAdapter:
    def material_to_a(self, chi): ...
    def material_derivative(self, chi): ...
    def reference_solve(self, rhs, *, adjoint=False): ...
    def green(self, v, *, adjoint=False): ...
    def observe(self, j, *, adjoint=False): ...
    def pack_real(self, y): ...
    def unpack_real(self, v): ...
    def whiten(self, v, *, adjoint=False): ...
    def material_pullback(self, chi, field, adjoint_source): ...

class RelativeFeedbackCache:
    # eb (n,s), yb (q,s), Db (q,n), Ug/Vg (n,k), local blocks D
    # descriptor + geometry/frequency/background/hash/precision metadata
    def validate(self, descriptor): ...

class RelativeFeedbackModel:
    def forward(self, chi): ...   # data, relative source, surrogate field, margins
    def adjoint(self, chi, data_load, state_cache): ...
    def jvp(self, chi, delta_chi, state_cache): ...
```

每个方法均向统一CostLedger记录RHS、kernel、factor、array bytes及wall span；nested spans不得重复累加。加入deadline与new-label计数，超限立刻停止。

## 5. B核心：不能只实现forward而忘记adjoint

令H由完整h=a(χ)−a_b构建；P=I−HD，C=P^{-1}H，U=U_g，V=V_g，K=I−V*CU。

```text
factor all disjoint local P blocks
CU = solve(P, H * U)
factor K = I - V^H @ CU
base = solve(P, H * eb)
c = solve(K, V^H @ base)
w = base + CU @ c
field = eb + D @ w + U @ (V^H @ w)
yhat = yb + Db @ w
```

对任意rhs，Ahat=I−H(D+UV*)：

```text
solve_A(rhs):
    t = solve(P, rhs)
    return t + CU @ solve(K, V^H @ t)

solve_A_adjoint(rhs):
    t = solve(P^H, rhs)
    gamma = solve(K^H, U^H @ (H^H * t))
    return t + solve(P^H, V @ gamma)
```

验证 `solve_A_adjoint` 与forward是同一离散映射的共轭伴随。不可因为K小就使用Hermitian solver；一般K非Hermitian。

data loss为real-white residual。先通过真实pack/white adjoint产生complex data_load，再 `z=solve_A_adjoint(Db^H @ data_load)`，最后调用material_pullback。ordinary欧氏复χ坐标的cell contraction为Σconj(a' E)z，梯度pack成[Re,Im]；质量尺度及general real whitening必须通过adapter处理。

不在线计算Δj=R_b w来凑一个“full current输出”，除非实验明确需要且计费。B的默认输出是material和data，以及relative source/surrogate field。

## 6. 边界与安全处理

χ=χ_b必须返回w=0、y=yb，同时Jacobian一般非零。Im χ≥0等物理约束在最终材料域施加；不得要求Im h≥0。source index置换应只置换各源forward列，公共material output不变。

检查local P与K的最小奇异值、相对尺度和condition，拒绝unsafe cores。默认禁止pinv、silent jitter、事后换rank和full fallback。若预注册D→0 fallback，保存原失败和额外cost；若没有预注册，直接返回failure。

材料ratio仅用于A/传统SOM baseline：跨所有sources/components拟合一个scalar a；再做受约束材料转换。dark-field floor与ridge在config固定，另外报告bias；project后current consistency必须重算。B不能用w/E“更新材料”，因为它只返回已输入h。

多频cache按频率分别key；共享的是材料/色散参数，不是把同一G_b用于不同ω。tensor/scalar不能混用；首轮3D限定isotropic scalar χ及三分量current。

## 7. 必须通过的测试

1. 原A20 Green/adjoint、packing/white、a和a'差分回归；full→relative identity。
2. source anchor下P零；非anchor P非零；receiver-U替换与affine offset不能混淆。
3. T2 intersection与projection反例；Q_A上G限制的独立计算。
4. direct dense Ahat solve与small-core solve在不同complex h一致；包含h=0和负Im h但最终χ被动的case。
5. real JVP/VJP dot-product、四个预注册有限差分步长平台、source置换等变性。
6. full-state residual与−H(G_b−G_bhat)w关系；approx receiver cache误差项。
7. common-material impossible-current反例；暗场、constitutive pole和unsafe core失败路径。
8. no-feedback=G_bhat0与dressed-linear完全一致，排除不同a(χ)转换造成的假feedback收益。
9. cache改变频率/geometry/background时拒绝使用；runtime读取oracle文件触发测试失败。
10. cost ledger包含准备、所有RHS、failed jobs、cache I/O，zero action必须与真正未调用一致。

complex128归一identity主阈值1e−10。单位不同的量使用声明尺度；禁止用P自己的近零norm归一P零测试。

## 8. 实验命令设计与输出

建议CLI：
```bash
python -m a24.cli freeze --config configs/a24_anatomy.json --job a24-a-001
python -m a24.cli anatomy --job a24-a-001 --device cpu
python -m a24.cli freeze --config configs/a24_no_nn_b0.json --job a24-b0-001
python -m a24.cli no-nn --job a24-b0-001 --device cpu
python -m a24.cli report --job a24-b0-001
```

它们是接口规范，不是ZIP已存在的可执行入口；实际当前可运行命令只有：
```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verification/algebra_checks.py
```

case记录至少含 `parent_id/background/amplitude/noise/method/actual_rank/operator_hash/status/material_nrmse/delta_nrmse/full_data_residual/state_residual/adjoint_error/core_margins/offline_s/online_s/peak_bytes/rhs_counts`。失败case所有不可得metric填null并附reason，不填0，不从均值样本中静默移除。

gate_decision同时保存threshold、可用parent数量、missing baselines、NOT_RUN及FAIL原因。report最后回答：F是否存在headroom？R是否保留它？普通adjoint是否同样好且更便宜？下一步是A/B/C哪条，还是STOP？

## 9. 可直接交付Codex的短prompt

> 按A24研究包实施，先读A24_EXECUTIVE_DECISION.md、MINIMAL_EXPERIMENT_SPEC.md、RELATIVE_FEEDBACK_OM_ARCHITECTURE.md和CODEX_A24_EXECUTION_SPEC.md。先用Plan mode列出后端映射、冻结配置与预算，再实现unit/anatomy和无NN的L/F/R配对B0。保持A20/A23材料与Maxwell合同，不使用truth-state Jacobian构基，不修改旧结果。默认CPU，严格执行预注册停止与完整cost ledger。训练C/D、大型3D及GPU实验全部保持关闭。交付真实结果、失败账本、Gate判决和可复现命令，不把合成代数检查当Maxwell成像证据。
