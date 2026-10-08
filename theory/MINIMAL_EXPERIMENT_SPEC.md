# A24｜最小、可证伪、顺序执行的实验规范

**本轮实际只运行了附带的CPU合成代数测试；以下真实Maxwell与网络实验均为NOT_RUN。** 阈值是执行前拟定的工程筛查标准，不是数学定理；执行者须在看到输出前保存完整配置、代码版本和hash。失败后不得改阈值、rank或先验并沿用原gate名称。

## 0. 只做一次实验时：优先B0，不训练NN

最有判别力的问题不是“P删了以后rank少多少”，而是：

> 在同一完整材料参数化、同一先验、同一affine参考特解下，精确relative feedback是否比dressed-linear模型改善图像？若有，低成本传播closure能否保住这一收益？

三臂为L（无relative反馈）、F（精确relative反馈）、R（SA-RF约化反馈）。F的“oracle”仅指使用精确物理算子，**不允许读取未知truth-state Jacobian或真实材料**；它在算法当前候选χ处执行完整forward/adjoint并如实计费。它是机制上限对照，不自动是快速部署候选。

结果分流：F不优于L→先验/可识别性/优化预算可能主导，不训练B；F优于L但R失败→反馈有价值、当前压缩失败，不用NN掩盖；R保留收益且有成本余量→才考虑小网络迁移。

## 1. 数据与后端冻结

### 2D机制主平台（拟定默认配置）

2D TM、24×24 cells、8 sources、32 receivers。domain与频率使用无量纲k·length定义并写manifest，建议domain边长1个自由空间波长，source/receiver在domain外闭合曲线上。所有方法使用同一G、S、self-term、离散积分权重、time convention、noise packing和constitutive map。不得把2D scalar结果写成3D验证。

两个参考类别：弱均匀背景；已知较强有耗inhomogeneous背景。默认χ_b分别为0.1+0.04i，以及已知环形区域χ_b=2+0.1i、其余0.1+0.04i。几何mask在config写出，不从待重建truth提取。若现成后端的材料规范不同，必须先明确换算并冻结，不能直接把这些χ数值当DDA polarizability。

四个parent对象：两个多尺度shell、两个非对称分段材料，支持位置/厚度在生成配置中固定；每个parent两个相对幅度，max|Δχ|建议0.3与1.2；保持所有最终材料被动。2 backgrounds×4 parents×2 amplitudes=16个clean full-wave states，主noise为无噪声和20dB，共32个观测条件。noise相对于每个state的差分data RMS定义并保存；同一condition各方法共享同一realization。

四个parents只是feasibility筛查，不能将32行当32个独立对象。历史A23四个对象可作已暴露3D诊断，不能用作blind generalization。

### 少量3D确认

A/B完成后另列最多4个4³或6³ cells的3D dyadic-Maxwell states，2种非Gaussian形状；直接调用冻结A20/A23后端，不重写Green或polarizability。此小网格只能确认矢量实现和方向性机制，不能支持高分辨率3D算法性能。

### 成本边界

A的tiny anatomy建议CPU wall≤2分钟；2D B0总CPU wall≤30分钟、new clean states≤16、GPU=0。到预算立即停止，保留NOT_RUN和失败。3D确认单列预算≤10 CPU分钟，不自动扩网格。上述都是后续执行规范，本包未运行这些阶段。

## 2. Experiment A：algebra 与 subspace anatomy

### A0：现有合成测试

运行附带脚本，验证source anchor、Schur inverse、relative-source identity、low-rank core、real adjoint、共同材料残差、投影/交集反例和非正规反例。它不使用真实Green，不跨越物理Gate2。

### A1：真实算子空间审计

在同一个小Maxwell背景上比较：classical observable split；ideal TSOM intersection；projected-TSOM实现；restricted-internal-operator SVD；原OPM；source-anchored OPM/OM；affine-source OM；M+feedback；exact-adjoint control。

至少有两组配对：

