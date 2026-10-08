# A24 后端与 anatomy 对照表

本文件记录实施合同。测试及 anatomy 只能由共享账本的 charged runner 执行；源文件存在和静态编译通过不代表任何数值或成像 Gate 通过。

## 1. 2D TM 与既有 3D 后端

| 项目 | A24 2D TM 合同 | 既有 A20/A23 3D 合同 |
|---|---|---|
| 来源 | 独立命名的 `a24.physics.Physics2D`，读取未修改的 `vendor/a2/physics.py` | 原 `a20.backend` 与 vendored A17/A9 dyadic Maxwell |
| 时间约定 | exp(-i omega t)，outgoing Hankel H0(1) | 沿用原 DDA 约定，另行确认 |
| 几何 | 单位正方形；k=2π；8 源，32 接收器；源半径 .75，接收半径 .8 | 原 3D geometry/receiver model，不把 2D 当 scalar 开关 |
| 当前维数 | N=grid²，n=N，单分量 | N voxels，n=3N，三分量 |
| 材料映射 | a(χ)=χ，a′=1；此 χ 已是原 A2 VIE contrast | 原 polarizability / self-term；不能直接用裸 χ 替代 |
| 内部传播 | G=原 A2 `D.dense_direct()`；A0/A1 仅 grid8、n64 | 原 dyadic Green actions |
| 质量坐标 | current c=√v j，field e=√v E，v=cell area | 沿用原 material/current L2 度量 |
| 数据算子 | S=原 A2 S/√v；输出 scattered data，与原 A2 一致 | 原 3D receiver model |
| 实数据排列 | `(q,s)` → 每源 `[Re(q),Im(q)]`，源为最外层块 | A20 的源轴表达需显式转换；不能混排 |
| 材料实坐标 | x=√v `[Reχ,Imχ]`，p=2N | 原 material chart/quality 合同 |
| 数值实现 | complex128、general complex LU，无 pinv、jitter、隐式 rank 搜索 | 沿用原实现，不修改历史代码与结果 |

`Physics2D.vie.dense_reference` 返回未质量归一的物理电流；与 A24 full current 比较前乘 √v。接收数据不再乘质量因子。原 A2 的 equal-area self-cell 项保留；没有换成 square-integrated 项。

2D production 在冻结的有限网格上使用 native dense G 和 LU。部署 relative cache 不存储完整 R_b 或 G_b；传播 closure 从计费的 G / reference solve 及其伴随动作构建。仅 anatomy/test 的 tiny evaluator 可以显式形成 R_b、G_b、Schur inverse 或 dense Ahat，用来验证等式，不能把它们移进 imaging runtime。

## 2. 背景与 relative source

已知背景首先解 L_b j_b=b，L_b=I-diag(χ_b)G，b=diag(χ_b)e_inc。cache 记录 e_b、y_b 和 D_b=S R_b；D_b 通过 receiver-adjoint reference solves 构建。对当前合法材料 χ，h=χ-χ_b：

`w=(I-diag(h)G_b)^(-1)diag(h)e_b`，`y=y_b+D_b w`，`G_b=G R_b`。

χ_b 点的 w=0 和 y=y_b 是精确参考身份；Jacobian 通常非零。最终 χ 被动时允许 Im h<0。F 在当前估计 χ 解 native full state，所有动作计入 online；F 不读取未知 truth 状态。R 保留完整逐体素 h，并仅压缩传播反馈。ROM 保留固定 current correction 空间，是不同的数学对象。

L 使用完整相同 a(χ) 映射且令 relative feedback 为零。2D 中 a=χ，因此 dressed-linear χ 与 linear-a+exact conversion 精确相同；不把局部材料转换造成的差异算成 feedback 收益。

R 的局部 P=I-HD 与全局 K=I-Vg* P⁻¹H Ug 分别监测 σ_min、relative σ_min 与 condition。forward 与 adjoint 使用同一 general complex factorization。unsafe P 或 K 直接保存失败；不采用默认 fallback。

## 3. Anatomy 的预注册配对

