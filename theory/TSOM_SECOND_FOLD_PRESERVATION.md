# A24｜TSOM 第二重约束：哪些保留，哪些被替代

## 1. 最重要的区分

TSOM 的第二重 subspace 来自内部 current-to-field 算子 G_D 的谱；A23 的 P_raw=Kb 来自已知照明 forcing 的 Schur 残差。前者是**传播与正则化的建模选择**，后者是**构造 current bank 的种子**。删除后者不等于删除前者，也不会自动保留前者。[B01 §6.4.2–6.4.3; P20code; P23a]

原 TSOM 2009 和 FFT-TSOM 2011 的全文本轮未成功取得，以下原方法细节以作者教材的明确公式为依据；不把后来的教材表述、近似实现和原论文逐字等同。FFT-TSOM 的已有3D应用也已在教材 §6.4.4 核对。[R01,R02]

## 2. 数学对象与非等价性

设观测强空间 O=Range(Q_o)，P_-=I−Q_oQ_o*，A=Range(P_-)；内部传播强空间 D_k=Range(V_{D,k})，来自 G_D 的前 k 个右奇异向量。

教材理想式(6.70)使用 A∩D_k；近似式(6.71)使用 Range(P_- V_{D,k})。二者一般不同：
\[
 A\cap D_k\subseteq P_-D_k,
\]
且等号成立当且仅当 D_k 对 P_- 不变，即两个正交投影可交换。不要用 principal-angle 很小替代这条精确条件。证明与三维反例见 `THEOREMS_AND_COUNTEREXAMPLES.md` T2。

另一个合理但不同的方法，是对 G_D 限制在 A 上后作 SVD，即分解 G_D Q_A，得到 A 内按内部场贡献排序的右空间。它不是原来的“两次分别SVD再取交集”，应称 **restricted-internal-operator baseline**，而不是声称原TSOM本来如此。

## 3. TSOM 正则化究竟提供什么

原方法把数据中可靠的一部分先确定，再限制需要非线性搜索的剩余电流。内部谱或 Fourier 近似避免在大量弱传播/高空间频率方向上自由搜索；逐渐扩展第二重空间提供 coarse-to-fine continuation。对于固定 acquisition，G_S、G_D 的预处理可复用；FFT-TSOM 已经通过 Fourier basis 避免完整 G_D SVD。[B01; R02]

不过，“G_D δj 很小”不等于“删除 δj 后完整 state residual 很小”：
\[
 \delta r=(I-A G_D)\delta j,
\]
这里仍有未被 G_D 滤掉的 δj 本身。传播谱截断是有用的 regularized model reduction，不是把 Maxwell current 的某些分量证明为结构零。尤其一个尖锐材料边缘可以产生细电流结构，同时只产生较平滑的内部场。

这正是 SA-RF 候选的动机：**完整保留材料源的局部项，只压缩它返回内部场的作用。** 它不是原 TSOM 第二重 hard current truncation 的同义替换。

## 4. Architecture A：可精确保留的实现

A 中令 j_s=j_{o,s}+V_M c_s，其中 j_o 包含已知参考特解和数据确定的修正。

### Hard intersection

构造
\[
 V_A=\operatorname{orth}\bigl(\operatorname{Range}(V_M)\cap A\cap D_k\bigr).
\]
这样保持所声明的 hard admissible current correction，但可能损失重要材料激发，rank还可能变成零。若原先 hard constraint 作用在总电流而不是 correction，必须连同 j_o 检查 affine set 是否可行；只限制 c 不会自动限制 j_o。

### Soft spectral regularization

更温和地使用
\[
 R_2(j)=\frac\lambda2\sum_s\|(I-P_{D_k})j_s\|^2.
\]
在 c 坐标下 Hessian 为
\[
 \lambda V_M^*(I-P_{D_k})V_M,
\]
并存在来自 j_o 的线性项
\[
 \lambda\operatorname{Re}\sum_s c_s^*V_M^*(I-P_{D_k})j_{o,s}.
\]
不能漏掉 affine anchor 的交叉项，然后宣称惩罚与原始总电流版本等价。

