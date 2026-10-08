# A24｜TSOM / SOM-Net / OPM 严格代数审计

研究日期：2026-10-08。主裁决：**不存在已核实的“TSOM = A23 的 O/P seed 分解”。可删的是特定参考点的 forcing seed，不是 TSOM 的内部传播谱。** 本文的原文证据层级见 `SOURCES_AND_READING_LEDGER.md`。2009 TSOM 与 2011 FFT-TSOM 原论文全文本轮未取得；其算法关系由作者本人 2018 教材 §6.4 直接核对，不能把这一层级写成两篇原论文已经逐页复核。SOM-Net 的 arXiv v2 方法正文已经读取。[B01,R01–R04]

## 1. 全包统一记号

固定频率、网格、源与接收模型，先采用各向同性、非磁介质。设 N 个体素，d=1 对应 2D TM，d=3 对应 3D vector Maxwell；n=dN 是每源复电流维数，s 是源数，q 是每源复接收通道数，p=2N 是复标量材料的实参数维数。多源实数据维数 m=2qs。受限实介电常数或色散模型应另改 p。

所有正交、伴随及范数默认已经做材料/电流质量坐标变换；测量端的实化与噪声白化最后统一施加，不能把白化逆矩阵当成伴随。`*` 是共轭转置；互易性用的 `T` 是不共轭转置。

\[
 A=\operatorname{diag}(a_i I_d),\quad j_s=A(e_s^{inc}+Gj_s),\quad y_s=Sj_s.
\]

\(a=a(\chi)\) 是真实离散 constitutive coefficient。A23 的 DDA 系数是极化率而非裸 \(\chi\)：
\[
 a(\chi)=\frac{3v\chi}{3+\kappa\chi},\quad
 a'(\chi)=\frac{9v}{(3+\kappa\chi)^2},\quad
 \chi(a)=\frac{3a}{3v-\kappa a}.
\]

参考状态：
\[
 L_b=I-A_bG,\quad R_b=L_b^{-1},\quad b_s=A_be_s^{inc},
 \quad j_{b,s}=R_bb_s,\quad e_{b,s}=e_s^{inc}+Gj_{b,s}.
\]

当前材料假设产生 \(h=a(\chi)-a_b\)、\(H=\operatorname{diag}(h_iI_d)\)。以后使用 **\(q_s^{rel}\)** 表示相对 contrast source，避免与接收数 q 混淆：
\[
 q_s^{rel}=H e_s,\qquad \Delta j_s=R_bq_s^{rel}.
\]

定义两个背景算子：
\[
 \mathcal G_b=GR_b,\qquad \mathcal D_b=SR_b.
\]

它们分别把相对材料激发送回内部场和接收数据。尤其 \(GR_b\neq R_bG\) 一般成立；不得交换乘法次序。

## 2. 逐项术语对应表

