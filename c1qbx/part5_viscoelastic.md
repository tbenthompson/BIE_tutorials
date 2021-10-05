---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

```{code-cell} ipython3
:tags: [remove-cell]

from config import setup, import_and_display_fnc

setup()
```

```{code-cell} ipython3
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from common import (
    gauss_rule,
    qbx_matrix,
    qbx_setup,
    double_layer_matrix,
    hypersingular_matrix,
    stage1_refine,
    qbx_panel_setup,
    stage2_refine,
    pts_grid,
    apply_interp_mat
)
```

This next section will construct the free surface panelized surface `free`. The `corner_resolution` specifies how large the panels will be near the fault-surface intersection. Away from that intersection, the panels will each be double the length of the prior panel, thus enabling the full surface to efficiently represent an effectively infinite free surface.

```{code-cell} ipython3
corner_resolution = 5000
surf_half_L = 2000000
fault_bottom = 15000
visco_half_L = 500000
visco_depth = 20000
shear_modulus = 3e10
viscosity = 5e18

qx, qw = gauss_rule(6)
t = sp.var("t")

control_points = [
    (0, 0, 0, corner_resolution),
    (0, -visco_depth, 0, corner_resolution)
]  # np.array([(0, 0, 2, corner_resolution)])
# for i in range(15):
#     control_points.append((0, -i * 1000, 0, 1000))# = np.array([(0, 0, 2, corner_resolution)])
fault, free, VB = stage1_refine(
    [
        (t, t * 0, fault_bottom * (t + 1) * -0.5),  # fault
        (t, -t * surf_half_L, 0 * t),  # free surface
        (t, -t * visco_half_L, -visco_depth + 0 * t),  # viscoelastic boundary
    ],
    (qx, qw),
    control_points=control_points,
)
```

```{code-cell} ipython3
expansions = qbx_panel_setup([fault, fault, free, VB], directions=[-1, 1, 1, 1], p=10)
```

```{code-cell} ipython3
fault_stage2, fault_interp_mat = stage2_refine(fault, expansions)
free_stage2, free_interp_mat = stage2_refine(free, expansions)
VB_stage2, VB_interp_mat = stage2_refine(VB, expansions)
```

```{code-cell} ipython3
%matplotlib inline
plt.figure(figsize=(10, 4))
plt.subplot(1, 2, 1)
plt.plot(fault.pts[:, 0], fault.pts[:, 1], "r-o")
plt.plot(free.pts[:, 0], free.pts[:, 1], "k-o")
plt.plot(VB.pts[:, 0], VB.pts[:, 1], "b-o")
for i in range(expansions.N):
    plt.gca().add_patch(
        plt.Circle(expansions.pts[i], expansions.r[i], color="b", fill=False)
    )
# plt.xlim([-25000, 25000])
# plt.ylim([-50000, 1000])
plt.xlim([-2500000, 2500000])
plt.ylim([-5000000, 1000])


plt.subplot(1, 2, 2)
plt.plot(fault_stage2.pts[:, 0], fault_stage2.pts[:, 1], "r-o")
plt.plot(free_stage2.pts[:, 0], free_stage2.pts[:, 1], "k-o")
plt.plot(VB_stage2.pts[:, 0], VB_stage2.pts[:, 1], "b-o")
plt.plot(expansions.pts[:, 0], expansions.pts[:, 1], "bo")
for i in range(expansions.N):
    plt.gca().add_patch(
        plt.Circle(expansions.pts[i], expansions.r[i], color="b", fill=False)
    )
plt.xlim([-1500, 1500])
plt.ylim([-3000, 1])

plt.show()
```

```{code-cell} ipython3
print("number of points in the free surface discretization:", free.n_pts)
print("                        visco bdry   discretization:", VB.n_pts)
print("                        fault        discretization:", fault.n_pts)
print("                        free surface     quadrature:", free_stage2.n_pts)
print("                        visco bdry       quadrature:", VB_stage2.n_pts)
print("                        fault            quadrature:", fault_stage2.n_pts)
print("number of                         expansion centers:", expansions.N)
```

