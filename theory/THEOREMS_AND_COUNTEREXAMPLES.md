# A24｜定理、证明与反例

本文全部有限维结果在声明的离散模型下成立，不自动构成连续Maxwell离散误差定理。*为Hermitian adjoint，T为transpose；实材料梯度用realification后的adjoint。质量归一后使用Euclidean范数。基础线性代数、Woodbury、resolvent和DWR机制有既有先例；这里不主张这些数学工具首创。[R18–R23]

统一记号：L_b=I−A_bG，R_b=L_b^{-1}，j_b=R_b b，h=a(χ)−a_b，H=diag(h_iI_d)，L_a=L_b−HG，e_b=e_inc+Gj_b。\(\mathcal G_b=GR_b,\mathcal D_b=SR_b\)。多源共享χ。

## T1｜P-seed elimination 与传播保留

### 假设

U*U=I，L_b与A_U=U*L_bU可逆。R_U=UA_U^{-1}U*，Π=I−UU*，K=Π(I−L_bR_U)。每个参考特解j_{b,s}∈Range(U)。删除P时保持U、其它raw seeds、rank规则、传播算子及decoder不变。

### 结论

Kb_s=0；任意线性feedback递推的P descendants均为零。因此从basis construction删除这条**零链**不改变精确表示。它不删除内部反馈。

### 证明

j_b=Uc，b=L_bUc，于是R_Ub=UA_U^{-1}U*L_bUc=Uc=j_b；故Kb=Π(b−L_bj_b)=0。线性作用于零仍为零。

取U的正交补Q，定义T_Q=(I−R_UL_b)Q、K_Q=Q*(I−L_bR_U)、C_Q=Q*L_bT_Q。由block Gaussian elimination，
\[
 R_b=R_U+T_QC_Q^{-1}K_Q.
\]
P=0只消去第二项对b_s的响应，不消去它对材料RHS B_sv的响应。特别是C_Q及其逆一般非平凡。

### 近似锚定

若\(\widehat j_b\in U\)，r=b−L_b\widehat j_b，则K L_bU=0，故Kb=Kr。删除未表示的源响应时
\[
 \|e_j\|\le\|T_QC_Q^{-1}K_Q\|\|r\|,
 \quad\|e_y\|\le\|ST_QC_Q^{-1}K_Q\|\|r\|.
\]
不能仅用||r||小就宣布输出误差小。

### 反例与算法后果

L_b=[[0,1],[1,0]]可逆，U=e1却使A_U=0，证明前提不满足。L=diag(1,ε²)、被删RHS=εe2、S=e2^T，seed很小而data=1/ε。

改变U以装入sources可能挤掉receiver方向；T1不保证这项额外改变无损。更干净的 **affine anchor** 是直接写j=j_b+Δj并精确相减得(L_b−HG)Δj=He_b；它不要求j_b占correction basis，也不意味着旧U下Kb本来为零。固定receiver预算的消融应采用此式。

## T2｜OM与TSOM的等价/非等价

### 假设与空间

A=O^⊥是observable split的ambiguous空间，P_A其正交投影，D为内部G的选定right-singular空间。教材理想TSOM空间A∩D，投影实现为P_AD。[B01 eqs.6.70–6.71]

### 结论与证明

总有A∩D⊆P_AD，因为v∈A∩D时P_Av=v。等号成立当且仅当P_AD⊆D；这等价于D对P_A不变。由于P_A自伴随，该不变性也使D^⊥不变，等价于P_A与P_D可交换。

若OM使用current bankV_M，则它与指定TSOM correction space等价当且仅当Range(V_M)等于该空间；同维度或相同标签都不够。若只要求保留某组材料任务，充分条件是该组所有真实correction被两个表示共同包含，并使用等价物理求解/度量；这弱于空间整体相同，但强于只看principal angles。

### 可精确等价的常见充分条件

若O⊆D，则P_A与P_D可交换，D=O⊕(A∩D)，因而P_AD=A∩D，维数为dim(D)−dim(O)。这正是M0−L维度公式的一种明确充分条件。一般非嵌套空间只能使用dim(A∩D)=dim(D)−rank(P_O|_D)，不能无条件假定M0−L。原TSOM的具体算子空间是否满足这种包含或足够接近，需要原文假设及数值检查；不能由一个任意矩阵反例否定其已报告算法。

