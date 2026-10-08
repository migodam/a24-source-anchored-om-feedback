# A24｜P seed 消去与反馈保留

本文件证明的是有限维离散 Maxwell 模型的精确代数；不是连续算子离散误差定理。沿用 `TSOM_SOMNET_ALGEBRA_AUDIT.md` 记号。背景、频率及 acquisition 固定，L_b 和所用 projected core 均须可逆。已有 source-anchor 消去结论来自 A23，本轮把其适用范围、affine 替代与传播保留条件整理成可实施命题。[P23a]

## T1a：固定 retained space 的精确 P-seed elimination

令 U*U=I，Π=I−UU*，
\[
 A_U=U^*L_bU,\quad R_U=UA_U^{-1}U^*,\quad
 K=\Pi(I-L_bR_U),\quad T=(I-R_UL_b)\Pi.
\]
若每个参考照明满足 \(j_{b,s}=L_b^{-1}b_s\in\operatorname{Range}U\)，则
\[
 Kb_s=0,\qquad F_{eff}^kKb_s=0\quad(k\ge0).
\]

**证明。** 写 j_b=Uc。由 U*b=A_Uc 得 R_Ub=Uc=j_b，再代入 Kb=Π(b−L_bj_b)=0。任何线性算子作用于零仍为零。没有弱散射、正规性或 \(\rho(F)<1\) 假设。

**精确保留结论。** 在同一 U、同一非零 O/M seeds、相同正交化/截断政策下，删除结构零 P 后的 trial/test space、reduced transfer 和重建目标完全不变。若实现对零 seed 自身归一化，roundoff 可能被放大成伪方向；判零应以完整 forcing 和参考残差尺度为准。

**不能随之改变的量。** U 中 receiver/source 的配额、M/O 的 rank cap、保留 basis 的总 rank、正则化与材料 decoder。一旦改变这些量，得到的是另一种算法，需要独立误差分析。

## T1b：精确 Schur feedback 没有消失

取 Q 为 Range(Π) 的正交基，定义
\[
 T_Q=(I-R_UL_b)Q,\quad K_Q=Q^*(I-L_bR_U),\quad
 C_Q=Q^*L_bT_Q.
\]
则
\[
 \boxed{R_b=R_U+T_QC_Q^{-1}K_Q.}
\]

**证明。** 在正交坐标 [U,Q] 中把 L_b 写成块矩阵。消去 U-block 后，补空间核心为
\(Q^*L_bQ-Q^*L_bU A_U^{-1}U^*L_bQ=C_Q\)。块逆公式给出上式。也可验证左乘 L_b 后在 U 和 Q 两个坐标上的作用都是恒等。

因此材料切线/任意材料 RHS g 的输出是
\[
 SR_bg=SR_Ug+ST_QC_Q^{-1}K_Qg.
\]
Source anchoring 只让 g=b_s 时第二项为零。对 g=B_sv 或 g=H(h)e_b，第二项一般不为零；C_Q 也没有变成 I。被删的是已知特解的补空间 forcing，不是背景 multiple scattering。

**反例。** 取 L=diag(1,2)，U=e1，b=e1。Kb=0，但 KB=e2 对 B=e2 非零；补空间逆为1/2，删去其传播会使材料响应加倍。非正规例子可使误差更大。

## T1c：近似锚定的 forward error

若 \(\widehat j_b\in\operatorname{Range}U\)，r=b−L_b\widehat j_b，则
\[
 Kb=Kr,\quad j_b-R_Ub=T_QC_Q^{-1}K_Qr.
\]
所以
\[
 \|j_b-R_Ub\|\le\|T_QC_Q^{-1}K_Q\|\|r\|,
\]
\[
 \|S(j_b-R_Ub)\|\le\|ST_QC_Q^{-1}K_Q\|\|r\|.
\]

**证明。** R_UL_b\widehat j_b=\widehat j_b，所以 K L_b\widehat j_b=0；再代入块逆公式。

这约束的是“丢弃 reference complement response”的误差，不自动约束“更换两个任意 Galerkin 空间”的误差。后者应先计算完整 state residual，再用 resolvent/inf-sup bound。

**小 seed 并不安全。** L=diag(1,ε²)，g=εe2，S=e2ᵀ 时 seed 范数 ε、输出1/ε。故必须记录输出放大/稳定性；不能只给 principal angles。

## T1d：affine source anchor，无需占用 correction rank

即使 U 不包含 j_b，仍可精确写
\[
 j_s=j_{b,s}+\Delta j_s,
\]
\[
 (L_b-HG)\Delta j_s=H e_{b,s}.
\]
参考 h=0 时，右端结构零。用任意合规 correction space 对 Δj 建模，都不需要再为旧 b_s 构造 P seed。