```{code-cell} ipython3
%matplotlib inline
plt.figure()
plt.plot(fault.pts[:, 0], fault.pts[:, 1], "r-o")
plt.plot(fault_stage2.pts[:, 0], fault_stage2.pts[:, 1], "r*")
plt.plot(free_stage2.pts[:, 0], free_stage2.pts[:, 1], "k-o")
plt.plot(VB_stage2.pts[:, 0], VB_stage2.pts[:, 1], "k-o")
plt.plot(expansions.pts[:, 0], expansions.pts[:, 1], "bo")
for i in range(expansions.N):
    plt.gca().add_patch(
        plt.Circle(expansions.pts[i], expansions.r[i], color="b", fill=False)
    )
plt.xlim([-500, 500])
plt.ylim([-20250, -19750])
plt.show()
```

```{code-cell} ipython3
free_disp_to_free_disp = apply_interp_mat(
    qbx_matrix(double_layer_matrix, free_stage2, free.pts, expansions)[:, 0, :],
    free_interp_mat,
)
```

```{code-cell} ipython3
fault_slip_to_free_disp = -apply_interp_mat(
    qbx_matrix(double_layer_matrix, fault_stage2, free.pts, expansions)[:, 0, :],
    fault_interp_mat,
)
```

```{code-cell} ipython3
free_disp_solve_mat = np.eye(free_disp_to_free_disp.shape[0]) + free_disp_to_free_disp
free_disp_solve_mat_inv = np.linalg.inv(free_disp_solve_mat)

slip = np.ones(fault.n_pts)
free_disp = free_disp_solve_mat_inv.dot(fault_slip_to_free_disp.dot(slip))

# Note that the analytical solution is slightly different than in the buried
# fault setting because we need to take the limit of an arctan as the
# denominator of the argument  goes to zero.
s = 1.0
analytical_fnc = lambda x: -np.arctan(-fault_bottom / x) / np.pi
analytical = analytical_fnc(free.pts[:, 0])
```

```{code-cell} ipython3
for XV in [50000.0]:
    # XV = 5 * corner_resolution
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(free.pts[:, 0], free_disp, "ko")
    plt.plot(free.pts[:, 0], analytical, "bo")
    plt.xlabel("$x$")
    plt.ylabel("$u_z$")
    plt.title("Displacement")
    plt.xlim([-XV, XV])
    plt.ylim([-0.6, 0.6])

    plt.subplot(1, 2, 2)
    plt.plot(free.pts[:, 0], np.log10(np.abs(free_disp - analytical)))
    plt.xlabel("$x$")
    plt.ylabel(r"$\log_{10}|u_{\textrm{BIE}} - u_{\textrm{analytic}}|$")
    plt.title("Error (number of digits of accuracy)")
    plt.tight_layout()
    plt.xlim([-XV, XV])
    plt.show()
```

```{code-cell} ipython3
from math import factorial

def Fn(n, x, D, H):
    return np.arctan(2 * x * D / (x ** 2 + (2 * n * H) ** 2 - D ** 2))


def analytic_to_surface(slip, D, H, x, t):
    t_R = viscosity / shear_modulus
    C = slip / np.pi
    T1 = np.arctan(D / x)
    T2 = 0
    for n in range(1, 50):
        m_factor = 0
        for m in range(1, n + 1):
            m_factor += ((t / t_R) ** (n - m)) / factorial(n - m)
        n_factor = 1 - np.exp(-t / t_R) * m_factor
        T2 += n_factor * Fn(n, x, D, H)
    return C * (T1 + T2)


def analytic_soln(x, t):
    return analytic_to_surface(1.0, fault_bottom, visco_depth, x, t)

siay = 31556952
plt.figure(figsize=(6, 6))
for t in [0, 10.0 * siay, 20.0 * siay, 100.0 * siay]:
    plt.plot(
        free.pts[:, 0] / 1000.0,
        analytic_soln(free.pts[:, 0], t),
        label=f"{t/siay:.0f} years",
    )
plt.xlim([-100, 100])
plt.legend()
plt.show()
```

```{code-cell} ipython3
import_and_display_fnc("common", "single_layer_matrix")
import_and_display_fnc("common", "adjoint_double_layer_matrix")
```

