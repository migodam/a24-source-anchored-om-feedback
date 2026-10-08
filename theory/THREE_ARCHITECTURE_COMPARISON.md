# A24｜三种 OM 架构的数学与计算比较

## 1. 路线裁决

A 是最小迁移/消融对照；B 是有条件的主研究候选；C 是必须保留的更简单竞争者。当前没有训练或真实 Maxwell 成像结果，不能按愿望将 B 判成最佳。B 的具体版本采用 **完整材料源 + 压缩传播**，而不是仅给 fixed-current ROM 加 NN。

| 项目 | A：Minimal OM-SOM-Net | B：Feedback-native SA-RF | C：Physics + prior completion |
|---|---|---|---|
| 网络直接预测 | 2rs 个 real current coefficients | p=2N 个 real material correction /全图 prior | p 维结构补全或少量 prior parameters |
| currents | 固定 M bank 内自由系数 | 同一 χ 经物理 closure 生成，无独立每源自由 current | 通常不输出 current |
| 关键物理 | e=Ei+Gj，解析公共材料比值 | relative source equation + 小核心 inverse +一致 adjoint | 粗成像、弱方向 prior、一次物理 recoil |
| 内部反馈 | NN/交替 current update 隐式承担；背景 dressing可保留 | 每 block 显式有理反馈；不要求浅 Neumann | coarse/recoil 可选同一 SA-RF |
| 建议 blocks | 2–3，同时保留原4层 baseline | 2–3 material blocks | 1个 decoder + 1个受限物理修正 |
| 新颖性风险 | 高，ICLM/CS-Net/VBRL近邻直接 | 中高：ROM、CIE-I、physics-unrolling均已有 | 高，两步成像/learned prior已有 |
| 主要风险 | 合法 current 被固定 bank 排除 | 传播低秩不成立、n k²与接收伴随太贵 | prior hallucination与OOD、recoil无增量 |

## 2. Architecture A：完整更新合同

已知 χ^k 后先解析构造 c_M^k，再预测 δc^k：
\[
 c_s^{k+1}=Z_M^*H(h^k)e_{b,s}+N_\theta(\chi^k,c_s^k,c_{M,s}^k,\text{O features}),
\]
\[
 j_s^{k+1}=j_{b,s}+\delta j_{o,s}+V_Mc_s^{k+1},\quad
 e_s^{k+1}=e_s^{inc}+Gj_s^{k+1},
\]
\[
 \chi^{k+1}=\Pi_\mathcal C\chi\!\left(\operatorname{CommonLS}_{s,\alpha}(j^{k+1},e^{k+1})\right).
\]

材料转换的 pole guard 和 projected LS 非精确性见迁移文档。固定量包括 S/G、reference fields、observable basis、V_M、Z_M、GV_M；训练量只有 coefficient network、可选正步长/正则权重。典型缓存 O(n(r+ell+s)+qr)，另加参数/activations；每 block O(nrs)+NN，是否每层加 receiver residual须明确。动态 bank不是这个主合同。

理论性质：observable split 可硬保留；common LS 的 residual可精确计算；无完整 Maxwell manifold guarantee。有效性取决于 declared material class 的 basis coverage，不存在全材料精确性。

## 3. Architecture B：完整更新合同

固定 \(\widehat{\mathcal G}_b=D+U_gV_g^*\)、\(\mathcal D_b=Z_b^*\)。
\[
 C_h=(I-HD)^{-1}H,\quad K_h=I-V_g^*C_hU_g,
\]
\[
 c_s=K_h^{-1}V_g^*C_he_{b,s},\quad
 \widehat w_s=C_h(e_{b,s}+U_gc_s),\quad
 \widehat y_s=y_{b,s}+\mathcal D_b\widehat w_s.
\]
给 r=白化数据残差，计算同一 surrogate 的 exact discrete adjoint g。然后
\[
 \chi^{k+1}=\Pi_\mathcal C\operatorname{Prior}_\theta(\chi^k-\tau_kD_kg;\text{physical features}).
\]

输入：y、已知 acquisition/reference 与初值。输出：公共 full material image，另返回 predicted data、local/core margins、缺陷统计。完整 current不是免费输出；需要时另付 R_b\widehat w 的 action。

固定物理量为背景缓存及构建方式，训练量是小 prior/correction operator与有界步长。不训练完整 inverse，也不让网络改写 G、a(χ) 或互易性。多源共享 core与材料，网络可共享跨block参数。

每 block（b为固定局部块current大小）约
\[
 O(nb^2+n b k+n k^2+k^3+nks+nqs)+T_{prior},
\]
伴随再增加 receiver contraction和若干相同量级的core应用。内存 O(nq+nk+nb+ns+k²s)+NN activations。n k²组装不可省略；细化见成本文档。

理论性质：在近似传播模型内公共材料一致性是硬的；full-model state error由 r_h 控制；full material excitation保留；全局收敛与图像可恢复性没有自动保证。

