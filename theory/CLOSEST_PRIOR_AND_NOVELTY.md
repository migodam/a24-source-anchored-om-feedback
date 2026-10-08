# A24｜最近邻与新颖性审计

**判决：存在值得检验的架构差异，但新颖性尚未清关。A、B、C都不能仅凭“OM”“显式物理”“残差电流”“少层unrolling”成为强TAP论文。** 本轮检索截至2026-10-08；检索不等于穷尽全部文献。特别是原TSOM两篇与2025年CCR/VBRL全文仍需逐式复核。来源、DOI及实际阅读层级集中在 `SOURCES_AND_READING_LEDGER.md`。

## 1. 最接近的先例，而非外围名单

| 先例 | 已经覆盖的内容 | 对A24的限制 | 本轮证据层级 |
|---|---|---|---|
| SOM / TSOM / FFT-TSOM [R01–R03] | 数据确定电流、ambiguous current搜索、内部传播子空间、Fourier加速 | O/P名称不是新的物理分解；少current维数不是新思想 | 作者教材详细公式；原2009/2011全文未取得 |
| Inhomogeneous-background SOM，Chen 2010 [R05] | 已知非均匀背景中的SOM | “参考背景 + SOM”不能首创 | 作者出版目录及论文metadata |
| DCS / dominant-current U-Net，Wei & Chen，2019/online2018 [R28] | dominant current构造较好的初始contrast，再由U-Net恢复材料 | C的物理初值+图像prior已有直接先例；DCS不是A23 forcing-P | 原文metadata及同作者SOM-Net引言/参考文献[18]；原全文未取得 |
| ICLM，Wei & Chen 2019 [R06] | contrast-source learning，major current bypass，主要学习minor part | 只让NN预测ambiguous/residual current不是新贡献 | 作者摘要、SOM-Net正文交叉核对；全文未取得 |
| CS-Net，Sanghvi等，2020/online2019 [R07] | 学radiation operator噪声空间，再与data确定部分结合、物理迭代、多分辨率 | A和C均有直接前身 | 作者摘要经索引；全文未取得 |
| PM-Net，2022/online2021 [R08] | 增广Lagrangian拆成四个准线性子问题，contrast/source模块交替展开 | 物理unrolling、双变量模块、少参数均已有 | 作者摘要；SOM-Net引言支持 |
| SOM-Net，Liu等2022 [R04] | deterministic current和BP材料初值，full-current子网络，解析field/material update，多变量loss | “CNN学电流、解析恢复材料”已经是原方法 | arXiv v2正文§II逐式读取 |
| NIE/CIE-I，Zhong等2016 [R09] | 改写积分方程处理强非线性，并与subspace inversion结合 | “Maxwell代数改写 + TSOM”不是新概念 | bibliographic确认，后续作者正文介绍；原全文未取得 |
| 3D CIE-I + FFT-TSOM，2019 [R10] | 上述机制用于3D逆散射 | 不能以3D作为单独新颖性 | 作者开放论文可获取文本；部分公式解析不全 |
| WT-TSOM + CIE-I，2020 [R11] | wavelet电流展开、nested正则化、强散射反演 | 换wavelet/material-informed basis本身不够 | 作者开放HTML方法、引言和结论 |
| S-DBIM，Ye & Chen2017 [R12] | distorted-background/subspace联合反演 | 背景相对化、current-informed field更新不是空白 | 作者目录、后续作者论文引用；原全文未取得 |
| Two-step contrast source learning，Si等2024 [R13] | deterministic source→full source→初始contrast→U-Net refinement | C的“两阶段”不是创新 | 开放全文主要方法 |
| MiPhDUO，Zumbo等2024 [R14] | 少量物理gradient操作与CNN级联 | B必须优于ordinary adjoint-unrolling，不只是相似命名 | 作者摘要；全文未取得 |
| CCR，Fei等2025 [R15] | 非均匀背景、current-assisted operator、residual encoder-decoder、有耗材料 | **B的高优先级直接最近邻**；未读全文不能排除相同算子实现 | 作者摘要与DOI metadata；全文未取得 |
| VBRL，Du等2025 [R16] | 利用散射场variation更新deterministic current，只学习residual current，多模块级联 | A的“更好的输入 + residual预测”已非常拥挤 | 作者摘要；IEEE当期信息；全文未取得 |
| Meta/untrained SOM系列 [R17] | 将SOM与低数据/未训练网络、初始化/正则化联合 | 样本效率必须有直接对照 | metadata级，不据此编造逐层结构 |
| DeepCSI，2025预印本 [R26] | current network、材料变量与state/data/TV约束联合，逐对象优化 | 不能把physics/self-supervision/current变量当新颖性；也不能把逐对象训练当一次amortized inference | 作者预印本摘要与引言；未逐式审核全部方法 |
| CSPDNN，2026预印本 [R27] | BP/current/material输入、CNN电流输出、解析field/共同材料更新与物理loss | 当前物理网络与analytic recovery仍是活跃直接近邻 | 原作者HTML §2–3方法；逐对象优化，不等同预训练快速推断 |