- **代数配对**：固定同一U且U包含全部source currents，原OPM和drop-zero-P OM。不能更换U、rank阈值或M/O探针。
- **实际设计配对**：固定8个receiver-retained方向，j_b作affine offset；与同样拥有这个offset的普通ROM/adjoint方案比较。增加的ns存储全部计费。

保留“用source替换receiver方向”的旧A23配置作为confound control，不用它判断P本身的必要性。未经anchor直接删P只作负向控制。

预注册ℓ=16、current目标rank32；真实rank不足就报告不足，不padding。M/O探针使用独立固定seed，不能包含本次truth或full-GN optimum。内部传播primary rank k=16，k=32仅为预先列出的敏感性臂，不在test后择优改primary结论。

分别报告：actual retained/correction/union rank；source/current reconstruction error；material-to-data transfer error；adjoint pullback error；feedback action error；core σ_min与condition；setup、QR、cache I/O时间；每类vector RHS和kernel次数。principal angles只是补充。

## 3. Experiment B0：同先验的无NN成像

### 三个机制臂

L：\(\widehat y=y_b+\mathcal D_bH(h)e_b\)，但h=a(χ)−a_b使用精确局部转换，排除constitutive非线性被误认为feedback。

F：在同一参考下使用完整 \(w=(I-H\mathcal G_b)^{-1}He_b\)，完整discrete adjoint。

R：使用同样的完整χ、同样data算子与prior，只把\(\mathcal G_b\)换成预注册D+UV*。primary D=0,k=16；D为2×2 cell不相交局部块和k=32的情况只作预注册诊断，不得自动追加更多rank。

### 共同优化器与初始化

全部从同一个constrained dressed-linear或BP初值出发，用相同full-grid TV/wavelet proximal、相同物理box constraints、相同更新数K=3。步长由独立background/validation预算选定；主运行不根据truth调步长。可增加共同K=6诊断，作为固定预算质量曲线，不与K=3混报。

主prior为完整图像TV，λ按预先声明noise model/独立validation冻结；不能候选用shape prior而baseline用isotropic L2。另设共享wavelet sparse prior是独立重复实验，不在观察结果后选择有利prior。

若算法需line search，所有臂统一最多一次half-step retry，并把额外forward算入时间；不能让F做无限迭代而R/L只做三步。K相同与walltime相同是两种不同比较，应同时报告，不相互替代。

### 强非机制基线

Born/BP、dressed-linear χ、linear-a+exact conversion、ordinary adjoint+同prior、普通affine ROM，以及合理实现的SOM/FFT-TSOM。可获得CIE-I/WT-TSOM可靠实现时加入；暂缺则标NOT_IMPLEMENTED，不能宣称已击败它。传统迭代基线报告自身质量—walltime曲线，不只拿任意一次迭代对比NN三层。

### 判别量

材料full χ NRMSE、Δχ NRMSE、Re/Im误差、shell内外edge与support、passivity/constitutive poles、完整Maxwell数据残差、common-material residual、full-state residual、预测失败、CPU/wall/peak memory。

在offline evaluator另外计算
\[
 d_{FB}=f_{full}(χ)-f_L(χ),\qquad
 ρ_{closure}=\|W(f_R-f_{full})\|/\|Wd_{FB}\|.
\]
分母低于noise或固定numerical floor的case不计算不稳定ratio，保留absolute errors并标记NO_RESOLVABLE_FEEDBACK，不删除该case。

## 4. Experiment C：最小SOM-Net迁移（本阶段禁用）

只有Gate1–3和成本microbenchmark有正面证据后，另行启动小训练：original SOM-Net、A、B、C，以及ordinary adjoint+相同prior NN。首先2D；不把其训练权重/成绩当3D证明。

建议独立parents训练64/128/256三档，验证32，测试32；测试含未见shell厚度、不对称组合、contrast、noise。训练/验证/测试按parent划分，不按source、旋转或noise realization拆分。固定两组训练seed，更新步数、batch、优化器和labels一致；数据集生成与训练成本单列。具体最大steps须在训练启动前依据一次hardware microbenchmark冻结，禁止无上限early-stopping搜索。

