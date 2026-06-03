# 工作完成情况与内容介绍

## 项目目标

本项目将 SuperSplat 的 3D Gaussian Splat 编辑前端与 PhysGaussian 的 MPM 仿真后端连接起来，使用户可以在浏览器中选择模型、设置物理参数、提交仿真，并把返回的运动数据加载为可播放动画。

## 已完成内容

1. **SuperSplat 前端集成**
   - 新增物理仿真面板和底部工具栏入口。
   - 支持模型注册、官方配置预览、对象/场景选择、材料参数和时间参数编辑。
   - 支持 explicit MPM、implicit MPM、PBMPM local/global 求解入口。
   - 移除了当前不稳定或未完成的求解 UI：有限质量刚体、G2P Local-SO3、implicit obj energy。
   - 去掉 PBMPM 的“试验”文案，参数名保持前端兼容，同时内部使用 `iteration_count`、`elasticity_ratio`、`elastic_relaxation` 等语义。
   - 增加 `motion.physmotion.json`、`motion.bin`、`indices.bin` 加载与播放逻辑。

2. **PhysGaussian 后端桥接**
   - 新增 `server/phys_backend.py` FastAPI 服务。
   - 提供模型上传/注册、模型列表、配置预览、仿真提交、任务状态、motion 文件和求解 trace 下载接口。
   - 前端传入的选择框、对象参数、材料参数、求解参数会被转换为 PhysGaussian 配置。
   - 官方配置模式不再锁定求解方法和时间参数，只锁场景、对象、材料和边界等官方预设内容。

3. **PhysGaussian 求解扩展**
   - 新增/扩展 `integrator` 选择：`mpm`、`implicit_mpm`、`pbmpm`。
   - 隐式 MPM 增加 Newton/GMRES 求解历史记录，输出 `solver_trace.json`。
   - PBMPM 增加 local/global 投影参数和向后兼容字段。
   - PBMPM 是本项目在 PhysGaussian/Warp MPM 路径中的改写实现，不是直接运行上游 WebGPU demo。
   - PBMPM 最新修复加入了边界检查、位置 clamp、矩阵安全 clamp 和松弛系数范围限制，避免越界导致 CUDA illegal memory access。

4. **诊断与同步工具**
   - 新增服务器同步脚本 `tools/sync_workspace_to_cloud.ps1`。
   - 新增一致性检查、后端健康检查、近期 run 检查、motion delta 检查和求解 trace 分析工具。
   - 当前服务器有效公网入口为 `https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/`，`/api/health` 已确认可访问；`8448` 当前没有服务监听/转发。

## 当前状态

- 服务器端 `phys_backend` 已正常启动在内部 `0.0.0.0:6006`。
- 公网预览通过 `8443` 访问，`8448` 当前不可用。
- PBMPM 修复代码已同步到服务器，远端 `mpm_utils.py` 的 SHA-256 为 `7ca62716bfa2157110d96a60b072b0925b179369f90b1b890e43145af670162d`。
- 上一次完整 PBMPM 失败原因是 P2G PBMPM kernel 越界触发 CUDA illegal memory access；修复后仍需继续验证完整仿真结果。
- 隐式 MPM 可以跑通，但 30 帧 ficus 级别示例约 12 分钟，主要慢在大量 substep 和 Newton/GMRES 迭代；动画加载慢则主要来自 dense motion 二进制体积。

## 代码组织

- `server/`：本项目新增后端桥接服务。
- `tools/`：同步、检查和调试脚本。
- `tools/internal_dev/`：内部开发用的第三方样例数据下载、注册和 preview 调试脚本，不包含数据本体。
- `src-overrides/`：需要覆盖到 SuperSplat 和 PhysGaussian 上游仓库的必要源码。
- `docs/`：引用说明、使用说明、完成情况和同步策略。

## PBMPM 说明

本仓库不提交 `vendor/pbmpm*` 的完整 checkout，因为它们当前没有本地未提交 diff，而且会以嵌套 Git 仓库形式进入提交。PBMPM 真正需要提交的是本项目对 PhysGaussian 的改写实现，已经在 `src-overrides/physgaussian-src/` 中纳入。
