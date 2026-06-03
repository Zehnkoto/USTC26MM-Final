import sys
import os

import torch

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from engine_utils import *
from warp_utils import *
from mpm_utils import *


class MPM_Simulator_WARP:
    def __init__(self, n_particles, n_grid=100, grid_lim=1.0, device="cuda:0"):
        self.initialize(n_particles, n_grid, grid_lim, device=device)
        self.time_profile = {}

    def initialize(self, n_particles, n_grid=100, grid_lim=1.0, device="cuda:0"):
        self.n_particles = n_particles

        self.mpm_model = MPMModelStruct()
        # domain will be [0,grid_lim]*[0,grid_lim]*[0,grid_lim] !!!
        # domain will be [0,grid_lim]*[0,grid_lim]*[0,grid_lim] !!!
        # domain will be [0,grid_lim]*[0,grid_lim]*[0,grid_lim] !!!
        self.mpm_model.grid_lim = grid_lim
        self.mpm_model.n_grid = n_grid
        self.mpm_model.grid_dim_x = self.mpm_model.n_grid
        self.mpm_model.grid_dim_y = self.mpm_model.n_grid
        self.mpm_model.grid_dim_z = self.mpm_model.n_grid
        (
            self.mpm_model.dx,
            self.mpm_model.inv_dx,
        ) = self.mpm_model.grid_lim / self.mpm_model.n_grid, float(
            self.mpm_model.n_grid / self.mpm_model.grid_lim
        )

        self.mpm_model.E = wp.zeros(shape=n_particles, dtype=float, device=device)
        self.mpm_model.nu = wp.zeros(shape=n_particles, dtype=float, device=device)
        self.mpm_model.mu = wp.zeros(shape=n_particles, dtype=float, device=device)
        self.mpm_model.lam = wp.zeros(shape=n_particles, dtype=float, device=device)

        self.mpm_model.update_cov_with_F = False
        self.mpm_model.pbmpm_elasticity_ratio = 0.75
        self.mpm_model.pbmpm_elastic_relaxation = 1.5
        self.mpm_model.pbmpm_plasticity = 0.0
        self.mpm_model.pbmpm_yield_min = 0.55
        self.mpm_model.pbmpm_yield_max = 1.85

        # material is used to switch between different elastoplastic models. 0 is jelly
        self.mpm_model.material = 0

        self.mpm_model.plastic_viscosity = 0.0
        self.mpm_model.softening = 0.1
        self.mpm_model.yield_stress = wp.zeros(
            shape=n_particles, dtype=float, device=device
        )
        self.mpm_model.friction_angle = 25.0
        sin_phi = wp.sin(self.mpm_model.friction_angle / 180.0 * 3.14159265)
        self.mpm_model.alpha = wp.sqrt(2.0 / 3.0) * 2.0 * sin_phi / (3.0 - sin_phi)

        self.mpm_model.gravitational_accelaration = wp.vec3(0.0, 0.0, 0.0)

        self.mpm_model.rpic_damping = 0.0  # 0.0 if no damping (apic). -1 if pic

        self.mpm_model.grid_v_damping_scale = 1.1  # globally applied

        self.mpm_state = MPMStateStruct()

        self.mpm_state.particle_x = wp.empty(
            shape=n_particles, dtype=wp.vec3, device=device
        )  # current position

        self.mpm_state.particle_v = wp.zeros(
            shape=n_particles, dtype=wp.vec3, device=device
        )  # particle velocity

        self.mpm_state.particle_F = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )  # particle F elastic

        self.mpm_state.particle_R = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )  # particle R rotation

        self.mpm_state.particle_init_cov = wp.zeros(
            shape=n_particles * 6, dtype=float, device=device
        )  # initial covariance matrix

        self.mpm_state.particle_cov = wp.zeros(
            shape=n_particles * 6, dtype=float, device=device
        )  # current covariance matrix

        self.mpm_state.particle_F_trial = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )  # apply return mapping will yield

        self.mpm_state.particle_stress = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )

        self.mpm_state.particle_vol = wp.zeros(
            shape=n_particles, dtype=float, device=device
        )  # particle volume
        self.mpm_state.particle_mass = wp.zeros(
            shape=n_particles, dtype=float, device=device
        )  # particle mass
        self.mpm_state.particle_density = wp.zeros(
            shape=n_particles, dtype=float, device=device
        )
        self.mpm_state.particle_C = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )
        self.mpm_state.particle_D = wp.zeros(
            shape=n_particles, dtype=wp.mat33, device=device
        )
        self.mpm_state.particle_Jp = wp.zeros(
            shape=n_particles, dtype=float, device=device
        )

        self.mpm_state.particle_selection = wp.zeros(
            shape=n_particles, dtype=int, device=device
        )

        self.mpm_state.grid_m = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=float,
            device=device,
        )
        self.mpm_state.grid_v_in = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self.mpm_state.grid_v_out = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self._implicit_grid_an = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self._implicit_grid_dirichlet = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=int,
            device=device,
        )
        self._implicit_grid_v_target = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )

        self.time = 0.0
        self.implicit_history = []
        self.solver_history = []

        self.grid_postprocess = []
        self.collider_params = []
        self.modify_bc = []
        self.implicit_grid_constraint_builders = []
        self.implicit_grid_constraint_params = []

        self.tailored_struct_for_bc = MPMtailoredStruct()
        self.pre_p2g_operations = []
        self.impulse_params = []

        self.particle_velocity_modifiers = []
        self.particle_velocity_modifier_params = []
        self.fixed_particle_params = []
        self.fixed_particle_counts = []
        self.fixed_particle_tensors = []

    def _apply_fixed_particles(self, time=None, device="cuda:0"):
        constraint_time = self.time if time is None else float(time)
        for k, params in enumerate(self.fixed_particle_params):
            wp.launch(
                kernel=apply_fixed_particle_indices,
                dim=self.fixed_particle_counts[k],
                inputs=[constraint_time, self.mpm_state, params],
                device=device,
            )

    # the h5 file should store particle initial position and volume.
    def load_from_sampling(
        self, sampling_h5, n_grid=100, grid_lim=1.0, device="cuda:0"
    ):
        if not os.path.exists(sampling_h5):
            print("h5 file cannot be found at ", os.getcwd() + sampling_h5)
            exit()

        h5file = h5py.File(sampling_h5, "r")
        x, particle_volume = h5file["x"], h5file["particle_volume"]

        x = x[()].transpose()  # np vector of x # shape now is (n_particles, dim)

        self.dim, self.n_particles = x.shape[1], x.shape[0]

        self.initialize(self.n_particles, n_grid, grid_lim, device=device)

        print(
            "Sampling particles are loaded from h5 file. Simulator is re-initialized for the correct n_particles"
        )
        particle_volume = np.squeeze(particle_volume, 0)

        self.mpm_state.particle_x = wp.from_numpy(
            x, dtype=wp.vec3, device=device
        )  # initialize warp array from np

        # initial velocity is default to zero
        wp.launch(
            kernel=set_vec3_to_zero,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_v],
            device=device,
        )
        # initial velocity is default to zero

        # initial deformation gradient is set to identity
        wp.launch(
            kernel=set_mat33_to_identity,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_F],
            device=device,
        )
        wp.launch(
            kernel=set_mat33_to_identity,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_F_trial],
            device=device,
        )
        # initial deformation gradient is set to identity

        self.mpm_state.particle_vol = wp.from_numpy(
            particle_volume, dtype=float, device=device
        )

        print("Particles initialized from sampling file.")
        print("Total particles: ", self.n_particles)

    # shape of tensor_x is (n, 3); shape of tensor_volume is (n,)
    def load_initial_data_from_torch(
        self,
        tensor_x,
        tensor_volume,
        tensor_cov=None,
        n_grid=100,
        grid_lim=1.0,
        device="cuda:0",
    ):
        self.dim, self.n_particles = tensor_x.shape[1], tensor_x.shape[0]
        assert tensor_x.shape[0] == tensor_volume.shape[0]
        # assert tensor_x.shape[0] == tensor_cov.reshape(-1, 6).shape[0]
        self.initialize(self.n_particles, n_grid, grid_lim, device=device)

        self.import_particle_x_from_torch(tensor_x, device)
        self.mpm_state.particle_vol = wp.from_numpy(
            tensor_volume.detach().clone().cpu().numpy(), dtype=float, device=device
        )
        if tensor_cov is not None:
            self.mpm_state.particle_init_cov = wp.from_numpy(
                tensor_cov.reshape(-1).detach().clone().cpu().numpy(),
                dtype=float,
                device=device,
            )

            if self.mpm_model.update_cov_with_F:
                self.mpm_state.particle_cov = self.mpm_state.particle_init_cov

        # initial velocity is default to zero
        wp.launch(
            kernel=set_vec3_to_zero,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_v],
            device=device,
        )
        # initial velocity is default to zero

        # initial deformation gradient is set to identity
        wp.launch(
            kernel=set_mat33_to_identity,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_F],
            device=device,
        )
        wp.launch(
            kernel=set_mat33_to_identity,
            dim=self.n_particles,
            inputs=[self.mpm_state.particle_F_trial],
            device=device,
        )
        # initial trial deformation gradient is set to identity

        print("Particles initialized from torch data.")
        print("Total particles: ", self.n_particles)

    # must give density. mass will be updated as density * volume
    def set_parameters(self, device="cuda:0", **kwargs):
        self.set_parameters_dict(kwargs, device=device)

    def set_parameters_dict(self, kwargs={}, device="cuda:0"):
        if "material" in kwargs:
            if kwargs["material"] == "jelly":
                self.mpm_model.material = 0
            elif kwargs["material"] == "metal":
                self.mpm_model.material = 1
            elif kwargs["material"] == "sand":
                self.mpm_model.material = 2
            elif kwargs["material"] == "foam":
                self.mpm_model.material = 3
            elif kwargs["material"] == "snow":
                self.mpm_model.material = 4
            elif kwargs["material"] == "plasticine":
                self.mpm_model.material = 5
            else:
                raise TypeError("Undefined material type")

        if "grid_lim" in kwargs:
            self.mpm_model.grid_lim = kwargs["grid_lim"]
        if "n_grid" in kwargs:
            self.mpm_model.n_grid = kwargs["n_grid"]
        self.mpm_model.grid_dim_x = self.mpm_model.n_grid
        self.mpm_model.grid_dim_y = self.mpm_model.n_grid
        self.mpm_model.grid_dim_z = self.mpm_model.n_grid
        (
            self.mpm_model.dx,
            self.mpm_model.inv_dx,
        ) = self.mpm_model.grid_lim / self.mpm_model.n_grid, float(
            self.mpm_model.n_grid / self.mpm_model.grid_lim
        )
        self.mpm_state.grid_m = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=float,
            device=device,
        )
        self.mpm_state.grid_v_in = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self.mpm_state.grid_v_out = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self._implicit_grid_an = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )
        self._implicit_grid_dirichlet = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=int,
            device=device,
        )
        self._implicit_grid_v_target = wp.zeros(
            shape=(self.mpm_model.n_grid, self.mpm_model.n_grid, self.mpm_model.n_grid),
            dtype=wp.vec3,
            device=device,
        )

        if "E" in kwargs:
            wp.launch(
                kernel=set_value_to_float_array,
                dim=self.n_particles,
                inputs=[self.mpm_model.E, kwargs["E"]],
                device=device,
            )
        if "nu" in kwargs:
            wp.launch(
                kernel=set_value_to_float_array,
                dim=self.n_particles,
                inputs=[self.mpm_model.nu, kwargs["nu"]],
                device=device,
            )
        if "yield_stress" in kwargs:
            val = kwargs["yield_stress"]
            wp.launch(
                kernel=set_value_to_float_array,
                dim=self.n_particles,
                inputs=[self.mpm_model.yield_stress, val],
                device=device,
            )
        if "hardening" in kwargs:
            self.mpm_model.hardening = kwargs["hardening"]
        if "xi" in kwargs:
            self.mpm_model.xi = kwargs["xi"]
        if "friction_angle" in kwargs:
            self.mpm_model.friction_angle = kwargs["friction_angle"]
            sin_phi = wp.sin(self.mpm_model.friction_angle / 180.0 * 3.14159265)
            self.mpm_model.alpha = wp.sqrt(2.0 / 3.0) * 2.0 * sin_phi / (3.0 - sin_phi)

        if "g" in kwargs:
            self.mpm_model.gravitational_accelaration = wp.vec3(
                kwargs["g"][0], kwargs["g"][1], kwargs["g"][2]
            )

        if "density" in kwargs:
            density_value = kwargs["density"]
            wp.launch(
                kernel=set_value_to_float_array,
                dim=self.n_particles,
                inputs=[self.mpm_state.particle_density, density_value],
                device=device,
            )
            wp.launch(
                kernel=get_float_array_product,
                dim=self.n_particles,
                inputs=[
                    self.mpm_state.particle_density,
                    self.mpm_state.particle_vol,
                    self.mpm_state.particle_mass,
                ],
                device=device,
            )
        if "rpic_damping" in kwargs:
            self.mpm_model.rpic_damping = kwargs["rpic_damping"]
        if "plastic_viscosity" in kwargs:
            self.mpm_model.plastic_viscosity = kwargs["plastic_viscosity"]
        if "softening" in kwargs:
            self.mpm_model.softening = kwargs["softening"]
        if "grid_v_damping_scale" in kwargs:
            self.mpm_model.grid_v_damping_scale = kwargs["grid_v_damping_scale"]
        if "additional_material_params" in kwargs:
            for params in kwargs["additional_material_params"]:
                param_modifier = MaterialParamsModifier()
                param_modifier.point = wp.vec3(params["point"])
                param_modifier.size = wp.vec3(params["size"])
                param_modifier.density = params["density"]
                param_modifier.E = params["E"]
                param_modifier.nu = params["nu"]
                wp.launch(
                    kernel=apply_additional_params,
                    dim=self.n_particles,
                    inputs=[self.mpm_state, self.mpm_model, param_modifier],
                    device=device,
                )

            wp.launch(
                kernel=get_float_array_product,
                dim=self.n_particles,
                inputs=[
                    self.mpm_state.particle_density,
                    self.mpm_state.particle_vol,
                    self.mpm_state.particle_mass,
                ],
                device=device,
            )

    def set_particle_material_by_indices(
        self, indices, E=None, nu=None, density=None, device="cuda:0"
    ):
        if not torch.is_tensor(indices):
            indices = torch.tensor(indices, dtype=torch.long, device=device)
        else:
            indices = indices.to(device=device, dtype=torch.long)
        if indices.numel() == 0:
            return

        valid = torch.logical_and(indices >= 0, indices < self.n_particles)
        indices = indices[valid]
        if indices.numel() == 0:
            return

        if E is not None:
            wp.to_torch(self.mpm_model.E)[indices] = float(E)
        if nu is not None:
            wp.to_torch(self.mpm_model.nu)[indices] = float(nu)
        if density is not None:
            wp.to_torch(self.mpm_state.particle_density)[indices] = float(density)
            wp.launch(
                kernel=get_float_array_product,
                dim=self.n_particles,
                inputs=[
                    self.mpm_state.particle_density,
                    self.mpm_state.particle_vol,
                    self.mpm_state.particle_mass,
                ],
                device=device,
            )

    def finalize_mu_lam(self, device="cuda:0"):
        wp.launch(
            kernel=compute_mu_lam_from_E_nu,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model],
            device=device,
        )

    def p2g2p(self, step, dt, device="cuda:0"):
        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )
        wp.launch(
            kernel=zero_grid,
            dim=(grid_size),
            inputs=[self.mpm_state, self.mpm_model],
            device=device,
        )

        # apply pre-p2g operations on particles
        for k in range(len(self.pre_p2g_operations)):
            wp.launch(
                kernel=self.pre_p2g_operations[k],
                dim=self.n_particles,
                inputs=[self.time, dt, self.mpm_state, self.impulse_params[k]],
                device=device,
            )
        # apply dirichlet particle v modifier
        for k in range(len(self.particle_velocity_modifiers)):
            wp.launch(
                kernel=self.particle_velocity_modifiers[k],
                dim=self.n_particles,
                inputs=[
                    self.time,
                    self.mpm_state,
                    self.particle_velocity_modifier_params[k],
                ],
                device=device,
            )
        self._apply_fixed_particles(time=self.time, device=device)

        # compute stress = stress(returnMap(F_trial))
        with wp.ScopedTimer(
            "compute_stress_from_F_trial",
            synchronize=True,
            print=False,
            dict=self.time_profile,
        ):
            wp.launch(
                kernel=compute_stress_from_F_trial,
                dim=self.n_particles,
                inputs=[self.mpm_state, self.mpm_model, dt],
                device=device,
            )  # F and stress are updated

        # p2g
        with wp.ScopedTimer(
            "p2g",
            synchronize=True,
            print=False,
            dict=self.time_profile,
        ):
            wp.launch(
                kernel=p2g_apic_with_stress,
                dim=self.n_particles,
                inputs=[self.mpm_state, self.mpm_model, dt],
                device=device,
            )  # apply p2g'

        # grid update
        with wp.ScopedTimer(
            "grid_update", synchronize=True, print=False, dict=self.time_profile
        ):
            wp.launch(
                kernel=grid_normalization_and_gravity,
                dim=(grid_size),
                inputs=[self.mpm_state, self.mpm_model, dt],
                device=device,
            )

        if self.mpm_model.grid_v_damping_scale < 1.0:
            wp.launch(
                kernel=add_damping_via_grid,
                dim=(grid_size),
                inputs=[self.mpm_state, self.mpm_model.grid_v_damping_scale],
                device=device,
            )

        # apply BC on grid
        with wp.ScopedTimer(
            "apply_BC_on_grid", synchronize=True, print=False, dict=self.time_profile
        ):
            for k in range(len(self.grid_postprocess)):
                wp.launch(
                    kernel=self.grid_postprocess[k],
                    dim=grid_size,
                    inputs=[
                        self.time,
                        dt,
                        self.mpm_state,
                        self.mpm_model,
                        self.collider_params[k],
                    ],
                    device=device,
                )
                if self.modify_bc[k] is not None:
                    self.modify_bc[k](self.time, dt, self.collider_params[k])

        # g2p
        with wp.ScopedTimer(
            "g2p", synchronize=True, print=False, dict=self.time_profile
        ):
            wp.launch(
                kernel=g2p,
                dim=self.n_particles,
                inputs=[self.mpm_state, self.mpm_model, dt],
                device=device,
            )  # x, v, C, F_trial are updated
        self._apply_fixed_particles(time=self.time + dt, device=device)

        #### CFL check ####
        # particle_v = self.mpm_state.particle_v.numpy()
        # if np.max(np.abs(particle_v)) > self.mpm_model.dx / dt:
        #     print("max particle v: ", np.max(np.abs(particle_v)))
        #     print("max allowed  v: ", self.mpm_model.dx / dt)
        #     print("does not allow v*dt>dx")
        #     input()
        #### CFL check ####
        self.time = self.time + dt
        self.solver_history.append(
            {
                "integrator": "explicit",
                "step": int(step),
                "dt": float(dt),
                "time": float(self.time),
                "converged": True,
            }
        )

    def p2g2p_pbmpm(
        self,
        step,
        dt,
        device="cuda:0",
        elasticity_ratio=None,
        elastic_relaxation=None,
        plasticity=0.0,
        yield_min=0.55,
        yield_max=1.85,
        projection_iterations=None,
        r_scale=None,
        s_scale=None,
        iteration_count=None,
    ):
        if elasticity_ratio is None:
            elasticity_ratio = 1.0 if r_scale is None else r_scale
        if elastic_relaxation is None:
            elastic_relaxation = 1.5 if s_scale is None else s_scale
        if iteration_count is None:
            iteration_count = 5 if projection_iterations is None else projection_iterations
        self.mpm_model.pbmpm_elasticity_ratio = float(elasticity_ratio)
        self.mpm_model.pbmpm_elastic_relaxation = float(elastic_relaxation)
        self.mpm_model.pbmpm_plasticity = float(plasticity)
        self.mpm_model.pbmpm_yield_min = float(yield_min)
        self.mpm_model.pbmpm_yield_max = float(yield_max)

        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )
        for k in range(len(self.pre_p2g_operations)):
            wp.launch(
                kernel=self.pre_p2g_operations[k],
                dim=self.n_particles,
                inputs=[self.time, dt, self.mpm_state, self.impulse_params[k]],
                device=device,
            )
        for k in range(len(self.particle_velocity_modifiers)):
            wp.launch(
                kernel=self.particle_velocity_modifiers[k],
                dim=self.n_particles,
                inputs=[
                    self.time,
                    self.mpm_state,
                    self.particle_velocity_modifier_params[k],
                ],
                device=device,
            )
        self._apply_fixed_particles(time=self.time, device=device)

        iteration_count = max(1, int(iteration_count))
        for iteration in range(iteration_count):
            with wp.ScopedTimer(
                "pbmpm_project_constraints",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                wp.launch(
                    kernel=pbmpm_project_constraints,
                    dim=self.n_particles,
                    inputs=[self.mpm_state, self.mpm_model],
                    device=device,
                )

            wp.launch(
                kernel=zero_grid,
                dim=(grid_size),
                inputs=[self.mpm_state, self.mpm_model],
                device=device,
            )

            with wp.ScopedTimer(
                "pbmpm_p2g_displacement",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                wp.launch(
                    kernel=p2g_pbmpm_with_D,
                    dim=self.n_particles,
                    inputs=[self.mpm_state, self.mpm_model, dt],
                    device=device,
                )

            with wp.ScopedTimer(
                "pbmpm_grid_update",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                wp.launch(
                    kernel=grid_normalization_no_gravity,
                    dim=(grid_size),
                    inputs=[self.mpm_state, self.mpm_model],
                    device=device,
                )

            if self.mpm_model.grid_v_damping_scale < 1.0:
                wp.launch(
                    kernel=add_damping_via_grid,
                    dim=(grid_size),
                    inputs=[self.mpm_state, self.mpm_model.grid_v_damping_scale],
                    device=device,
                )

            with wp.ScopedTimer(
                "pbmpm_apply_BC_on_grid",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                for k in range(len(self.grid_postprocess)):
                    wp.launch(
                        kernel=self.grid_postprocess[k],
                        dim=grid_size,
                        inputs=[
                            self.time,
                            dt,
                            self.mpm_state,
                            self.mpm_model,
                            self.collider_params[k],
                        ],
                        device=device,
                    )
                    if self.modify_bc[k] is not None:
                        self.modify_bc[k](self.time, dt, self.collider_params[k])

            with wp.ScopedTimer(
                "pbmpm_g2p_displacement",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                wp.launch(
                    kernel=g2p_pbmpm_update_D,
                    dim=self.n_particles,
                    inputs=[self.mpm_state, self.mpm_model, dt],
                    device=device,
                )

        wp.launch(
            kernel=pbmpm_integrate_particles,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model, dt],
            device=device,
        )
        self._apply_fixed_particles(time=self.time + dt, device=device)

        self.time = self.time + dt
        self.solver_history.append(
            {
                "integrator": "pbmpm",
                "step": int(step),
                "dt": float(dt),
                "time": float(self.time),
                "converged": True,
                "pbmpm": {
                    "elasticity_ratio": float(elasticity_ratio),
                    "elastic_relaxation": float(elastic_relaxation),
                    "plasticity": float(plasticity),
                    "yield_min": float(yield_min),
                    "yield_max": float(yield_max),
                    "iteration_count": int(iteration_count),
                },
            }
        )

    def _implicit_apply_pre_p2g(self, dt, device="cuda:0"):
        for k in range(len(self.pre_p2g_operations)):
            wp.launch(
                kernel=self.pre_p2g_operations[k],
                dim=self.n_particles,
                inputs=[self.time, dt, self.mpm_state, self.impulse_params[k]],
                device=device,
            )
        for k in range(len(self.particle_velocity_modifiers)):
            wp.launch(
                kernel=self.particle_velocity_modifiers[k],
                dim=self.n_particles,
                inputs=[
                    self.time,
                    self.mpm_state,
                    self.particle_velocity_modifier_params[k],
                ],
                device=device,
            )
        self._apply_fixed_particles(time=self.time, device=device)

    def _implicit_initialize_grid(self, device="cuda:0"):
        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )
        wp.launch(
            kernel=zero_grid,
            dim=grid_size,
            inputs=[self.mpm_state, self.mpm_model],
            device=device,
        )
        wp.launch(
            kernel=p2g_apic_no_stress,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model],
            device=device,
        )
        wp.launch(
            kernel=grid_normalization_no_gravity,
            dim=grid_size,
            inputs=[self.mpm_state, self.mpm_model],
            device=device,
        )

    def _implicit_refresh_dirichlet_constraints(self, dt, device="cuda:0"):
        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )
        wp.launch(
            kernel=zero_grid_int,
            dim=grid_size,
            inputs=[self._implicit_grid_dirichlet],
            device=device,
        )
        wp.launch(
            kernel=zero_grid_vec3,
            dim=grid_size,
            inputs=[self._implicit_grid_v_target],
            device=device,
        )
        for k in range(len(self.implicit_grid_constraint_builders)):
            wp.launch(
                kernel=self.implicit_grid_constraint_builders[k],
                dim=grid_size,
                inputs=[
                    self.time,
                    dt,
                    self.mpm_state,
                    self.mpm_model,
                    self.implicit_grid_constraint_params[k],
                    self._implicit_grid_dirichlet,
                    self._implicit_grid_v_target,
                ],
                device=device,
            )

    def _implicit_residual(
        self,
        grid_du_wp,
        grid_vn_wp,
        grid_an_wp,
        grid_force_wp,
        grid_residual_wp,
        trial_F_wp,
        trial_stress_wp,
        beta,
        gamma,
        dt,
        device="cuda:0",
    ):
        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )
        wp.launch(
            kernel=implicit_du_to_velocity,
            dim=grid_size,
            inputs=[
                self.mpm_state,
                grid_du_wp,
                grid_vn_wp,
                grid_an_wp,
                beta,
                gamma,
                dt,
            ],
            device=device,
        )

        for k in range(len(self.grid_postprocess)):
            wp.launch(
                kernel=self.grid_postprocess[k],
                dim=grid_size,
                inputs=[
                    self.time,
                    dt,
                    self.mpm_state,
                    self.mpm_model,
                    self.collider_params[k],
                ],
                device=device,
            )

        with wp.ScopedTimer(
            "implicit_trial_stress",
            synchronize=True,
            print=False,
            dict=self.time_profile,
        ):
            wp.launch(
                kernel=implicit_compute_trial_stress,
                dim=self.n_particles,
                inputs=[
                    self.mpm_state,
                    self.mpm_model,
                    trial_F_wp,
                    trial_stress_wp,
                    dt,
                ],
                device=device,
            )

        wp.launch(
            kernel=zero_grid_vec3,
            dim=grid_size,
            inputs=[grid_force_wp],
            device=device,
        )
        wp.launch(
            kernel=implicit_accumulate_internal_force,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model, trial_stress_wp, grid_force_wp],
            device=device,
        )
        wp.launch(
            kernel=implicit_finalize_residual,
            dim=grid_size,
            inputs=[
                self.mpm_state,
                self.mpm_model,
                grid_du_wp,
                grid_vn_wp,
                grid_an_wp,
                grid_force_wp,
                grid_residual_wp,
                gamma,
                dt,
            ],
            device=device,
        )
        return wp.to_torch(grid_residual_wp)

    @staticmethod
    def _gmres_matrix_free(matvec, rhs, tol=1e-3, max_iter=24):
        b_norm = torch.linalg.norm(rhs)
        if float(b_norm.detach().cpu()) < 1e-20:
            return torch.zeros_like(rhs), 0, 0.0

        def solve_upper_triangular(upper, target):
            if upper.numel() == 0:
                return target
            solution = torch.zeros_like(target)
            diag_floor = torch.tensor(1e-20, dtype=target.dtype, device=target.device)
            for row in range(target.shape[0] - 1, -1, -1):
                rhs_value = target[row]
                if row + 1 < target.shape[0]:
                    rhs_value = rhs_value - torch.dot(
                        upper[row, row + 1 :],
                        solution[row + 1 :],
                    )
                diag = upper[row, row]
                diag_safe = torch.where(
                    torch.abs(diag) > diag_floor,
                    diag,
                    torch.where(diag < 0.0, -diag_floor, diag_floor),
                )
                solution[row] = rhs_value / diag_safe
            return solution

        q_vectors = [rhs / b_norm]
        h = torch.zeros(
            (max_iter + 1, max_iter),
            dtype=rhs.dtype,
            device=rhs.device,
        )
        givens_c = torch.zeros(max_iter, dtype=rhs.dtype, device=rhs.device)
        givens_s = torch.zeros(max_iter, dtype=rhs.dtype, device=rhs.device)
        g = torch.zeros(max_iter + 1, dtype=rhs.dtype, device=rhs.device)
        g[0] = b_norm
        best_x = torch.zeros_like(rhs)
        best_rel = float("inf")
        used_iter = 0

        for j in range(max_iter):
            v = matvec(q_vectors[j])
            for i in range(j + 1):
                hij = torch.dot(q_vectors[i], v)
                h[i, j] = hij
                v = v - hij * q_vectors[i]
            # A second modified Gram-Schmidt pass improves orthogonality for
            # nearly dependent Krylov vectors, matching the paper's GMRES note.
            for i in range(j + 1):
                correction = torch.dot(q_vectors[i], v)
                h[i, j] = h[i, j] + correction
                v = v - correction * q_vectors[i]

            h[j + 1, j] = torch.linalg.norm(v)
            if float(h[j + 1, j].detach().cpu()) > 1e-20 and j + 1 < max_iter:
                q_vectors.append(v / h[j + 1, j])
            arnoldi_norm = h[j + 1, j]

            for i in range(j):
                temp = givens_c[i] * h[i, j] + givens_s[i] * h[i + 1, j]
                h[i + 1, j] = -givens_s[i] * h[i, j] + givens_c[i] * h[i + 1, j]
                h[i, j] = temp

            rotation_norm = torch.sqrt(h[j, j] * h[j, j] + h[j + 1, j] * h[j + 1, j])
            if float(rotation_norm.detach().cpu()) <= 1e-20:
                givens_c[j] = torch.ones((), dtype=rhs.dtype, device=rhs.device)
                givens_s[j] = torch.zeros((), dtype=rhs.dtype, device=rhs.device)
            else:
                givens_c[j] = h[j, j] / rotation_norm
                givens_s[j] = h[j + 1, j] / rotation_norm

            h[j, j] = givens_c[j] * h[j, j] + givens_s[j] * h[j + 1, j]
            h[j + 1, j] = torch.zeros((), dtype=rhs.dtype, device=rhs.device)
            g_j = givens_c[j] * g[j] + givens_s[j] * g[j + 1]
            g[j + 1] = -givens_s[j] * g[j] + givens_c[j] * g[j + 1]
            g[j] = g_j

            solution = solve_upper_triangular(
                h[: j + 1, : j + 1],
                g[: j + 1],
            )
            q_stack = torch.stack(q_vectors[: j + 1], dim=1)
            best_x = q_stack @ solution
            best_rel = float((torch.abs(g[j + 1]) / b_norm).detach().cpu())
            used_iter = j + 1
            if best_rel <= tol:
                return best_x, used_iter, best_rel
            if len(q_vectors) <= j + 1:
                break
            if float(torch.abs(arnoldi_norm).detach().cpu()) <= 1e-20:
                break

        return best_x, used_iter, best_rel

    def p2g2p_implicit(
        self,
        step,
        dt,
        device="cuda:0",
        beta=0.25,
        gamma=0.5,
        newton_tol=1e-4,
        newton_max_iter=8,
        newton_abs_tol=1e-6,
        gmres_tol=1e-3,
        gmres_max_iter=24,
        jvp_eps=1e-4,
        line_search_max_iter=8,
        armijo_c1=1e-4,
        ew_eta_min=1e-5,
        ew_eta_max=0.5,
        ew_gamma=0.9,
        ew_alpha=1.5,
        stiffness_preconditioner_scale=1.0,
        stagnation_tol=1e-8,
    ):
        grid_size = (
            self.mpm_model.grid_dim_x,
            self.mpm_model.grid_dim_y,
            self.mpm_model.grid_dim_z,
        )

        self._implicit_apply_pre_p2g(dt, device=device)
        self._implicit_initialize_grid(device=device)
        self._implicit_refresh_dirichlet_constraints(dt, device=device)

        grid_vn = wp.to_torch(self.mpm_state.grid_v_out).clone()
        grid_an = wp.to_torch(self._implicit_grid_an)
        grid_mass = wp.to_torch(self.mpm_state.grid_m)
        grid_mass_mask = grid_mass > 1e-15
        dirichlet_mask = wp.to_torch(self._implicit_grid_dirichlet) > 0
        active_mask = grid_mass_mask & (~dirichlet_mask)
        if not bool(grid_mass_mask.any().detach().cpu()):
            self.time = self.time + dt
            self.implicit_history.append(
                {
                    "integrator": "implicit",
                    "step": step,
                    "dt": float(dt),
                    "time": float(self.time),
                    "active_nodes": 0,
                    "converged": True,
                    "newton_iters": 0,
                    "accepted_steps": 0,
                    "gmres_iters": 0,
                    "line_search_evals": 0,
                    "initial_residual": 0.0,
                    "final_residual": 0.0,
                    "final_relative_residual": 0.0,
                    "newton_trace": [],
                }
            )
            return self.implicit_history[-1]

        grid_stiffness_wp = wp.zeros(shape=grid_size, dtype=float, device=device)
        wp.launch(
            kernel=zero_grid_float,
            dim=grid_size,
            inputs=[grid_stiffness_wp],
            device=device,
        )
        wp.launch(
            kernel=implicit_accumulate_stiffness_diag,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model, grid_stiffness_wp],
            device=device,
        )
        grid_stiffness = wp.to_torch(grid_stiffness_wp)

        grid_du = (dt * grid_vn + 0.5 * dt * dt * grid_an).clone()
        grid_v_target = wp.to_torch(self._implicit_grid_v_target)

        def apply_dirichlet_du(du_tensor):
            if not bool(dirichlet_mask.any().detach().cpu()):
                return du_tensor
            out = du_tensor.clone()
            v_n = grid_vn[dirichlet_mask]
            a_n = grid_an[dirichlet_mask]
            v_tar = grid_v_target[dirichlet_mask]
            a_np1 = (v_tar - v_n - dt * (1.0 - gamma) * a_n) * (
                1.0 / (gamma * dt)
            )
            out[dirichlet_mask] = (
                dt * v_n
                + dt * dt * (0.5 - beta) * a_n
                + beta * dt * dt * a_np1
            )
            return out

        grid_du = apply_dirichlet_du(grid_du)
        grid_force_wp = wp.zeros(shape=grid_size, dtype=wp.vec3, device=device)
        grid_residual_wp = wp.zeros(shape=grid_size, dtype=wp.vec3, device=device)
        trial_F_wp = wp.zeros(shape=self.n_particles, dtype=wp.mat33, device=device)
        trial_stress_wp = wp.zeros(shape=self.n_particles, dtype=wp.mat33, device=device)

        grid_vn_wp = wp.from_torch(grid_vn, dtype=wp.vec3)
        grid_an_wp = self._implicit_grid_an

        def residual_from_du(du_tensor):
            du_tensor = apply_dirichlet_du(du_tensor)
            grid_du_wp_local = wp.from_torch(du_tensor.contiguous(), dtype=wp.vec3)
            residual_grid = self._implicit_residual(
                grid_du_wp_local,
                grid_vn_wp,
                grid_an_wp,
                grid_force_wp,
                grid_residual_wp,
                trial_F_wp,
                trial_stress_wp,
                beta,
                gamma,
                dt,
                device=device,
            )
            return residual_grid[active_mask].reshape(-1).clone()

        residual = residual_from_du(grid_du)
        initial_norm = torch.linalg.norm(residual).clamp_min(1e-20)
        previous_residual_norm = None
        total_gmres_iters = 0
        total_line_search_iters = 0
        accepted_steps = 0
        converged = False
        last_relative = float("inf")
        newton_trace = []

        mass_active = grid_mass[active_mask].reshape(-1, 1).expand(-1, 3).reshape(-1)
        stiffness_active = grid_stiffness[active_mask].reshape(-1, 1).expand(-1, 3).reshape(-1)
        precond_diag = (
            mass_active / (beta * dt * dt)
            + stiffness_preconditioner_scale * stiffness_active
        )
        precond_diag = torch.clamp(precond_diag, min=1e-12)
        precond_min = float(torch.min(precond_diag).detach().cpu())
        precond_max = float(torch.max(precond_diag).detach().cpu())
        precond_mean = float(torch.mean(precond_diag).detach().cpu())

        def unpack_active(vec):
            out = torch.zeros_like(grid_du)
            out[active_mask] = vec.reshape(-1, 3)
            return out

        for _newton_iter in range(newton_max_iter):
            residual_norm = torch.linalg.norm(residual)
            last_relative = float((residual_norm / initial_norm).detach().cpu())
            if (
                last_relative <= newton_tol
                or float(residual_norm.detach().cpu()) <= newton_abs_tol
            ):
                converged = True
                break

            def matvec_preconditioned(y):
                direction = y / precond_diag
                direction_grid = unpack_active(direction)
                direction_scale = torch.max(torch.abs(direction_grid[active_mask]))
                eps = jvp_eps / torch.clamp(direction_scale, min=1e-12)
                r_plus = residual_from_du(grid_du + eps * direction_grid)
                r_minus = residual_from_du(grid_du - eps * direction_grid)
                return (r_plus - r_minus) / (2.0 * eps)

            rhs = -residual
            if previous_residual_norm is None:
                ew_tol = ew_eta_max
            else:
                ratio = float(
                    (residual_norm / torch.clamp(previous_residual_norm, min=1e-20))
                    .detach()
                    .cpu()
                )
                ew_tol = ew_gamma * (ratio ** ew_alpha)
            ew_floor = min(ew_eta_min, gmres_tol)
            ew_tol = min(ew_eta_max, max(ew_floor, ew_tol))
            y, gmres_iters, gmres_rel = self._gmres_matrix_free(
                matvec_preconditioned,
                rhs,
                tol=ew_tol,
                max_iter=gmres_max_iter,
            )
            j_delta = matvec_preconditioned(y)
            total_gmres_iters += gmres_iters
            delta_active = y / precond_diag
            delta_grid = unpack_active(delta_active)

            current_phi = 0.5 * torch.dot(residual, residual)
            directional_derivative = torch.dot(residual, j_delta)
            iteration_record = {
                "newton_iter": int(_newton_iter),
                "residual": float(residual_norm.detach().cpu()),
                "relative_residual": float(last_relative),
                "objective": float(current_phi.detach().cpu()),
                "ew_tolerance": float(ew_tol),
                "gmres_iters": int(gmres_iters),
                "gmres_relative_residual": float(gmres_rel),
                "directional_derivative": float(directional_derivative.detach().cpu()),
                "direction": "gmres",
                "accepted": False,
                "alpha": 0.0,
                "line_search_evals": 0,
            }
            if float(directional_derivative.detach().cpu()) >= 0.0:
                delta_active = -residual / precond_diag
                delta_grid = unpack_active(delta_active)
                directional_derivative = -torch.dot(residual, residual / precond_diag)
                iteration_record["direction"] = "preconditioned_steepest_descent"
                iteration_record["directional_derivative"] = float(
                    directional_derivative.detach().cpu()
                )

            alpha = 1.0
            accepted = False
            for _ls_iter in range(line_search_max_iter):
                trial_du = grid_du + alpha * delta_grid
                trial_residual = residual_from_du(trial_du)
                trial_phi = 0.5 * torch.dot(trial_residual, trial_residual)
                armijo_rhs = current_phi + armijo_c1 * alpha * directional_derivative
                iteration_record["last_trial_objective"] = float(
                    trial_phi.detach().cpu()
                )
                iteration_record["last_armijo_rhs"] = float(
                    armijo_rhs.detach().cpu()
                )
                if float(trial_phi.detach().cpu()) <= float(armijo_rhs.detach().cpu()):
                    step_norm = torch.linalg.norm(alpha * delta_grid[active_mask].reshape(-1))
                    base_norm = torch.linalg.norm(grid_du[active_mask].reshape(-1)).clamp_min(1e-20)
                    grid_du = trial_du
                    previous_residual_norm = residual_norm
                    residual = trial_residual
                    accepted = True
                    accepted_steps += 1
                    total_line_search_iters += _ls_iter + 1
                    iteration_record["accepted"] = True
                    iteration_record["alpha"] = float(alpha)
                    iteration_record["line_search_evals"] = int(_ls_iter + 1)
                    iteration_record["trial_relative_residual"] = float(
                        (torch.linalg.norm(residual) / initial_norm).detach().cpu()
                    )
                    iteration_record["trial_objective"] = float(
                        trial_phi.detach().cpu()
                    )
                    if float((step_norm / base_norm).detach().cpu()) <= stagnation_tol:
                        converged = bool(
                            float((torch.linalg.norm(residual) / initial_norm).detach().cpu())
                            <= max(newton_tol * 10.0, 1e-8)
                        )
                    break
                alpha *= 0.5

            if not accepted:
                steepest = unpack_active(residual / precond_diag)
                iteration_record["direction"] = "fallback_steepest_descent"
                alpha = 1.0
                for _ls_iter in range(line_search_max_iter):
                    trial_du = grid_du - alpha * steepest
                    trial_residual = residual_from_du(trial_du)
                    trial_phi = 0.5 * torch.dot(trial_residual, trial_residual)
                    iteration_record["last_trial_objective"] = float(
                        trial_phi.detach().cpu()
                    )
                    if float(trial_phi.detach().cpu()) < float(current_phi.detach().cpu()):
                        previous_residual_norm = residual_norm
                        grid_du = trial_du
                        residual = trial_residual
                        accepted = True
                        accepted_steps += 1
                        total_line_search_iters += _ls_iter + 1
                        iteration_record["accepted"] = True
                        iteration_record["alpha"] = float(alpha)
                        iteration_record["line_search_evals"] = int(_ls_iter + 1)
                        iteration_record["trial_relative_residual"] = float(
                            (torch.linalg.norm(residual) / initial_norm).detach().cpu()
                        )
                        iteration_record["trial_objective"] = float(
                            trial_phi.detach().cpu()
                        )
                        break
                    alpha *= 0.5
            newton_trace.append(iteration_record)
            if not accepted:
                break

        final_norm = torch.linalg.norm(residual)
        last_relative = float((final_norm / initial_norm).detach().cpu())
        converged = (
            converged
            or last_relative <= newton_tol
            or float(final_norm.detach().cpu()) <= newton_abs_tol
        )

        grid_du = apply_dirichlet_du(grid_du)
        grid_du_wp = wp.from_torch(grid_du.contiguous(), dtype=wp.vec3)
        self._implicit_residual(
            grid_du_wp,
            grid_vn_wp,
            grid_an_wp,
            grid_force_wp,
            grid_residual_wp,
            trial_F_wp,
            trial_stress_wp,
            beta,
            gamma,
            dt,
            device=device,
        )

        if self.mpm_model.grid_v_damping_scale < 1.0:
            wp.launch(
                kernel=add_damping_via_grid,
                dim=grid_size,
                inputs=[self.mpm_state, self.mpm_model.grid_v_damping_scale],
                device=device,
            )

        wp.launch(
            kernel=implicit_project_du_from_velocity,
            dim=grid_size,
            inputs=[
                self.mpm_state,
                grid_du_wp,
                grid_vn_wp,
                self._implicit_grid_an,
                beta,
                gamma,
                dt,
            ],
            device=device,
        )

        wp.launch(
            kernel=g2p_implicit,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model, grid_du_wp, dt],
            device=device,
        )
        self._apply_fixed_particles(time=self.time + dt, device=device)

        wp.launch(
            kernel=compute_stress_from_F_trial,
            dim=self.n_particles,
            inputs=[self.mpm_state, self.mpm_model, dt],
            device=device,
        )

        wp.launch(
            kernel=implicit_update_acceleration_from_velocity,
            dim=grid_size,
            inputs=[
                self.mpm_state,
                grid_vn_wp,
                self._implicit_grid_an,
                gamma,
                dt,
            ],
            device=device,
        )

        for k in range(len(self.grid_postprocess)):
            if self.modify_bc[k] is not None:
                self.modify_bc[k](self.time, dt, self.collider_params[k])

        self.time = self.time + dt
        diagnostics = {
            "integrator": "implicit",
            "step": step,
            "dt": float(dt),
            "time": float(self.time),
            "active_nodes": int(active_mask.sum().detach().cpu()),
            "dirichlet_nodes": int((grid_mass_mask & dirichlet_mask).sum().detach().cpu()),
            "converged": bool(converged),
            "beta": float(beta),
            "gamma": float(gamma),
            "newton_tol": float(newton_tol),
            "newton_abs_tol": float(newton_abs_tol),
            "newton_max_iter": int(newton_max_iter),
            "gmres_tol": float(gmres_tol),
            "gmres_max_iter": int(gmres_max_iter),
            "jvp_eps": float(jvp_eps),
            "line_search_max_iter": int(line_search_max_iter),
            "armijo_c1": float(armijo_c1),
            "ew_eta_min": float(ew_eta_min),
            "ew_eta_max": float(ew_eta_max),
            "ew_gamma": float(ew_gamma),
            "ew_alpha": float(ew_alpha),
            "stiffness_preconditioner_scale": float(stiffness_preconditioner_scale),
            "stagnation_tol": float(stagnation_tol),
            "preconditioner_min": precond_min,
            "preconditioner_max": precond_max,
            "preconditioner_mean": precond_mean,
            "newton_iters": int(len(newton_trace)),
            "accepted_steps": int(accepted_steps),
            "gmres_iters": int(total_gmres_iters),
            "line_search_evals": int(total_line_search_iters),
            "initial_residual": float(initial_norm.detach().cpu()),
            "final_residual": float(final_norm.detach().cpu()),
            "final_relative_residual": float(last_relative),
            "newton_trace": newton_trace,
        }
        self.implicit_history.append(diagnostics)
        return diagnostics

    # set particle densities to all_particle_densities,
    def reset_densities_and_update_masses(
        self, all_particle_densities, device="cuda:0"
    ):
        all_particle_densities = all_particle_densities.clone().detach()
        self.mpm_state.particle_density = torch2warp_float(
            all_particle_densities, dvc=device
        )
        wp.launch(
            kernel=get_float_array_product,
            dim=self.n_particles,
            inputs=[
                self.mpm_state.particle_density,
                self.mpm_state.particle_vol,
                self.mpm_state.particle_mass,
            ],
            device=device,
        )

    # clone = True makes a copy, not necessarily needed
    def import_particle_x_from_torch(self, tensor_x, clone=True, device="cuda:0"):
        if tensor_x is not None:
            if clone:
                tensor_x = tensor_x.clone().detach()
            self.mpm_state.particle_x = torch2warp_vec3(tensor_x, dvc=device)

    # clone = True makes a copy, not necessarily needed
    def import_particle_v_from_torch(self, tensor_v, clone=True, device="cuda:0"):
        if tensor_v is not None:
            if clone:
                tensor_v = tensor_v.clone().detach()
            self.mpm_state.particle_v = torch2warp_vec3(tensor_v, dvc=device)

    # clone = True makes a copy, not necessarily needed
    def import_particle_F_from_torch(self, tensor_F, clone=True, device="cuda:0"):
        if tensor_F is not None:
            if clone:
                tensor_F = tensor_F.clone().detach()
            tensor_F = torch.reshape(tensor_F, (-1, 3, 3))  # arranged by rowmajor
            self.mpm_state.particle_F = torch2warp_mat33(tensor_F, dvc=device)

    # clone = True makes a copy, not necessarily needed
    def import_particle_C_from_torch(self, tensor_C, clone=True, device="cuda:0"):
        if tensor_C is not None:
            if clone:
                tensor_C = tensor_C.clone().detach()
            tensor_C = torch.reshape(tensor_C, (-1, 3, 3))  # arranged by rowmajor
            self.mpm_state.particle_C = torch2warp_mat33(tensor_C, dvc=device)

    def export_particle_x_to_torch(self):
        return wp.to_torch(self.mpm_state.particle_x)

    def export_particle_v_to_torch(self):
        return wp.to_torch(self.mpm_state.particle_v)

    def export_particle_F_to_torch(self):
        F_tensor = wp.to_torch(self.mpm_state.particle_F)
        F_tensor = F_tensor.reshape(-1, 9)
        return F_tensor

    def export_particle_R_to_torch(self, device="cuda:0"):
        with wp.ScopedTimer(
            "compute_R_from_F",
            synchronize=True,
            print=False,
            dict=self.time_profile,
        ):
            wp.launch(
                kernel=compute_R_from_F,
                dim=self.n_particles,
                inputs=[self.mpm_state, self.mpm_model],
                device=device,
            )

        R_tensor = wp.to_torch(self.mpm_state.particle_R)
        R_tensor = R_tensor.reshape(-1, 9)
        return R_tensor

    def export_particle_C_to_torch(self):
        C_tensor = wp.to_torch(self.mpm_state.particle_C)
        C_tensor = C_tensor.reshape(-1, 9)
        return C_tensor

    def export_particle_cov_to_torch(self, device="cuda:0"):
        if not self.mpm_model.update_cov_with_F:
            with wp.ScopedTimer(
                "compute_cov_from_F",
                synchronize=True,
                print=False,
                dict=self.time_profile,
            ):
                wp.launch(
                    kernel=compute_cov_from_F,
                    dim=self.n_particles,
                    inputs=[self.mpm_state, self.mpm_model],
                    device=device,
                )

        cov = wp.to_torch(self.mpm_state.particle_cov)
        return cov

    def print_time_profile(self):
        print("MPM Time profile:")
        for key, value in self.time_profile.items():
            print(key, sum(value))

    # a surface specified by a point and the normal vector
    def add_surface_collider(
        self,
        point,
        normal,
        surface="sticky",
        friction=0.0,
        start_time=0.0,
        end_time=999.0,
    ):
        point = list(point)
        # Normalize normal
        normal_scale = 1.0 / wp.sqrt(float(sum(x**2 for x in normal)))
        normal = list(normal_scale * x for x in normal)

        collider_param = Dirichlet_collider()
        collider_param.start_time = start_time
        collider_param.end_time = end_time

        collider_param.point = wp.vec3(point[0], point[1], point[2])
        collider_param.normal = wp.vec3(normal[0], normal[1], normal[2])

        if surface == "sticky" and friction != 0:
            raise ValueError("friction must be 0 on sticky surfaces.")
        if surface == "sticky":
            collider_param.surface_type = 0
        elif surface == "slip":
            collider_param.surface_type = 1
        elif surface == "cut":
            collider_param.surface_type = 11
        else:
            collider_param.surface_type = 2
        # frictional
        collider_param.friction = friction

        self.collider_params.append(collider_param)

        @wp.kernel
        def collide(
            time: float,
            dt: float,
            state: MPMStateStruct,
            model: MPMModelStruct,
            param: Dirichlet_collider,
        ):
            grid_x, grid_y, grid_z = wp.tid()
            if time >= param.start_time and time < param.end_time:
                offset = wp.vec3(
                    float(grid_x) * model.dx - param.point[0],
                    float(grid_y) * model.dx - param.point[1],
                    float(grid_z) * model.dx - param.point[2],
                )
                n = wp.vec3(param.normal[0], param.normal[1], param.normal[2])
                dotproduct = wp.dot(offset, n)

                if dotproduct < 0.0:
                    if param.surface_type == 0:
                        state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                            0.0, 0.0, 0.0
                        )
                    elif param.surface_type == 11:
                        if (
                            float(grid_z) * model.dx < 0.4
                            or float(grid_z) * model.dx > 0.53
                        ):
                            state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                                0.0, 0.0, 0.0
                            )
                        else:
                            v_in = state.grid_v_out[grid_x, grid_y, grid_z]
                            state.grid_v_out[grid_x, grid_y, grid_z] = (
                                wp.vec3(v_in[0], 0.0, v_in[2]) * 0.3
                            )
                    else:
                        v = state.grid_v_out[grid_x, grid_y, grid_z]
                        normal_component = wp.dot(v, n)
                        if param.surface_type == 1:
                            v = (
                                v - normal_component * n
                            )  # Project out all normal component
                        else:
                            v = (
                                v - wp.min(normal_component, 0.0) * n
                            )  # Project out only inward normal component
                        if normal_component < 0.0 and wp.length(v) > 1e-20:
                            v = wp.max(
                                0.0, wp.length(v) + normal_component * param.friction
                            ) * wp.normalize(
                                v
                            )  # apply friction here
                        state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                            0.0, 0.0, 0.0
                        )

        self.grid_postprocess.append(collide)
        self.modify_bc.append(None)

        @wp.kernel
        def mark_implicit_dirichlet(
            time: float,
            dt: float,
            state: MPMStateStruct,
            model: MPMModelStruct,
            param: Dirichlet_collider,
            mask: wp.array(dtype=int, ndim=3),
            target: wp.array(dtype=wp.vec3, ndim=3),
        ):
            grid_x, grid_y, grid_z = wp.tid()
            if time >= param.start_time and time < param.end_time:
                offset = wp.vec3(
                    float(grid_x) * model.dx - param.point[0],
                    float(grid_y) * model.dx - param.point[1],
                    float(grid_z) * model.dx - param.point[2],
                )
                n = wp.vec3(param.normal[0], param.normal[1], param.normal[2])
                dotproduct = wp.dot(offset, n)
                if dotproduct < 0.0 and param.surface_type == 0:
                    mask[grid_x, grid_y, grid_z] = 1
                    target[grid_x, grid_y, grid_z] = wp.vec3(0.0, 0.0, 0.0)

        self.implicit_grid_constraint_builders.append(mark_implicit_dirichlet)
        self.implicit_grid_constraint_params.append(collider_param)

    # a cubiod is a rectangular cube'
    # centered at `point`
    # dimension is x: point[0]±size[0]
    #              y: point[1]±size[1]
    #              z: point[2]±size[2]
    # all grid nodes lie within the cubiod will have their speed set to velocity
    # the cuboid itself is also moving with const speed = velocity
    # set the speed to zero to fix BC
    def set_velocity_on_cuboid(
        self,
        point,
        size,
        velocity,
        start_time=0.0,
        end_time=999.0,
        reset=0,
    ):
        point = list(point)

        collider_param = Dirichlet_collider()
        collider_param.start_time = start_time
        collider_param.end_time = end_time
        collider_param.point = wp.vec3(point[0], point[1], point[2])
        collider_param.size = size
        collider_param.velocity = wp.vec3(velocity[0], velocity[1], velocity[2])
        # collider_param.threshold = threshold
        collider_param.reset = reset
        self.collider_params.append(collider_param)

        @wp.kernel
        def collide(
            time: float,
            dt: float,
            state: MPMStateStruct,
            model: MPMModelStruct,
            param: Dirichlet_collider,
        ):
            grid_x, grid_y, grid_z = wp.tid()
            if time >= param.start_time and time < param.end_time:
                offset = wp.vec3(
                    float(grid_x) * model.dx - param.point[0],
                    float(grid_y) * model.dx - param.point[1],
                    float(grid_z) * model.dx - param.point[2],
                )
                if (
                    wp.abs(offset[0]) < param.size[0]
                    and wp.abs(offset[1]) < param.size[1]
                    and wp.abs(offset[2]) < param.size[2]
                ):
                    state.grid_v_out[grid_x, grid_y, grid_z] = param.velocity
            elif param.reset == 1:
                if time < param.end_time + 15.0 * dt:
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(0.0, 0.0, 0.0)

        def modify(time, dt, param: Dirichlet_collider):
            if time >= param.start_time and time < param.end_time:
                param.point = wp.vec3(
                    param.point[0] + dt * param.velocity[0],
                    param.point[1] + dt * param.velocity[1],
                    param.point[2] + dt * param.velocity[2],
                )  # param.point + dt * param.velocity

        self.grid_postprocess.append(collide)
        self.modify_bc.append(modify)

        @wp.kernel
        def mark_implicit_dirichlet(
            time: float,
            dt: float,
            state: MPMStateStruct,
            model: MPMModelStruct,
            param: Dirichlet_collider,
            mask: wp.array(dtype=int, ndim=3),
            target: wp.array(dtype=wp.vec3, ndim=3),
        ):
            grid_x, grid_y, grid_z = wp.tid()
            if time >= param.start_time and time < param.end_time:
                offset = wp.vec3(
                    float(grid_x) * model.dx - param.point[0],
                    float(grid_y) * model.dx - param.point[1],
                    float(grid_z) * model.dx - param.point[2],
                )
                if (
                    wp.abs(offset[0]) < param.size[0]
                    and wp.abs(offset[1]) < param.size[1]
                    and wp.abs(offset[2]) < param.size[2]
                ):
                    mask[grid_x, grid_y, grid_z] = 1
                    target[grid_x, grid_y, grid_z] = param.velocity
            elif param.reset == 1:
                if time < param.end_time + 15.0 * dt:
                    mask[grid_x, grid_y, grid_z] = 1
                    target[grid_x, grid_y, grid_z] = wp.vec3(0.0, 0.0, 0.0)

        self.implicit_grid_constraint_builders.append(mark_implicit_dirichlet)
        self.implicit_grid_constraint_params.append(collider_param)

    def add_bounding_box(self, start_time=0.0, end_time=999.0):
        collider_param = Dirichlet_collider()
        collider_param.start_time = start_time
        collider_param.end_time = end_time

        self.collider_params.append(collider_param)

        @wp.kernel
        def collide(
            time: float,
            dt: float,
            state: MPMStateStruct,
            model: MPMModelStruct,
            param: Dirichlet_collider,
        ):
            grid_x, grid_y, grid_z = wp.tid()
            padding = 3
            if time >= param.start_time and time < param.end_time:
                if grid_x < padding and state.grid_v_out[grid_x, grid_y, grid_z][0] < 0:
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        0.0,
                        state.grid_v_out[grid_x, grid_y, grid_z][1],
                        state.grid_v_out[grid_x, grid_y, grid_z][2],
                    )
                if (
                    grid_x >= model.grid_dim_x - padding
                    and state.grid_v_out[grid_x, grid_y, grid_z][0] > 0
                ):
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        0.0,
                        state.grid_v_out[grid_x, grid_y, grid_z][1],
                        state.grid_v_out[grid_x, grid_y, grid_z][2],
                    )

                if grid_y < padding and state.grid_v_out[grid_x, grid_y, grid_z][1] < 0:
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        state.grid_v_out[grid_x, grid_y, grid_z][0],
                        0.0,
                        state.grid_v_out[grid_x, grid_y, grid_z][2],
                    )
                if (
                    grid_y >= model.grid_dim_y - padding
                    and state.grid_v_out[grid_x, grid_y, grid_z][1] > 0
                ):
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        state.grid_v_out[grid_x, grid_y, grid_z][0],
                        0.0,
                        state.grid_v_out[grid_x, grid_y, grid_z][2],
                    )

                if grid_z < padding and state.grid_v_out[grid_x, grid_y, grid_z][2] < 0:
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        state.grid_v_out[grid_x, grid_y, grid_z][0],
                        state.grid_v_out[grid_x, grid_y, grid_z][1],
                        0.0,
                    )
                if (
                    grid_z >= model.grid_dim_z - padding
                    and state.grid_v_out[grid_x, grid_y, grid_z][2] > 0
                ):
                    state.grid_v_out[grid_x, grid_y, grid_z] = wp.vec3(
                        state.grid_v_out[grid_x, grid_y, grid_z][0],
                        state.grid_v_out[grid_x, grid_y, grid_z][1],
                        0.0,
                    )

        self.grid_postprocess.append(collide)
        self.modify_bc.append(None)

    # particle_v += force/particle_mass * dt
    # this is applied from start_dt, ends after num_dt p2g2p's
    # particle velocity is changed before p2g at each timestep
    def add_impulse_on_particles(
        self,
        force,
        dt,
        point=[1, 1, 1],
        size=[1, 1, 1],
        num_dt=1,
        start_time=0.0,
        device="cuda:0",
    ):
        impulse_param = Impulse_modifier()
        impulse_param.start_time = start_time
        impulse_param.end_time = start_time + dt * num_dt

        impulse_param.point = wp.vec3(point[0], point[1], point[2])
        impulse_param.size = wp.vec3(size[0], size[1], size[2])
        impulse_param.mask = wp.zeros(shape=self.n_particles, dtype=int, device=device)

        impulse_param.force = wp.vec3(
            force[0],
            force[1],
            force[2],
        )

        wp.launch(
            kernel=selection_add_impulse_on_particles,
            dim=self.n_particles,
            inputs=[self.mpm_state, impulse_param],
            device=device,
        )

        self.impulse_params.append(impulse_param)

        @wp.kernel
        def apply_force(
            time: float, dt: float, state: MPMStateStruct, param: Impulse_modifier
        ):
            p = wp.tid()
            if time >= param.start_time and time < param.end_time:
                if param.mask[p] == 1:
                    impulse = wp.vec3(
                        param.force[0] / state.particle_mass[p],
                        param.force[1] / state.particle_mass[p],
                        param.force[2] / state.particle_mass[p],
                    )
                    state.particle_v[p] = state.particle_v[p] + impulse * dt

        self.pre_p2g_operations.append(apply_force)

    def fix_particles_by_indices(
        self,
        indices,
        velocity=[0, 0, 0],
        start_time=0.0,
        end_time=999.0,
        reset_deformation=1,
        device="cuda:0",
    ):
        if not torch.is_tensor(indices):
            indices = torch.tensor(indices, dtype=torch.long, device=device)
        else:
            indices = indices.to(device=device, dtype=torch.long)
        if indices.numel() == 0:
            return

        valid = torch.logical_and(indices >= 0, indices < self.n_particles)
        indices = torch.unique(indices[valid], sorted=True)
        if indices.numel() == 0:
            return

        indices_i32 = indices.to(torch.int32).contiguous()
        rest_x = wp.to_torch(self.mpm_state.particle_x)[indices].clone().contiguous()
        params = FixedParticleModifier()
        params.indices = wp.from_torch(indices_i32, dtype=int)
        params.rest_x = torch2warp_vec3(rest_x, dvc=device)
        params.velocity = wp.vec3(float(velocity[0]), float(velocity[1]), float(velocity[2]))
        params.start_time = float(start_time)
        params.end_time = float(end_time)
        params.reset_deformation = int(reset_deformation)
        self.fixed_particle_params.append(params)
        self.fixed_particle_counts.append(int(indices.numel()))
        self.fixed_particle_tensors.append((indices_i32, rest_x))
        self._apply_fixed_particles(time=self.time, device=device)

    def enforce_particle_velocity_translation(
        self, point, size, velocity, start_time, end_time, device="cuda:0"
    ):

        # first select certain particles based on position

        velocity_modifier_params = ParticleVelocityModifier()

        velocity_modifier_params.point = wp.vec3(point[0], point[1], point[2])
        velocity_modifier_params.size = wp.vec3(size[0], size[1], size[2])

        velocity_modifier_params.velocity = wp.vec3(
            velocity[0], velocity[1], velocity[2]
        )

        velocity_modifier_params.start_time = start_time
        velocity_modifier_params.end_time = end_time

        velocity_modifier_params.mask = wp.zeros(
            shape=self.n_particles, dtype=int, device=device
        )

        wp.launch(
            kernel=selection_enforce_particle_velocity_translation,
            dim=self.n_particles,
            inputs=[self.mpm_state, velocity_modifier_params],
            device=device,
        )
        self.particle_velocity_modifier_params.append(velocity_modifier_params)

        @wp.kernel
        def modify_particle_v_before_p2g(
            time: float,
            state: MPMStateStruct,
            velocity_modifier_params: ParticleVelocityModifier,
        ):
            p = wp.tid()
            if (
                time >= velocity_modifier_params.start_time
                and time < velocity_modifier_params.end_time
            ):
                if velocity_modifier_params.mask[p] == 1:
                    state.particle_v[p] = velocity_modifier_params.velocity

        self.particle_velocity_modifiers.append(modify_particle_v_before_p2g)

    # define a cylinder with center point, half_height, radius, normal
    # particles within the cylinder are rotating along the normal direction
    # may also have a translational velocity along the normal direction
    def enforce_particle_velocity_rotation(
        self,
        point,
        normal,
        half_height_and_radius,
        rotation_scale,
        translation_scale,
        start_time,
        end_time,
        device="cuda:0",
    ):

        normal_scale = 1.0 / wp.sqrt(
            float(normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2)
        )
        normal = list(normal_scale * x for x in normal)

        velocity_modifier_params = ParticleVelocityModifier()

        velocity_modifier_params.point = wp.vec3(point[0], point[1], point[2])
        velocity_modifier_params.half_height_and_radius = wp.vec2(
            half_height_and_radius[0], half_height_and_radius[1]
        )
        velocity_modifier_params.normal = wp.vec3(normal[0], normal[1], normal[2])

        horizontal_1 = wp.vec3(1.0, 1.0, 1.0)
        if wp.abs(wp.dot(velocity_modifier_params.normal, horizontal_1)) < 0.01:
            horizontal_1 = wp.vec3(0.72, 0.37, -0.67)
        horizontal_1 = (
            horizontal_1
            - wp.dot(horizontal_1, velocity_modifier_params.normal)
            * velocity_modifier_params.normal
        )
        horizontal_1 = horizontal_1 * (1.0 / wp.length(horizontal_1))
        horizontal_2 = wp.cross(horizontal_1, velocity_modifier_params.normal)

        velocity_modifier_params.horizontal_axis_1 = horizontal_1
        velocity_modifier_params.horizontal_axis_2 = horizontal_2

        velocity_modifier_params.rotation_scale = rotation_scale
        velocity_modifier_params.translation_scale = translation_scale

        velocity_modifier_params.start_time = start_time
        velocity_modifier_params.end_time = end_time

        velocity_modifier_params.mask = wp.zeros(
            shape=self.n_particles, dtype=int, device=device
        )

        wp.launch(
            kernel=selection_enforce_particle_velocity_cylinder,
            dim=self.n_particles,
            inputs=[self.mpm_state, velocity_modifier_params],
            device=device,
        )
        self.particle_velocity_modifier_params.append(velocity_modifier_params)

        @wp.kernel
        def modify_particle_v_before_p2g(
            time: float,
            state: MPMStateStruct,
            velocity_modifier_params: ParticleVelocityModifier,
        ):
            p = wp.tid()
            if (
                time >= velocity_modifier_params.start_time
                and time < velocity_modifier_params.end_time
            ):
                if velocity_modifier_params.mask[p] == 1:
                    offset = state.particle_x[p] - velocity_modifier_params.point
                    horizontal_distance = wp.length(
                        offset
                        - wp.dot(offset, velocity_modifier_params.normal)
                        * velocity_modifier_params.normal
                    )
                    cosine = (
                        wp.dot(offset, velocity_modifier_params.horizontal_axis_1)
                        / horizontal_distance
                    )
                    theta = wp.acos(cosine)
                    if wp.dot(offset, velocity_modifier_params.horizontal_axis_2) > 0:
                        theta = theta
                    else:
                        theta = -theta
                    axis1_scale = (
                        -horizontal_distance
                        * wp.sin(theta)
                        * velocity_modifier_params.rotation_scale
                    )
                    axis2_scale = (
                        horizontal_distance
                        * wp.cos(theta)
                        * velocity_modifier_params.rotation_scale
                    )
                    axis_vertical_scale = translation_scale
                    state.particle_v[p] = (
                        axis1_scale * velocity_modifier_params.horizontal_axis_1
                        + axis2_scale * velocity_modifier_params.horizontal_axis_2
                        + axis_vertical_scale * velocity_modifier_params.normal
                    )

        self.particle_velocity_modifiers.append(modify_particle_v_before_p2g)

    # given normal direction, say [0,0,1]
    # gradually release grid velocities from start position to end position
    def release_particles_sequentially(
        self, normal, start_position, end_position, num_layers, start_time, end_time
    ):
        num_layers = 50
        point = [0, 0, 0]
        size = [0, 0, 0]
        axis = -1
        for i in range(3):
            if normal[i] == 0:
                point[i] = 1
                size[i] = 1
            else:
                axis = i
                point[i] = end_position

        half_length_portion = wp.abs(start_position - end_position) / num_layers
        end_time_portion = end_time / num_layers
        for i in range(num_layers):
            size[axis] = half_length_portion * (num_layers - i)
            self.enforce_particle_velocity_translation(
                point=point,
                size=size,
                velocity=[0, 0, 0],
                start_time=start_time,
                end_time=end_time_portion * (i + 1),
            )