### 反例

R³中O=span(e1)，D=span((e1+e2)/√2,e3)。A∩D=span(e3)，但P_AD=span(e2,e3)。而A∩D^⊥={0}，所以O、A∩D、A∩D^⊥三者并不自动填满R³。此反例限定任意投影的数学关系，不是在宣布原TSOM算法无效。

### 材料感知的条件性最优性

令材料随机扰动零均值、covariance Γ，X_s=R_bB_sδx。对rank-r正交投影P，
\[
 \mathbb E\sum_s\|(I-P)X_s\|^2
 =\operatorname{tr}C_M-\operatorname{tr}(PC_M),
\quad C_M=\sum_sR_bB_s\Gamma B_s^*R_b^*.
\]
最大化trace项由C_M前r特征向量完成，故该M空间在指定prior的current误差下最优。证明是Hermitian特征分解后的Ky Fan变分原理。它不证明image最优；prior未覆盖的OOD方向就是反例。

### 等价变量变化

Δj=R_bw是可逆变量变化，故完整空间的物理表示等价；但是R_b通常非酉。源空间普通Euclidean SVD与原current SVD并不等价。把current范数拉回w空间得到R_b*R_b度量，才恢复相同几何问题。

## T3｜截断、反馈、数据与图像误差

### 假设

A_h=I−H\mathcal G_b及\widehat A_h=I−H\widehat{\mathcal G}_b可逆。w=A_h^{-1}He_b，\widehat w=\widehat A_h^{-1}He_b。

### 精确误差与证明

定义r_h=H(\mathcal G_b−\widehat{\mathcal G}_b)\widehat w。由A_h\widehat w=He_b−r_h，
\[
 w-\widehat w=A_h^{-1}r_h,
\quad \Delta j-R_b\widehat w=R_bA_h^{-1}r_h,
\quad y-\widehat y=\mathcal D_bA_h^{-1}r_h.
\]
范数界直接取operator norm。若接收缓存也近似，额外加
\(\|(\mathcal D_b-\widehat{\mathcal D}_b)\widehat w\|\)。

对隐含current \(\widehat j=j_b+R_b\widehat w\)，完整state残差
\[
 L_a\widehat j-A e_{inc}=-r_h.
\]
证明将j_b方程相减，并用L_aR_b=A_h。该式不意味着在线已经支付了R_b\widehat w或full residual评估。

### 固定current子空间的误差另计

V,W列正交，W*LV可逆，β=σ_min(W*LV)>0，Petrov解\widehat j=V(W*LV)^{-1}W*b。对任意v∈V，
\[
 \|j-\widehat j\|\le(1+\|L\|/\beta)\|j-v\|.
\]
证明为\widehat j−v=V(W*LV)^{-1}W*L(j−v)，再三角不等式和取inf。它说明小projection error还需稳定core；仅principal angles不够。

### 局部材料ratio界

单体素、跨全部源/分量堆叠E、J=aE。估计\widehat E=E+δE、\widehat J=J+δJ，W≻0，\widehat E≠0。无ridge的共同least-squares给
\[
 \widehat a-a=\frac{\widehat E^*W(\delta J-a\delta E)}{\widehat E^*W\widehat E},
\quad |\widehat a-a|\le\frac{\|\delta J-a\delta E\|_W}{\|\widehat E\|_W}.
\]
由直接代入及Cauchy–Schwarz得证。暗场分母趋零时无统一界；χ(a)转换还需整个连接路径避开constitutive pole，并乘\(\sup|dχ/da|\)。ridge额外产生bias，不能沿用无ridge等式。

### 条件性图像界

