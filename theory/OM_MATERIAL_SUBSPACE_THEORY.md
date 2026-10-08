# A24｜OM 空间、材料可恢复性与误差传播

本文区分三类截断：固定电流空间、材料 chart、内部传播算子。它们不能共用一个“rank”来论证图像保真。所有新结论均为本轮推导；历史实现见 [P20code,P23a]，TSOM 定义见 [B01]。

## 1. Range(OPM) 与 Range(OM)

令 \(\mathcal M_d=\operatorname{span}_{j=0}^dF_{eff}^jM_0\)，\(\mathcal P_d\) 类似，\(\mathcal O_d=\operatorname{span}_{j=0}^d(F_{eff}^*)^jO_0\)。在没有另外截断/丢列时，A20 代码最终合并的是
\[
 \mathcal V_{OPM}=\operatorname{Range}U+\mathcal O_d+\mathcal P_d+\mathcal M_d,
\]
\[
 \mathcal V_{OM}=\operatorname{Range}U+\mathcal O_d+\mathcal M_d.
\]
对补空间 W，T W=W−U A_U^{-1}U*L_bW，因此加上 U 后，使用 W 或 TW 的总空间相同；这不表示对应坐标/core 数值相同。

固定 U 且 P_raw=0 时，两空间精确相等；否则一般仅有 \(\mathcal V_{OM}\subseteq\mathcal V_{OPM}\)。若 P 可由 M/coupling 高一阶 closure 生成，则换 degree 后可包含，但其 action 和 rank 必须重计。

当 orthogonalization、SVD cap 或 test basis 不同，仅空间包含也不保证 Galerkin material image 单调改善。非 Hermitian/noncoercive Maxwell core 没有一般 best-approximation 常数1的性质。

## 2. T2：OM 与 TSOM 不存在普遍等价

classical TSOM 的 affine current family 为
\[
 \mathcal J_T(y)=j^+(y)+(\mathcal A\cap\mathcal D_k)
\]
或其投影近似 \(j^+(y)+P_-\mathcal D_k\)。固定 OM current family 为
\[
 \mathcal J_M(y)=j^+(y)+P_-\mathcal V_M.
\]
两者对全部系数等价，当且仅当其 direction spaces 相等；与是否把某族叫 M 或 P 无关。proof 是两个 affine 集合拥有同一 base point，其差集分别等于相应 direction space。

**相互失败的反例。** 在 ambiguous 二维平面里，取 TSOM direction=e2、M direction=e3。真实材料激发若沿 e3，TSOM 截断差而 M 精确；真实激发若沿 e2，结论反转。没有跨材料类的统一优势。

**条件性的 material-aware 最优。** 若事先规定材料扰动协方差 Γ，以及已知参考切线 B、传播 R_b，则在纯 current L2 平均误差意义下，\(R_bB\Gamma^{1/2}\) 的前 r 个左奇异向量最小化 rank-r 正交投影误差。证明由 Eckart–Young 对该 snapshot/operator 矩阵直接得到。它优化的是指定 prior 下的 current loss，不等于 material Bayes risk，更不保证多源/有限幅度 OOD。若指标为 data/decoder-weighted loss，应对加权 operator 另求最优；再加内部场稳定性约束也会改变解。

因此 M 可以比 bare G 的谱更贴近指定材料任务，但这种收益有 class/prior 条件，且普通 task-aware ROM 同样拥有它。

## 3. Relative source 的 O 与 classical current 的 O

完整变换 Δj=R_bw 是一一映射，\(\mathcal D_b=SR_b\)。在欧氏 norm 下，S 与 \(\mathcal D_b\) 的右奇异向量一般不是简单地乘 R_b 即相互对应。

若在 w-space 采用 pullback metric
\[
 \|w\|_{R_b^*R_b}=\|R_bw\|_2,
\]
则 w→Δj 是等距变换，使用这一 metric 的 generalized singular problem 与 current-space 的 SVD 等价。若使用普通 Euclidean w-SVD，则改变了正则化几何，不应声称经典 SOM split 原样保留。

## 4. Material + feedback closure 的维度边界

固定 h 时，\(w=(I-H\mathcal G_b)^{-1}He_b\)。若 Neumann 展开收敛，或者只考虑代数 Krylov span，可写成由
\[
 He_b,\quad H\mathcal G_bHe_b,\quad (H\mathcal G_b)^2He_b,\ldots
\]
生成的空间。有限维可用 Cayley–Hamilton 给出精确有限多项式表示，只要 inverse 存在；所需 degree 最坏可达 n−1，系数也可能病态。这不是 few-layer 保证。

