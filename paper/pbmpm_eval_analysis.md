# PBMPM Parameter Supplementary Analysis

Total runs: 21; success: 20; failure: 1.
Projection residual and constraint residual fields are empty in this package, so the report analyzes success state, timing, motion, bbox, and renders.

## common_grid
- `pbmpm_common_grid_g25_f0p02_s0p0001_str1p0_rel1p5_c4b16895`: success=True; grid=25; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=3.0; wall=40.65; max_disp=0.0051; mean_disp=0.0008; bbox_ratio=1.0005; frames=31; failure=
- `pbmpm_common_grid_g50_f0p02_s0p0001_str1p0_rel1p5_65eae116`: success=True; grid=50; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=5.0; wall=46.88; max_disp=0.0356; mean_disp=0.0023; bbox_ratio=1.0016; frames=31; failure=
- `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=11.00; wall=75.91; max_disp=0.1625; mean_disp=0.0154; bbox_ratio=1.0218; frames=31; failure=

## common_substep
- `pbmpm_common_grid_g50_f0p02_s0p0001_str1p0_rel1p5_65eae116`: success=True; grid=50; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=5.0; wall=46.88; max_disp=0.0356; mean_disp=0.0023; bbox_ratio=1.0016; frames=31; failure=
- `pbmpm_common_substep_dt_g50_f0p02_s0p0005_str1p0_rel1p5_f0fa7e59`: success=True; grid=50; frame_dt=0.02; substep_dt=0.0005; strength=1.0; relaxation=1.5; iters=24.00; wall=38.66; max_disp=0.4417; mean_disp=0.0070; bbox_ratio=1.0071; frames=31; failure=
- `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=1.5; iters=24.00; wall=22.42; max_disp=1.6493; mean_disp=0.2556; bbox_ratio=1.2151; frames=31; failure=

## relax_grid100
- `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel0p0_f59ce47d`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=0.0; iters=11.00; wall=77.44; max_disp=0.3387; mean_disp=0.1998; bbox_ratio=1.0647; frames=31; failure=
- `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel1p0_32030778`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.0; iters=11.00; wall=75.50; max_disp=0.1725; mean_disp=0.0255; bbox_ratio=1.0267; frames=31; failure=
- `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=11.00; wall=75.91; max_disp=0.1625; mean_disp=0.0154; bbox_ratio=1.0218; frames=31; failure=
- `pbmpm_relax_grid100_g100_f0p02_s0p0001_str1p0_rel2p0_288d979f`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=2.0; iters=11.00; wall=75.93; max_disp=0.1546; mean_disp=0.0107; bbox_ratio=1.0187; frames=31; failure=

## relax_dt001
- `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel0p0_5b1182ee`: success=False; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=0.0; iters=24.00; wall=10.57; max_disp=1.6918; mean_disp=1.0298; bbox_ratio=2.4005; frames=7; failure=exit_code_-6
- `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel1p0_f7ad95d8`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=1.0; iters=24.00; wall=22.78; max_disp=1.6811; mean_disp=0.3767; bbox_ratio=1.3003; frames=31; failure=
- `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=1.5; iters=24.00; wall=22.42; max_disp=1.6493; mean_disp=0.2556; bbox_ratio=1.2151; frames=31; failure=
- `pbmpm_relax_dt001_g50_f0p02_s0p001_str1p0_rel2p0_728a4370`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=2.0; iters=24.00; wall=22.80; max_disp=1.5650; mean_disp=0.1281; bbox_ratio=1.0991; frames=31; failure=

## strength_grid100
- `pbmpm_strength_grid100_g100_f0p02_s0p0001_str0p25_rel1p5_87332a7e`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=0.25; relaxation=1.5; iters=5.0; wall=44.26; max_disp=0.2650; mean_disp=0.0525; bbox_ratio=1.0419; frames=31; failure=
- `pbmpm_strength_grid100_g100_f0p02_s0p0001_str0p5_rel1p5_b102c176`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=0.5; relaxation=1.5; iters=8.0; wall=60.08; max_disp=0.2008; mean_disp=0.0282; bbox_ratio=1.0307; frames=31; failure=
- `pbmpm_common_grid_g100_f0p02_s0p0001_str1p0_rel1p5_de36d981`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=1.0; relaxation=1.5; iters=11.00; wall=75.91; max_disp=0.1625; mean_disp=0.0154; bbox_ratio=1.0218; frames=31; failure=
- `pbmpm_strength_grid100_g100_f0p02_s0p0001_str2p0_rel1p5_28c62c78`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=2.0; relaxation=1.5; iters=17.00; wall=109.6; max_disp=0.1213; mean_disp=0.0072; bbox_ratio=1.0133; frames=31; failure=
- `pbmpm_strength_grid100_g100_f0p02_s0p0001_str4p0_rel1p5_31e480f9`: success=True; grid=100; frame_dt=0.02; substep_dt=0.0001; strength=4.0; relaxation=1.5; iters=22.00; wall=135.0; max_disp=0.1000; mean_disp=0.0041; bbox_ratio=1.0086; frames=31; failure=

## strength_dt001
- `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str0p25_rel1p5_80bf1d51`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=0.25; relaxation=1.5; iters=24.00; wall=22.56; max_disp=1.6696; mean_disp=0.3001; bbox_ratio=1.2472; frames=31; failure=
- `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str0p5_rel1p5_18c3e13c`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=0.5; relaxation=1.5; iters=24.00; wall=22.49; max_disp=1.6545; mean_disp=0.2648; bbox_ratio=1.2225; frames=31; failure=
- `pbmpm_common_substep_dt_g50_f0p02_s0p001_str1p0_rel1p5_988cc863`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=1.0; relaxation=1.5; iters=24.00; wall=22.42; max_disp=1.6493; mean_disp=0.2556; bbox_ratio=1.2151; frames=31; failure=
- `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str2p0_rel1p5_1e6850ed`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=2.0; relaxation=1.5; iters=24.00; wall=22.74; max_disp=1.6490; mean_disp=0.2551; bbox_ratio=1.2148; frames=31; failure=
- `pbmpm_strength_grid50_dt001_g50_f0p02_s0p001_str4p0_rel1p5_70129129`: success=True; grid=50; frame_dt=0.02; substep_dt=0.001; strength=4.0; relaxation=1.5; iters=25.00; wall=23.05; max_disp=1.6290; mean_disp=0.2443; bbox_ratio=1.2042; frames=31; failure=
