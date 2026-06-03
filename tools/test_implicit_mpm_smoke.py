from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch
import warp as wp


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "mpm_solver_warp").exists():
            return parent
    return Path("/root/autodl-tmp/ustc26mm/src/physgaussian-src")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "mpm_solver_warp"))

from mpm_solver_warp import MPM_Simulator_WARP  # noqa: E402


def make_block(device: str, side: int = 4) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    coords = torch.linspace(0.44, 0.56, side, device=device)
    grid = torch.stack(torch.meshgrid(coords, coords, coords, indexing="ij"), dim=-1)
    x = grid.reshape(-1, 3).contiguous()
    volume = torch.full((x.shape[0],), (0.12**3) / x.shape[0], device=device)
    cov = torch.zeros((x.shape[0], 6), dtype=x.dtype, device=device)
    cov[:, 0] = 1e-5
    cov[:, 3] = 1e-5
    cov[:, 5] = 1e-5
    return x, volume, cov


def make_solver(device: str, gravity: list[float]) -> MPM_Simulator_WARP:
    x, volume, cov = make_block(device)
    solver = MPM_Simulator_WARP(x.shape[0], n_grid=18, grid_lim=1.0, device=device)
    solver.load_initial_data_from_torch(x, volume, cov, n_grid=18, grid_lim=1.0, device=device)
    solver.set_parameters(
        material="jelly",
        E=1.0e4,
        nu=0.3,
        density=800.0,
        g=gravity,
        grid_v_damping_scale=1.0,
        rpic_damping=0.0,
        device=device,
    )
    solver.finalize_mu_lam(device=device)
    return solver


def summarize(solver: MPM_Simulator_WARP, initial_x: torch.Tensor) -> dict[str, float]:
    x = solver.export_particle_x_to_torch().detach()
    v = solver.export_particle_v_to_torch().detach()
    cov = solver.export_particle_cov_to_torch().detach()
    rot = solver.export_particle_R_to_torch().detach()
    delta = x - initial_x
    return {
        "com_z": float(x[:, 2].mean().cpu()),
        "max_abs_delta": float(delta.abs().max().cpu()),
        "max_speed": float(torch.linalg.norm(v, dim=1).max().cpu()),
        "finite": bool(
            torch.isfinite(x).all().cpu()
            and torch.isfinite(v).all().cpu()
            and torch.isfinite(cov).all().cpu()
            and torch.isfinite(rot).all().cpu()
        ),
    }


def run_case(device: str, dt: float, steps: int, gravity: list[float]) -> dict[str, object]:
    explicit = make_solver(device, gravity)
    implicit = make_solver(device, gravity)
    initial_x = explicit.export_particle_x_to_torch().detach().clone()

    for step in range(steps):
        explicit.p2g2p(step, dt, device=device)
        implicit.p2g2p_implicit(
            step,
            dt,
            device=device,
            beta=0.25,
            gamma=0.5,
            newton_tol=1e-4,
            newton_max_iter=8,
            gmres_tol=1e-3,
            gmres_max_iter=24,
            jvp_eps=1e-4,
            line_search_max_iter=8,
        )

    e = summarize(explicit, initial_x)
    im = summarize(implicit, initial_x)
    x_e = explicit.export_particle_x_to_torch().detach()
    x_i = implicit.export_particle_x_to_torch().detach()
    return {
        "dt": dt,
        "steps": steps,
        "gravity": gravity,
        "explicit": e,
        "implicit": im,
        "mean_position_l2": float(torch.linalg.norm(x_e - x_i, dim=1).mean().cpu()),
        "implicit_history_tail": implicit.implicit_history[-3:],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dt", type=float, default=2e-4)
    parser.add_argument("--steps", type=int, default=4)
    args = parser.parse_args()

    wp.init()
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this Warp smoke test")

    cases = [
        run_case(args.device, args.dt, args.steps, [0.0, 0.0, 0.0]),
        run_case(args.device, args.dt, args.steps, [0.0, 0.0, -9.8]),
        run_case(args.device, args.dt * 5.0, max(1, args.steps // 2), [0.0, 0.0, -9.8]),
    ]
    print(json.dumps({"cases": cases}, indent=2))

    zero = cases[0]
    if zero["implicit"]["max_abs_delta"] > 1e-7:
        raise SystemExit("zero-gravity implicit case moved unexpectedly")
    for case in cases:
        if not case["explicit"]["finite"] or not case["implicit"]["finite"]:
            raise SystemExit("non-finite state detected")
        if case["gravity"][2] < 0 and not (case["implicit"]["com_z"] < 0.500001):
            raise SystemExit("implicit gravity case did not move downward")


if __name__ == "__main__":
    main()
