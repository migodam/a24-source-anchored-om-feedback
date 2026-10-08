# 执行前实现约定与来源差异

全部约定在数值输出前冻结，原研究包文件不修改。

1. 用户已选择研究包默认二维主实验并授权独立公开 A24 仓库。
   A20–A23 并无二维接口，因此封装现有 A2 VIE 核心，而不是给三维 DDA
   加 scalar 开关。原二维模块保持逐字快照；未运行它的 GMRES 分支。
   使用同一有限网格离散矩阵的 dense LU；这不是 solver acceleration。
2. 2D `a=chi`，Green 含原 self-cell 积分；3D 使用原 CM/RR 极化率，
   `Goff` 对角为零。二维 current/field 为 sqrt(area) 质量归一；
   三维 current 为 p/sqrt(volume)。材料坐标均为 sqrt(cell_measure)[Re,Im]。
3. 二维初始化是共同背景线性 adjoint 步加受约束 TV proximal。
   已知背景 Jacobian 可用于步长与背景编码，但任何 truth-state Jacobian
   都不进入 runtime。Runtime config 白名单移除 parent mask、parents、
   truth 与生成幅度；在线加载器拒绝 mixed NPZ 和 offline 路径。
4. 固定 normalized data fidelity 为 .5||W residual||²/||W yb||²。
   每源同方差复噪声时 W 为 scalar，因此该比值等于 .5||res||²/||yb||²。
   噪声 covariance 的实/虚方差各 sigma²/2；Gate 数据残差仍使用真正的
   sqrt(2)/sigma 白化，不用目标归一化代替噪声白化。
5. TV(delta chi) 为全网格实/虚联合 isotropic TV。lambda=.01(1+sigma/beta)，
   beta=背景数据 RMS；步长=.8/lambda_max(Jb^T Jb/||yb||²)。两条规则无
   truth error 调参。PDHG cap2000，normalized KKT/gap1e-6，物理可行1e-10。
   固定一次 half-step retry；拒绝更新保留状态并计费。
6. 二维 dressed-linear 与 linear-a+exact-conversion 等价于 L。
   ordinary full adjoint+同 TV 等价于 F 的材料算法。它们是等价别名，
   不制造独立胜利。BORN_TV 是同背景 offset 的 undressed incremental Born。
7. AFFINE_ROM32 使用八个背景-only、独立随机、1-cell平滑的完整材料probes，
   汇集全部八源背景 tangent snapshots，经SVD形成 rank≤32 Galerkin current
   空间。背景probe准备全部计费，既不使用truth snapshots也不凑rank。
   它的一致性是 projected state；
   w一般不等于h*field，单独报告 constitutive residual。
8. 旧 A2 explicit-current 程序使用 Gaussian12 参数及另一优化预算，不能
   充当 full-grid TV 的传统 SOM/FFT-TSOM。可靠同协议实现缺失明确记录；
   本实验不声称击败所有传统反演方法或清关新颖性。
9. Parent 内等权平均全部8个背景/幅度/噪声条件。Gate3支持要求两家族
   各至少一个 parent F改善≥10%，且R保留≥80%。所有条件 closure/data
   约束单列。Noiseless data恶化 allowance1e-10；noisy allowance为sqrt(m)
   真白化单位。无可分辨feedback的ratio保持null，不能用floor制造PASS。
10. Gate4、NN、额外K=6、波形先验重复实验与新场景均关闭。k32与2x2局部
    blocks已预注册为诊断，不能挑胜者替换 primary rank16。
11. A0/A1≤120秒，B0含失败/计时/报告≤1800秒，条件性3D≤600秒。
    CPU预算指数值/报告进程占用wall，另记录process CPU。代码编写的人类/LLM
    等待时间不冒充计算成本。所有计算作业有独立inclusive receipt。
    静态检查/发布控制器费用另外留账；不重置或借阶段额度。
12. 采用Git source commit和blob记录。历史SHA256字段保留，未进行新的SHA256检查。

## 输出后实现修正（冻结科学定义不变）

- 公共初始化失败改为给所有方法保留显式失败行，恢复作业只处理原矩阵缺失
  条件，已有 clean labels 不重复生成。首个中断与重跑费用保留。
- Gate2 是所有独立任务满足阈值的要求；有效超阈值反例不能被其他缺失
  条件遮蔽。初版 controller 输出保留，最终 FAIL 使用原5%/0.99门槛。
- 未完成且没有 receipt 的旧作业阻止新预算分配，不能默认零费用。
- cold 表补列原先遗漏的实测 geometry；原列与精确来源均保留。
  磁盘加载型 cache cold 未测量，标 NOT_RUN。

详见 [科学审阅](SCIENTIFIC_REVIEW.md)。这些修正未改变材料、先验、步长、
容差、K、degree、rank、random seeds、条件选择、物理 solver 或图像结果。