若可接受prior集合Ω上，在所考察局部区域有secant下界
\[
 \|W[f(x)-f(x_*)]\|\ge\sigma\|x-x_*\|,\quad\sigma>0,
\]
且y=f(x*)+n、||Wn||≤δ、||W(\widehat f(\widehat x)−y)||≤η、||W(\widehat f−f)(\widehat x)||≤ε_f，则
\[
 \|\widehat x-x_*\|\le(η+δ+ε_f)/\sigma.
\]
证明为data空间三角不等式再除σ。这是局部/受限识别性条件，A23的p>m全开放材料域通常不具备它。f(x1,x2)=x1直接反驳全局bound。

若只比较同一prior的两个MAP局部解，真目标梯度μ-strongly monotone，surrogate梯度误差≤ε_g，则两解距离≤ε_g/μ。由一阶最优性及strong monotonicity证明；约束convex时用相应variational inequalities。ε_g可界为ε_J R_res+L_J ε_f。该结果比较算法解，不消除prior bias，也不保证离真值近。

## T4｜有限反馈阶数与少层网络稳定性

### 反馈多项式：无需收缩的恒等式

I−F可逆，p_d(F)=Σ_{j=0}^d F^j。则
\[
 (I-F)^{-1}-p_d(F)=(I-F)^{-1}F^{d+1}.
\]
证明用(I−F)p_d=I−F^{d+1}。仅在可验证的诱导范数||F||=η<1时，才能进一步得到η^{d+1}/(1−η)型几何界。

反例F=[[0,100],[0,0]]：ρ(F)=0，但degree0误差100；degree1才精确。被动介质、特征值小、浅层经验稳定，均不能替代非正规resolvent/power控制。

### 有理小核心：不需要Neumann收敛

T7直接解\widehat A_h，不要求ρ(H\widehat G_b)<1。误差由T3控制；局部块和K_h的σ_min须远离零。可逆不代表数值条件良好，小core谱半径也不能取代σ_min。

### 外层material blocks：条件性稳定而非全局收敛宣称

在一个凸局部区域，设f的Hessian满足μI≼∇²f≼LI，0<μ≤L，步长0<τ<2/L，Prior_θ为ℓ_θ-Lipschitz，Π_C为闭凸集合的Euclidean投影。则
\[
 \Phi(x)=\Pi_C\operatorname{Prior}_\theta(x-\tau\nabla f(x))
\]
的Lipschitz常数不超过
\[
 q=\ell_\theta\max(|1-\tau\mu|,|1-\tau L|).
\]
证明：两点gradient差为连接线段平均Hessian乘以两点差，其谱仍在[μ,L]；再用复合映射Lipschitz界。若q<1且区域被映射到自身，Banach定理给唯一固定点及几何收敛。

**限制**：Maxwell inverse objective不自动局部强凸，普通CNN也不自动ℓ≤1；固定点不是自动等于truth或MAP。预条件D≠I需在相应metric重新推导，不能偷用Euclidean常数。若实际Prior还接收χ、gradient、field等额外conditioning features，必须把它们对x的依赖纳入完整Jacobian/Lipschitz界：例如分量Lipschitz常数为ℓ_0、ℓ_i且feature映射为L_i-Lipschitz时，界变为ℓ_0 q_gradient+Σ_i ℓ_i L_i。上面的单输入公式不能直接认证本包所有feature-conditioned网络。

若第k层仅有有限Lipschitz常数q_k，模型/gradient近似引入单层误差ε_k，则两条轨迹
\[
 \|\widehat x_K-x_K\|\le\left(\prod_{j=0}^{K-1}q_j\right)\|\widehat x_0-x_0\|
 +\sum_{i=0}^{K-1}\left(\prod_{j=i+1}^{K-1}q_j\right)\epsilon_i.
\]
通过递推证明。这比无依据地宣称“2–3层收敛”更准确；层数优越性必须实验检验。

## T5｜共同材料与physics-native consistency

### 固定field/current的必要充分条件

在一个体素，将全部源/矢量分量堆叠E和J。存在共同scalar a使J=aE，当且仅当E≠0且J∈span(E)，或E=0且J=0。由标量乘法定义即得。E≠0时最佳weighted LS的最小残差为
\[
 \|J\|_W^2-\frac{|E^*WJ|^2}{E^*WE}.
\]
证明将二次式配方。E=(1,1)、J=(1,2)给a=1.5但残差不为零，反驳“每源预测current后取平均材料便自动物理一致”。