若要求所有 h 都成立，需要包含各种 material-dependent products 的联合 span，通常可以填满整个 current space。它不应被一个固定 rank4 M seed bank 冒充。

本轮 SA-RF 使用另一条路：\(\widehat{\mathcal G}_b=D+U_gV_g^*\) 的反馈小核心随 h 改变，但 H 的每个体素都保留。它不声称这些 current families 的全体 union 低秩。

## 5. T3a：任意 current approximation 的 residual bound

对真实材料 a，L_a=I−AG，forcing b_a=Aeinc。任意 \(\widehat j\) 的 state residual 是 r=b_a−L_a\widehat j。则
\[
 j-\widehat j=L_a^{-1}r,
\]
\[
 \|j-\widehat j\|\le\|L_a^{-1}\|\|r\|,\quad
 \|S(j-\widehat j)\|\le\|SL_a^{-1}\|\|r\|.
\]
证明为代入线性方程相减。该定理同时覆盖删 P、ROM、NN current，不要求 Galerkin。小 residual 仍须乘非正规 resolvent 放大；不能把 residual 与 image error 等同。

## 6. T3b：SA-RF 传播与接收误差

令 \(A_h=I-H\mathcal G_b\)，\(\widehat A_h=I-H\widehat{\mathcal G}_b\)。精确 w=A_h^{-1}He_b，近似 \(\widehat w=\widehat A_h^{-1}He_b\)。定义可用于检查的物理缺陷
\[
 r_h=H(\mathcal G_b-\widehat{\mathcal G}_b)\widehat w.
\]
则
\[
 \boxed{w-\widehat w=A_h^{-1}r_h,}
\]
\[
 \Delta j-R_b\widehat w=R_bA_h^{-1}r_h,
\]
\[
 \Delta y-\mathcal D_b\widehat w=\mathcal D_bA_h^{-1}r_h.
\]

**证明。** A_h\widehat w=He_b−r_h，与 A_hw=He_b 相减。

若接收 cache 也压缩为 \(\widehat{\mathcal D}_b\)，再加
\[
 (\mathcal D_b-\widehat{\mathcal D}_b)\widehat w.
\]
因此
\[
 \|\Delta y-\widehat{\mathcal D}_b\widehat w\|
 \le \|\mathcal D_bA_h^{-1}\|\|r_h\|
 +\|\mathcal D_b-\widehat{\mathcal D}_b\|\|\widehat w\|.
\]

若仅知道 \(\|\mathcal G_b-\widehat{\mathcal G}_b\|\le\varepsilon_G\)，则 \(\|r_h\|\le\|H\|\varepsilon_G\|\widehat w\|\)。精确 SVD 的 tail singular value 可给离散 spectral bound；random probes 只给带条件/概率的估计，未经校准不能称 certificate。

对于隐含 current \(\widehat j=j_b+R_b\widehat w\)，有
\[
 L_a\widehat j-Ae^{inc}=-r_h.
\]
这精确解释了 reduced propagation 引起的 full state inconsistency。在线若只输出图像和 data，未显式求 R_b\widehat w；不能声称已经免费输出完整电流。

## 7. T3c：adjoint / material gradient 保真

