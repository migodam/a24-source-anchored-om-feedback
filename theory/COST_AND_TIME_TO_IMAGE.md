# A24｜完整成本、内存与 time-to-image

**没有测得A24加速。以下是可执行计费模型与成立条件，不是benchmark。** A23的真实cold结果说明，删去若干算子动作或P列，可能只节省不到1%的总准备时间。[P23r]

## 1. 符号与成本单位

N cells，n=dN complex current coordinates，s illuminations，q complex receiver channels/source，m=2sq real data，p=2N real isotropic material coordinates。r表示current correction rank，k表示反馈秩，ℓ表示observable rank，b表示局部块的current维数，K表示material/network blocks。

记 C_G(t)、C_R(t)、C_R*(t) 分别为t个RHS的Green action、已知背景solve及adjoint solve实际时间；C_fact是背景预处理/分解，C_QR是基底正交化，C_NN是指定batch、precision、hardware下NN时间。t个RHS不等于t次kernel launch；block solve速度不能按单列时间机械相乘。

原DenseDDA可有O(n³)分解及O(n²t)回代；FFT action可为O(t n log n)。这些是不同后端，主对照必须共享后端或明确比较的是整套实现。任何GPU同步、host-device transfer、cache load、图像输出和失败重试均应记账。

## 2. Offline、cold、warm 的边界

- **永久准备**：网格、材料模型、acquisition、频率、参考背景固定后可跨对象复用的算子和网络权重。
- **每次acquisition准备**：新source/receiver几何、白化、参考fields、背景预测、必要SVD与cache传输。
- **在线**：本次measurement→image，包括data preprocessing、所有physical/NN blocks、拒绝判据和输出。
- **独立评估**：truth forward、full-image metrics、full-state检查。科学评价时单列，不能用它帮助在线选择；若部署算法确实需要full validation，它应转入online成本。

cold image时间是本次所需准备加online；warm不是cache copy的时间。训练数据生成、训练及调参列为另外的amortization账本。

## 3. 方法级成本表

| 方法 | 主要offline准备 | 每图主要online成本 | 不能忽略的项目 |
|---|---|---|---|
| SOM/TSOM | S的截断SVD；exact TSOM可需内部G谱/交集 | I次data/state交替更新，含G/G*、S/S*和current coefficients | exact内部SVD与可复用部分分开 |
| FFT-TSOM | observable split + Fourier grid/filter | O(I s n log n)+receiver actions及投影 | **已经避免完整G的SVD**；不能再把这个当A24节省 |
| 原SOM-Net | SVD/BP相关算子、离线训练 | K个CNN、K次G作用、O(Ksn)field/material比值 | **并非每层一次完整Maxwell solve**；未用的每层receiver action不能强加给baseline |
| A：minimal OM | 参考fields、M probes/压缩、V_M及其G作用、必要adjoint cache | O(Ksnr)+coefficient NN+material ratio，data checks按实际计 | basis生成可能比原SOM-Net多；只缩head不必然缩CNN |
| B：SA-RF | 背景特解、receiver adjoints、内部return低秩分解 | O(K[nb²+nbk+nk²+k³+nsk+nsq])+prior | n k²组装和n s q收缩常是瓶颈 |
| B-ROM | 参考特解、V、GV、SV及core | O(K[nr²+r³+nsr])+prior，输出/adjoint另计 | fixed-current rank带来表示误差 |
| C：coarse+completion | 参考transfer/稳定谱、prior representation | 一次coarse decoder、一次prior、一次B或ordinary-adjoint recoil | full covariance不能默认免费；NN未必需要 |
| OPM→材料反演 | 参考解、U、O/P/M chains、QR、投影、材料transfer | decoder或多次reduced inversion | 名称不决定成本；重建质量必须同级 |

这里O表达数量级，不代表所有方法常数相同。原SOM-Net的G作用可由dense GEMM或FFT实现，必须在相同硬件和quality约束下实际测量。

## 4. A的可计数实现

若采用t个材料probe，所有源的原始M需st个reference tangent RHS；若不显式存完整M，可选receiver/task或current-coordinate adjoint收缩。构造 V_M 后，缓存 G V_M、G Q_o，及需要的 R_b*V_M。具体选择不能把primal和dual两套昂贵cache都算成免费。

典型式为
\[
 T_{A,off}=C_{fact}+C_R(s)+C_R(st)+C_{QR}+C_G(r+\ell)+C_{SVD,S}+T_{IO},
\]
若还用Z_M=R_b*V_M，添加C_R*(r)，或明确以已有存储替代。在线
\[
 T_{A,on}\approx T_{obs}+K[T_{NN,coeff}+c_1nsr+c_2n s+T_{checks}].
\]
r远小于n仅保证系数维度下降；当CNN feature extractor仍在full grid运行，输出维数减少不等于总FLOPs减少n/r。

## 5. B的真实offline代价

采用randomized rank-k分解，oversampling o，power次数t_p。令k_o=k+o。对 \(\mathcal G_b-D\) 的一次forward action需要R_b solve再G action；adjoint需要G*再R_b*。

