import sys

sys.path.append("gaussian-splatting")

import argparse
import math
import cv2
import torch
import os
import numpy as np
import json
from tqdm import tqdm

# Gaussian splatting dependencies
from utils.sh_utils import eval_sh
from scene.gaussian_model import GaussianModel
from diff_gaussian_rasterization import (
    GaussianRasterizationSettings,
    GaussianRasterizer,
)
from scene.cameras import Camera as GSCamera
from gaussian_renderer import render, GaussianModel
from utils.system_utils import searchForMaxIteration
from utils.graphics_utils import focal2fov

# MPM dependencies
from mpm_solver_warp.engine_utils import *
from mpm_solver_warp.mpm_solver_warp import MPM_Simulator_WARP
import warp as wp

# Particle filling dependencies
from particle_filling.filling import *

# Utils
from utils.decode_param import *
from utils.transformation_utils import *
from utils.camera_view_utils import *
from utils.render_utils import *

wp.init()
wp.config.verify_cuda = True

ti.init(arch=ti.cuda, device_memory_GB=8.0)


class PipelineParamsNoparse:
    """Same as PipelineParams but without argument parser."""

    def __init__(self):
        self.convert_SHs_python = False
        self.compute_cov3D_python = False
        self.debug = False


def load_checkpoint(model_path, sh_degree=3, iteration=-1):
    # Find checkpoint
    checkpt_dir = os.path.join(model_path, "point_cloud")
    if iteration == -1:
        iteration = searchForMaxIteration(checkpt_dir)
    checkpt_path = os.path.join(
        checkpt_dir, f"iteration_{iteration}", "point_cloud.ply"
    )

    # Load guassians
    gaussians = GaussianModel(sh_degree)
    gaussians.load_ply(checkpt_path)
    return gaussians


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--iteration", type=int, default=-1)
    parser.add_argument("--output_path", type=str, default=None)
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--output_ply", action="store_true")
    parser.add_argument("--output_h5", action="store_true")
    parser.add_argument("--output_super_motion", action="store_true")
    parser.add_argument("--render_img", action="store_true")
    parser.add_argument("--compile_video", action="store_true")
    parser.add_argument("--white_bg", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.model_path):
        AssertionError("Model path does not exist!")
    if not os.path.exists(args.config):
        AssertionError("Scene config does not exist!")
    if args.output_path is not None and not os.path.exists(args.output_path):
        os.makedirs(args.output_path)

    # load scene config
    print("Loading scene config...")
    (
        material_params,
        bc_params,
        time_params,
        preprocessing_params,
        camera_params,
    ) = decode_param_json(args.config)

    # load gaussians
    print("Loading gaussians...")
    model_path = args.model_path
    gaussians = load_checkpoint(model_path, iteration=args.iteration)
    pipeline = PipelineParamsNoparse()
    pipeline.compute_cov3D_python = True
    background = (
        torch.tensor([1, 1, 1], dtype=torch.float32, device="cuda")
        if args.white_bg
        else torch.tensor([0, 0, 0], dtype=torch.float32, device="cuda")
    )

    # init the scene
    print("Initializing scene and pre-processing...")
    params = load_params_from_gs(gaussians, pipeline)

    init_pos = params["pos"]
    init_cov = params["cov3D_precomp"]
    init_screen_points = params["screen_points"]
    init_opacity = params["opacity"]
    init_shs = params["shs"]
    original_gs_num = init_pos.shape[0]
    active_gs_indices = torch.arange(original_gs_num, dtype=torch.int64, device="cuda")

    # throw away low opacity kernels
    mask = init_opacity[:, 0] > preprocessing_params["opacity_threshold"]
    init_pos = init_pos[mask, :]
    init_cov = init_cov[mask, :]
    init_opacity = init_opacity[mask, :]
    init_screen_points = init_screen_points[mask, :]
    init_shs = init_shs[mask, :]
    active_gs_indices = active_gs_indices[mask]

    # rorate and translate object
    if args.debug:
        if not os.path.exists("./log"):
            os.makedirs("./log")
        particle_position_tensor_to_ply(
            init_pos,
            "./log/init_particles.ply",
        )
    rotation_matrices = generate_rotation_matrices(
        torch.tensor(preprocessing_params["rotation_degree"]),
        preprocessing_params["rotation_axis"],
    )
    rotated_pos = apply_rotations(init_pos, rotation_matrices)

    if args.debug:
        particle_position_tensor_to_ply(rotated_pos, "./log/rotated_particles.ply")

    # select a sim area and save params of unslected particles
    unselected_pos, unselected_cov, unselected_opacity, unselected_shs = (
        None,
        None,
        None,
        None,
    )
    if preprocessing_params["sim_area"] is not None:
        boundary = preprocessing_params["sim_area"]
        assert len(boundary) == 6
        mask = torch.ones(rotated_pos.shape[0], dtype=torch.bool).to(device="cuda")
        for i in range(3):
            mask = torch.logical_and(mask, rotated_pos[:, i] > boundary[2 * i])
            mask = torch.logical_and(mask, rotated_pos[:, i] < boundary[2 * i + 1])

        unselected_pos = init_pos[~mask, :]
        unselected_cov = init_cov[~mask, :]
        unselected_opacity = init_opacity[~mask, :]
        unselected_shs = init_shs[~mask, :]

        rotated_pos = rotated_pos[mask, :]
        init_cov = init_cov[mask, :]
        init_opacity = init_opacity[mask, :]
        init_shs = init_shs[mask, :]
        active_gs_indices = active_gs_indices[mask]

    selected_indices = preprocessing_params.get("active_gs_indices", None)
    if selected_indices is not None:
        selected_indices = torch.tensor(
            selected_indices, dtype=torch.long, device="cuda"
        )
        selected_indices = selected_indices[
            torch.logical_and(
                selected_indices >= 0, selected_indices < original_gs_num
            )
        ]
        selected_mask_full = torch.zeros(
            original_gs_num, dtype=torch.bool, device="cuda"
        )
        selected_mask_full[selected_indices] = True
        selected_mask = selected_mask_full[active_gs_indices]

        rotated_pos = rotated_pos[selected_mask, :]
        init_cov = init_cov[selected_mask, :]
        init_opacity = init_opacity[selected_mask, :]
        init_shs = init_shs[selected_mask, :]
        active_gs_indices = active_gs_indices[selected_mask]

    transformed_pos, scale_origin, original_mean_pos = transform2origin(rotated_pos, preprocessing_params["scale"])
    transformed_pos = shift2center111(transformed_pos)

    # modify covariance matrix accordingly
    init_cov = apply_cov_rotations(init_cov, rotation_matrices)
    init_cov = scale_origin * scale_origin * init_cov

    if args.debug:
        particle_position_tensor_to_ply(
            transformed_pos,
            "./log/transformed_particles.ply",
        )

    # fill particles if needed
    gs_num = transformed_pos.shape[0]
    device = "cuda:0"
    filling_params = preprocessing_params["particle_filling"]

    if filling_params is not None:
        print("Filling internal particles...")
        mpm_init_pos = fill_particles(
            pos=transformed_pos,
            opacity=init_opacity,
            cov=init_cov,
            grid_n=filling_params["n_grid"],
            max_samples=filling_params["max_particles_num"],
            grid_dx=material_params["grid_lim"] / filling_params["n_grid"],
            density_thres=filling_params["density_threshold"],
            search_thres=filling_params["search_threshold"],
            max_particles_per_cell=filling_params["max_partciels_per_cell"],
            search_exclude_dir=filling_params["search_exclude_direction"],
            ray_cast_dir=filling_params["ray_cast_direction"],
            boundary=filling_params["boundary"],
            smooth=filling_params["smooth"],
        ).to(device=device)

        if args.debug:
            particle_position_tensor_to_ply(mpm_init_pos, "./log/filled_particles.ply")
    else:
        mpm_init_pos = transformed_pos.to(device=device)

    # init the mpm solver
    print("Initializing MPM solver and setting up boundary conditions...")
    mpm_init_vol = get_particle_volume(
        mpm_init_pos,
        material_params["n_grid"],
        material_params["grid_lim"] / material_params["n_grid"],
        unifrom=material_params["material"] == "sand",
    ).to(device=device)

    if filling_params is not None and filling_params["visualize"] == True:
        shs, opacity, mpm_init_cov = init_filled_particles(
            mpm_init_pos[:gs_num],
            init_shs,
            init_cov,
            init_opacity,
            mpm_init_pos[gs_num:],
        )
        gs_num = mpm_init_pos.shape[0]
    else:
        mpm_init_cov = torch.zeros((mpm_init_pos.shape[0], 6), device=device)
        mpm_init_cov[:gs_num] = init_cov
        shs = init_shs
        opacity = init_opacity

    if args.debug:
        print("check *.ply files to see if it's ready for simulation")

    # set up the mpm solver
    mpm_solver = MPM_Simulator_WARP(10)
    mpm_solver.load_initial_data_from_torch(
        mpm_init_pos,
        mpm_init_vol,
        mpm_init_cov,
        n_grid=material_params["n_grid"],
        grid_lim=material_params["grid_lim"],
    )
    mpm_solver.set_parameters_dict(material_params)

    active_lookup = {
        int(original_index): local_index
        for local_index, original_index in enumerate(
            active_gs_indices.detach().cpu().tolist()
        )
    }

    if "particle_material_params" in material_params:
        labeled_materials = []
        for params in material_params["particle_material_params"]:
            local_indices = [
                active_lookup[int(original_index)]
                for original_index in params["indices"]
                if int(original_index) in active_lookup
            ]
            if local_indices:
                labeled_materials.append((local_indices, params))
                mpm_solver.set_particle_material_by_indices(
                    local_indices,
                    E=params["E"],
                    nu=params["nu"],
                    density=params["density"],
                    device=device,
                )
        if labeled_materials and mpm_init_pos.shape[0] > gs_num:
            labeled_indices = []
            labeled_param_ids = []
            for param_id, (local_indices, _params) in enumerate(labeled_materials):
                labeled_indices.extend(local_indices)
                labeled_param_ids.extend([param_id] * len(local_indices))
            labeled_indices_tensor = torch.tensor(
                labeled_indices, dtype=torch.long, device=device
            )
            labeled_param_ids_tensor = torch.tensor(
                labeled_param_ids, dtype=torch.long, device=device
            )
            fill_pos = mpm_init_pos[gs_num:]
            source_pos = mpm_init_pos[labeled_indices_tensor]
            query_chunk_size = 4096
            source_chunk_size = 8192
            inherited = []
            with torch.no_grad():
                for start in range(0, fill_pos.shape[0], query_chunk_size):
                    chunk = fill_pos[start : start + query_chunk_size]
                    best_dist = torch.full(
                        (chunk.shape[0],),
                        float("inf"),
                        dtype=chunk.dtype,
                        device=device,
                    )
                    best_param_ids = torch.empty(
                        (chunk.shape[0],),
                        dtype=labeled_param_ids_tensor.dtype,
                        device=device,
                    )
                    for source_start in range(0, source_pos.shape[0], source_chunk_size):
                        source_chunk = source_pos[source_start : source_start + source_chunk_size]
                        dist = torch.cdist(chunk, source_chunk)
                        local_dist, local_nearest = dist.min(dim=1)
                        better = local_dist < best_dist
                        if better.any():
                            best_dist[better] = local_dist[better]
                            best_param_ids[better] = labeled_param_ids_tensor[
                                source_start + local_nearest[better]
                            ]
                    inherited.append(best_param_ids)
            inherited_param_ids = torch.cat(inherited, dim=0)
            for param_id, (_local_indices, params) in enumerate(labeled_materials):
                fill_indices = torch.nonzero(
                    inherited_param_ids == param_id, as_tuple=False
                ).reshape(-1)
                if fill_indices.numel() == 0:
                    continue
                fill_indices = fill_indices + gs_num
                mpm_solver.set_particle_material_by_indices(
                    fill_indices,
                    E=params["E"],
                    nu=params["nu"],
                    density=params["density"],
                    device=device,
                )

    mapped_bc_params = []
    for bc in bc_params:
        if bc.get("type") == "fixed_particle_indices":
            local_indices = [
                active_lookup[int(original_index)]
                for original_index in bc.get("indices", [])
                if int(original_index) in active_lookup
            ]
            if not local_indices:
                continue
            mapped = dict(bc)
            mapped["indices"] = local_indices
            mapped["original_indices_count"] = len(bc.get("indices", []))
            mapped["local_indices_count"] = len(local_indices)
            mapped_bc_params.append(mapped)
        else:
            mapped_bc_params.append(bc)
    bc_params = mapped_bc_params

    # Note: boundary conditions may depend on mass, so the order cannot be changed!
    set_boundary_conditions(mpm_solver, bc_params, time_params)

    mpm_solver.finalize_mu_lam()

    # camera setting
    mpm_space_viewpoint_center = (
        torch.tensor(camera_params["mpm_space_viewpoint_center"]).reshape((1, 3)).cuda()
    )
    mpm_space_vertical_upward_axis = (
        torch.tensor(camera_params["mpm_space_vertical_upward_axis"])
        .reshape((1, 3))
        .cuda()
    )
    (
        viewpoint_center_worldspace,
        observant_coordinates,
    ) = get_center_view_worldspace_and_observant_coordinate(
        mpm_space_viewpoint_center,
        mpm_space_vertical_upward_axis,
        rotation_matrices,
        scale_origin,
        original_mean_pos,
    )

    # run the simulation
    substep_dt = time_params["substep_dt"]
    frame_dt = time_params["frame_dt"]
    frame_num = time_params["frame_num"]
    step_per_frame = max(1, int(round(frame_dt / substep_dt)))
    integrator = time_params.get("integrator", "explicit")
    implicit_params = time_params.get("implicit_mpm", {})
    pbmpm_params = time_params.get("pbmpm", {})
    motion_stream = None
    motion_manifest_path = None

    def write_super_motion_frame():
        pos = mpm_solver.export_particle_x_to_torch()[:gs_num].to(device)
        cov3D = mpm_solver.export_particle_cov_to_torch().view(-1, 6)[:gs_num].to(device)
        pos = apply_inverse_rotations(
            undotransform2origin(
                undoshift2center111(pos),
                scale_origin,
                original_mean_pos,
            ),
            rotation_matrices,
        )
        cov3D = cov3D / (scale_origin * scale_origin)
        cov3D = apply_inverse_cov_rotations(cov3D, rotation_matrices)
        scaling, quat = covariance_to_scaling_rotation(cov3D)
        motion_stream.write(
            np.ascontiguousarray(pos.detach().cpu().numpy(), dtype=np.float32).tobytes()
        )
        motion_stream.write(
            np.ascontiguousarray(quat.detach().cpu().numpy(), dtype=np.float32).tobytes()
        )
        motion_stream.write(
            np.ascontiguousarray(scaling.detach().cpu().numpy(), dtype=np.float32).tobytes()
        )
        motion_stream.flush()

    if args.output_super_motion:
        assert args.output_path is not None
        motion_dir = os.path.join(args.output_path, "super_motion")
        os.makedirs(motion_dir, exist_ok=True)
        motion_bin_path = os.path.join(motion_dir, "motion.bin")
        motion_indices_path = os.path.join(motion_dir, "indices.bin")
        motion_manifest_path = os.path.join(motion_dir, "motion.physmotion.json")
        motion_manifest = {
            "format": "phys-motion-v1",
            "binary": "motion.bin",
            "indices": "indices.bin",
            "frameCount": frame_num + 1,
            "frameRate": int(round(1.0 / frame_dt)) if frame_dt > 0 else 30,
            "numSplats": int(original_gs_num),
            "attributes": ["position", "rotation", "scale"],
            "frameStrideBytes": int(gs_num) * 10 * np.dtype(np.float32).itemsize,
            "updateBounds": False,
        }
        with open(motion_manifest_path, "w", encoding="utf-8") as f:
            json.dump(motion_manifest, f, indent=2)
        motion_stream = open(motion_bin_path, "wb")
        active_gs_indices.detach().cpu().numpy().astype(np.uint32).tofile(motion_indices_path)
        write_super_motion_frame()

    if args.output_ply or args.output_h5:
        directory_to_save = os.path.join(args.output_path, "simulation_ply")
        if not os.path.exists(directory_to_save):
            os.makedirs(directory_to_save)

        save_data_at_frame(
            mpm_solver,
            directory_to_save,
            0,
            save_to_ply=args.output_ply,
            save_to_h5=args.output_h5,
        )

    opacity_render = opacity
    shs_render = shs
    height = None
    width = None
    for frame in tqdm(range(frame_num)):
        current_camera = None
        rasterize = None
        if args.render_img:
            current_camera = get_camera_view(
                model_path,
                default_camera_index=camera_params["default_camera_index"],
                center_view_world_space=viewpoint_center_worldspace,
                observant_coordinates=observant_coordinates,
                show_hint=camera_params["show_hint"],
                init_azimuthm=camera_params["init_azimuthm"],
                init_elevation=camera_params["init_elevation"],
                init_radius=camera_params["init_radius"],
                move_camera=camera_params["move_camera"],
                current_frame=frame,
                delta_a=camera_params["delta_a"],
                delta_e=camera_params["delta_e"],
                delta_r=camera_params["delta_r"],
            )
            rasterize = initialize_resterize(
                current_camera, gaussians, pipeline, background
            )

        for step in range(step_per_frame):
            global_step = frame * step_per_frame + step
            if integrator == "implicit":
                mpm_solver.p2g2p_implicit(
                    global_step,
                    substep_dt,
                    device=device,
                    beta=implicit_params.get("beta", 0.25),
                    gamma=implicit_params.get("gamma", 0.5),
                    newton_tol=implicit_params.get("newton_tol", 1e-4),
                    newton_abs_tol=implicit_params.get("newton_abs_tol", 1e-6),
                    newton_max_iter=implicit_params.get("newton_max_iter", 8),
                    gmres_tol=implicit_params.get("gmres_tol", 1e-3),
                    gmres_max_iter=implicit_params.get("gmres_max_iter", 24),
                    jvp_eps=implicit_params.get("jvp_eps", 1e-4),
                    line_search_max_iter=implicit_params.get(
                        "line_search_max_iter", 8
                    ),
                    armijo_c1=implicit_params.get("armijo_c1", 1e-4),
                    ew_eta_min=implicit_params.get("ew_eta_min", 1e-5),
                    ew_eta_max=implicit_params.get("ew_eta_max", 0.5),
                    ew_gamma=implicit_params.get("ew_gamma", 0.9),
                    ew_alpha=implicit_params.get("ew_alpha", 1.5),
                    stiffness_preconditioner_scale=implicit_params.get(
                        "stiffness_preconditioner_scale", 1.0
                    ),
                    stagnation_tol=implicit_params.get("stagnation_tol", 1e-8),
                )
            elif integrator == "pbmpm":
                mpm_solver.p2g2p_pbmpm(
                    global_step,
                    substep_dt,
                    device=device,
                    elasticity_ratio=pbmpm_params.get(
                        "elasticity_ratio", pbmpm_params.get("r_scale", 1.0)
                    ),
                    elastic_relaxation=pbmpm_params.get(
                        "elastic_relaxation", pbmpm_params.get("s_scale", 1.5)
                    ),
                    plasticity=pbmpm_params.get("plasticity", 0.0),
                    yield_min=pbmpm_params.get("yield_min", 0.55),
                    yield_max=pbmpm_params.get("yield_max", 1.85),
                    iteration_count=pbmpm_params.get(
                        "iteration_count", pbmpm_params.get("projection_iterations", 1)
                    ),
                )
            else:
                mpm_solver.p2g2p(global_step, substep_dt, device=device)

        if args.output_ply or args.output_h5:
            save_data_at_frame(
                mpm_solver,
                directory_to_save,
                frame + 1,
                save_to_ply=args.output_ply,
                save_to_h5=args.output_h5,
            )

        if args.output_super_motion:
            write_super_motion_frame()

        if args.render_img:
            pos = mpm_solver.export_particle_x_to_torch()[:gs_num].to(device)
            cov3D = mpm_solver.export_particle_cov_to_torch()
            rot = mpm_solver.export_particle_R_to_torch()
            cov3D = cov3D.view(-1, 6)[:gs_num].to(device)
            rot = rot.view(-1, 3, 3)[:gs_num].to(device)

            pos = apply_inverse_rotations(
                undotransform2origin(
                    undoshift2center111(pos), scale_origin, original_mean_pos
                ),
                rotation_matrices,
            )
            cov3D = cov3D / (scale_origin * scale_origin)
            cov3D = apply_inverse_cov_rotations(cov3D, rotation_matrices)
            opacity = opacity_render
            shs = shs_render
            if preprocessing_params["sim_area"] is not None:
                pos = torch.cat([pos, unselected_pos], dim=0)
                cov3D = torch.cat([cov3D, unselected_cov], dim=0)
                opacity = torch.cat([opacity_render, unselected_opacity], dim=0)
                shs = torch.cat([shs_render, unselected_shs], dim=0)

            colors_precomp = convert_SH(shs, current_camera, gaussians, pos, rot)
            rendering, raddi = rasterize(
                means3D=pos,
                means2D=init_screen_points,
                shs=None,
                colors_precomp=colors_precomp,
                opacities=opacity,
                scales=None,
                rotations=None,
                cov3D_precomp=cov3D,
            )
            cv2_img = rendering.permute(1, 2, 0).detach().cpu().numpy()
            cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            if height is None or width is None:
                height = cv2_img.shape[0] // 2 * 2
                width = cv2_img.shape[1] // 2 * 2
            assert args.output_path is not None
            cv2.imwrite(
                os.path.join(args.output_path, f"{frame}.png".rjust(8, "0")),
                255 * cv2_img,
            )

    if args.render_img and args.compile_video:
        fps = int(1.0 / time_params["frame_dt"])
        os.system(
            f"ffmpeg -framerate {fps} -i {args.output_path}/%04d.png -c:v libx264 -s {width}x{height} -y -pix_fmt yuv420p {args.output_path}/output.mp4"
        )

    if args.output_path is not None:
        if integrator == "implicit" and hasattr(mpm_solver, "implicit_history"):
            trace_steps = mpm_solver.implicit_history
        else:
            trace_steps = getattr(mpm_solver, "solver_history", [])
        solver_trace = {
            "format": "physgaussian-solver-trace-v1",
            "integrator": integrator,
            "substep_dt": float(substep_dt),
            "frame_dt": float(frame_dt),
            "frame_num": int(frame_num),
            "step_per_frame": int(step_per_frame),
            "gaussian_count": int(gs_num),
            "original_gaussian_count": int(original_gs_num),
            "simulated_particle_count": int(mpm_solver.n_particles),
            "active_original_gaussian_count": int(active_gs_indices.numel()),
            "implicit_mpm": implicit_params if integrator == "implicit" else None,
            "pbmpm": pbmpm_params if integrator == "pbmpm" else None,
            "steps": trace_steps,
        }
        trace_path = os.path.join(args.output_path, "solver_trace.json")
        with open(trace_path, "w", encoding="utf-8") as trace_file:
            json.dump(solver_trace, trace_file, indent=2)
        if integrator == "implicit" and hasattr(mpm_solver, "implicit_history"):
            legacy_trace_path = os.path.join(args.output_path, "implicit_solver_trace.json")
            with open(legacy_trace_path, "w", encoding="utf-8") as trace_file:
                json.dump(mpm_solver.implicit_history, trace_file, indent=2)

    if motion_stream is not None:
        motion_stream.close()
