# A24｜Source-anchored relative-feedback OM：主候选

**主候选不是“固定 OPM bank 改叫 OM”。它是：已知参考特解作 affine anchor，完整逐体素材料产生相对 contrast source，仅压缩内部反馈传播，并缓存其到接收端的作用。** 这避免把薄 shell、非对称边缘及大部分全图材料自由度直接截掉。是否足够低秩、足够快，留给预注册的 Maxwell 小实验。

本文件把该候选称为 **SA-RF：source-anchored relative feedback**；“OM”是 observation + material excitation 的计算角色，不声称是新的正交直和分解。变量变换、Woodbury 消元及背景 Green 思想本身属于已有数学；论文新颖性必须来自具体架构及可证伪的性能机制，而非这些恒等式。[R05,R08–R12,R18]

## 1. 从精确相减，而不是 Born 截断开始

固定参考 j_b、e_b、R_b。未知材料差 h=a(χ)−a_b，H=diag(h_iI_d)。
\[
 \Delta j_s=R_bH(e_{b,s}+G\Delta j_s)
 = (I-R_bHG)^{-1}R_bHe_{b,s}.
\]
定义相对材料源 \(w_s:=q_s^{rel}=H e_s\)，则
\[
 \boxed{\Delta j_s=R_bw_s,\quad
 w_s=H(e_{b,s}+\mathcal G_bw_s),\quad
 \Delta y_s=\mathcal D_bw_s,}
\]
\[
 \mathcal G_b=GR_b,\qquad \mathcal D_b=SR_b.
\]

**证明。** 上式第一式代入总场 e=e_b+GΔj 即得第二式；代入数据方程即得第三式。逆变换 w=L_bΔj 可逆，故没有近似。可逆条件为 L_b 及 L_a=L_b−HG 可逆。由于
\[
 L_aR_b=I-H\mathcal G_b,
\]
第二个条件正好等价于 I−H\mathcal G_b 可逆。

相对反馈 H\mathcal G_b 与 current 形式 R_bHG 相似，具有相同特征值，但由于变换非酉，其算子范数和非正规瞬态未必相同。

## 2. O 与 M 的真实位置

O 不再是一个必须占满电流 basis 的固定标签。它可以是：\(\mathcal D_b\) 的稳定数据反演；或当前残差经 \(\mathcal D_b^*\) 以及相对反馈伴随回传的材料归因。

M 是完整 H e，而不是固定32维 truth chart。网络或无 NN 先验产生 χ 的全图假设，随后 H 由 a(χ) 精确计算。不存在用未知 truth-state Jacobian 构造特征的循环定义。

相对 observable source
\[
 w_s^+=\mathcal D_{b,\ell}^{\dagger}(y_s-Sj_{b,s})
\]
可作初始化特征；但不要把 w_s^+ 直接等同于 classical j_s^+。对于有噪声数据，最终用白化 data fidelity 而非把所有保留分量硬钉死，更利于共同材料一致性。

## 3. 核心改变：压缩传播，不硬截完整电流

选固定背景内部算子的结构近似
\[
 \widehat{\mathcal G}_b=D+U_gV_g^*,\qquad U_g,V_g\in\mathbb C^{n\times k}.
\]
D 为易处理的局部/不相交小块算子，k 是全局反馈秩。D=0 是最简单合法版本；3D 近场明显时，应先检验小块版本。不能假定 vector Maxwell Green 是低通或全局低秩。

对每个完整材料假设 h，定义
\[
 C_h=(I-HD)^{-1}H,\qquad
 K_h=I_k-V_g^*C_hU_g.
\]
计算
\[
 c_s=K_h^{-1}V_g^*C_he_{b,s},
\]
\[
 \boxed{\widehat w_s=C_h(e_{b,s}+U_gc_s).}
\]
数据为
\[
 \widehat y_s=Sj_{b,s}+\mathcal D_b\widehat w_s.
\]

### T7：完整材料源、有限反馈核心

假设 I−HD 及 K_h 可逆。上述公式精确解出
\[
 \widehat w_s=H(e_{b,s}+\widehat{\mathcal G}_b\widehat w_s).
\]
若 \(\widehat{\mathcal G}_b=\mathcal G_b\)，则它对**任意允许的完整逐体素 h**给出原 Maxwell 离散系统的精确 data；不需要 h 处在 k 维材料空间。