### B的共同材料结论

所有源使用同一个h、同一个\widehat G_b并解w_s=H(e_b,s+\widehat G_b w_s)，则严格满足同一材料的**surrogate state/source consistency**。full-Maxwell残差仍为T3的−r_h。由共同方程直接得证。

约束必须施加在最终χ，而不是错误地要求Im h≥0。相对于有耗背景减少损耗时，合法材料的h可以有负虚部。DDA极化率还须遵守原CM/RR转换；χ-passivity不能被任意polarizability clipping替代。

若A中对ratio得到的χ再投影到可行域，原预测J一般不再满足新χ的constitutive关系；必须报告这个residual或重新计算state。投影后的合法材料与物理一致current是两项不同要求。

tensor材料时E和J为矩阵，识别3×3本构张量需要足够独立照明，并需对称性/PSD损耗约束；scalar ratio不得逐分量误用。

## T6｜完整摊销复杂度

### 假设与结论

两方法达到预先固定的同一quality和feasibility标准；offline时间O_i可复用N次，warm时间t_i包含全部online必需动作。则
\[
 T_{new}<T_{base}\iff O_{new}-O_{base}<N(t_{base}-t_{new}).
\]
证明为总时间O_i+Nt_i直接相减。额外offline为正且warm不更快时永远不能回本；warm节省为正时cross-over为ΔO/Δt。不同quality、不同acquisition复用范围时前提不成立。

反例：offline多100秒、每图只省1毫秒，需要超过100000次才回本；这不是一次性成像的实际优势。算法后果是cold/warm/N=1,10,100均报告，不用rank代替walltime。

## T7｜完整材料源与低维反馈求解可以分离

### 假设

\widehat G_b=D+UV*，U,V∈C^{n×k}，I−HD和K=I−V*C_hU可逆，C_h=(I−HD)^{-1}H。H可以是完整逐体素材料差，不要求低维chart。

### 结论

\[
 c_s=K^{-1}V^*C_he_{b,s},\qquad
 \widehat w_s=C_h(e_{b,s}+Uc_s)
\]
精确求解该surrogate的所有源，且只需一次共同k×k分解。若\widehat G_b=G_b，则给出精确离散Maxwell数据。

### 证明

从w=H(e_b+Dw+UV*w)得到w=C_he_b+C_hU(V*w)。令c=V*w，得到Kc=V*C_he_b，反代即得。

### 反例、边界与后果

不同H使C_h e_b改变，可产生不在固定Range(U)内的source。故“feedback rank k”不等于“材料/电流rank k”。本轮合成rank2示例验证了此差别，但不是实际Maxwell成像证据。

分解也可能人为breakdown：H=D=1而UV*=−1，完整G_b=0、state完全良态，但I−HD=0。此时应记录factorization failure，按预注册规则换分解或拒绝，不能偷偷ridge然后说同一恒等式仍精确。

当3D近场使D必须很大、或低秩余项k接近n时，T7仍正确但可能毫无速度优势。需要T6而非只用T7宣布算法成功。

## 附命题｜正确的dual-weighted residual形式

任意X_hat≈L^{-1}B、Z_hat≈L^{-*}S*，令
\[
 H_c=SX_{hat}+Z_{hat}^*(B-LX_{hat}).
\]
则
\[
 SL^{-1}B-H_c=(S-Z_{hat}^*L)L^{-1}(B-LX_{hat}).
\]
展开左侧即得。若去掉correction，写成同一双侧乘积，需要额外RLR=R等Galerkin投影性质。标量L=S=B=1、R=1/2时，真实未修正defect=1/2，错误乘积=1/4。learned closure不能自动使用Galerkin专有恒等式。[P23c; R19]

## 数值核验的边界

`verification/algebra_checks.py`以小型合成矩阵检验T1/T2/T3/T5/T7和上述反例，全部assertions通过。矩阵不是物理Green算子，没有训练，也没有真实材料图像。Gate1的代数正确性得到支持，Gate2–Gate5仍需真实Maxwell实验，不因本文件而自动通过。