软谱权重可取 ψ(σ_i)，对较小内部奇异值施加较强惩罚。直接惩罚 ||G_D j||² 会反而更强地抑制大奇异值方向，不是同一个 TSOM 正则化。所有权重、k 和噪声关系在 validation/先验阶段冻结。

### Fourier / wavelet realization

可用低频 Fourier projector 或多尺度 wavelet filter 近似 P_D，但需把这种近似与 exact internal SVD 分开报告。Fourier/wavelet 替代以及渐进扩展均有直接先例，不能作为本轮独立创新。[R02,R11]

## 5. Architecture B：哪些作用被替代

B 的相对材料源满足
\[
 w=H(e_b+\widehat{\mathcal G}_b w),\qquad j=j_b+R_b w.
\]
这里 w 一般不在固定低维 current subspace 内。内部传播的谱/局部结构进入 \(\widehat{\mathcal G}_b=D+U_gV_g^*\)，而不是把 w 本身截成 U_g c。

因此 B 对原 TSOM 第二重约束的结论是：

| 原作用 | B中的状态 | 具体条件 |
|---|---|---|
| 内部 current-to-field coupling | 近似保留；完整算子时精确保留 | 用独立 action / residual 检查 |
| hard current-space 截断 | **未保留，被替代** | 改为完整材料源 + 传播压缩 |
| 小维度非线性联立反馈 | 保留为 k×k material-conditioned core | 局部块及core均可逆 |
| 噪声正则化 | 由 data likelihood + 材料prior替代 | 必须与对照使用相同prior |
| coarse-to-fine | 可保留，但不是默认免费 | 预注册nested rank/scale，计算成本累加 |
| 当前数据可靠分量精确冻结 | 默认不硬冻结 | 噪声下用soft data consistency |
| 全current输出 | 不作为在线必需输出 | 计算 R_b w 需另付费 |

若坚持原 TSOM penalty，需计算
\[
 \|(I-P_D)(j_b+R_b w)\|^2.
\]
对完整逐体素 w，作用 R_b 一般不便宜。把它改成 ||(I-P_D)w||² 会改变度量与物理变量，不能称 exact preservation。可以离线压缩相应 penalty operator，但其额外cost/error必须进入账本。最小B不采用这个昂贵修补，而明确把 hard second-fold constraint 替换为 propagation-error budget 和材料regularization。

## 6. Architecture C：保留弱信息的不确定性，而非强行删除

C 用稳定 likelihood directions 判断哪些材料分量由数据支持，哪些主要由先验补全。这个split是 material/noise/prior相关的，不等于 G_D 的谱分解。弱方向不置零，而以 Gaussian/GMM、wavelet或小NN给出先验条件推断，再做 nonlinear feedback consistency correction。

它保留了 TSOM 的“不要让不可靠自由度任意拟合噪声”的精神，但改变了正则化对象。不要宣称既保留原TSOM全部稳定性定理，又同时拥有一个不同的 posterior 模型。

## 7. M 能否比第二重空间更 material relevant？

可有条件地可以，不能普遍成立。给定材料prior协方差 Γ、参考fields及任务loss，材料驱动 covariance
\[
 C_M=\sum_s R_bB_s\Gamma B_s^*R_b^*
\]
的前r个特征向量最小化该声明分布下的平均 current projection error。G_D 的无材料谱一般不最小化这个量。这给出材料感知选择的严格意义，但不是 material image NRMSE 最优定理。

反例也直接：训练prior把某个材料方向方差设为零，该方向对应的真实对象可被M漏掉，而TSOM较宽的内部空间保留它。3D强散射/近接触时，训练材料激发与真实OOD激发相差很大，M的条件优势可能反转。

**建议：A用soft second-fold作为独立消融；B保留完整材料源、验证传播误差；C保留完整材料prior。不要强迫三种架构都服从同一个hard current truncation。**
