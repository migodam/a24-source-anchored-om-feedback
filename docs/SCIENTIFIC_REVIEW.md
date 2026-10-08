# Codex 科学审阅与停止判断

冻结的无 NN 配置没有通过当前压缩架构的充分性门槛。结论是停止扩展，
不是否定相对 Maxwell 恒等式，也不是证明所有 feedback 成像都无效。

47 项最终测试通过。两种背景中的 source-anchored、同 U、同 probe 配对
支持删去已为零的 forcing-P；弱背景的归一化 P norm 为 4.79e-16，
Schur coupling identity error 为 4.23e-15。非 anchor 控制的 P norm 为
0.1321，删 P 后空间确实改变。由此可支持的是条件性解析等价，不能推出
不同 receiver 配额之间的算法优越性。

独立任务审计在 R16 自己产生的合法估计处完成，不在 truth state 构建。
20 个有效观测条件中有 6 个超过冻结的 5% material-transfer 或 adjoint
误差门槛；最大误差分别为 5.35177% 和 5.37776%。所有可用 gradient
cosine 均超过 0.99，这不能抵消另一条必需的任务误差条件。因此 Gate2
为 FAIL。缺失的 12 个条件不能消除已有的反例。

弱背景的四个 parent 各有完整四条件子组。F 相对 L 的 parent 等权改善
为 3.97936%，逐 parent 为 2.01460%、3.48854%、6.38222%、4.03209%，
均未达到 10%。R16 保留了这些小幅改善的大部分，但不能据此将 Gate3
授予 PASS。正式 Gate3 要求每 parent 跨两个背景的八条件平均；强背景
公共初始化失败使四个完整 parent 平均均不可得，故为 HOLD。

公共初始化失败的材料可行性为零违约，primal stationarity 很小，
但 dual fixed-point residual 未达到 1e-6。例如首个复算失败条件的
该 residual 为 4.47303e-6，而 normalized gap 已为 5.91067e-8。
不能只依据图像看似合理、gap 小或约束可行就绕过冻结的 KKT 验收。
这限制了对强背景 feedback 成像收益的判断，不能归因为 Maxwell 物理失败。

224 个方法条件均留有状态：136 成功、84 公共初始化失败、4 Born 单臂
失败。136 个成功图像也没有一个达到 full-chi、delta-chi、数据残差和
物理可行性的共同质量区。已知强背景能稀释 full-chi 相对误差；因此必须
同时保留 delta-chi 和数据残差，不能用较小的 full-chi NRMSE 冒充成像成功。

Gate5 为 QUALITY_TARGET_NOT_REACHED。cold、warm 和 N=1/10/100 的
组成已经报告，N=10/100 是由实际 setup/warm 投影的计费表，而非实际
部署重复。当前证据不支持同质量 20% time-to-image 改善。
ordinary full adjoint + 同 TV 与 F 等价；它不能被当作另一臂的独立胜利。
SOM/FFT-TSOM 和 CIE-I/WT-TSOM 的合同缺口进一步限制全算法比较。

三维确认、NN、额外 degree/rank 搜索、新场景、非线性重建扩展均 NOT_RUN。
若未来继续，应另行预注册公共 TV 求解器的健康验收与优化预算，并重新
验证强背景的完整配对，而不是放宽现有阈值、挑选诊断 rank32 替代主臂
或用 NN 掩盖这些缺口。这里没有授权或启动下一阶段。

## 判定汇总器修正记录

初版汇总器只有在 32 个 task 条件齐全时才允许判 FAIL，导致有效的
超阈值反例被 missing coverage 遮蔽。修正的是量词判断的实现：
“全部条件必须满足”已有一个有效反例即可否定。阈值、随机 seeds、
材料、步长、TV、rank、实验数据和分组均未改变。
初版输出保留在 `results/b0/GATE_DECISION_INITIAL_CONTROLLER.json`，
最终输出在 `results/b0/GATE_DECISION.json`；新增两个测试验证这一区别。

## 失败恢复与计费修正记录

首个 B0 controller 在公共初值失败时退出，累计 37.914679 秒、10 labels。
恢复任务将此失败显式登记，保留已失败的 Born 行，并只完成原矩阵缺失
条件；已有 clean labels 从隔离的 offline cache 读取，不重跑其 Maxwell。
恢复任务耗时 9.279044 秒，另付费生成 6 labels，总计仍为 16。
背景重建、失败的重复尝试和审计全部计费，不重置阶段预算。
中断却没有 finalized receipt 的作业现在会阻止后续预算分配。

原始每图 cold 列漏列 geometry setup；报告保留原数值并增加从相应作业
实测 geometry 推导的 cold-in-memory 组成。必需的所有物理准备、公共初值
与三次更新包含在内。archive export 属科学保存费用，留在 inclusive job
账本；disk-loaded-cache 冷启动没有测量，明确为 NOT_RUN。这里没有速度 GO。
