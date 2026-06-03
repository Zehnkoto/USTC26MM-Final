# 使用说明：完整部署与拉取指令

下面以 Linux/服务器部署为主。仓库本身只保存本项目新增源码、覆盖文件、工具和文档；SuperSplat 与 PhysGaussian 需要从上游单独拉取。

## 1. 拉取三个源码仓库

```bash
mkdir -p ~/ustc26mm
cd ~/ustc26mm

git clone <本项目仓库地址> USTC26MM-Final
git clone https://github.com/playcanvas/supersplat.git supersplat-src
git clone --recurse-submodules https://github.com/XPandora/PhysGaussian.git physgaussian-src
```

如果 PhysGaussian 已经先普通 clone，需要补拉子模块：

```bash
cd ~/ustc26mm/physgaussian-src
git submodule update --init --recursive
```

## 2. 覆盖本项目修改源码

```bash
cd ~/ustc26mm/USTC26MM-Final

rsync -a src-overrides/supersplat-src/ ../supersplat-src/
rsync -a src-overrides/physgaussian-src/ ../physgaussian-src/
```

Windows PowerShell 本地复现可用：

```powershell
cd C:\path\to\USTC26MM-Final
Copy-Item -Recurse -Force .\src-overrides\supersplat-src\* ..\supersplat-src\
Copy-Item -Recurse -Force .\src-overrides\physgaussian-src\* ..\physgaussian-src\
```

## 3. 安装 SuperSplat 前端依赖并构建

```bash
cd ~/ustc26mm/supersplat-src
npm install
npm run build
```

构建完成后，静态文件位于 `~/ustc26mm/supersplat-src/dist`。服务器部署时可把它同步到统一目录：

```bash
mkdir -p ~/ustc26mm/supersplat-dist
rsync -a --delete ~/ustc26mm/supersplat-src/dist/ ~/ustc26mm/supersplat-dist/
```

## 4. 安装 PhysGaussian 环境

PhysGaussian 推荐使用 Python 3.9 与 CUDA 版 PyTorch。版本细节以 PhysGaussian 上游 README 为准。

```bash
conda create -n physgaussian python=3.9
conda activate physgaussian

cd ~/ustc26mm/physgaussian-src
pip install -r requirements.txt
pip install -e gaussian-splatting/submodules/diff-gaussian-rasterization/
pip install -e gaussian-splatting/submodules/simple-knn/
```

如果服务器已有可用的 PhysGaussian 环境，可以直接复用，但要确认该环境中已有 CUDA PyTorch、Warp、Taichi 和 gaussian-splatting 子模块依赖。

## 5. 安装后端 bridge 依赖

```bash
conda activate physgaussian
cd ~/ustc26mm/USTC26MM-Final
pip install -r server/requirements.txt
```

## 6. 启动物理后端和前端静态服务

```bash
cd ~/ustc26mm/USTC26MM-Final

PHYSGAUSSIAN_ROOT=~/ustc26mm/physgaussian-src \
PYTHON_BIN=$(which python) \
SUPER_SPLAT_DIST=~/ustc26mm/supersplat-dist \
python -m uvicorn server.phys_backend:app --host 0.0.0.0 --port 6006
```

本项目当前服务器实际使用内部端口 `6006`。公网预览入口由平台/Nginx 转发提供，目前确认可用：

```text
https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/
```

健康检查：

```bash
curl -k https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/api/health
```

注意：`8448` 当前没有服务监听或公网转发，不应作为本项目预览入口。

## 7. 内部样例数据工具

本仓库不包含第三方样例数据、训练模型、PLY、checkpoint 或 motion 缓存。开发时使用的 ficus、bread、plane、wolf 等样例需要从 PhysGaussian/DeformSuite 等原始来源另行获取，并按其许可引用。

如果内部开发人员在共享服务器上已经具备这些样例数据，可以使用 `tools/internal_dev/` 中的脚本下载或注册样例模型：

```bash
cd ~/ustc26mm/USTC26MM-Final

# 下载/解压官方样例数据，并批量注册到后端 work/models
bash tools/internal_dev/download_phys_models.sh

# 或只注册已经存在的官方样例目录
python tools/internal_dev/register_official_phys_models.py

# 或只注册 ficus iteration-7000 内部样例
python tools/internal_dev/register_ficus_7000.py
```

这些脚本包含服务器路径假设，主要供内部开发和复现实验使用；正式部署也可以通过后端 API 上传或注册其他训练好的 3DGS/PhysGaussian 模型。后端会寻找 `point_cloud/iteration_*/point_cloud.ply` 作为预览和仿真输入。

## 8. 同步到现有云端工作区

本地开发完成后，可用同步脚本检查并上传关键文件：

```powershell
powershell -ExecutionPolicy Bypass -File tools\check_workspace_consistency.ps1
powershell -ExecutionPolicy Bypass -File tools\sync_workspace_to_cloud.ps1 -Apply
```

如果需要同时清理云端旧的嵌套 dist：

```powershell
powershell -ExecutionPolicy Bypass -File tools\sync_workspace_to_cloud.ps1 -Apply -CleanDist
```

每次同步后建议再检查：

```bash
curl -k https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/api/health
```
