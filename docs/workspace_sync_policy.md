# 工作区同步策略

本项目同时涉及本仓库、SuperSplat 上游源码、PhysGaussian 上游源码和云端服务器。为了避免前端、后端、求解器不同步，后续修改应遵循这一份策略。

## 本地目录

统一工作区根目录：

```text
C:\Users\李亭皑\Documents\Codex\2026-05-29
```

关键目录：

- `github`：本项目仓库，保存后端 bridge、工具、文档、覆盖源码和 PBMPM 参考源码。
- `supersplat-src`：SuperSplat 上游源码工作区。
- `physgaussian-src`：PhysGaussian 上游源码工作区。

## 云端目录

统一云端工作区：

```text
/root/autodl-tmp/ustc26mm
```

关键目录：

- `server/phys_backend.py`：云端后端 bridge。
- `supersplat-src-patched/`：云端 SuperSplat patched source。
- `supersplat-dist/`：云端前端静态文件。
- `src/physgaussian-src/`：云端 PhysGaussian patched source。

## 同步原则

1. 本地源码是默认 source of truth。
2. 云端允许临时热修，但热修后必须拉回或合并到本地，再从本地统一同步。
3. 不直接整目录覆盖云端；先检查差异，再同步明确文件。
4. SuperSplat 修改后先构建 `dist`，再上传静态文件。
5. PhysGaussian 求解器修改后，至少做语法检查或一次最小运行验证，再同步到云端；临时验证脚本不进入仓库。

## 推荐流程

只读检查：

```powershell
powershell -ExecutionPolicy Bypass -File tools\check_workspace_consistency.ps1
```

预览同步动作：

```powershell
powershell -ExecutionPolicy Bypass -File tools\sync_workspace_to_cloud.ps1
```

执行同步：

```powershell
powershell -ExecutionPolicy Bypass -File tools\sync_workspace_to_cloud.ps1 -Apply
```

执行同步并清理云端旧的嵌套 `dist`：

```powershell
powershell -ExecutionPolicy Bypass -File tools\sync_workspace_to_cloud.ps1 -Apply -CleanDist
```

## 当前服务器入口

当前公网可用入口：

```text
https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/
```

健康检查：

```bash
curl -k https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/api/health
```

`8448` 当前不是有效预览端口。
