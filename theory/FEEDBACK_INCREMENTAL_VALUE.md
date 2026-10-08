# A24｜Feedback 的独立增量在哪里？

## 1. 必须接受的负面起点

“用了 Maxwell”“学 ambiguous current”“参考背景”“少量 unrolled blocks”均不是独立新颖性。SOM-Net、ICLM、CS-Net、PM-Net、inhomogeneous-background SOM、CIE-I及其3D FFT-TSOM实现已覆盖相邻机制。[R04–R12]

A23 cached Schur 的完整 cold preparation节省仅约0.35%–0.86%；source anchoring实验又同时改变receiver retained预算与最终rank。因此“remove P → substantial speedup”当前没有支持。[P23r]

本轮需要检验的是一个更窄的命题：**在共享参考背景的任务类里，让完整材料源通过便宜、明确、可监测的相对传播闭合，比让网络或固定current chart承担这部分物理更有效。**

## 2. Computational value

### 已经可证明

固定anchor下零P的所有descendants都可删除；affine subtraction可让已知特解不占correction rank；同一背景的receiver adjoint可跨源共享；SA-RF每个material block仅分解一次共同k×k核心。

### 仍需实测

是否降低**完整time-to-image**。SA-RF需离线背景solves与n×q缓存；每block常有两次nqs级forward/adjoint contractions和n k²组装。原SOM-Net不是每层完整Maxwell solve，且不一定每层计算receiver data。B完全可能比它更慢。

本轮不可接受的速度证据：basis rank降低、只计小core、只计warm NN kernel、未计cache生成/搬运、不同硬件或只比较不等质量图像。可接受证据是同一quality target下的cold/warm/按复用次数摊销时间，以及全部失败/校验动作。

## 3. Reconstruction value：何种物理regime值得测

三个条件应同时出现：

1. 相对于参考的高阶响应超过measurement noise，而不是近乎线性的easy case。
2. 该响应会影响材料恢复，而不只是落在decoder不敏感或不可识别的方向。
3. 低成本feedback approximation的误差小于它修复的误差。

可诊断的量：
\[
 d_{FB}=f_{full}(\chi)-[y_b+\mathcal D_bH(h)e_b],
\]
\[
 \rho_{signal}=\|Wd_{FB}\|/\sqrt m,
\quad \rho_{closure}=\|W(\widehat f-f_{full})\|/\|Wd_{FB}\|.
\]
第一项仅在已白化单位噪声条件下如此归一化；无噪声时使用预注册相对data尺度。真实χ在这些诊断中只属于offline evaluator。

即便ρ_signal很大，也不保证image改进。若linear decoder D把反馈bias送到材料空间，二阶展开近似为
\[
 z=Ah+Q(h,h)+n,\quad h_L=Dz.
\]
一个feedback correction c是否降低材料平方误差，精确条件是
\[
 \|e\|^2-\|e-c\|^2=2\langle e,c\rangle-\|c\|^2>0,
 \quad e=h_L-h.
\]
它要求correction与真正材料误差对齐，且不过冲。减少forward residual或增大current basis都不自动满足它。该等式仅用于解释/离线诊断；算法不能读取e。

最有希望的regime：已知强背景内中等相对变化、材料细节比内部场更细、观察返回仍有足够信噪比。主要反例：参考近共振、large-relative-change、强局部场集中导致k很大、limited-aperture下相关材料方向本来不可识别。

## 4. Learning value

B要求网络只提出一个公共材料假设，而不是独立为每个源构造任意复电流；同一小物理核心处理新增材料与背景之间的重复相互作用。学习器不必重新拟合这部分已知source/contrast-dependent physics。

但这是**inductive bias假设**而非训练样本效率定理。参数更多、标签更多、训练更久、数据增强更强都会混淆它。最小学习对照须同时匹配：parameter count、depth、训练scene、noise、labels、optimizer更新数、prior architecture，并额外报告FLOPs、actions及训练walltime。

