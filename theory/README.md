# A24｜Source-Anchored OM Feedback Imaging 研究包

2026-10-08｜理论 + 原文审计 + 算法设计 + 极小实验规范

## 先读哪三份

[最终裁决](A24_EXECUTIVE_DECISION.md) → [主候选完整推导](RELATIVE_FEEDBACK_OM_ARCHITECTURE.md) → [第一轮可证伪实验](MINIMAL_EXPERIMENT_SPEC.md)。实施时另读 [Codex规范](CODEX_A24_EXECUTION_SPEC.md)。

核心建议：**full-grid material excitation，compressed internal-field feedback，affine source anchor。** 不把未知材料和current同时压进固定小chart。现在只建议小型无NN机制实验，不建议大型3D训练。

## 完整14项交付

| 文件 | 内容 |
|---|---|
| [TSOM_SOMNET_ALGEBRA_AUDIT.md](TSOM_SOMNET_ALGEBRA_AUDIT.md) | 术语、空间、原SOM-Net及A20–A23审计 |
| [P_ELIMINATION_AND_FEEDBACK_PRESERVATION.md](P_ELIMINATION_AND_FEEDBACK_PRESERVATION.md) | 精确删P、affine锚定、retained coupling |
| [OM_MATERIAL_SUBSPACE_THEORY.md](OM_MATERIAL_SUBSPACE_THEORY.md) | OM/TSOM空间关系、material/adjoint/image误差 |
| [RELATIVE_FEEDBACK_OM_ARCHITECTURE.md](RELATIVE_FEEDBACK_OM_ARCHITECTURE.md) | full source + 小反馈核心主候选 |
| [SOM_NET_MIGRATION_THEORY.md](SOM_NET_MIGRATION_THEORY.md) | 最小SOM-Net改造、共同材料一致性 |
| [THREE_ARCHITECTURE_COMPARISON.md](THREE_ARCHITECTURE_COMPARISON.md) | A/B/C完整更新、维数、成本与失效 |
| [FEEDBACK_INCREMENTAL_VALUE.md](FEEDBACK_INCREMENTAL_VALUE.md) | 独立增量、反解释和matched controls |
| [TSOM_SECOND_FOLD_PRESERVATION.md](TSOM_SECOND_FOLD_PRESERVATION.md) | 谱约束的精确保留、近似或替代 |
| [CLOSEST_PRIOR_AND_NOVELTY.md](CLOSEST_PRIOR_AND_NOVELTY.md) | 最近邻、重合风险、尚未清关的优先权 |
| [COST_AND_TIME_TO_IMAGE.md](COST_AND_TIME_TO_IMAGE.md) | 完整offline/online、cache、内存、摊销 |
| [THEOREMS_AND_COUNTEREXAMPLES.md](THEOREMS_AND_COUNTEREXAMPLES.md) | T1–T7及DWR，假设/证明/反例/后果 |
| [MINIMAL_EXPERIMENT_SPEC.md](MINIMAL_EXPERIMENT_SPEC.md) | A–D顺序、预算、预注册Gate和停止规则 |
| [CODEX_A24_EXECUTION_SPEC.md](CODEX_A24_EXECUTION_SPEC.md) | 接口、核心伪代码、测试、权限隔离 |
| [A24_EXECUTIVE_DECISION.md](A24_EXECUTIVE_DECISION.md) | 最终13问、GO/HOLD/NO-GO |

补充：[来源与实际阅读范围](SOURCES_AND_READING_LEDGER.md)，[代数验证说明](verification/README.md)，`verification/algebra_checks.py`、`verification/algebra_results.json`、`proposed_protocol.json`、`MANIFEST.sha256`。

## 实际做过与没有做过

已做：原作者教材相关章节、SOM-Net方法原文和项目理论/结果的指定部分核对；文献搜索；全部新公式推导；小型CPU合成代数检查，全部assertions通过。

未做：真实Maxwell成像、NN训练、GPU实验、完整time-to-image benchmark。原TSOM2009/FFT-TSOM2011等关键全文尚未取得，部分长项目报告亦只读取可获取范围。详情逐项列在reading ledger；因此没有完成最终优先权清关，也没有3D性能胜利。

`proposed_protocol.json`是未来真实实验的拟定配置，不是已经执行的protocol或结果。任何执行前修改必须产生新版本并在查看输出前冻结。

## 运行现有验证

Python 3.10+、NumPy。测试环境Python3.13.5/NumPy2.3.5，无GPU。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verification/algebra_checks.py
```

脚本会重写同目录`algebra_results.json`，不同BLAS的roundoff和运行时间可不同。原始交付hash在`MANIFEST.sha256`，重新运行后results hash预期改变。它只测试有限维代数，不是现成的Maxwell成像软件。

## 当前决策

Gate1有数学及代数支持，真实后端检查待执行；Gate2–5均NOT_RUN。首个真实实验只检验相同prior下L无反馈、F精确反馈、R便宜反馈的材料收益和完整代价。失败就按分流规则停止，而不是自动训练更大网络。