**证明。** 令 c_s=V_g*\widehat w_s。由局部消元有 \(\widehat w_s=C_he_b+C_hU_gc_s\)。左乘 V_g* 得 K_h c_s=V_g*C_he_b，再代回。反向代入原方程验证即可。多源共享同一个 K_h，只分解一次。

这里没有宣称所有材料的电流都在一个固定 k 维空间。C_h 随每个体素的材料变化；不同 h 对应不同 material-dressed source family。小的是需要联立求解的全局反馈变量，不是图像维度。

### 为什么这比固定 M chart 更值得测试

固定 q≈Vc 直接丢掉 Range(V) 外的电流。新式保留 C_h e_b 的全部局部空间结构，并只对场的远程耦合进行近似。即使某个高空间频率电流对内部场贡献很小，也不会自动把它作为材料边缘的载体删掉。

本轮12维合成“局部+rank2”算子检查中，上式的相对源误差1.68e−16，而将精确源投影到该固定rank2传播像后的误差为93.22%。**这只证明两个限制不是同一件事；不是 Maxwell 成像收益，不是证明 TSOM 会产生93%的误差。**

## 4. D 的构建不能隐藏 selected inverse

禁止声称“免费取 \(GR_b\) 的全部3×3对角块”：直接求这些块可能需要大量背景 solves。

可实施的便宜选择：从已知裸 G 取不相交局部块 G_loc，令
\[
 D=G_{loc}(I-A_bG_{loc})^{-1}.
\]
这只是定义一个易算的局部背景传播近似，不等于真实 \(\mathcal G_b\) 的对角块。其所有误差都进入 remainder \(\mathcal G_b-D\) 的低秩近似。DDA 已把 self-term 吸收进 a 时，单体素 G_loc 可能为零，必须如实得到 D=0，不能重复加 self-interaction。

若每个独立块大小为 b 个 current coordinates，在线局部分解成本 O(nb²)，应用成本 O(nb s)；不是无条件 O(n)。相邻重叠 patch 需要额外一致性/迭代，不在最小版中。

另一个失效必须检测：I−HD 可能奇异而完整 I−H\mathcal G_b 可逆。例如标量 H=D=1、全局项−1，使总 \(\mathcal G_b=0\)。这是此消元方式 breakdown，而不是物理介质一定有共振。允许预注册切换 D=0；其成本与失败记录不能删除。

## 5. 如何得到 U_g,V_g 与接收缓存

已知背景 action：
\[
 v\mapsto (\mathcal G_b-D)v=G(R_bv)-Dv,
\]
\[
 v\mapsto(\mathcal G_b-D)^*v=R_b^*G^*v-D^*v.
\]
每列需一个背景 primal/adjoint solve 加一次 G/G* action。离线用固定 rank 的 randomized SVD、物理频谱基或已知训练材料产生的 task snapshots；方法必须声明其是全空间 approximation 还是仅训练分布上的 approximation。

接收端用
\[
 Z_b=L_b^{-*}S^*,\quad \mathcal D_b=Z_b^*.
\]
同一背景和接收器只需 q 个 adjoint RHS，而不是 s×q；不同接收几何需更新此缓存。其 n×q 存储和每次 nqs 收缩都计费。若 q 很大，可压缩 Z_b，但须加独立 output/adjoint 误差，不能只给内部场 SVD 误差。

离线不必存满 R_b 或 \(\mathcal G_b\)；tiny oracle 可以，为 verification 使用，不能作为大规模部署复杂度。

## 6. 精确 discrete adjoint：不再另造一个“dual NN”