以下结果才支持学习收益：在同一误差目标下，较少训练parents达到质量；OOD shape/contrast保持优势；2–3个material blocks达到原4层SOM-Net同等或更好图像。不能把原2D TM训练的成功当3D vector证据。

Generic-recurrence control用同样的输入/状态维度与可训练参数，但将精确物理反馈作用替换为可学习映射。另需一个参数匹配的no-feedback模型。这样可以区分“物理交互免学习”与“仅增加了迭代容量”。

## 5. Physical consistency value

SA-RF精确强制的是：同一h、所有源的w=H\widehat e、同一近似传播算子、与该算子一致的adjoint。对于full Maxwell，残差等于传播缺陷而非自动零。

同时报告：材料truth error；full nonlinear predicted data；common-material residual；full-state residual；passivity/constitutive pole violation；互易性defect；core最小奇异值；所有失败与fallback。

当full current未实际计算，报告“隐含current的误差关系”，不要把它写成已输出current或已验证full-state residual。实验用于检查的full solves也需单独收费。

小PDE residual不等于正确image：f(x1,x2)=x1型的歧义可有多个完全consistent材料。被动性可以排除一部分不合法解，无法凭空提供数据没有的形状信息。

## 6. A21 primal/dual 的可用部分

A21说明单边primal approximation可能不能保持材料任务。[P21] 本轮用它要求：不仅检查material→source→data，也检查residual→source adjoint→material。

最简单实现已是
\[
 g_i=\operatorname{realpack}\sum_{s,\alpha}
 \overline{a_i'\widehat e_{s,i,\alpha}}z_{s,i,\alpha}.
\]
它本身是物理bilinear coupling。额外attention、gating或“dual branch”若只重复这个收缩，并没有新信息；若更贵且不改善error，直接删除。只有缓存/低秩替代ordinary adjoint确实更便宜，或可训练prior利用这些features产生matched-capacity增量，才具有方法价值。

尤其不可把oracle post-step adjoint load作为online feature，不可把A21保留某个GN optimum的证明偷换成未训练网络的generalization保证。

## 7. TSOM 与 A23 之外可以检验的具体差别

| 变化 | 可检验的技术机制 | 必须排除的解释 |
|---|---|---|
| affine source anchor | 固定receiver correction预算不再被source特解占用 | 只是总存储/总rank增加 |
| full-grid material source | sharp support不被固定current chart直接截掉 | 只是更强shape prior |
| 小有理feedback核心 | 每block包含多阶已知相互作用 | 只是网络更深/更大 |
| receiver-adjoint cache | 无需online background solve即可得到data及pullback | offline成本被隐藏 |
| full-model defect监测 | 能识别近共振/传播截断失败 | 只降低surrogate residual |

这五项的组合是候选工程贡献。前三项分别在affine ROM、material-parametric forward models、Woodbury/CIE-I类方法中都有先例；**不能仅凭组合名称宣布first**。真正强TAP潜力取决于能否证明和展示在3D Maxwell上的完整误差—成本优势。

## 8. 一个必须接受的可能结果

若exact feedback oracle能改善无NN图像，但低秩版不能：机制有价值，当前压缩方式失败，不应立刻训练NN去掩盖它。

若exact feedback也不能在相同prior/预算下改善：可能measurement信息或prior主导，B缺少architecture headroom，优先C/ordinary adjoint。

若A与B一样好：独立收益更可能来自anchor/basis/learning，不是feedback。

若generic recurrence匹配B：不能证明物理feedback是必要归纳偏置。

若B图像更好但完整成本更高：它是quality/consistency候选，不是用户要求的更快算法，应如实标记trade-off。

## 9. 信息论边界

exact relative identity不改变实际Maxwell measurement likelihood。O与M是计算路径，primal与dual是同一Jacobian的两个方向，网络输入是原data的确定性变换。这里没有新增Fisher information；更好结果只能来自更忠实使用已有信息、较好的正则化/先验或较低数值误差。