令 \(B_E\delta\chi=H(a'(\chi)\delta\chi)E\)，多源叠合后
\[
 J=\mathcal D_bA_h^{-1}B_E,\qquad
 \widehat J=\widehat{\mathcal D}_b\widehat A_h^{-1}B_{\widehat E}.
\]
由添加/减去中间项，
\[
 \|J-\widehat J\|\le
 \|\mathcal D_b-\widehat{\mathcal D}_b\|\|A_h^{-1}\|\|B_E\|
 +\|\widehat{\mathcal D}_b\|\|A_h^{-1}-\widehat A_h^{-1}\|\|B_E\|
 +\|\widehat{\mathcal D}_b\|\|\widehat A_h^{-1}\|\|B_E-B_{\widehat E}\|,
\]
\[
 A_h^{-1}-\widehat A_h^{-1}
 =A_h^{-1}H(\mathcal G_b-\widehat{\mathcal G}_b)\widehat A_h^{-1}.
\]
同时 E−\widehat E=\mathcal G_b(w−\widehat w)+(\mathcal G_b−\widehat{\mathcal G}_b)\widehat w。白化与实化 operator norm 应一并乘入。

因此“实现的 forward/adjoint dot-product test 通过”只表明其**内部互为伴随**；它不代表它们接近 full Maxwell 的 J/J*。实验须另测 full-model residual pullback、方向导数及 task interpolation，而非只看 current angle。[P21]

## 8. T3d：解析材料恢复的局部误差

对一个 voxel，把所有 source/vector components 叠成 J_i、E_i，使用正权 W_i。真值 J_i=a_iE_i。令 \(\widehat E_i=E_i+\delta E_i\)、\(\widehat J_i=J_i+\delta J_i\)，且 \(\|\widehat E_i\|_{W_i}>0\)。LS 系数满足
\[
 \widehat a_i-a_i=
 \frac{\widehat E_i^*W_i(\delta J_i-a_i\delta E_i)}
 {\widehat E_i^*W_i\widehat E_i},
\]
\[
 |\widehat a_i-a_i|\le
 \frac{\|\delta J_i-a_i\delta E_i\|_{W_i}}
 {\|\widehat E_i\|_{W_i}}.
\]

**证明。** 把 \(\widehat J_i=a_i\widehat E_i+\delta J_i-a_i\delta E_i\) 代入比值，再用 Cauchy–Schwarz。

若材料恢复在 χ 坐标进行，需乘局部 \(\sup|d\chi/da|\)，并保证 inverse constitutive map 远离 pole。暗区场能量趋零时本界发散，这是真实可识别性问题。加入分母 ridge 可改善数值稳定但产生偏差，不可伪装成免费无偏恢复。

## 9. T3e：有限幅度图像误差的条件界

在声明的可行先验集合 \(\mathcal C_0\) 内，若存在 secant lower bound
\[
 \|f(x)-f(x_*)\|\ge\sigma_{rec}\|x-x_*\|,
\]
且 \(\|y-f(x_*)\|\le\delta\)、\(\|\widehat f(\widehat x)-y\|\le\eta\)、\(\|f(\widehat x)-\widehat f(\widehat x)\|\le\varepsilon_f\)，则
\[
 \boxed{\|\widehat x-x_*\|\le(\eta+\delta+\varepsilon_f)/\sigma_{rec}.}
\]
证明仅用三角不等式与 secant lower bound。局部 Jacobian 满列秩加足够小的 Lipschitz 扰动可导出局部版本；仅在一点满秩不能无条件给任意有限幅度界。

A23 的 p=3456>m=1536，不可能在全材料开放邻域内具有这样的统一局部线性 lower bound。限制先验 manifold 可以降低有效维数，但真值不在该 manifold 时必须报告 approximation bias。[P23r]

另一种比较是**同一先验 MAP 的模型误差**：若真实与近似 objective 在共同凸局部邻域有 μ-strong monotonicity，且梯度误差上界 ε_g，则各自最优点间距离 ≤ε_g/μ；其中可取 ε_g≤ε_J R_res+L_J ε_f。证明由两组 variational optimality inequalities 相加及强单调性。这个界比较 MAP 解，不证明 MAP 接近不可识别真值。

## 10. 弱信息、全图与约束

不能沿用全材料 isotropic L2 作为唯一先验。最小实验统一采用 full-grid TV 或 multiscale sparse penalty，并允许非平滑边界；固定小 shape chart 仅作有明确 bias 的专门 baseline。

物理域在 χ/constitutive parameters 中定义：passivity、允许的实部范围、有限损耗、pole margins。多频共享色散参数，不逐频任意修补。有限数据支持的 stable directions 与 prior-completed directions 分开报告；同一 prior 用于所有 feedback 消融。

**无全局图像界的反例：** f(x1,x2)=x1。任意 x2 改变不影响 measurement。再精确的 feedback 或 NN 都不能从这份 data 区分两个 x2；只能由先验选择。物理一致性缩小可行集合，但不增加该 measurement 的 Fisher information。

## 结论

OM 可以在条件性任务类里胜过 TSOM，也可能输。应允许 current error 略大但 image 更好；也应拒绝 current residual 更小而材料不可行的结果。SA-RF 最值得测试的是“full material excitation / compressed propagation”的误差位置是否更有利，而不是新的字母排列。