令 \(\widehat A_h=I-H\widehat{\mathcal G}_b\)，\(\widehat e_s=e_b+\widehat{\mathcal G}_b\widehat w_s\)。对材料扰动 δχ：
\[
 \delta\widehat w_s=\widehat A_h^{-1}H(a'(\chi)\delta\chi)\widehat e_s.
\]
对数据 residual r，先按真实白化/实化把 adjoint load 送回复 receiver，再求
\[
 \widehat A_h^*z_s=\mathcal D_b^*r_s.
\]
这可以用相同局部块和 k×k 核心的伴随求解完成。定义
\[
 t_i=\sum_{s,\alpha}\overline{a_i'(\chi_i)\widehat e_{s,i,\alpha}}\,z_{s,i,\alpha}.
\]
在 [Reχ,Imχ] 排列及普通欧氏体素坐标下，梯度是 [Re t,Im t]；质量坐标需再施加对应尺度。无需 material Jacobian 全矩阵。

这是同一 surrogate forward 的严格伴随，不是另一条统计信息。A21 的启示是不能只验证 primal；最小方案直接使用普通 adjoint，并与 exact-adjoint baseline 比较。attention/bilinear gating 只有在 matched-capacity 实验里确实有增量才加入。

## 7. Architecture B 的2–3个 material blocks

\[
 (\widehat y^k,\widehat w^k,\widehat e^k,\text{margins})
   =\operatorname{SA\!RF}(\chi^k),
\]
\[
 g^k=\widehat J(\chi^k)^*W^*W(\widehat y^k-y),
\]
\[
 \chi^{k+1}=\Pi_{\mathcal C}
 \left\{\operatorname{Prior}_{\theta}
 [\chi^k-\tau_k D_k g^k;\,\chi^k,g^k,\text{field energy},\text{residual features}]
 \right\}.
\]

D_k 为有界正对角 scaling；\(\mathcal C\) 是预注册物理材料域。Prior 可为 TV/wavelet proximal，也可为共享参数的小 residual network。NN 不预测任意每源电流、不学习完整 L^{-1}。源轴先做对称聚合，以免固定源排序被误学为物理。稳定性分析须包含这些conditioning features对χ的依赖；单输入prox的Lipschitz界不能直接当作整个多输入CNN的稳定证书。

**2–3个 block 不等于2–3次散射。** 每个小核心的逆已包含 surrogate 中所有阶全局反馈；block 数表示材料假设更新次数。单个反馈 solve 未必便宜，必须计入局部组装、n k² core assembly、forward/adjoint data contractions。

注意：w=H\widehat e 后，再用 w/\widehat e 做解析材料更新只会返回同一个 h，不会产生新逆信息。B 的材料改进必须来自测量 residual / prior；不能将这种恒等比值包装成额外网络层。

## 8. 与 current-ROM 版本的区别

备选 B-ROM：Δj=Vc，求
\[
 [V^*L_bV-V^*HGV]c_s=V^*He_{b,s}.
\]
缓存 GV 可免 online G action，但 arbitrary full h 的 core assembly 仍 O(nr²)，且固定 V 仍排除部分真实电流。这是普通 affine parametric ROM，应作为强 baseline，不能认为它已经解决本轮的 current chart 缺陷。

SA-RF 把 full local material source 保留下来，压缩的是 internal field return；数学对象不同。二者谁优必须同时看 full material error、full Maxwell data residual、成本和峰值内存。

## 9. 强绝对对比度、相对变化与物理性质

当 \(\|R_bH G\|\) 或适当加权 norm 小而 \(\|AG\|\) 大，reference-centered feedback 有条件优势。绝对对比度高本身不是充分条件；若 L_b 近共振，R_b 很大，小 h 也会被放大。与 DBIM 相比，这里固定背景缓存但保留 relative inverse；与完整 DBIM 比没有全局稳定性优势定理。

若 reciprocal discretization 满足 Gᵀ=G、A_bᵀ=A_b，则
\(\mathcal G_b^T=\mathcal G_b\)，因为 \(G(I-A_bG)^{-1}=(I-GA_b)^{-1}G\)。可用复对称低秩分解或对称化 preserving reciprocity；不能强行 Hermitian 化。对称化 rank 可能翻倍，计入预算。

Imχ≥0 在 e^{−iωt} 约定下是材料被动性约束；它不自动保证任意压缩算子的能量性质，也不保证 core condition number 小。多频还需共同色散模型/因果性，不能仅逐频 clipping。

## 10. 真正的主假设与停止条件

主假设：存在实际 Maxwell regime，使完整材料源保留 + 小的、可监测的传播 closure，在相同先验与完整时间预算下优于 fixed-current truncation / no-feedback OM。

该假设未由本轮 algebra checks 证明。若为了达到可接受 data/adjoint fidelity，k 或局部块成本过大；若普通 adjoint + prior 同等好且更快；或 reduced closure 的失真大于它恢复的 nonlinear signal，则 SA-RF 应 NO-GO。此时保留 C 或传统方法，不扩大训练。
