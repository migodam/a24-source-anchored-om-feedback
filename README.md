# A24：Source-anchored OM 与 relative Maxwell feedback 成像

**当前压缩架构未通过：Gate1 PASS；Gate2 FAIL；Gate3 HOLD；
Gate4 NOT_RUN；Gate5 QUALITY_TARGET_NOT_REACHED。**
47 项最终测试通过，不能据此宣称成像或加速成功。

从 [完整中文研究报告](A24_RESEARCH_REPORT_ZH.md) 开始阅读。
[科学审阅与停止判断](docs/SCIENTIFIC_REVIEW.md) 解释数值反例、优化失败和证据边界；
[执行报告](A24_EXECUTION_REPORT.md) 提供运行、预算与复现信息。

固定 24×24 二维 TM/VIE，8 sources、32 receivers，两个已知背景，
四个合成 parent、双幅度、无噪声/20dB：16 clean states、32 observations。
七臂共 224 条记录：136 成功、84 公共初始化失败、4 Born 单臂失败。
强背景初始化的冻结 KKT 验收未通过，正式八条件 parent 比较均不完整。

可用弱背景子组中，精确反馈 F 相对 L 的 parent 等权改善仅 3.98%。
R16 在 6 个有效条件超过冻结的 5% 独立任务误差要求，故 Gate2 FAIL。
成功图像没有进入共同质量区，因此没有同质量 time-to-image 优势证据。
3D 确认、NN、额外 degree/rank 搜索和大实验全部 **NOT_RUN**。

![冻结高幅度 shell 对照](results/report/figures/image_weak_2401_1.2_snr20.png)

## 证据入口

- [最终 gate decision](results/b0/GATE_DECISION.json) 与
  [初版判定实现记录](results/b0/GATE_DECISION_INITIAL_CONTROLLER.json)。
- [逐条件数据](results/b0/CASES.csv)、[独立任务审计](results/b0/TASK_AUDIT.csv)、
  [失败日志](results/b0/FAILURE_LEDGER.jsonl)、[全部作业](results/jobs/)。
- [成像数组](results/b0/images/)、[隔离的观测](results/b0/data/online/)、
  [隔离的 offline truth/clean labels](results/b0/data/offline/)。
- [图表与原始绘图数据](results/report/)、[完整逐事件成本压缩档](results/archive/)、
  [成本汇总](results/COST_SUMMARY.json)。
- [原研究包](theory/)、[后端映射](docs/BACKEND_MAP.md)、
  [实现约定与协议差异](docs/PROTOCOL_IMPLEMENTATION_DECISIONS.md)、
  [冻结配置](configs/a24_frozen.json)、[来源](SOURCE_MANIFEST.json)。
- [Release 与匿名核验](https://github.com/migodam/a24-source-anchored-om-feedback/releases/tag/v0.1.0-no-nn-pilot)。

2D 复用原 A2 离散核，`a=chi`，含原 self-cell integral；3D 代码复用冻结
A20/A23 dyadic DDA、CM/RR 极化率及材料导数，但没有执行。
二维结果不能当作三维 Vector-Maxwell 成像证明。
ordinary full adjoint + 同 TV 与 F 等价；SOM/FFT-TSOM 的旧 Gaussian prior
实现不匹配，CIE-I/WT-TSOM 缺少可靠实现，均不声称已击败。

## 复现与预算

现有 Python、NumPy/SciPy/Matplotlib，CPU 单线程。精确环境见
[ENVIRONMENT.json](ENVIRONMENT.json)。不安装 CUDA，不修改 solver。

```bash
export PYTHONPATH=src
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
python -m a24.cli freeze --job independent-freeze-001
python -m a24.cli anatomy --job independent-a-001
python -m a24.cli no-nn --job independent-b0-001
python -m a24.cli report --job independent-report-001
```

在发布目录原位运行会继承已有预算和标签，复用保存的结果；不会免费重置。
若用户需要独立重新生成，应在自己的副本中将发布的 `results/` 整体保留为
只读档案，再使用空结果目录，明确作为一个新的、相同有限预算的独立复现。
不要覆盖原档案。当前执行没有自动启动这种新实验。

A0/A1≤120 CPU wall 秒；B0 含失败、计时、报告和发布≤1800秒；
条件性3D≤600秒且最多4states，未启动；GPU=0。
每个 job ID 唯一。未知中断成本会阻止新预算分配。
所有方法共用初始化、材料约束、TV、K=3 和一次 half-step retry。
没有根据输出修改阈值、prox cap、先验、rank 或场景。

冷启动与 warm 的实测组成、N=1/10/100 计费投影均报告。
N=10/100 不是实际重复部署；disk-loaded-cache cold 为 NOT_RUN。
代码、理论、数值 identity、2D 图像、3D 与完整部署证据分别记录。
