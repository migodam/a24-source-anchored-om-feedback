# A24｜SOM-Net 最小迁移：Architecture A

**定位：低风险的工程对照，不作为独立强 TAP novelty。** “保留确定电流、学习剩余电流”已有 SOM、ICLM、CS-Net 以及后续 residual-current 网络先例。A 的意义是分离 basis/anchor 改进与显式 feedback 的增量。[B01,R04,R06,R07,R16]

## 1. 原算法逐层审计与迁移

| 原组件 | 原文方法层面 | A24 处理 |
|---|---|---|
| deterministic current | 接收 SVD 的稳定分量 | 保留；或相对 data 上构造 correction |
| BP permittivity | 输入材料初值 | 保留为 matched initializer；不可换更强初值后归功于 feedback |
| learned current | CNN 输出 full induced current | 改为固定可解释 bank 中的 correction coefficients |
| total-field update | e=Ei+Gj | 保留精确已离散 action 或缓存 basis image |
| permittivity update | 跨源加权解析 ratio | 3D 改成跨源及矢量分量的共同系数；真实 constitutive map |
| data consistency | forward prediction + loss | 保留；不能当硬约束 |
| current consistency | supervised current labels | 同样训练信息预算，另报告 full-state residual |
| material consistency | analytic update + image losses | 明确 common material residual；passivity 作为声明的 projection |

原 SOM-Net 正文主要为2D TM，输出实/虚两通道；其四个 subnetwork 是实验选择，不是定理。本文不把该 CNN 直接称为3D算法。[R04]

## 2. 运行时不使用 truth 的 material-excitation bank

用已知参考、固定多尺度材料原子 φ_l（wavelets、patch constants、允许的结构先验），构造离线 probes
\[
 X_{s,l}=R_bH(\phi_l)e_{b,s}.
\]
设置
\[
 V_M=\operatorname{orth}_r\{P_-X_{s,l}\},\qquad
 P_-=I-Q_oQ_o^*,\quad Q_o=V_{s,\ell}.
\]

不得读取 test truth 的 J、支撑、oracle GN step 来选 φ_l、r 或列。跨源先汇集再压缩，记录丢掉的 source/material energy 与 data task error。bank 仅对声明的 prior/频率/参考有效；r 不解释为可恢复材料维数。

构建成本包含 (s×原子数) RHS；可先合规随机/结构化抽样，但必须记录其逼近误差。若训练集中估计 bank，应计入训练数据/先验而非纯物理免费结构。固定 SVD/QR 的 gauge 和排序；重建必须对复相位/酉变换一致，不能把未经对齐的任意 basis 坐标喂给同一个 network。

## 3. Affine observable anchor

令
\[
 \delta j_{o,s}=S_{\ell}^{\dagger}(y_s-Sj_{b,s}),\quad
 j_s^k=j_{b,s}+\delta j_{o,s}+V_Mc_s^k.
\]
参考数据精确且 h=0 时，δj_o=0、c=0 给出 j_b。即便 j_b 不在 V_M 或 correction retained U 中，也没有 P seed。

这种 hard observable anchor 在无噪声时有清晰含义；有噪声时固定 noisy coefficient 可能与共同材料不兼容。因此主噪声版使用 soft filtered anchor，允许一个小 observable correction，并把它计入 output rank；hard版只作机制对照。不得因使用同一 noisy datum 两次就当增加了信息。

## 4. 解析材料激发 + learned coefficient correction

给 χ^k，先计算 h^k=a(χ^k)−a_b。缓存
\[
 Z_M=R_b^*V_M.
\]
解析 coefficient prediction 为
\[
 c_{M,s}^k=Z_M^*H(h^k)e_{b,s}-V_M^*\delta j_{o,s}.
\]
最后一项在严格正交时为零，保留它便于数值审计。它只是 relative dressed-linear current coefficient，**没有新增材料之间的 relative feedback**。

网络输出
\[
 \delta c_s^k=N_\theta(\chi^k,c_s^k,c_{M,s}^k,\text{observable features}_s,\text{residual features}),
\]
\[
 c_s^{k+1}=c_{M,s}^k+\delta c_s^k.
\]
网络可按源共享权重，公共材料特征按源集合聚合。学习量为2rs个实系数，不是2ns个独立电流坐标；减少的只是 output/activation 维度，并不自动按 n/r 减少参数或 latency。

最小实现可先保留原 CNN，再对其输出作 V_M* 投影；这只验证空间限制，不算真正降低 network output complexity。正式 coefficient-head 版本需 encoder + r维 head，参数量与原模型匹配。

## 5. 总场与物理材料更新

