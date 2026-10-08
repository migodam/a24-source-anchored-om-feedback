# A24｜来源、实际阅读范围与引用编号

检索/读取日期：2026-10-08。本文是证据账本，不宣称穷尽检索，也不把摘要读取写成全文审阅。所有本轮新证明与实验阈值由本研究包给出；文献用来核对原方法和最近邻，不为未运行的A24性能背书。

## 1. 阅读层级

**FULL-METHOD**：读取原作者正文的相关算法/公式。**BOOK-METHOD**：读取作者教材的相关完整章节页，但未取得指定原论文全文。**ABSTRACT**：读取作者摘要或索引保存的作者摘要。**METADATA**：仅标题/DOI/作者目录/原文引用链。**PARTIAL**：指定源只读到声明的部分。

网页/PDF截图工具多次失败；未用OCR猜测图表。教材页面返回可读文本但图像不可用，raw materialization亦被权限拒绝。因此不引用未看见的图像或从图中读取数值。开放论文HTML方法可读时按文本核对，不声称独立复现其数值图。

## 2. 项目一手来源

A20/A22冻结repo：`migodam/a20-opm-imaging`，本轮读取commit `b85a29a51f4ea7b4d93617e827d88e23933b89df`。A23读取`migodam/a23-fast-material-imaging`公开main及其source manifest；历史科学版本信息保留在项目manifest，执行时应再次固定实际checkout，而不是只凭main URL复现。