## 4. Architecture C：先推断数据支持的材料，再补全先验

### 4.1 无 NN 的 Gaussian 基线

在已知参考或当前可部署粗图 x0 附近线性化；实化白化后令 A=J0Γ^{1/2}，Γ为声明的 full-grid prior covariance action。以 x=μ+Γ^{1/2}z 参数化，线性 Gaussian 模型的 posterior 为
\[
 \bar x=\mu+\Gamma J_0^*(I+J_0\Gamma J_0^*)^{-1}(y-f(x_0)-J_0(\mu-x_0)),
\]
\[
 \Sigma=\Gamma-\Gamma J_0^*(I+J_0\Gamma J_0^*)^{-1}J_0\Gamma.
\]
若保留 A=UΣ_A V* 的稳定部分，则 whitened prior coordinates 的强方向方差由1变成1/(1+σ_i²)，未保留方向仍按prior处理，不声称由数据恢复。

Γ应用采用wavelet diagonal、稀疏precision或低秩加对角，不默认存 p² dense covariance。full material domain保留，只有数据支持的 correction低秩。若强行用32D chart并把外部材料设0，必须重新计chart bias。

GMM版本按各成分的线性Gaussian marginal likelihood加权，分别计算上述mean/covariance；额外成本乘成分数。passivity projection 后不是精确Gaussian posterior，uncertainty只能称局部proxy，校准需另外实测。

### 4.2 Learned / structured completion

输入 coarse x_c、data-supported map、field energy、physical residual、局部uncertainty proxy：
\[
 x_p=\Pi_\mathcal C\{x_c+\operatorname{Complete}_\theta(x_c,g_c,u_c)\}.
\]
Complete 可以是完整网格的 multiscale sparse proximal、TV、patch Gaussian/GMM，或一个小decoder。应输出 full material，包括未被测量独立确认的弱方向；报告中明确标记“prior-dependent completion”，不能混称physics reconstruction。

若使用稳定材料 projector P_s，它必须由已知参考/预测状态和noise/prior定义，不能从test truth计算。prior network限制在 I−P_s 中可减少强方向污染，但 nonlinear data不再因此严格不变。

### 4.3 一次低成本物理 recoil

主合同不用新的完整 GN。计算 g_p=\widehat J(x_p)*W*W(\widehat f(x_p)−y)，并试一步
\[
 x_{out}=\Pi_\mathcal C(x_p-\tau P_sD_pg_p).
\]
只允许预注册的一个步长及一次减半重试，或直接固定步长；把所有 forward/adjoint actions计入。若 surrogate data objective不下降，保留x_p并记录recoil rejected；不能删去该case。也允许小维restricted LS recoil作为另注册分支，但不能免费多算。

最后评估必须用full nonlinear Maxwell f_full(x_out)，而不是只报告用于接受步的surrogate residual。该full solve在实验中是评估成本；若部署也要执行它，则计入online time。

### 4.4 C 的可证明性质和局限

在线性Gaussian假设下mean/covariance公式准确；在非线性问题上只是局部proxy。投影保证显式材料域可行但不恢复可识别性。recoil能改善surrogate data fit的条件不等于改善真值image。其优势可能主要来自prior而非feedback；必须比较同一decoder有/无recoil、有/无physicalfeedback。

C通常只运行少数物理动作，可能比每层forward+adjoint的B更便宜。若C已经达到同等质量与稳健性，不应为维持“feedback-native network”叙事坚持B。

## 5. 不能遗漏的四个对照

第一，ordinary adjoint + 同一个prior network；第二，affine current-ROM + 同一个prior；第三，CIE-I/FFT-TSOM或TSOM-derived unrolling；第四，B中的physicalfeedback替换为matched-parameter generic recurrence。它们分别排除额外prior、affine lifting、已有积分方程改写和更大network的解释。

## 6. 三个理论上可以成立、但不能预先当实测结果的收益

**输出维度：** B直接预测p=2N，而自由3D全current输出为2ns=6Ns；s=6时两者相差18倍。但原网络可按源共享权重，数据搬运/物理缓存不会等比例缩小，所以18倍不是参数、显存或时间加速。

**少层：** B每次小核心inverse显式总结surrogate的全部反馈阶数，网络不必用depth逼近同样的线性反馈；但材料非线性/先验推断仍可能需更多blocks。必须实测2/3/4层matched baselines。

**泛化：** 若变化只在h，固定已知背景相互作用不需重新学习；形状细节由full-grid h表示。新几何/频率会改变cache；高relative change或近共振仍可能失效。不能把fixed-acquisition表现叫跨频跨几何泛化。

## 7. 选择顺序

先比较无NN B与无反馈版本的物理初始化，再测试A→B的matched migration，始终保留C与ordinary adjoint+prior。只有当物理反馈在明确regime中以可接受成本改善full image、full data和合法性，才允许扩大训练。
