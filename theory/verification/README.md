# A24｜可复现的CPU代数核验

## 实际运行范围

`algebra_checks.py`是本包唯一已经执行的数值程序。使用Python3.13.5、NumPy2.3.5和固定随机种子241008；不联网、不训练、不调用GPU、不读取原项目truth/current/Jacobian。主要矩阵维数为18个复current坐标、6个三分量cell、3个sources、5个receivers；另有12维、rank2的合成结构例子。

**这些随机矩阵不是Maxwell Green算子。** 检查说明推导的有限维代数和反例可复现，不能证明真实3D传播可压缩、材料成像变好、网络泛化更强或time-to-image下降。

## 运行

从研究包根目录运行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verification/algebra_checks.py
```

依赖仅Python3.10+与NumPy。脚本重写同目录`algebra_results.json`；复算后浮点尾数、运行时间与结果hash可能变化。`MANIFEST.sha256`描述交付时的文件版本。不要将此脚本与`CODEX_A24_EXECUTION_SPEC.md`中尚待实现的CLI混淆。

## 已核验的核心项目

| 检查 | 交付结果 | 含义 |
|---|---:|---|
| source-anchored P/forcing范数 | 2.82e−16 | 同U下P为数值零 |
| Schur inverse恒等式相对误差 | 3.74e−16 | 仍保留完整complement反馈 |
| retained-coupling恒等式误差 | 4.61e−16 | 一般U下degree-shift必须计coupling |
| 忽略retained coupling的误差 | 4.04% | 反驳无条件P/M合并 |
| relative-current恒等式误差 | 1.47e−15 | 背景相对式是精确有限幅度关系 |
| 小有理core与完整surrogate解的误差 | 1.68e−16 | 小反馈solve不要求全材料源低维 |
| same-surrogate实adjoint检验 | 2.15e−16 | 正确处理复field与实材料坐标 |
| corrected DWR恒等式误差 | 3.65e−16 | 包含correction时的双侧残差式 |

同一rank2合成例子中，把完整source投影到固定rank2传播像的误差为93.22%；它只展示两种空间限制不同，**不是TSOM实验结果**。非正规2×2反例的谱半径为0，而degree0 resolvent误差为100。共同材料反例E=(1,1)、J=(1,2)的LS材料为1.5，但仍有非零residual。

截断传播例子还核验了source/data误差上界和完整state residual恒等式。全部assertions通过，机器可读原始数值保留在JSON中。

## 计时与未运行项

JSON里的`elapsed_cpu_wall_seconds`仅为测试函数内的墙钟计时，不含完整解释器启动、文献工作、文件准备，更不是A24真实部署计时。不得用它推断Maxwell吞吐或NN速度。

真实Experiment A1、B0、3D确认以及C/D网络实验全部未运行。`proposed_protocol.json`是将来执行前需要进一步冻结的规范，不是本轮实验回执。