| 对照 | 固定内容 | 判别与局限 |
|---|---|---|
| same-U source anchored OPM / drop-zero-P OM | U=orth([所有 j_b,receiver8])；同一 O/M raw probes、压缩阈值、degree1、target rank32 | 用完整 forcing norm 判 P 零；比较 basis projector、material transfer、adjoint pullback；保留全部 Schur feedback |
| nonanchor OPM / dropP 负对照 | receiver8 U，同一 probes 与 degree | P 一般非零；截断后的 projector 若偶合相同，也不能据此宣称 raw P 零 |
| affine source OM / ordinary affine current ROM | receiver8，全体 j_b 作为相同 affine offset | 源特解不挤占 correction rank；offset 的 n×s 存储和参考 solve 全部计费 |
| A23-style source replacement confound | retained budget8 优先容纳所有八个 A24 sources；只在真实 deflation 后补 receiver | 单独描述 source/receiver 分配改变，不用于判断 P 必要性；不是历史 six+two 的逐字复制 |
| classical observable | S 的 ℓ16 right singular space | 数据可见性基准，不冒充 A23 O seed |
| ideal TSOM intersection | O 的正交补 A 与 G 的内部右奇异空间 D 的交集 | 从 null(O*D) 独立计算 |
| projected TSOM | range((I-OO*)D) | 一般不同于交集；报告 projection/intersection rank、commutator 与 D 外分量 |
| restricted-G | 先取 Q_A，再分解 G Q_A | 以 Q_A*G*G Q_A 独立核验；命名明确，不声称复现原 FFT-TSOM |
| M+feedback 与 exact-adjoint control | 完整材料坐标；R16 primary，R32/local16 是冻结诊断 | 用独立材料/数据任务比较真实 full tangent 与 pullback；不训练、不择优改 primary |

degree1 的 O stream 用 F_eff*，M/P streams 用 F_eff。每族独立传播并先对自己的历史正交化；最后联合压缩到 target32。真实 rank 不足直接报告 `rank_deficient` 和实际 retained/correction/union rank，padding 恒为 0。

M/O seed domains 分别为 `[master_seed,1101]` 与 `[master_seed,2202]`；独立 material/data task domains 为 3303/4404。探针末维是 probe；源维显式保留到 `[source,probe]` 拼接。它们不使用四个成像 parent masks、候选 full state、truth Jacobian 或 full-GN optimum 构基。所有 bases 冻结后才创建独立 passive candidate 的 full evaluator state。

## 4. 指标与计费

主要记录 source/current reconstruction、full/delta data error、material-to-data transfer error、exact-adjoint pullback error、gradient cosine、feedback action error、core margins、full-state defect identity，以及实际 rank。gradient 或数据分母为零时指标为 null，保留绝对误差；不人为加分母 floor。P 零及近零 residual 等式以完整 forcing 归一。

material/image NRMSE 在 anatomy 中为 null：没有生成 reconstructed image。A1 transfer/adjoint 小并不替代 G2 的 image 条件，更不代表 G3–G5。

统一 Ledger 记录 reference/native solves、所有源 RHS、G/S actions、QR/SVD/core setup、失败动作与 cache I/O。不同方法共享 setup 时间在每条记录中只作为描述；不能相加。独立 feedback setup 逐项加一次。inclusive job wall 不累加 nested spans；计数可加，失败尝试不得删除。

预算 stop 保留余下全部 `NOT_RUN` 行及原因。`G1_identity_status` 保存 PASS/FAIL/NOT_RUN 细节；CLI 的二元 `G1_status` 在没有完整证据时为 FAIL，不能当作已经证明理论反例。向量输出为 `anatomy_vectors.npz`，JSON 为 `anatomy.json`。

## 5. 单元核验覆盖

`tests/test_algebra.py`：source anchor/negative control、same-U degree1 basis equality、Schur inverse与保留 coupling、conjugate adjoints、relative identity/T3 receiver error term、TSOM 反例/restricted Gram、unsafe retained core、common-material/dark-field 反例、packing/mass 坐标、oracle 权限和 cost/budget guards。

`tests/test_physics.py`：原 A2 dense reference、full-relative/h0 非零 tangent、G/S/G_b adjoints、real JVP/VJP、四个冻结有限差分步长、dense surrogate / small core、被动材料的负 Im h、无 feedback 的 constitutive control、source permutation、cache dependency invalidation、unsafe local P 和 full-state defect。它们是有限网格数值核验，不是成像或连续 Maxwell 误差证明。

禁止单独无账本运行这些测试；父进程用 `active_ledger(book)` 将测试与 anatomy 放在同一个 ≤120 秒 A0/A1 stage。没有 GPU、训练或自动扩大 rank/网格。