PM-Net、CS-Net与DCS文献的期刊年和online年不同，本文明确区分。DCS已沿SOM-Net参考文献[18]定位为dominant current scheme [R28]，其核心是改进供U-Net使用的contrast输入，不能与ICLM的minor-current学习混为一谈。检索词CSI-Net仍会命中无线通信等不同领域；这里只将可靠识别的contrast-source文献归类。DeepCSI的2025 v1与2026 v2题名不同，见来源账本；本包不把v1审阅说成v2全文审计。

## 2. 传统理论最近邻

Projection-based parametric ROM、low-rank/Woodbury消元和affine lifting已经提供离线—在线分离。[R18] Dual-weighted residual已经提供primal/dual误差乘积结构。[R19] Learned primal-dual、learned proximal以及nonlinear data-consistent neural networks已经提供物理残差/先验结合的通用架构。[R20–R22] Likelihood-informed subspaces已经区分数据强信息方向和prior主导方向。[R23]

因此下列推导的定位应是：**A24具体模型下的正确性、约束和可测试算法设计**，不是“此前不存在的基础定理”。尤其T1源锚定、T3 resolvent误差、T7小核心消元在代数上都不宜主张首创。

Maxwell-informed/neural-operator相关工作也不能忽略。[R24,R25] 但通用forward neural operator并不自动提供本轮共同材料约束、离散adjoint一致性或full-model误差界；反过来，本轮也没有实验证据宣称比它们快或泛化更好。

## 3. 三种架构的新颖性风险

### A：高重合风险，作为迁移control

改为材料激发系数，保留解析field/material更新，是可实施的最小改造；它最容易验证“输出限制是否有用”。但如果结果只是相同CNN换个basis，应按SOM-Net/ICLM/CS-Net的普通变体评估，不足以单独支撑强TAP。VBRL进一步压缩了“只学current残差”的创新空间。

### B：条件性主候选，不是原SOM-Net直接等价重写

B以完整材料假设驱动物理闭合，并用精确surrogate adjoint更新材料，优化变量和计算路径已经改变。它是 **SOM-inspired、feedback-native material unrolling**，而非声称一行改动即可得到原SOM-Net的等价版本。

可检验的区别在于：
\[
\text{保留完整 }H e
\quad\text{而只压缩}\quad
\mathcal G_b=GR_b,
\]
并用material-conditioned小有理核心包含多阶反馈，缓存真实receiver pullback，显式暴露截断误差。相较fixed-current ROM，这不硬性限制整个source/image落在固定低维空间。

但“局部+低秩传播+Woodbury”也属于已知计算思想。真正需要建立的是：**这个限制对象的变化，在3D强背景/细材料结构任务中，能否以更小总成本保住对材料有效的非线性传输，并确实减少学习负担。** 若CCR等已有同一结构，需进一步缩小贡献到误差控制、source-anchored实现或具体性能机制，而不是换名。

### C：工程上可能最优，算法独立性较弱

先验补全再data-consistency correction有很强先例。C的贡献只能是明确的Maxwell相对反馈修正、完整材料prior而非固定小chart、可校准的不确定性/物理代价，以及对同容量普通decoder的实证优势。单独拼接Gaussian/Wiener + U-Net不够。

## 4. 可以与不可以写进论文摘要的内容

目前可以写作研究目标/方法定义：
- source特解以affine offset保存，避免占用receiver-correction预算；
- full-grid material excitation与低维feedback solve分离；
- 多源共享材料、共同小核心和一致adjoint；
- full-model误差由传播缺陷和resolvent放大显式控制。

目前不能写作已证实结果：更快20%、更少训练数据、更少层优于SOM-Net、强散射普遍稳定、首次OM/首次current-network、优于FFT-TSOM、完整3D成像成功。本文没有运行相应实验。

## 5. 强TAP应要求的最小贡献组合

理论需阐明“压缩传播而非完整电流”的可保留性条件，揭示3D vector/非正规条件下的失败边界，而不是仅给Woodbury公式。算法需做到无online背景完整solve、真实common-material consistency和全图输出。实证需满足：matched-capacity/matched-prior消融、实际full-Maxwell验证、复杂shell与不对称形状、完整time-to-image、非训练家族和有限跨频检验。

只有某一种组合同时给出质量—成本和机制证据，才有强TAP潜力。若B只有更小PDE残差，而材料误差和成本不改善，不能包装成更好imaging architecture。

## 6. 必须完成的优先权复核

在任何投稿/“新架构已成立”判断之前，逐式取得并检查R01、R02、R09、R15、R16，优先R15/CCR：其current-assisted operator是否已经实现了与 \(\mathcal D_bH(I-\mathcal G_bH)^{-1}\) 等价的低秩/残差传播？是否共享多源材料？其离线算子和网络层是否把full-current约束移到传播？

本轮没有这些全文，**因此不存在“已排除所有最近邻”的结论**。这不阻碍执行一个低成本、无需NN的机制实验，因为即使发现重合，该实验仍可判断用户当前物理资产是否值得继续。
