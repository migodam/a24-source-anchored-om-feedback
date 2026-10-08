# A24 anatomy 实施交付

职责仅包含 `src/a24/anatomy.py`、`tests/test_algebra.py`、`tests/test_physics.py` 和 `docs/BACKEND_MAP.md`；没有修改既有 A17–A23、theory 或 vendor。没有启动 DeepSeek、子代理、训练、参数 sweep 或 numerical physics run。

已实现：同 U/same-probe 的 source-anchor OPM/drop-zero-P OM；固定 receiver8 加 affine offset 的 OM/ordinary ROM；A23-style source-replacement allocation confound；observable、TSOM intersection、projected TSOM 与 restricted-G 独立审计；R16/R32/local16 的 task、adjoint、feedback action 与 core diagnostics。target32 不 padding，degree 固定为 1，独立 probes 与候选 full-state evaluator 权限分开。

输出：JSON-serializable `anatomy(config,out,book)`，保留全部 planned records、failures/NOT_RUN、G1 identity 与二元 runner status；保存诊断向量 NPZ。backend、质量坐标、adjoints、probe domains、计费与证据边界见 `docs/BACKEND_MAP.md`。

单元测试已写入，数值结果为 **NOT_RUN**。只有父 charged runner 可以执行；A0/A1 合计 ≤120 秒且所有失败与重试计入同一 Ledger。静态编译和任何后来父 runner 的结果应分别记录，不把静态检查变成 Gate 通过。

静态核验：`py_compile` 对 anatomy 与两个 test 文件通过，首次记录 wall=0.006710166 秒；没有 import 后端、初始化 geometry 或执行任何数值测试。最后轻微 schema 补充后的静态复核由父 runner 统一接收。

需要 Codex 审核：最终科学 Gate/claim 判断、same-prior 成像结果与 novelty。当前实现本身不提供 G2–G5 证据。