**证明。** 从 \((I-(A_b+H)G)(j_b+\Delta j)=(A_b+H)e^{inc}\) 减去 L_bj_b=A_be^{inc}，整理即可。

**保留了什么。** j_b 已含参考背景对该源的全部散射；H e_b 含新增材料在参考总场中的激发；\((L_b-HG)^{-1}\) 仍负责新增材料及背景间的反馈。仿射表示不是旧投影器满足 Kb=0 的声明，而是消除了原 forcing 的新方程。

**算法后果。** 把 s 个已知参考电流作为 offset 缓存；将 correction 的全部有限 rank 留给 receiver/material/必要谱方向。这直接避免 A23 中“6 source 挤掉 6 receiver”的配额混杂。但 offset 的 n×s 存储和参考解成本仍计费，普通 affine ROM 同样应获得这项改进。

## T1e：何时 P 可由 M closure 与 retained coupling 生成

先用 polarizability 全材料坐标，所以 \(B_sh=H(h)e_s\)。若材料方向 h*=a 可表达、而且实际 M bank 保留了所有 \(B_sh_*=j_s\)，当 U=0 时
\[
 b_s=(I-F)B_sh_*,\quad F=AG,
\]
\[
 \operatorname{span}\{F^jb_s:0\le j\le d\}
 \subseteq\operatorname{span}\{F^jB_sh_*:0\le j\le d+1\}.
\]
χ 坐标则要求 a' 可逆且 h*=a/a' 是允许的实参数方向。

有 U 时令 \(H_U=\Pi FU\)、\(a_*=A_U^{-1}U^*B_sh_*\)，可验证
\[
 KL_b=(I-F_{eff})\Pi,
\]
\[
 \Pi B_sh_*=KB_sh_*-H_Ua_*,
\]
\[
 \boxed{Kb_s=(I-F_{eff})(KB_sh_*-H_Ua_*).}
\]
因此 P 的 d 阶 descendants 可由 M 和 retained-complement coupling 的 d+1 阶 descendants 生成。**缺少 H_U 的纯 M 版本一般不成立。** 本轮随机代数检查遗漏 coupling 后出现约4.04%的 RHS 误差；这是反例，不是 Maxwell 效能估计。

**适用限制。** 固定 loss/dispersion chart 未必包含 h*；每族 rank4 的多源 SVD 可能丢掉必要列；给 M 增加一层 action 也未必比保留 P 更省。定理不为任意压缩后的 bank 提供免费包含关系。

## 传播与正则化的保留清单

| 项目 | source-anchor 删 P 后状态 | 必须采取的行动 |
|---|---|---|
| 参考照明的精确特解 | 固定 U 锚定或 affine offset 下保留 | 验证参考残差，缓存按依赖失效 |
| 参考背景内部散射 | 在 R_b、e_b 或 Schur core 中保留 | 不删除 core，不把 R_b=I |
| 新材料重复散射 | 不由 Kb=0 保证 | 保留 relative feedback / reduced core |
| retained ↔ complement 耦合 | 一般仍存在 | Schur lifting T、K 或等价全方程必须保留 |
| TSOM second-fold regularization | **不会自动保留** | 单独保留 spectral penalty/projector，或明确替换为传播过滤 |
| receiver-adjoint fidelity | 不由 source anchoring 保证 | 保留 dual probes / cached adjoint /输出误差验证 |
| 全材料可恢复性 | 没有保证 | 同一先验、完整材料评估与可识别性分析 |

## 强散射、非正规、多频与换参考

强散射不破坏 T1a 的恒等式，但会放大近似锚定/传播截断误差。L_b 可逆也不保证 U*L_bU 可逆：L=[[0,1],[1,0]]、U=e1 就是反例。必须显式监测小核心。

不同频率应分别验证背景、anchor、G/S 与 constitutive law；共享一个 U 可以尝试，但零-P 结论须在每频成立。换源后，新源电流未必在旧 U；换接收器不会改变旧 forcing identity，但会改变 O 和观测保真度。换参考材料时，旧 j_b 不再是新 L_b 的特解。affine 表示可继续使用旧参考，只要把完整 h 纳入反馈，但“大相对变化”的低秩/浅层质量必须重新验证。

## 结论

可以删除独立 P basis，**条件是已知源特解被精确保留或通过 affine subtraction 消去**。其传播作用可在 Schur/relative 算子中完整保留；其“TSOM 正则化作用”不能因为同叫 P 而凭空继承。A24 应分别检验 algebraic deletion、propagation approximation、material regularization 三个独立问题。
