# Render Insert Report

Render root: local outputs_downloads render directory (not committed).
Render summary: `{"run_count": 47, "failure_count": 1, "success_count": 46, "failure_path": "/root/autodl-tmp/ustc26mm/outputs/ablation_supersplat_renders_frontend_state_close_i7000_20260608_frontend_state_close_132333/render_failures.jsonl"}`
Render index run_count: `47`
Render failures recorded: `1`

## Generated Group Figures
- `baseline` -> `figures\render_strips\group_baseline.png`
- `grid` -> `figures\render_strips\group_grid.png`
- `frame_dt` -> `figures\render_strips\group_frame_dt.png`
- `substep_dt` -> `figures\render_strips\group_substep_dt.png`
- `implicit_tolerance` -> `figures\render_strips\group_implicit_tolerance.png`
- `pbmpm_strength` -> `figures\render_strips\group_pbmpm_strength.png`

## Group Figure Run Lists
### `baseline`
- 显式 MPM
g=50, f=0.02, s=1e-4: `explicit_g50_f0p02_s0p0001_d1ad4c1c`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_default_c445737e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str1p0_b6b9d44a`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `grid`
- 显式 MPM
g=25, f=0.02, s=1e-4: `explicit_g25_f0p02_s0p0001_2718b8d9`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 显式 MPM
g=50, f=0.02, s=1e-4: `explicit_g50_f0p02_s0p0001_d1ad4c1c`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 显式 MPM
g=100, f=0.02, s=1e-4: `explicit_g100_f0p02_s0p0001_35f9641a`; found=[0]; missing=[5, 10, 15, 20, 25, 30]; note=failed/incomplete
- 隐式 default
g=25, f=0.02, s=1e-4: `implicit_g25_f0p02_s0p0001_default_308d0146`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_default_c445737e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=100, f=0.02, s=1e-4: `implicit_g100_f0p02_s0p0001_default_deffd421`; found=[0, 5, 10]; missing=[15, 20, 25, 30]; note=stopped/incomplete
- PBMPM str=1.0
g=25, f=0.02, s=1e-4: `pbmpm_g25_f0p02_s0p0001_str1p0_75ef7973`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str1p0_b6b9d44a`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=100, f=0.02, s=1e-4: `pbmpm_g100_f0p02_s0p0001_str1p0_da2eddf5`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `frame_dt`
- 显式 MPM
g=50, f=0.02, s=1e-4: `explicit_g50_f0p02_s0p0001_d1ad4c1c`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 显式 MPM
g=50, f=0.04, s=1e-4: `explicit_g50_f0p04_s0p0001_aad240a7`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 显式 MPM
g=50, f=0.06, s=1e-4: `explicit_g50_f0p06_s0p0001_5e5535da`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_default_c445737e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.04, s=1e-4: `implicit_g50_f0p04_s0p0001_default_3be4da76`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.06, s=1e-4: `implicit_g50_f0p06_s0p0001_default_e393a478`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str1p0_b6b9d44a`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.04, s=1e-4: `pbmpm_g50_f0p04_s0p0001_str1p0_8d5f1f05`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.06, s=1e-4: `pbmpm_g50_f0p06_s0p0001_str1p0_efb4ee18`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `substep_dt`
- 显式 MPM
g=50, f=0.02, s=1e-4: `explicit_g50_f0p02_s0p0001_d1ad4c1c`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 显式 MPM
g=50, f=0.02, s=5e-4: `explicit_g50_f0p02_s0p0005_ce103b7d`; found=[0]; missing=[5, 10, 15, 20, 25, 30]; note=failed/incomplete
- 显式 MPM
g=50, f=0.02, s=1e-3: `explicit_g50_f0p02_s0p001_b36c8e73`; found=[0]; missing=[5, 10, 15, 20, 25, 30]; note=failed/incomplete
- 隐式 default
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_default_c445737e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=5e-4: `implicit_g50_f0p02_s0p0005_default_abcfb0d3`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=1e-3: `implicit_g50_f0p02_s0p001_default_c5bf619c`; found=[0]; missing=[5, 10, 15, 20, 25, 30]; note=stopped/incomplete
- PBMPM str=1.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str1p0_b6b9d44a`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=5e-4: `pbmpm_g50_f0p02_s0p0005_str1p0_0e2d8fa1`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=1e-3: `pbmpm_g50_f0p02_s0p001_str1p0_c3d065be`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `implicit_tolerance`
- 隐式 relaxed
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_relaxed_a9866e0e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 default
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_default_c445737e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- 隐式 strict
g=50, f=0.02, s=1e-4: `implicit_g50_f0p02_s0p0001_strict_134d9989`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `pbmpm_strength`
- PBMPM str=0.25
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str0p25_e8ed7385`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=0.5
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str0p5_6c5dfd3b`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str1p0_b6b9d44a`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=2.0
g=50, f=0.02, s=1e-4: `pbmpm_g50_f0p02_s0p0001_str2p0_341e4fa3`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]

## Missing Frames
- `explicit_g100_f0p02_s0p0001_35f9641a` missing frames [5, 10, 15, 20, 25, 30]
- `implicit_g100_f0p02_s0p0001_default_deffd421` missing frames [15, 20, 25, 30]
- `explicit_g50_f0p02_s0p0005_ce103b7d` missing frames [5, 10, 15, 20, 25, 30]
- `explicit_g50_f0p02_s0p001_b36c8e73` missing frames [5, 10, 15, 20, 25, 30]
- `implicit_g50_f0p02_s0p001_default_c5bf619c` missing frames [5, 10, 15, 20, 25, 30]

## Runs With No Frames
- None

## Renderer Failures
- `explicit_g100_f0p02_s0p0001_35f9641a`: TimeoutError()

## LaTeX Insert Positions
- after `tab:common-baseline` -> `fig:baseline-render-strips` using `group_baseline.png` (`baseline`)
- after `tab:grid-ablation` -> `fig:grid-render-strips` using `group_grid.png` (`grid`)
- after `tab:frame-dt-ablation` -> `fig:frame-dt-render-strips` using `group_frame_dt.png` (`frame_dt`)
- after `tab:substep-dt-ablation` -> `fig:substep-dt-render-strips` using `group_substep_dt.png` (`substep_dt`)
- after `tab:implicit-profile-motion` -> `fig:implicit-tolerance-render-strips` using `group_implicit_tolerance.png` (`implicit_tolerance`)
- `group_pbmpm_strength.png` was generated but not inserted because `tab:pbmpm-strength-ablation` is not present in `main.tex`.

## Compile Status
- XeLaTeX compiled successfully after two passes with MiKTeX.
- Output PDF: `main.pdf` (28 pages).
- Large 9-row `frame_dt` and `substep_dt` figures use `height=0.45\textheight` to keep them close to their tables and reduce blank space.
- Remaining warnings are hyperref bookmark warnings for math in headings and two overfull lines from long `\texttt{...}` failure-reason strings.

<!-- BEGIN PBMPM_EVAL_REPORT -->
## PBMPM Supplementary Evaluation

Source packages:
- trace/json/csv: `local pbmpm trace package (not committed)`
- offline renders: `local pbmpm render package (not committed)`

Generated figures and insert positions:
- `group_pbmpm_eval_common_grid.png`: after `tab:pbmpm-common-grid-rel15`
- `group_pbmpm_eval_common_substep.png`: after `tab:pbmpm-common-substep-rel15`
- `group_pbmpm_eval_relax_grid100.png`: after `tab:pbmpm-relax-grid100`
- `group_pbmpm_eval_relax_dt001.png`: after `tab:pbmpm-relax-dt001`
- `group_pbmpm_eval_strength_grid100.png`: after `tab:pbmpm-strength-grid100`
- `group_pbmpm_eval_strength_dt001.png`: after `tab:pbmpm-strength-dt001`

Run lists and missing frames:
### `common_grid`
- PBMPM rel=1.5 g=25, f=0.02, s=1e-4: `pbmpm_common_grid_g25_f0p02_s0p0001_str1p0_rel1p5_c4b16895`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=50, f=0.02, s=1e-4: `pbmpm_common_grid_g50_f0p02_s0p0001_str1p0_rel1p5_65eae116`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=100, f=0.02, s=1e-4: `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `common_substep`
- PBMPM rel=1.5 g=50, f=0.02, s=1e-4: `pbmpm_common_grid_g50_f0p02_s0p0001_str1p0_rel1p5_65eae116`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=50, f=0.02, s=5e-4: `pbmpm_common_substep_dt_g50_f0p02_s0p0005_str1p0_rel1p5_f0fa7e59`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=50, f=0.02, s=1e-3: `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `relax_grid100`
- PBMPM rel=0.0 g=100, f=0.02, s=1e-4: `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel0p0_f59ce47d`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.0 g=100, f=0.02, s=1e-4: `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel1p0_32030778`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=100, f=0.02, s=1e-4: `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=2.0 g=100, f=0.02, s=1e-4: `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel2p0_288d979f`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `relax_dt001`
- PBMPM rel=0.0 g=50, f=0.02, s=1e-3: `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel0p0_5b1182ee`; found=[0, 5]; missing=[10, 15, 20, 25, 30]; note=failed/incomplete
- PBMPM rel=1.0 g=50, f=0.02, s=1e-3: `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel1p0_f7ad95d8`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=1.5 g=50, f=0.02, s=1e-3: `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM rel=2.0 g=50, f=0.02, s=1e-3: `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel2p0_728a4370`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `strength_grid100`
- PBMPM str=0.25 g=100, f=0.02, s=1e-4: `pbmpm_strength_grid100_g100_f0p02_s0p0001_str0p25_rel1p5_87332a7e`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=0.50 g=100, f=0.02, s=1e-4: `pbmpm_strength_grid100_g100_f0p02_s0p0001_str0p5_rel1p5_b102c176`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.00 g=100, f=0.02, s=1e-4: `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=2.00 g=100, f=0.02, s=1e-4: `pbmpm_strength_grid100_g100_f0p02_s0p0001_str2p0_rel1p5_28c62c78`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=4.00 g=100, f=0.02, s=1e-4: `pbmpm_strength_grid100_g100_f0p02_s0p0001_str4p0_rel1p5_31e480f9`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
### `strength_dt001`
- PBMPM str=0.25 g=50, f=0.02, s=1e-3: `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str0p25_rel1p5_80bf1d51`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=0.50 g=50, f=0.02, s=1e-3: `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str0p5_rel1p5_18c3e13c`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=1.00 g=50, f=0.02, s=1e-3: `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=2.00 g=50, f=0.02, s=1e-3: `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str2p0_rel1p5_1e6850ed`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]
- PBMPM str=4.00 g=50, f=0.02, s=1e-3: `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str4p0_rel1p5_70129129`; found=[0, 5, 10, 15, 20, 25, 30]; missing=[]

Data completeness:
- NaN/Inf counts are zero in `ablation_summary.csv`.
- Projection residual and constraint residual fields are empty in this package.
<!-- END PBMPM_EVAL_REPORT -->