基本双侧range finder可需约k_o次forward和k_o次adjoint RHS；每个power cycle再增加相应两侧动作，具体次数写入ledger，不能只记最终k。因而
\[
 T_{B,off}=C_{fact}+C_R(s)+C_{R^*}(q)
 +T_{range}(k_o,t_p)+T_{local}+T_{QR/SVD}+T_{IO}.
\]
不显式构造完整 \(GR_b\) 是必要条件。小型实验可用dense oracle核验，但不得据dense oracle声称大规模准备也是便宜的。

如果只用source/material snapshots，动作可能较少，但此时误差保证是分布/任务相关，不是整个full material operator的统一界。训练样本、holdout probes与在线test必须隔离。

## 6. B每个block展开计费

D由不相交b×b块组成。每次材料χ变化后：

1. 分解I−HD：O(nb²)，构造/应用C_h：O(n b t)。
2. 计算C_h U_g：O(nbk)，组装V_g*C_hU_g：O(nk²)，分解k×k核心：O(k³)。
3. s源右端、core回代、full source合成：O(n b s+nks+k²s)。
4. data prediction：直接cached \(\mathcal D_b\widehat w\) 是O(nqs)。
5. residual adjoint：再一次O(nqs)，小核心/局部块的共轭回代O(nks+k²s)，材料归因O(ns)。
6. full-image prior/NN、约束及输出：另计。

因此即使无online full solve，也不能宣称“成本只为k³”。预计算D_b U_g不能一般消除D_b C_h的成本，因为C_h依赖每个体素未知材料，不能随意交换这些矩阵。使用小material chart预存全部tensor会重新引入chart restriction和存储代价。

若省略每块adjoint或只做一次recoil，可以降低成本，但这是C或新算法变体，需单独命名和测试。

## 7. 存储示例：A23尺寸不是免费缓存

A23 n=5184、s=6、q=128。complex128按16 bytes/entry计算：

| 数组 | 元素数 | 内存 |
|---|---:|---:|
| D_b或Z_b | nq=663552 | 10.125 MiB |
| U_g和V_g，k=16 | 2nk=165888 | 2.53125 MiB |
| j_b和e_b | 2ns=62208 | 0.94921875 MiB |

合计约13.61MiB仅是这些cache，不含局部块、当前source/field、低秩分解workspace、solver因子、NN参数及激活、autodiff中间量。更大3D网格时按n线性增长；背景dense分解内存则为n²级，可能支配总成本。

若保存完整real Jacobian m×p，A23尺寸1536×3456的float64约40.5MiB；SA-RF adjoint不需要这个矩阵。相比一个已经matrix-free的ordinary adjoint baseline，它没有这项额外节省。

## 8. OPM及删P的成本公式

用实际action次数而不是family名字计费：
\[
 T_{OPM,off}=T_{ref}+T_U+N_FC_F+N_{F^*}C_{F^*}
 +T_{seed}+T_{QR}+T_{project}+T_{transfer}+T_{IO}.
\]
source anchoring后删去P，可以减少其seed及descendants相关N_F和QR列数，但不能减少早已为参考field、receiver或其它families支付的成本。

A23报告给出四scene完整cold encoder：原OPM 12.331/16.429/14.995/14.684秒；cached Schur 12.226/16.362/14.943/14.594秒，下降约0.857%/0.408%/0.350%/0.618%。这是特定backend的实测，不外推到新架构。[P23r]

同轮source-anchored OM误差约9.7%–10.4%，原OPM约4.9%–6.2%；但前者同时把U从8 receiver改成6 source+2 receiver、actual rank32改24。不能将这个比较解读为P不可删除，也不能当同质量加速。

## 9. T6：摊销优势的必要充分代数条件

每方法有offline成本O_i和稳定warm成本t_i，复用N次时
\[
 \overline T_i(N)=O_i/N+t_i.
\]
新方法更快当且仅当
\[
 O_{new}-O_{base}<N(t_{base}-t_{new}).
\]
若O_new≥O_base且t_new≥t_base，不存在任何N能使其更快。若额外准备ΔO>0且warm节省Δt>0，必须N>ΔO/Δt。证明是交叉相乘；它不是对质量的结论，必须先固定共同image/data/feasibility标准。

基准必须报告N=1、10、100以及真实应用预计N；不得只选一个能回本的巨大N。若每对象都需重新选背景或acquisition，实际N可能接近1。训练成本可再加T_train/N_deploy，数据标签生成成本另列，不能因为双方都用NN就省略不相同的训练资源。

## 10. Cache失效规则

网格、Green/self-term、频率、参考材料或constitutive law改变：R_b、G_b、D_b及fields通常全部失效。仅source改变且L_b/G/S完全相同：可保留传播与receiver cache，但需新的参考source solves。仅receiver改变：可保留内部传播，D_b和白化需更新。不同频率不能仅更新输入frequency token就宣称物理算子已正确迁移。

本轮Cost Gate不是“rank≤某数”，而是同质量完整摊销时间至少降低20%的预注册工程目标。未测得这一点前，速度收益状态只能为NOT_ESTABLISHED。
