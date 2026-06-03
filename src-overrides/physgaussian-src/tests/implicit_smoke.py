import os
import sys

import torch
import warp as wp


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "mpm_solver_warp"))

from mpm_solver_warp import MPM_Simulator_WARP


def main():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        raise RuntimeError("This smoke test requires CUDA because PhysGaussian uses Warp CUDA kernels.")

    wp.init()
    n_particles = 4
    x = torch.tensor(
        [
            [0.95, 1.00, 1.00],
            [1.05, 1.00, 1.00],
            [1.00, 0.95, 1.00],
            [1.00, 1.05, 1.00],
        ],
        device=device,
        dtype=torch.float32,
    )
    volume = torch.ones((n_particles,), device=device, dtype=torch.float32) * 1e-4
    cov = torch.zeros((n_particles, 6), device=device, dtype=torch.float32)

    solver = MPM_Simulator_WARP(n_particles, n_grid=16, grid_lim=2.0, device=device)
    solver.load_initial_data_from_torch(
        x,
        volume,
        cov,
        n_grid=16,
        grid_lim=2.0,
        device=device,
    )
    solver.set_parameters_dict(
        {
            "material": "jelly",
            "E": 1e4,
            "nu": 0.3,
            "density": 200.0,
            "g": [0.0, 0.0, 0.0],
            "grid_v_damping_scale": 0.9999,
            "rpic_damping": 0.0,
        },
        device=device,
    )
    solver.finalize_mu_lam(device=device)
    solver.import_particle_v_from_torch(
        torch.tensor([[0.1, 0.0, 0.0]] * n_particles, device=device),
        device=device,
    )

    solver.p2g2p_implicit(
        0,
        1e-4,
        device=device,
        beta=0.25,
        gamma=0.5,
        newton_tol=1e-3,
        newton_max_iter=1,
        gmres_tol=1e-2,
        gmres_max_iter=2,
        jvp_eps=1e-4,
        line_search_max_iter=2,
    )
    wp.synchronize()
    out = solver.export_particle_x_to_torch().detach().cpu()
    if not torch.isfinite(out).all():
        raise RuntimeError(f"Implicit smoke produced non-finite positions: {out}")
    print("OK implicit smoke")
    print(out)


if __name__ == "__main__":
    main()