```{code-cell} ipython3
# TODO: I NEED TO ENSURE THAT ALL THE EXPANSIONS THAT GET USED ARE ON THE SAME SIDE OF THE SOURCE SURFACE
free_expansions = expansions#qbx_panel_setup([free], directions=[1])
VB_expansions = expansions#qbx_panel_setup([VB], directions=[1])
```

```{code-cell} ipython3
free_disp_to_VB_syz = shear_modulus * apply_interp_mat(
    qbx_matrix(hypersingular_matrix, free_stage2, VB.pts, VB_expansions)[:, 1, :],
    free_interp_mat,
)
fault_slip_to_VB_syz = shear_modulus * apply_interp_mat(
    qbx_matrix(hypersingular_matrix, fault_stage2, VB.pts, VB_expansions)[:, 1, :],
    fault_interp_mat,
)
VB_S_to_VB_syz = apply_interp_mat(
    qbx_matrix(adjoint_double_layer_matrix, VB_stage2, VB.pts, VB_expansions)[:, 1, :],
    VB_interp_mat,
)

VB_S_to_free_disp = (1.0 / shear_modulus) * apply_interp_mat(
    qbx_matrix(single_layer_matrix, VB_stage2, free.pts, free_expansions)[:, 0, :],
    VB_interp_mat,
)
```

```{code-cell} ipython3
%%time
# The slip does not change so these two integral terms can remain
# outside the time stepping loop.
syz_fault = fault_slip_to_VB_syz.dot(slip)
rhs_slip = fault_slip_to_free_disp.dot(slip)

dt = 0.01 * siay
stress_integral = np.zeros(VB.n_pts)
t = 0
t_history = []
disp_history = []
S_history = []
for i in range(5001):
    # Step 1) Solve for free surface displacement.
    rhs = rhs_slip + VB_S_to_free_disp.dot(stress_integral)
    free_disp = free_disp_solve_mat_inv.dot(rhs)
    
    t_history.append(t)
    disp_history.append(free_disp)
    S_history.append(stress_integral.copy())

    # Step 2): Calculate viscoelastic boundary stress yz component and then d[S]/dt
    syz_free = free_disp_to_VB_syz.dot(free_disp)
    syz_VB = VB_S_to_VB_syz.dot(stress_integral)
    syz_full = syz_free + syz_fault + syz_VB
    dSdt = (shear_modulus / viscosity) * syz_full

    # Step 3): Update S, simple forward Euler time step.
    stress_integral -= 2 * dSdt * dt
    t += dt
t_history = np.array(t_history)
```

```{code-cell} ipython3
plt.figure(figsize=(14, 7))
X = free.pts[:, 0] / 1000

plt.subplot(1, 2, 1)
plt.plot(X, disp_history[0], "k-", linewidth=3, label="elastic")
steps_to_plt = [("m", 500, 5), ("b", 1000, 10), ("r", 2500, 25)]
for color, i, yr in steps_to_plt:
    plt.plot(X, disp_history[i], color + "-", label=str(yr) + " yrs")
    plt.plot(X, analytic_soln(free.pts[:, 0], t_history[i]), color + "-.")
plt.plot([], [], " ", label="BIE = solid")
plt.xlim([-100, 100])
plt.xlabel(r"$x ~ \mathrm{(km)}$")
plt.ylabel(r"$u ~ \mathrm{(m)}$")
plt.legend()

plt.subplot(1, 2, 2)
for color, i, yr in [("k", 0, 0)] + steps_to_plt:
    analytic = analytic_soln(free.pts[:, 0], t_history[i])
    numerical = disp_history[i]
    diff = analytic - numerical
    plt.plot(X, np.log10(np.abs(diff)), color + "-.")
plt.xlim([-100, 100])
plt.xlabel(r"$x ~ \mathrm{(km)}$")
plt.ylabel(r"$\log_{10}{|u_{\textrm{analytic}} - u|} ~ \mathrm{(m)}$")
plt.show()
```

```{code-cell} ipython3
velocity = siay * np.diff(np.array(disp_history), axis=0) / np.diff(t_history)[:, None]
plt.plot(t_history[1:] / siay, np.log10(np.max(np.abs(velocity), axis=1)))
plt.xlabel(r'$t ~ (\textrm{yr})$')
plt.ylabel(r'$\log_{10}(\textrm{max velocity in m/yr})$')
plt.show()
```