| 编号 | 文件与链接 | 实际读取 / 可支持内容 |
|---|---|---|
| P20 | [RESEARCH_REPORT_ZH.md](https://github.com/migodam/a20-opm-imaging/blob/b85a29a51f4ea7b4d93617e827d88e23933b89df/RESEARCH_REPORT_ZH.md) | 报告主文；A20后端、early/late、QP失败、gate及证据边界 |
| P20code | [src/a20/opm.py](https://github.com/migodam/a20-opm-imaging/blob/b85a29a51f4ea7b4d93617e827d88e23933b89df/src/a20/opm.py) | 文件前260行；SchurFeedback、build_seeds、BlockStream、Hierarchy及Projection入口 |
| P21 | [RELEASE_NOTES_A21.md](https://github.com/migodam/a20-opm-imaging/blob/b85a29a51f4ea7b4d93617e827d88e23933b89df/RELEASE_NOTES_A21.md) | 全文；five-state rank56 BOTH_G、primal/dual对照、oracle/offline限定 |
| P22 | [A22_R1_GPT_HANDOFF.md](https://github.com/migodam/a20-opm-imaging/blob/b85a29a51f4ea7b4d93617e827d88e23933b89df/A22_R1_GPT_HANDOFF.md) | 前145行请求，返回含主裁决、scope、核心表及部分协议；后续大段未全部读取 |
| P23a | [OPM_REDUNDANCY_AND_MINIMALITY.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/OPM_REDUNDANCY_AND_MINIMALITY.md) | 理论主文；P=Kb、source anchor、retained coupling |
| P23c | [CHEAP_FEEDBACK_OPERATORS.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/CHEAP_FEEDBACK_OPERATORS.md) | 主文；cached Schur、adjoint与动作成本 |
| P23o | [ONE_SHOT_INVERSE_THEORY.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/ONE_SHOT_INVERSE_THEORY.md) | 可获取正文至§8附近的主要公式；不声称全文附录均读取 |
| P23n | [FEEDBACK_NATIVE_NN_ARCHITECTURES.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/FEEDBACK_NATIVE_NN_ARCHITECTURES.md) | 架构理论主文 |
| P23r | [A23_RESEARCH_REPORT_ZH.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/A23_RESEARCH_REPORT_ZH.md) | 主裁决、尺寸、H1完整cost/fidelity比较及H2主要结果；长报告之后的全部附表未逐行读取 |
| P23m | [SOURCE_MANIFEST.json](https://github.com/migodam/a23-fast-material-imaging/blob/main/SOURCE_MANIFEST.json) | 来源、模型尺寸、固定设置 |
| P23s | [SOURCES.md](https://github.com/migodam/a23-fast-material-imaging/blob/main/SOURCES.md) | 前125行请求及返回的项目/文献索引；它是导航而非代替读原论文 |

这里没有下载A20/A23完整历史dataset，没有访问用户本地/远端训练机器，没有修改GitHub仓库。A21数值采用这次实际release，不沿用旧对话中较早的阶段描述。

## 3. 作者教材

**B01 — Xudong Chen, Computational Methods for Electromagnetic Inverse Scattering, Wiley, 2018. ISBN 9781119311980.**

用户Library文件ID `file_00000000370881faa4fb9f41351b4df7`。BOOK-METHOD：PDF页168–172（印刷149–153，§6.4.1 SOM）；PDF180–183（印刷161–164，§6.4.2–6.4.3 TSOM/FFT-TSOM）；PDF188–190（§6.4.4 vector-wave / 3D例子）。关键公式6.70/6.71用于区分交空间与投影像。

Library文本提供的引用范围：SOM见当前检索`turn13file0`；TSOM见`turn13file1`；vector-wave见`turn13file2`。这些是对话内来源标识，不是可从本地文件解析的网页URL。本包不重发教材PDF或版权章节。

## 4. 核心文献

| 编号 | 文献与永久入口 | 阅读层级与用途 |
|---|---|---|
| R01 | Zhong & Chen, *Twofold subspace-based optimization method for solving inverse scattering problems*, Inverse Problems 25,085003,2009. [DOI](https://doi.org/10.1088/0266-5611/25/8/085003) | 原全文未取得；METADATA + B01作者讲解。不能声称逐页读过 |
| R02 | Zhong & Chen, *An FFT Twofold Subspace-Based Optimization Method for Solving Electromagnetic Inverse Scattering Problems*, TAP59(3),914–927,2011. [DOI](https://doi.org/10.1109/TAP.2010.2103027) | 原全文未取得；作者PDF入口检索到但访问失败；B01验证Fourier替代SVD |
| R03 | Chen, *Application of signal-subspace and optimization methods in reconstructing extended scatterers*, JOSA A26,1022–1026,2009. [DOI](https://doi.org/10.1364/JOSAA.26.001022)；以及 *Subspace-Based Optimization Method for Solving Inverse-Scattering Problems*, TGRS48,42–49,2010/online2009. [DOI](https://doi.org/10.1109/TGRS.2009.2025122) | METADATA/作者目录+B01；两篇不同文章，不混用标题 |
| R04 | Liu et al., *SOM-Net: Unrolling the Subspace-based Optimization for Solving Full-wave Inverse Scattering Problems*, TGRS,2022. [arXiv](https://arxiv.org/abs/2209.03567) / [PDF](https://arxiv.org/pdf/2209.03567) | FULL-METHOD：v2方法§II、公式与algorithm；全文可检索，图截图失败，不抽取未见图像数值 |
| R05 | X. Chen, *Subspace-based optimization method for inverse scattering problems with an inhomogeneous background medium*, Inverse Problems26,074007,2010. [DOI](https://doi.org/10.1088/0266-5611/26/7/074007) | METADATA，作者出版目录核对；否定“背景SOM完全空白” |
| R06 | Zhun Wei & Xudong Chen, *Physics-Inspired Convolutional Neural Network for Solving Full-Wave Inverse Scattering Problems*, TAP67,6138–6148,2019. [DOI](https://doi.org/10.1109/TAP.2019.2922779) | ABSTRACT，major bypass/minor-current learning；原文未取得 |
| R07 | Y. Sanghvi, Y. Kalepu, U. K. Khankhoje, *Embedding Deep Learning in Inverse Scattering Problems*, TCI6,46–56,2020/online2019. [DOI](https://doi.org/10.1109/TCI.2019.2915580) | ABSTRACT；CS-Net learns noise-space/current、迭代与multiresolution |
| R08 | J. Liu et al., *Physical Model-Inspired Deep Unrolling Network for Solving Nonlinear Inverse Scattering Problems*, TAP70,1236–1249,2022/online2021. [DOI](https://doi.org/10.1109/TAP.2021.3111281) | ABSTRACT + R04引言，PM-Net四准线性模块 |
| R09 | Y. Zhong, M. Lambert, D. Lesselier, X. Chen, *A New Integral Equation Method to Solve Highly Nonlinear Inverse Scattering Problems*, TAP64,1788–1799,2016. [DOI](https://doi.org/10.1109/TAP.2016.2535492) | METADATA及R10/R11作者解释；原全文未取得，CIE-I/NIE关键优先权待复核 |
| R10 | Y. Zhong & K. Xu，CIE-I的3D逆散射研究，Journal of Imaging5(2),27,2019. [DOI](https://doi.org/10.3390/jimaging5020027) / [作者论文](https://www.mdpi.com/2313-433X/5/2/27) | PARTIAL原作者开放文本；验证3D FFT-TSOM/CIE-I最近邻，不声称全部公式已解析 |
| R11 | L. Zhang, Z. Ma, K. Xu, Y. Zhong, *Wavelet-Based Subspace Regularization for Solving Highly Nonlinear Inverse Scattering Problems with Contraction Integral Equation*, Electronics9,1760,2020. [DOI](https://doi.org/10.3390/electronics9111760) | FULL-METHOD可获取HTML主要段落；wavelet/nested/CIE-I，与本轮正则化直接相关 |
| R12 | X. Ye & X. Chen, *Subspace-Based Distorted-Born Iterative Method for Solving Inverse Scattering Problems*, TAP65,7224–7232,2017. [DOI](https://doi.org/10.1109/TAP.2017.2766658) | METADATA及原作者相关引用；原全文未取得 |
| R13 | A. Si, M. Wang, F. Fang, D.-H. Dai, *Two-Step Contrast Source Learning Method for Electromagnetic Inverse Scattering Problems*, Sensors24(18),5997,2024. [DOI](https://doi.org/10.3390/s24185997) / [全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11435635/) | FULL-METHOD主要流程；source estimate→contrast→U-Net，与C直接相关 |
| R14 | S. Zumbo, S. Mandija, T. Isernia, M. Bevacqua, *MiPhDUO: microwave imaging via physics-informed deep unrolled optimization*, Inverse Problems,2024. [DOI](https://doi.org/10.1088/1361-6420/ad2b99) | ABSTRACT；shallow physics-gradient/CNN级联，与B直接相关 |
| R15 | C. Fei, P. Liu, Y.-M. Wu, Y.-Q. Jin, *A Current-Coding Residual Structure for Solving Electromagnetic Inverse Scattering Problems in Inhomogeneous Background Media*, TAP73,10373–10385,2025. [DOI](https://doi.org/10.1109/TAP.2025.3609199) | ABSTRACT/METADATA；CCR；全文尚无，最重要待排重之一 |
| R16 | C. Du et al., *Variation-Based Residual Learning Method for Solving Inverse Scattering Problems*, TAP73,6961–6966,2025. [DOI](https://doi.org/10.1109/TAP.2025.3558043) | ABSTRACT及IEEE当期入口；VBRL；不得把作者performance声明当本轮复现 |
| R17 | Q. Huang, C. Li, X. Ye, K. Xu, R. Song, *Meta-Learning-Assisted Untrained Neural Network for Electromagnetic Inverse Scattering Problems*, TAP73,2548–2560,2025. [DOI](https://doi.org/10.1109/TAP.2025.3539938) / [作者目录](https://faculty.hfut.edu.cn/songrencheng/en/lwcg/245092/content/15351.htm) | METADATA/摘要；Meta-uSOM初始化与正则化相关。早期uSOM只作citation链，不编造其细节 |

作者出版目录辅助入口：[Xudong Chen Publications](https://www.ece.nus.edu.sg/stfpage/elechenx/Publications.htm)。它的索引日期较早，不能用于宣称截至2026年的作者全部成果已经覆盖。

## 5. 方法学与近期补充

| 编号 | 来源 | 读取及用途 |
|---|---|---|
| R18 | Benner, Gugercin, Willcox, *A Survey of Projection-Based Model Reduction Methods for Parametric Dynamical Systems*, SIAM Review,2015. [DOI](https://doi.org/10.1137/130932715) | metadata/既有理论入口；本包不声称已逐页审读 |
| R19 | Becker & Rannacher, *An optimal control approach to a posteriori error estimation in finite element methods*, Acta Numerica,2001. [DOI](https://doi.org/10.1017/S0962492901000010) | DWR优先权入口；本包双侧恒等式自行证明 |
| R20 | Adler & Öktem, *Learned Primal-Dual Reconstruction*,2018. [arXiv](https://arxiv.org/abs/1707.06474) | 原作者abstract/metadata；primal-dual unrolling先例 |
| R21 | Boink, Haltmeier, Holman, Schwab, *Data-consistent neural networks for solving nonlinear inverse problems*, Inverse Problems and Imaging17,203–229,2023/online2022. [DOI](https://doi.org/10.3934/ipi.2022037) | 原出版社abstract/HTML；nonlinear data-consistent completion先例，未挪用其定理条件 |
| R22 | *Deep null space learning for inverse problems: convergence analysis and rates*,2019. [DOI](https://doi.org/10.1088/1361-6420/aaf14a) / [arXiv](https://arxiv.org/abs/1806.06137) | 项目文献索引/metadata级；不据此提出新A24性能声明 |
| R23 | Cui et al., *Likelihood-informed dimension reduction for nonlinear inverse problems*,2014. [arXiv](https://arxiv.org/abs/1403.4680) | 项目文献索引/metadata级；prior/likelihood区分的既有背景 |
| R24 | Borcea, Liu, Zimmerling，Maxwell reduced-order-model逆问题研究，JCP515,113272,2024. [DOI](https://doi.org/10.1016/j.jcp.2024.113272) / [arXiv](https://arxiv.org/abs/2403.03844) | metadata级；不是本轮方法的已验证等价先例 |
| R25 | Gu et al., *NeurOLight: A Physics-Agnostic Neural Operator Enabling Parametric Photonic Device Simulation*,2022. [arXiv](https://arxiv.org/abs/2209.10098) | 原作者abstract；forward photonic operator，不等同本轮inverse共同材料闭合 |
| R26 | Sun et al., v1 *Physics-Informed Deep Contrast Source Inversion: A Unified Framework for Inverse Scattering Problems*,2025. [v1](https://arxiv.org/abs/2508.10555v1) / [HTML v1](https://arxiv.org/html/2508.10555v1). 2026-06-03的v2改题为 *A Differentiable Framework for Full and Phaseless Data Inversion Using Neural Implicit Contrast-Source Representation*. [v2](https://arxiv.org/abs/2508.10555v2) | v1摘要、引言及可获取方法段；v2仅核对最新题名、日期和摘要。DeepCSI的case-by-case训练即反演定位由v1明确说明；不把旧版本标题当最新版，也不声称逐式审核v2 |
| R27 | Yutong Du & Zicheng Liu, *Contrast-Source-Based Physics-Driven Neural Network for Inverse Scattering Problems*,2026. [arXiv](https://arxiv.org/abs/2601.19243) / [HTML](https://arxiv.org/html/2601.19243v1) | FULL-METHOD §2–3；CSPDNN、BP输入、current输出、跨源ratio、state/data/TV losses，按对象优化；未复现图像性能 |

| R28 | Z. Wei & X. Chen, *Deep-Learning Schemes for Full-Wave Nonlinear Inverse Scattering Problems*, TGRS57(4),1849–1860,2019/online2018. [DOI](https://doi.org/10.1109/TGRS.2018.2869221) | 原全文未取得；METADATA与同作者SOM-Net引言/参考文献[18]交叉定位。DCS=dominant current scheme；dominant-current构造初始contrast再送U-Net，不把它误归成只预测ambiguous current的网络 |

R26/R27保留preprint身份，不假定已发表TAP。R16/VBRL作者Changlin Du与R27作者Yutong Du不是同一篇文章，也不凭姓氏混合其贡献。

## 6. 缩写核验与检索缺口

本轮对“DCS-Net inverse scattering”“CSI-Net inverse scattering”“deep contrast source”等逐项搜索，并最终沿SOM-Net原文参考文献[18]定位到Wei与Chen的dominant current scheme（DCS），见R28。这里将DCS-based U-Net列为用户DCS类别的直接先例，但不假定所有名为DCS-Net的网络都等于它。CSI相关可靠条目包括CS-Net、DeepCSI、CSPDNN；其他领域的同名CSI-Net不得误计为Maxwell方法。R28原文尚未取得，完整逐式重合判断仍待补充。

2026综述仅用于找到原文，不用其二手总结替代技术证据。开放原文R26/R27补齐了近期current/source-learning发展，但不能据此宣称覆盖全部2026新作。

## 7. 明确未完成的任务

原R01/R02全文逐页阅读未完成；R09、R15、R16关键公式排重未完成；部分A23长报告后半及附表未逐行读完；没有完整3D实验或网络训练。它们是本包已显式保留的证据缺口，不由理论证明或合成测试代替。

## 8. 支持本轮结论的来源组合

TSOM不是A23 forcing-P：B01 + P20code + P23a。SOM-Net实际学习/解析更新：R04。删P很难直接带来速度：P23r真实cold表。只学current residual不是新颖性：R06/R07/R16，加R04原方法。代数改写+TSOM不是空白：R09–R11。结构性source学习持续发展：R15/R26/R27。A24具体新公式、反例、cost阈值及架构选择则属于本轮推导和设计，不伪装成这些论文已证明的结论。