同深度主比较K=3；原论文K=4为单独真实性baseline。再测试B/C的K=2能否达到原K=4质量，不能只比较不同depth却说容量相同。参数量控制在±1%；同时报告FLOPs、全图activations和物理actions，因为参数量相同不等于运行成本相同。

不强制所有网络预测相同维数，但输入信息、材料prior类别、辅助监督权限相同。若B用额外current/field真值监督，其余臂可访问相同标签或另设消融。

## 5. Experiment D：feedback增量，最高优先级学习消融

同一个B网络外壳内只改变物理closure：

D0 无relative反馈；D1 精确feedback（tiny diagnostic）；D2 约化物理feedback；D3 参数匹配generic recurrence；D4 原SOM-Net独立baseline。

另有anchor-only、full-source-vs-fixed-current、有/无局部D、exact-vs-approx receiver cache、matched-rank-vs-matched-time、hard-vs-soft second-fold各项独立控制。不要一次改五项再把总收益全部归于feedback。

generic recurrence不得偷用额外data/更长训练；其参数节省或增加通过同prior网络宽度调整补偿。精确物理closure没有trainable参数，也须报告其FLOPs，而不是视为免费。

机制证据至少包含：优势是否集中在|d_FB|超过noise的regime；下降的是完整材料误差而非只surrogate residual；source/field误差与adjoint误差是否符合T3；k增加时是否以预测方式接近精确feedback；OOD失效是否由传播缺陷或prior外推导致。

## 6. 预注册Gate与阈值

以下数值是筛查选择，不是理论常数。真正执行前应锁定所用版本；任何修改都生成新protocol编号。

| Gate | 主阈值 | 不可替代的条件 |
|---|---|---|
| 1 P-removal correctness | complex128下相对identity误差≤1e−10；P零判据以完整forcing尺度归一 | 同U、同其它seeds；core可逆且条件记录 |
| 2 physical sufficiency | independent material/data与adjoint任务误差各≤5%；非退化gradient方向cosine≥0.99 | 相同prior的image不得相对精确closure恶化超过5%；零分母按绝对尺度 |
| 3 incremental mechanism | F对L的full-material NRMSE在两种形状家族各有至少一个parent下降≥10%；R保留至少80%的paired改善 | 必须同时报告全部parents；物理可行；full data residual不得恶化超过noise预算；ρ_closure≤0.5 |
| 4 architecture headroom | matched-capacity下材料NRMSE平均下降≥10%，或同质量所需parents至少减半 | OOD不整体退化；full-Maxwell验证；训练seed和独立parent配对 |
| 5 cost headroom | 在固定质量区内完整warm或声明N下摊销time-to-image下降≥20% | cold、N=1/10/100全部报告；无隐藏准备/验证/fallback |

所有Gate采用两家族、四parent的描述性screening，不伪造大样本显著性。训练阶段可报告parent-paired bootstrap，但四parent的区间不能替代大规模泛化证据。

共同quality区预先规定为：full χ NRMSE≤0.35、Δχ NRMSE≤0.60、无材料非法/constitutive pole、20dB下whitened full-data residual≤1.2√m；无噪声用相对full-data residual≤0.05。若全部方法未进入该区，Gate5为QUALITY_TARGET_NOT_REACHED，而不是挑较差图像计算加速。此区是任务工程目标，不是适用于任何数据集的物理定律。

物理约束容差为1e−10（normalized quantities）；core相对σ_min floor=1e−10、condition cap=1e10，另报绝对尺度。极化率逆映射的pole距离采用相对分母尺度，不能在不同单位下照搬absolute1e−10。

## 7. 严格停止规则

Gate1失败：修实现/定义，不跑成像。Gate2失败但精确F有优势：可保留机制结论，当前R架构不进入训练。Gate3失败：不自动增加layers或data，报告没有增量证据。Gate4失败：保留便宜无NN/ordinary adjoint baseline。Gate5失败：可报告quality-only研究，但不得称为更快算法。

任何预算停止、奇异core、不可行材料、runtime异常、missing baseline都保留在失败账本。不能只在成功case上计算平均质量和加速，不能因某一幅图漂亮授予GO。