# EXTRA

```{code-cell} ipython3
nobs = 150
zoomx = [-15000, 15000]
zoomy = [-31000, -1000]
xs = np.linspace(*zoomx, nobs)
ys = np.linspace(*zoomy, nobs)
obs_pts = pts_grid(xs, ys)
obsx = obs_pts[:, 0].reshape((nobs, nobs))
obsy = obs_pts[:, 1].reshape((nobs, nobs))
```

```{code-cell} ipython3
free_disp_to_volume_disp = apply_interp_mat(
    qbx_matrix(double_layer_matrix, free_stage2, obs_pts, expansions), free_interp_mat
)
fault_slip_to_volume_disp = qbx_matrix(double_layer_matrix, fault_stage2, obs_pts, expansions)
VB_S_to_volume_disp = (1.0 / shear_modulus) * apply_interp_mat(
    qbx_matrix(single_layer_matrix, VB_stage2, obs_pts, expansions), VB_interp_mat
)

free_disp_to_volume_stress = shear_modulus * apply_interp_mat(
    qbx_matrix(hypersingular_matrix, free_stage2, obs_pts, expansions), free_interp_mat
)
fault_slip_to_volume_stress = shear_modulus * qbx_matrix(hypersingular_matrix, fault_stage2, obs_pts, expansions)
VB_S_to_volume_stress = apply_interp_mat(
    qbx_matrix(adjoint_double_layer_matrix, VB_stage2, obs_pts, expansions),
    VB_interp_mat,
)


def get_volumetric_disp(free_disp, slip, stress_integral):
    disp_free = free_disp_to_volume_disp.dot(free_disp)
    disp_fault = fault_slip_to_volume_disp.dot(slip)
    disp_VB = VB_S_to_volume_disp.dot(stress_integral)
    return (disp_free + disp_fault + disp_VB).reshape(obsx.shape)


def get_volumetric_stress(free_disp, slip, stress_integral):
    stress_free = free_disp_to_volume_stress.dot(free_disp)
    stress_fault = fault_slip_to_volume_stress.dot(slip)
    stress_VB = VB_S_to_volume_stress.dot(stress_integral)

    return (stress_free + stress_fault + stress_VB).reshape((*obsx.shape, 2))


def simple_plot(field, levels):
    n_dims = field.shape[2]
    plt.figure(figsize=(4 * n_dims, 4))
    for d in range(field.shape[2]):
        plt.subplot(1, n_dims, 1 + d)
        cntf = plt.contourf(
            obsx, obsy, field[:, :, d], levels=levels, extend="both", cmap="RdBu_r"
        )
        plt.contour(
            obsx,
            obsy,
            field[:, :, d],
            colors="k",
            linestyles="-",
            linewidths=0.5,
            levels=levels,
            extend="both",
        )
        plt.plot(free.pts[:, 0], free.pts[:, 1], "k-", linewidth=1.5)
        plt.plot(fault.pts[:, 0], fault.pts[:, 1], "k-", linewidth=1.5)
        plt.colorbar(cntf)
        plt.xlim(zoomx)
        plt.ylim(zoomy)
    plt.tight_layout()
    plt.show()
```

```{code-cell} ipython3
# slip_tapered = 1.0 + np.cos(
#     np.pi * (np.minimum(fault_stage2.pts[:, 1], -5000) + 5000) / 10000
# )  # np.minimum(np.ones_like(slip), np.exp(0.01 * (fault.pts[:,1] + 10000)))
slip_tapered = 1.0 / (1 + np.exp(-(fault_stage2.pts[:, 1] + 11000) / 1000.0))
plt.plot(fault_stage2.pts[:, 1], slip_tapered, 'b-*')
plt.show()
```

```{code-cell} ipython3
for terms in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
    disp = get_volumetric_disp(
        terms[0] * free_disp, terms[1] * slip_tapered, terms[2] * stress_integral
    )
    simple_plot(disp[:, :, None], None)
```

```{code-cell} ipython3
for terms in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
    stress = get_volumetric_stress(
        terms[0] * free_disp, terms[1] * slip_tapered, terms[2] * stress_integral
    )
    levels = np.linspace(-1e6, 1e6, 21)
    simple_plot(stress, levels)
```