预存 G V_M、G Q_o、j_b、e_b 后，
\[
 e_s^{k+1}=e_{b,s}+G\delta j_{o,s}+GV_Mc_s^{k+1}.
\]
此处没有 Maxwell inverse，但 dense basis lift 可能比 FFT 更贵，需实际计时。

每体素的共同系数（所有源和 d 个矢量分量）为
\[
 \widetilde a_i=
 \frac{\sum_{s,\alpha}\omega_s\overline{e_{s,i,\alpha}}j_{s,i,\alpha}+\eta a_i^{prior}}
 {\sum_{s,\alpha}\omega_s|e_{s,i,\alpha}|^2+\eta}.
\]
η=0 才是非正则 LS；η>0 明确加入先验偏差。ω_s 采用预注册 source normalization，并给小信号 denominator 设置固定 floor，不能在看 test truth 后调整。

2D scalar coefficient 与 χ 线性对应时，可作声明的 constrained projection。3D DDA 使用真实逆映射 χ(a)，验证 pole margin，再做 \(\chi^{k+1}=\Pi_\mathcal C\widetilde\chi\)。**该投影不是非线性 constitutive map 下精确 constrained LS 解**，而是显式、可复现的可行化步骤；所有对应对照使用同一规则。若要精确 constrained LS，应另求每体素的有约束二维实优化并计时，不得把 clipping 写成它。

## 6. T5：共同材料一致性的必要充分条件

给定某体素所有 source/component 的向量 E、J，存在一个共同 scalar a 使 J=aE，当且仅当：E≠0 时 J 在 span(E) 中；E=0 时必须 J=0。等价于非零 E 情况下 [E,J] 的列秩为1。

正权 W 下 LS 的最小残差为
\[
 R_{mat}^2=J^*WJ-\frac{|E^*WJ|^2}{E^*WE}.
\]

**证明。** 正交分解 J 为 E 的投影与其 W-orthogonal complement。共同材料存在当且仅当余项零。

**反例。** E=(1,1)、J=(1,2)，解析 ratio 返回 a=1.5，但剩余 residual=1/√2。能算出一个材料值不等于两源共享同一个物理解。3D 同一体素 x/y/z 分量也要合并，不能分别拟合三个 scalar permittivity。

**算法后果。** Architecture A 必须报告 R_mat 和 L(χ)j−b(χ)，它们不会因为解析更新而必然消失。Architecture B 则以共同 h 驱动所有源，严格满足近似传播模型下的公共 constitutive law；其 full-model residual由传播误差控制。

张量材料情况下，未知变成共同3×3 constitutive tensor；需要足够独立的局部照明列 E，采用受对称/被动性约束的 tensor fitting。标量 ratio 不再成立，本阶段3D验证只注册各向同性材料。

## 7. 训练 loss 与容量匹配

保持原数据、current labels、material labels、noise 和 split。使用
\[
 \mathcal L=\lambda_\chi\|\chi^K-\chi_{true}\|_M^2
 +\lambda_y\|W(Sj^K-y)\|^2
 +\lambda_j\|j^K-j_{true}\|^2
 +\lambda_{sta}\|L(\chi^K)j^K-b(\chi^K)\|^2
 +\lambda_{spec}\mathcal R_{TSOM}(j^K).
\]

各项可由既有标签或物理 action 计算；新增监督项必须同样给予 baseline，另设 matched-loss control。带真值的标签只在训练/评估空间存在，runtime API 不接受。训练 loss 权重不是 inference 物理证书。

为了单独考察反馈机制，A、B 及 generic-recurrence control 使用相同 prior network 容量和层数；不要用一个小 A 对比一个大 B 再称物理改善。

## 8. 复杂度、边界与不应有的宣称

每 block 至少包含 coefficient inference、O(nrs) 材料驱动 contraction、O(nrs) current/field lift、O(ns) material ratio；若在每层计算全部 residual，还加 data contractions。离线还需 M-bank、Z_M、G-images 和 observable SVD。详见 `COST_AND_TIME_TO_IMAGE.md`。

强 scattering 可能使 fixed V_M 丢失合法 current；weak noisy modes可能被 hard anchor 锁错；new sources/background/frequency 导致 cache/bank 失效；dynamic basis 更新会增加成本且带 gauge 问题。投影 current 不一定比原 full-current SOM-Net 更准。

## 9. 最小迁移的结论

A 是必须做的 isolation baseline：检测 affine anchoring、输出约束与较小 head 是否已经足够。它不能独立证明反馈价值，且“只学习 ambiguous/residual current”已被 ICLM、CS-Net 及2025 VBRL 类工作覆盖。只有 A→B 的 matched intervention 在 full Maxwell material/data/成本上产生增量，才值得写新的 feedback-native 架构论文。
