# 引用说明

本项目是在三个开源/论文系统基础上做的集成与扩展。论文、上游工程和第三方代码均应在报告、展示和仓库说明中明确引用。

## 上游项目

1. **SuperSplat Editor**
   - 项目地址：https://github.com/playcanvas/supersplat
   - 用途：作为 3D Gaussian Splat 的浏览器编辑器和前端交互基础。
   - 本项目修改：新增物理面板、物理会话管理、运动数据加载与播放、物体/场景选择到后端仿真的参数传递。
   - 许可：以 SuperSplat 上游仓库 `LICENSE` 为准。

2. **PhysGaussian: Physics-Integrated 3D Gaussians for Generative Dynamics**
   - 项目地址：https://github.com/XPandora/PhysGaussian
   - 项目页：https://xpandora.github.io/PhysGaussian/
   - arXiv：https://arxiv.org/abs/2311.12198
   - 用途：作为 MPM 仿真和 3D Gaussian 动态生成基础。
   - 本项目修改：增加前端参数桥接、隐式 MPM、PBMPM local/global 投影入口、求解历史记录与 motion 导出。
   - 许可：以 PhysGaussian 上游仓库 `LICENSE` 为准。

3. **PB-MPM / A Position Based Material Point Method**
   - 代码地址：https://github.com/electronicarts/pbmpm
   - SIGGRAPH 2024 可读版本：https://github.com/electronicarts/pbmpm/tree/siggraph2024
   - 论文/项目引用：Chris Lewin, *A Position Based Material Point Method*, ACM SIGGRAPH 2024.
   - 用途：作为 PBMPM 算法语义、local/global 投影流程和 WebGPU 参考实现。
   - 本项目处理：没有把 PB-MPM WebGPU 源码作为运行时直接调用，而是在 PhysGaussian/Warp MPM 路径中实现了本项目的改写版 PBMPM。
   - 本地实现位置：`src-overrides/physgaussian-src/mpm_solver_warp/mpm_utils.py` 与 `src-overrides/physgaussian-src/mpm_solver_warp/mpm_solver_warp.py`。
   - 需要说明：本项目版本是面向 3D Gaussian/PhysGaussian 数据流的 PBMPM 改写实现，包含额外的边界检查、矩阵 clamp、位置 clamp、松弛系数限制、兼容前端参数和求解 trace；不能简单等同于上游 WebGPU demo。
   - 许可：PB-MPM 源码为 BSD 3-Clause，见 `vendor/pbmpm*/LICENSE.md`。

## 需要在报告中说明的二次开发

- 前端：基于 SuperSplat 增加 PhysGaussian 交互面板、选择工具联动、仿真参数 UI、历史/调试入口和动画播放。
- 后端：新增 FastAPI bridge，把前端模型、对象选择和求解参数转换为 PhysGaussian 配置并管理仿真任务。
- 求解器：在 PhysGaussian 基础上扩展 explicit MPM、implicit MPM 和 PBMPM 入口，并输出求解细节 trace。
- 数据格式：新增 `motion.physmotion.json`、`motion.bin`、`indices.bin`，供 SuperSplat 播放仿真结果。

## 样例数据说明

本仓库不提交第三方训练模型、PLY、checkpoint 或 motion 数据。开发过程中使用的 ficus、bread、plane、wolf 等样例来自 PhysGaussian/DeformSuite 相关公开样例资源；如果在报告或演示中使用这些样例，应额外注明其原始来源和许可。

`tools/internal_dev/` 中的脚本只供内部人员在共享服务器上下载或注册这些样例数据，不代表数据本体随本仓库发布。

## 第三方参考代码处理

PBMPM 上游源码可按需在本地单独 clone 阅读，但不作为本项目运行时依赖提交。本仓库提交的是 PhysGaussian 中的本地改写实现和必要覆盖源码，避免把第三方嵌套 Git 仓库或演示媒体一起上传。
