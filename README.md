# A24：Source-anchored OM 与 relative Maxwell feedback

本仓库用于固定预算的无 NN 机制实验。原始研究包完整保存在 `theory/`。
实现来源与冻结协议见 `SOURCE_MANIFEST.json` 和 `configs/a24_frozen.json`。

当前状态：IMPLEMENTATION_PRE_NUMERICAL。尚无 A24 成像结论。

二维主实验使用已有 A2 TM/VIE 离散核；条件性三维确认使用 A20/A23
冻结的 dyadic-Maxwell DDA。两者本构、self-term 与证据范围分别报告。

## 执行

Python 3.10+，NumPy/SciPy/Matplotlib，CPU 单线程，GPU 与训练禁用。

```bash
export PYTHONPATH=src
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
python -m a24.cli freeze --job a24-freeze-001
python -m a24.cli anatomy --job a24-a-001
python -m a24.cli no-nn --job a24-b0-001
python -m a24.cli report --job a24-report-001
```

`no-nn` 强制要求 Gate1 PASS。每个 job ID 唯一，不覆盖已有作业。
重跑继承同阶段已消耗预算。原始 clean label 上限16；测试、失败、
独立评价与计时全部计费。不要把 tiny algebra 当成真实成像或速度优势。
