# A24｜最终理论裁决与路线选择

日期：2026-10-08。

## 裁决

**GO：一个小型、无需NN的真实Maxwell机制实验。HOLD：OM-SOM-Net架构收益。NO-GO：现在就启动大型3D训练。**

本轮找到值得检验的算法差别，不是“OPM删P改名OM”，而是：

> 已知source特解作affine anchor；完整逐体素材料产生相对source；只压缩它返回内部场的作用；通过同一material-conditioned小核心完成多源反馈，并使用一致的receiver adjoint更新材料。

这条路线称SA-RF。它有明确的精确极限、误差界和成本失败条件，但本轮尚无真实Maxwell成像/速度/泛化胜利。原TSOM 2009、FFT-TSOM 2011及若干关键最近邻全文未成功取得；已读作者教材的具体公式、SOM-Net方法原文、A23指定理论文件的可获取主文和A20–A22主要结果；部分长报告与原论文全文仍有缺口，逐项范围见来源账本。**新颖性未完成最终清关。**

## 1. 对13个核心问题的逐项回答

### 1）TSOM真的有适合改成OM的O/P分解吗？

有observation与internal-propagation双重考量，但它不是A23的O/P seed分解。经典第一重分离数据可确定current与ambiguous current；第二重限制内部G的谱相关current空间。可以设计TSOM-inspired OM，不能直接把原论文一个叫P的bank删掉。[B01; R01,R02]

### 2）A23 P redundancy能迁移到什么？

只迁移到“已知source particular solution已精确保留后，旧forcing在Schur complement的剩余激发为零”这一结构。它可删该P seed及descendants；不能迁移为“内部传播谱无用”或“KBv也为零”。

### 3）能否删除独立P，同时保留传播和正则化？

传播可以通过Schur/relative inverse精确保留；正则化必须另外保留其projector/penalty，或者明确替换。没有任何P-zero定理自动保留TSOM second fold。优先affine anchor，不挤占receiver-retained预算。

### 4）M能否比TSOM第二重空间更material-relevant？

在声明的材料prior和任务loss下可以：R_bBΓ^{1/2}的主空间优化对应current平均误差，bare G谱通常不优化这个目标。但没有普适material-image优势，OOD或有限幅度反馈可以使结论反转。固定rank4/32材料chart不应再次成为全图瓶颈。

### 5）原SOM-Net最小怎么改？

A：保留data-determined current、BP/参考初值、解析field与共同材料LS；NN从预测任意full current改为预测材料激发ambiguous basis中的少量系数，保留soft second-fold选项。它是迁移control，不是目前最强novelty候选。原SOM-Net的核心本来就包含current学习和解析材料恢复。[R04]

### 6）能否构造更强feedback-native网络？

数学上可以，推荐B/SA-RF：full χ hypothesis→full material source→小有理feedback closure→data residual→严格surrogate adjoint→small prior correction。它不是原SOM-Net的等价实现，而是继承其物理交替精神的新计算路径。是否“更强”尚待Gate3/4证明。

### 7）Schur/relative algebra到底增加了什么？

增加的是可明确分工和控制误差的实现：source anchor可独立于correction rank，材料源可独立于反馈秩，重复散射可在小material-conditioned core中求和，primal/dual误差可分别审计。它没有创造新的Maxwell物理，也没有增加measurement Fisher information。SOM-Net使用原物理场方程，已有CIE-I/ROM/current-network先例必须作为强对照。

### 8）目前能认定哪种增量价值？

已经成立的是条件性代数删除、共同材料surrogate consistency和误差分解。更快、更准、更少训练样本、更少层全部未建立。最有希望的是让NN不再学习部分已知多次散射相互作用；最危险的是offline背景solve和online nqs/nk²成本抵消收益。

### 9）能否天然降低NN输出维数？

A把2ns个实current输出变为2rs个系数，但可能排除真实current。B直接预测一个共享材料image，输出p=2N，而不是每源每分量的2dNs；完整材料源由解析物理计算，不缩成固定小chart。对于A23的d=3,s=6，这个形式上的NN输出维数比为18，但不是18倍FLOPs、速度或训练量提升。

### 10）能否更少unrolled layers？

有合理机制：一个小有理core逆已包含其surrogate中的所有阶反馈，2–3个block表示2–3次材料修正而非只保留2–3阶散射。没有一般2–3层收敛定理；非正规反例否定单靠谱半径的浅层保证。必须与原4-block SOM-Net及同深度/同容量基线分别比较。

### 11）是否无需NN就可能足够？

是。B的Prior换成TV/wavelet proximal，或C使用Gaussian/GMM/结构化先验，就是合法无NN版本。若它已达到同样quality/time目标，不必为了网络名义增加训练。

### 12）有真正强TAP新颖性潜力吗？