| 对象 | 精确定义 / 空间 | 与 A23 的关系 |
|---|---|---|
| classical deterministic current | \(S=U_s\Sigma_sV_s^*\)，\(j_s^+=V_{s,\ell}\Sigma_{s,\ell}^{-1}U_{s,\ell}^*y_s\) | 是从实际数据得到的电流分量；**不是** A23 O seed |
| classical observable subspace | \(\mathcal O_j=\operatorname{Range}V_{s,\ell}\) | 测量算子的稳定右奇异空间；固定几何时可缓存 |
| classical ambiguous current | \(j_s^-=P_-z_s\)，\(P_-=I-V_{s,\ell}V_{s,\ell}^*\) | 包括小非零奇异值方向及真正 nullspace；不应统称严格不可辐射 |
| TSOM first fold | 对外部 current-to-data 算子 S 做稳定/弱分解 | 与 observation 机制 RELATED；不等于 Schur O chain |
| TSOM internal operator | 教材 \(G_D\)，本包 G；current → internal scattered field | 不等于 F=AG，不等于 Schur \(F_{eff}\)，也不等于相对 \(\mathcal G_b\) |
| TSOM second fold | 内部 G 的右奇异空间 \(\mathcal D_k\)；在 ambiguous 部分采用交空间或投影近似 | 是谱约束/截断；原论文没有 A23 forcing-P 的直接同名物 |
| A23 retained source current | \(j_{b,s}\in\operatorname{Range}U\) 时可被 \(R_Ub_s\) 精确恢复 | 属于已知特解；可改用 affine offset 单独保留 |
| A23 M raw seed | \([KB_sv_i]_{s,i}\)，\(B_sv=H(a_b'v)e_{b,s}\) | 材料切线驱动的 complement RHS；不是完整有限幅度材料流形 |
| A23 P raw seed | \([Kb_s]_s\) | 已知照明 forcing 的 complement 残差；source anchoring 后为零 |
| A23 O raw seed | \([T^*S^*w_{s,i}]_{s,i}\) | receiver/residual 的 adjoint 探针；不是从 SVD 直接重建的 \(j^+\) |
| feedback-propagated current | \(TF_{eff}^kKB_sv\) 或 \(R_bHGR_bH e_b\) 等 | 是传播后的响应；与 seed 不同类型 |
| receiver-adjoint current | \(Z_b=R_b^*S^*\) 或其 probe 压缩 | 对偶物理场；\(\mathcal D_b=Z_b^*\)，不提供新独立数据 |
| A24 relative observable source | \(\mathcal D_b\) 的截断 SVD 得到 \((q^{rel})^+\) | 与 classical O_j 是不同欧氏谱空间；经正确变换后可有等价表示 |
| A24 finite material excitation | \(q_s^{rel}=H(e_{b,s}+\mathcal G_bq_s^{rel})\) | 完整有限幅度材料驱动；不使用 unknown truth-state Jacobian |

A23 实际代码按源汇总后对每族截 rank4，再分别 Arnoldi：M/P 沿前向 \(F_{eff}\)，O 沿 \(F_{eff}^*\)。不能把“每族四列”写成“每源四列均保留”，也不能把原始 seed 的包含关系直接转给截断后的 bank。[P23a]

## 3. 原 TSOM 的交集和投影必须分开

教材 Eq.(6.70) 的理想限制是
\[
 j_s=j_s^++z_s,\qquad z_s\in\mathcal A\cap\mathcal D_k,
 \quad \mathcal A=\operatorname{Range}P_-.
\]
Eq.(6.71) 则明确介绍近似：
\[
 z_s=P_-V_{D,k}\beta_s,\qquad
 z_s\in P_-\mathcal D_k.
\]
一般只有
\[
 \mathcal A\cap\mathcal D_k\subseteq P_-\mathcal D_k,
\]
而非相等。证明：交集中的 z 满足 \(z=P_-z\)，故属于投影像。反向包含要求 \(P_-\mathcal D_k\subseteq\mathcal D_k\)；对正交投影，这等价于该空间被 P_- 约化，可用两个投影对易表述。

**一个应认真保留的教材几何限定。** 任意两个非对易谱投影，不一定使
\(\mathcal O_j\oplus(\mathcal A\cap\mathcal D_k)\oplus(\mathcal A\cap\mathcal D_k^\perp)\)
填满整个电流空间。取三维实空间：
\[
 \mathcal O_j=\operatorname{span}e_1,\quad
 \mathcal D_k=\operatorname{span}\{(e_1+e_2)/\sqrt2,e_3\}.
\]
此时交空间只有 e3，投影像却是 span(e2,e3)，上述三个交空间合计维数只有 2。因此教材的示意性三分解及 k−ell 维数不能当任意矩阵的普遍定理。这不否定 TSOM 数值方法；它要求实现明确选“交空间”“投影像”或“restricted-operator SVD”，而非混写。[B01, §6.4.2]

更稳妥的新参考是直接分解 \(GP_-\) 在 \(\mathcal A\) 上的作用。它准确度量 ambiguous current 对内部场的影响，但应命名 restricted-G spectral baseline，不能冒充原 TSOM 的逐字实现。

## 4. 原 SOM-Net 实际迁移单位

SOM-Net 使用 deterministic current 与 BP 材料初值；其子网络预测的是**完整诱导电流图**，总场按 \(e=e^{inc}+Gj\) 更新，材料按跨源加权比值更新。论文实验采用四个子网络，并以电流、数据及材料图像的监督损失训练。没有证据表明其主网络每层硬限制输出为 \(P_-\) 内的系数，也没有每层完整 Maxwell inverse。[R04, §II]

其物理 current 定义使用 \(-i(k_0/\eta_0)(\epsilon_r-1)\)，不同于教材 dimensionless contrast 与 A23 polarizability。迁移时必须连同 S、G、材料转换一起换尺度。

必须保留的是：物理可解释初值、多源共同材料、场与材料的耦合、真实 forward 检查。可替代的是：完整自由电流输出、四层固定选择、特定 CNN。不能当作硬物理证书的是有限权重的监督 loss。解析 LS 材料比值只给最佳公共系数，不保证所有源/矢量分量的 constitutive residual 为零。

## 5. 为什么 affine anchoring 比挤占 U 更自然

A23 H1 把 U8 的 8 个 receiver 方向改成 6 个 source 方向加 2 个 receiver 方向，source-OM 的 transfer 变差伴随着实际 rank32→24。这个结果不是单变量 P-removal 实验。[P23r]

A24 建议保留
\[
 j_s=j_{b,s}+\Delta j_s
\]
作为**已知 affine particular solution + 未知 correction**。j_b 独立缓存，不挤进 correction basis 的预算。相减后的 forcing 是 H e_b，不再是 b。这是一个精确变量变换，而非“原 U 没变却神奇使 Kb=0”。普通 affine ROM 也能这么做，必须列为强对照。

## 6. 数学对象四级结论

**SAME：** 固定 U/core 下已锚定 P 全零，保留 P 的 OPM 与删除它的 OM 给出同一非零 basis；数值零判据需用 forcing 尺度。

**EQUIVALENT representation：** 完整的 \(\Delta j\leftrightarrow q^{rel}=L_b\Delta j\) 是可逆重参数化；所有物理与材料条件仍须同时转换。

**RELATED mechanism：** TSOM 的内部场谱、Schur feedback 与 relative feedback 都处理内部传播，但所分解的算子和右端不同。

**DIFFERENT objects：** TSOM \(\mathcal D_k\)、A23 P_raw、A23 O_raw、classical observable current、material tangent bank，不能互换。

## 7. A20–A23 核心结论对本轮的约束

A20 初始 tangent/step 适配不能迁移到晚期；A21 的五状态原始报告是 rank56 BOTH_G 最坏 H-step 相对误差 4.40e−11，而 primal-only 中位 262%，且明确是 oracle/offline，不是部署算法。[P20,P21]

A22-R1 中 A2/A3 在主设置选到了相同投影，未产生 OPM 独立分离收益；不能把标签当额外物理信息。A23 的完整材料实验三项 gate 均失败。[P22,P23r]

因此本轮主候选不再寻找更好的 OPM 标签，而检验：**只压缩内部传播，保留逐体素材料激发，并在同一公共材料上闭合反馈，是否优于固定小电流空间。** 完整推导见 `RELATIVE_FEEDBACK_OM_ARCHITECTURE.md`。