有条件潜力，尚不是已成立算法论文。候选贡献应是“完整材料源、低成本feedback closure、共同材料/adjoint一致性、3D误差—成本证据”的具体组合与机制，而不是OM名字。ICLM、CS-Net、PM-Net、CIE-I、WT-TSOM、CCR2025、VBRL2025、DeepCSI2025及CSPDNN2026都压缩了泛泛current/physics-unrolling的新颖性空间。[R06–R16,R26,R27]

### 13）只投入一次小实验，先测什么？

同一full-grid χ、同一affine anchor、同一TV/可行域/初始化，比较L无relative反馈、F精确反馈、R便宜反馈。优先强已知背景+中等相对变化，加入asymmetric/shell。F告诉我们物理机制是否有价值，R告诉我们能否便宜保住它。这比先训练一个OM-SOM-Net更有判别力。

## 2. 主候选的完整核心

\[
 j=j_b+R_bw,\qquad w=H(e_b+\mathcal G_bw),
 \quad\mathcal G_b=GR_b,\quad y=y_b+\mathcal D_bw.
\]

选择\(\widehat{\mathcal G}_b=D+UV^*\)，保持完整逐体素H：
\[
 C_h=(I-HD)^{-1}H,\quad K_h=I-V^*C_hU,
\]
\[
 c_s=K_h^{-1}V^*C_he_{b,s},\qquad
 \widehat w_s=C_h(e_{b,s}+Uc_s).
\]

小的是feedback solve，不是图像。\(\mathcal D_b=SR_b\)由q个receiver-adjoint RHS缓存，避免online背景solve；nq缓存、nk²组装与nqs收缩必须计费。

对应完整物理缺陷
\[
 r_h=H(\mathcal G_b-\widehat{\mathcal G}_b)\widehat w,
 \quad y-\widehat y=\mathcal D_b(I-H\mathcal G_b)^{-1}r_h.
\]

近共振/非正规放大可让小传播误差变成大输出误差。强绝对contrast但小相对h只有在参考resolvent不过大时才可能有利。

## 3. A/B/C选择顺序

| 路线 | 定位 | 当前决策 |
|---|---|---|
| A minimal OM-SOM-Net | 最近的实现迁移、output restriction control | 保留设计，暂不训练 |
| B SA-RF | 主物理机制候选，full-source/压缩传播 | 首先做无NN L/F/R小实验 |
| C prior completion +一次recoil | 可能更便宜的实用竞争者 | 与ordinary adjoint+prior一起保留 |
| 原SOM/FFT-TSOM/CIE-I、ordinary adjoint、affine ROM | 强基线 | 不因新名称降低其预算或实现质量 |

若B的精确反馈都没有可测headroom，不直接改用大NN“救B”；转向C/ordinary adjoint，或者停止。若只有精确反馈有用而压缩失败，保留反馈机制结论，但当前SA-RF低秩架构NO-GO。

## 4. A20–A23证据如何影响本轮

A20早期current/reduced-step表现不能外推晚期；A21实际证明的是五个暴露states的oracle两侧GN fidelity，不是可部署网络优势；A22-R1 A2/A3相同projector导致零增量；A23全材料、弱信息和quadratic sketch失败说明不能再仅靠小chart和isotropic L2。[P20,P21,P22,P23r]

A23删P试验还混入source替换receiver方向，不能作为P物理不可删的证据；但它的完整cold计时清楚表明，cached Schur本身没有带来实质速度提升。因此B必须换“压缩对象”和计算布局，而不是再围绕OPM标签优化。

## 5. 本轮实际完成的验证

合成CPU测试通过source P-zero、Schur inverse、relative identity、core closure、real adjoint、retained coupling、共同材料和非正规反例。几个代表值：P/forcing≈2.82e−16；Schur inverse误差≈3.74e−16；relative identity≈1.47e−15；small-core误差≈1.68e−16。删除retained coupling的合成反例误差≈4.04%。

这些不是Maxwell Green矩阵实验，没有成像，没有NN，没有GPU，也没有A24 time-to-image数据。某个rank2合成示例93.22%的fixed-current projection误差仅说明两种限制不同，不是对TSOM的实测结论。

| Gate | 本轮状态 |
|---|---|
| 1 P-removal correctness | 数学条件已证明，小型代数支持；真实后端复核待执行 |
| 2 OM physical sufficiency | NOT_RUN |
| 3 feedback incremental mechanism | NOT_RUN |
| 4 architecture headroom | NOT_RUN |
| 5 full cost headroom | NOT_RUN |
| 关键最近邻全文清关 | PARTIAL；不得声称first |

## 6. 底线

**保留全部局部材料激发，压缩可控的内部反馈，而不是把材料和电流一起压进一个固定小空间。** 这是本轮最值得投入一次小实验的想法。它足够具体，可以被真实Maxwell数据否证；也足够诚实，即使最终普通adjoint+prior更优，也能给出明确结论而不需要继续包装OM。
