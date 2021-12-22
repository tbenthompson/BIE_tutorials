---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

```{code-cell} ipython3
:tags: [remove-cell]

from tectosaur2.nb_config import setup

setup()
```

```{code-cell} ipython3
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
from tectosaur2 import gauss_rule, refine_surfaces, integrate_term
from tectosaur2.laplace2d import double_layer, hypersingular
from tectosaur2.mesh import panelize_symbolic_surface, concat_meshes
```

```{code-cell} ipython3
shear_modulus = 3.2e10

qx, qw = gauss_rule(5)
t = sp.var("t")

fault_bottom = 40000
n_fault_panels = 200
edges = np.linspace(-1, 1, n_fault_panels + 1)
panel_bounds = np.stack((edges[:-1],edges[1:]), axis=1)
fault1 = panelize_symbolic_surface(
    t, -5000 + t * 0, fault_bottom * (t + 1) * -0.5,
    panel_bounds,
    qx, qw
)

fault2_x = 5000 + (t * 10000 + 10000) + (t ** 2 * 5000 - 5000)
fault2 = panelize_symbolic_surface(
    t, fault2_x, fault_bottom * (t + 1) * -0.5,
    panel_bounds,
    qx, qw
)
faults = concat_meshes((fault1, fault2))

surf_half_L = 100000
n_free_panels = 200
free_edges = np.linspace(-1, 1, n_free_panels + 1)
free_panel_bounds = np.stack((free_edges[:-1],free_edges[1:]), axis=1)
free = panelize_symbolic_surface(
    t, -t * surf_half_L, 0 * t,
    free_panel_bounds,
    qx, qw,
)
```

```{code-cell} ipython3
print(
    f"The free surface mesh has {free.n_panels} panels with a total of {free.n_pts} points."
)
print(
    f"The fault mesh has {faults.n_panels} panels with a total of {faults.n_pts} points."
)
```

```{code-cell} ipython3
plt.plot(free.pts[:,0]/1000, free.pts[:,1]/1000, 'k-')
plt.plot(fault1.pts[:,0]/1000, fault1.pts[:,1]/1000, 'r-')
plt.plot(fault2.pts[:,0]/1000, fault2.pts[:,1]/1000, 'r-')
plt.xlabel(r'$x ~ \mathrm{(km)}$')
plt.ylabel(r'$y ~ \mathrm{(km)}$')
plt.axis('scaled')
plt.xlim([-100, 100])
plt.ylim([-80, 20])
plt.show()
```

And, to start off the integration, we'll construct the operators necessary for solving for free surface displacement from fault slip.

```{code-cell} ipython3
singularities = np.array(
    [
        [-surf_half_L, 0],
        [surf_half_L, 0],
        [5000, 0],
        [-5000, 0]
    ]
)

(free_disp_to_free_disp, fault_slip_to_free_disp), report = integrate_term(
    double_layer, free.pts, free, faults, tol=1e-11, singularities=singularities, return_report=True
)
fault_slip_to_free_disp = fault_slip_to_free_disp[:, 0, :, 0]
free_disp_solve_mat = (
    np.eye(free_disp_to_free_disp.shape[0]) + free_disp_to_free_disp[:, 0, :, 0]
)
```

```{code-cell} ipython3
(free_disp_to_fault_stress, fault_slip_to_fault_stress), report = integrate_term(
    hypersingular,
    faults.pts,
    free,
    faults,
    tol=1e-10,
    singularities=singularities,
    return_report=True,
)
fault_slip_to_fault_stress *= shear_modulus
free_disp_to_fault_stress *= shear_modulus

fault_slip_to_fault_traction = np.sum(
    fault_slip_to_fault_stress[:,:,:,0] * faults.normals[:, :, None], axis=1
)
free_disp_to_fault_traction = np.sum(
    free_disp_to_fault_stress[:,:,:,0] * faults.normals[:, :, None], axis=1
)
```

```{code-cell} ipython3
A = -fault_slip_to_fault_traction
B = -free_disp_to_fault_traction
C = fault_slip_to_free_disp
Dinv = np.linalg.inv(free_disp_solve_mat)

total_fault_slip_to_fault_traction = A - B.dot(Dinv.dot(C))
```

I'll just do a quick check to confirm that this operator is accurate:

```{code-cell} ipython3
analytical_sd = -np.arctan(-fault_bottom / free.pts[:,0]) / np.pi
numerical_sd = Dinv.dot(-C).sum(axis=1)
rp = (faults.pts[:,1] + 1) ** 2
analytical_ft = -(shear_modulus / (2 * np.pi)) * ((1.0 / (faults.pts[:,1] + fault_bottom)) - (1.0 / (faults.pts[:,1] - fault_bottom)))
numerical_ft = total_fault_slip_to_fault_traction.sum(axis=1)
plt.figure(figsize=(10,5))
plt.subplot(1,2,1)
plt.title('Stress')
plt.plot(faults.pts[:,1], np.log10(np.abs(numerical_ft)), 'b-')
plt.xlim([-fault_bottom, 0])
plt.xlabel('$\mathrm{depth ~~ (m)}$')
plt.ylabel('$t$')
plt.subplot(1,2,2)
plt.title('Displacement')
plt.plot(free.pts[:,0], numerical_sd, 'b-')
plt.xlim([-100000, 100000])
plt.xlabel('$x ~~ \mathrm{(m)}$')
plt.ylabel('$u$')
plt.show()
```

## Rate and state friction

+++

Okay, now that we've constructed the necessary boundary integral operators, we get to move on to describing the frictional behavior on the fault.

#### TODO: Explain!!

```{code-cell} ipython3
siay = 31556952 # seconds in a year
density = 2670  # rock density (kg/m^3)
cs = np.sqrt(shear_modulus / density)  # Shear wave speed (m/s)
eta = shear_modulus / (2 * cs)  # The radiation damping coefficient (kg / (m^2 * s))
Vp = 1e-9  # Rate of plate motion
sigma_n = 50e6  # Normal stress (Pa)

# parameters describing "a", the coefficient of the direct velocity strengthening effect
a0 = 0.01
amax = 0.025
fy = faults.pts[:, 1]
H = 15000
h = 3000
fp_a = np.where(
    fy > -H, a0, np.where(fy > -(H + h), a0 + (amax - a0) * (fy + H) / -h, amax)
)

# state-based velocity weakening effect
fp_b = 0.015

# state evolution length scale (m)
fp_Dc = 0.008

# baseline coefficient of friction
fp_f0 = 0.6

# if V = V0 and at steady state, then f = f0, units are m/s
fp_V0 = 1e-6
```

```{code-cell} ipython3
plt.figure(figsize=(3, 5))
plt.plot(fp_a, fy/1000, label='a')
plt.plot(np.full(fy.shape[0], fp_b), fy/1000, label='b')
plt.xlim([0, 0.03])
plt.ylabel('depth')
plt.legend()
plt.show()
```

First, a Python implementation of the quasidynamic shear stress equations. There are two components to a standard definition of rate and state friction:

\begin{align}
\tau_{qd} = F(V, \theta)\\
\frac{d\theta}{dt} = G(V, \theta)
\end{align}

where $F(V, \theta)$ is the strength of friction, depending on slip rate and state and $G(V, \theta)$ gives the state evolution. For $G$, we will use the aging law, given by the `aging_law` function below.

We also need to relate the quasidynamic shear stress to the quasistatic shear stress:
\begin{equation}
\tau_{qd} = \tau_{qs} - \eta * V
\end{equation}
which results in the full quasidynamic stress balance equation:
\begin{equation}
\tau_{qs} - \eta * V - F(V, \theta) = 0
\end{equation}
The specific form we use here is  implemented below in the `qd_equation` function.

At each time step, we'll need to compute the velocity, $V$ and the state derivative $d\theta/dt$. Computing the state derivative is easy because it's directly given by the aging law. But, computing the velocity is harder because its only given implicitly in the frictional strength equation. The `solve_friction` function below implements Newton's method with a backtracking line search to solve the friction equation for the current velocity. The `qd_equation_dV` function implements the derivative of the stress balance with respect to velocity. This derivative is necessary for Newton's method.

```{code-cell} ipython3
# The regularized form of the aging law.
def aging_law(fp_a, V, state):
    return (fp_b * fp_V0 / fp_Dc) * (np.exp((fp_f0 - state) / fp_b) - (V / fp_V0))

def qd_equation(fp_a, shear_stress, V, state):
    # The regularized rate and state friction equation
    F = sigma_n * fp_a * np.arcsinh(V / (2 * fp_V0) * np.exp(state / fp_a))

    # The full shear stress balance:
    return shear_stress - eta * V - F

def qd_equation_dV(fp_a, V, state):
    # First calculate the derivative of the friction law with respect to velocity
    # This is helpful for equation solving using Newton's method
    expsa = np.exp(state / fp_a)
    Q = (V * expsa) / (2 * fp_V0)
    dFdV = fp_a * expsa * sigma_n / (2 * fp_V0 * np.sqrt(1 + Q * Q))

    # The derivative of the full shear stress balance.
    return -eta - dFdV


def solve_friction(fp_a, shear, V_old, state, tol=1e-10):
    V = V_old
    max_iter = 150
    for i in range(max_iter):
        # Newton's method step!
        f = qd_equation(fp_a, shear, V, state)
        dfdv = qd_equation_dV(fp_a, V, state)
        step = f / dfdv

        # We know that slip velocity should not be negative so any step that
        # would lead to negative slip velocities is "bad". In those cases, we
        # cut the step size in half iteratively until the step is no longer
        # bad. This is a backtracking line search.
        while True:
            bad = step > V
            if np.any(bad):
                step[bad] *= 0.5
            else:
                break

        # Take the step and check if everything has converged.
        Vn = V - step
        if np.max(np.abs(step) / Vn) < tol:
            break
        V = Vn
        if i == max_iter - 1:
            raise Exception("Failed to converge.")

    # Return the solution and the number of iterations required.
    return Vn, i
```

We'll also check $h^*$ which is the minimum length scale of an instability and $L_b$, the length scale of the rupture process zone. Both these length scales need to be well resolved by the fault discretization. Here we have approximately eight point within the process zone and almost 80 points within $h^*$.

```{code-cell} ipython3
for fm in [fault1, fault2]:
    mesh_L = np.max(np.abs(np.diff(fm.pts[:, 1])))
    Lb = shear_modulus * fp_Dc / (sigma_n * fp_b)
    hstar = (np.pi * shear_modulus * fp_Dc) / (sigma_n * (fp_b - fp_a))
    print(mesh_L, Lb, np.min(hstar[hstar > 0]))
```

## Quasidynamic earthquake cycle derivatives

+++

Let's set of the last few pieces to do a full earthquake cycle simulation:
- initial conditions.
- a function to put the pieces together and calculate the full system state at each time step, including the time derivatives of slip and frictional state.
- the time stepping algorithm itself.

First, **initial conditions**. This initial state is exactly as specified in the BP-1 description linked at the top:
1. We solve for the steady frictional state at each point using `scipy.optimize.fsolve`. This is the initial state.
2. We identify the value of shear stress that will result in steady plate rate slip rates in the deeper portions of the fault: `tau_amax`. This is the initial shear stress.
3. The initial slip deficit is zero.

```{code-cell} ipython3
from scipy.optimize import fsolve
import copy

init_state_scalar = fsolve(lambda S: aging_law(fp_a, Vp, S), 0.7)[0]
init_state = np.full(faults.n_pts, init_state_scalar)
tau_amax = -qd_equation(amax, 0, Vp, init_state_scalar)

init_traction = np.full(faults.n_pts, tau_amax)
init_slip_deficit = np.zeros(faults.n_pts)
init_conditions = np.concatenate((init_slip_deficit, init_state))
```

Next, solving for system state. This ties the pieces together by:
1. Solving for the quasistatic shear stress using the boundary integral matrices derived at the beginning of this notebook.
2. Solving the rate and state friction equations for the slip rate.
3. Calculating the state evolution using the aging law.

The middle lines of `SystemState.calc` do these three steps. There's a bunch of other code surrounding those three lines in order to deal with invalid inputs and transform from slip to slip deficit.

```{code-cell} ipython3
class SystemState:

    V_old = np.full(faults.n_pts, Vp)
    state = None

    def calc(self, t, y, verbose=False):
        # Separate the slip_deficit and state sub components of the
        # time integration state.
        slip_deficit = y[: init_slip_deficit.shape[0]]
        state = y[init_slip_deficit.shape[0] :]

        # If the state values are bad, then the adaptive integrator probably
        # took a bad step.
        if np.any((state < 0) | (state > 2.0)):
            return False

        # The big three lines solving for quasistatic shear stress, slip rate
        # and state evolution
        tau_qs = init_traction - total_fault_slip_to_fault_traction.dot(slip_deficit)
        V = solve_friction(fp_a, tau_qs, self.V_old, state)[0]
        dstatedt = aging_law(fp_a, V, state)
        if not np.all(np.isfinite(V)):
            return False
        self.V_old = V

        slip_deficit_rate = Vp - V
        out = slip_deficit, state, tau_qs, V, slip_deficit_rate, dstatedt
        self.state = out
        return self.state


def plot_system_state(SS):
    """This is just a helper function that creates some rough plots of the
    current state to help with debugging"""
    slip_deficit, state, tau_qs, slip_deficit_rate, dstatedt = SS

    plt.figure(figsize=(15, 9))
    plt.subplot(2, 3, 1)
    plt.title("slip")
    plt.plot(faults.pts[:, 1], slip_deficit)

    plt.subplot(2, 3, 2)
    plt.title("state")
    plt.plot(faults.pts[:, 1], state)

    plt.subplot(2, 3, 3)
    plt.title("tau qs")
    plt.plot(faults.pts[:, 1], tau_qs)

    plt.subplot(2, 3, 4)
    plt.title("slip rate")
    plt.plot(faults.pts[:, 1], slip_deficit_rate)

    plt.subplot(2, 3, 6)
    plt.title("dstatedt")
    plt.plot(faults.pts[:, 1], dstatedt)
    plt.tight_layout()

    plt.show()


def calc_derivatives(state, t, y):
    """
    This helper function calculates the system state and then extracts the
    relevant derivatives that the integrator needs. It also intentionally
    returns infinite derivatives when the `y` vector provided by the integrator
    is invalid.
    """
    if not np.all(np.isfinite(y)):
        return np.inf * y
    state = state.calc(t, y)
    if not state:
        return np.inf * y
    derivatives = np.concatenate((state[-2], state[-1]))
    return derivatives
```

## Integrating through time

```{code-cell} ipython3
%%time
from scipy.integrate import RK45

# We use a 5th order adaptive Runge Kutta method and pass the derivative function to it
# the relative tolerance will be 1e-11 to make sure that even
state = SystemState()
derivs = lambda t, y: calc_derivatives(state, t, y)
integrator = RK45
atol = Vp * 1e-6
rtol = 1e-11
rk = integrator(derivs, 0, init_conditions, 1e50, atol=atol, rtol=rtol)

# Set the initial time step to one day.
rk.h_abs = 60 * 60 * 24

# Integrate for 1000 years.
max_T = 300 * siay

n_steps = 1000000
t_history = [0]
y_history = [init_conditions.copy()]
for i in range(n_steps):

    # Take a time step and store the result
    if rk.step() != None:
        raise Exception("TIME STEPPING FAILED")
        break
    t_history.append(rk.t)
    y_history.append(rk.y.copy())

    # Print the time every 5000 steps
    if i % 1000 == 0:
        print(f"step={i}, time={rk.t / siay} yrs, step={(rk.t - t_history[-2]) / siay}")
    if rk.t > max_T:
        break

y_history = np.array(y_history)
t_history = np.array(t_history)
```

## Plotting the results

+++

Now that we've solved for 1000 years of fault slip evolution, let's plot some of the results. I'll start with a super simple plot of the maximum log slip rate over time.

```{code-cell} ipython3
derivs_history = np.diff(y_history, axis=0) / np.diff(t_history)[:, None]
max_vel = np.max(np.abs(derivs_history), axis=1)
plt.plot(t_history[1:] / siay, np.log10(max_vel))
plt.xlabel('$t ~~ \mathrm{(yrs)}$')
plt.ylabel('$\log_{10}(V)$')
plt.show()
```

And next, we'll make the classic plot showing the spatial distribution of slip over time:
- the blue lines show interseismic slip evolution and are plotted every fifteen years
- the red lines show evolution during rupture every three seconds.

```{code-cell} ipython3
for j in range(2):
    fm = fault1 if j == 0 else fault2
    plt.figure(figsize=(10, 4))
    last_plt_t = -1000
    last_plt_slip = init_slip_deficit
    event_times = []
    for i in range(len(y_history) - 1):
        y = y_history[i]
        t = t_history[i]
        slip_deficit_full = y[: init_slip_deficit.shape[0]]
        fault1_sd = slip_deficit_full[:fault1.n_pts]
        fault2_sd = slip_deficit_full[fault1.n_pts:]
        slip_deficit = fault1_sd if j == 0 else fault2_sd
        should_plot = False

        # Plot a red line every three second if the slip rate is over 0.1 mm/s.
        if (
            max_vel[i] >= 0.0001 and t - last_plt_t > 3
        ):
            if len(event_times) == 0 or t - event_times[-1] > siay:
                event_times.append(t)
            should_plot = True
            color = "r"

        # Plot a blue line every fifteen years during the interseismic period
        if t - last_plt_t > 15 * siay:
            should_plot = True
            color = "b"

        if should_plot:
            # Convert from slip deficit to slip:
            slip = -slip_deficit + Vp * t
            plt.plot(slip, fm.pts[:,1] / 1000.0, color + "-", linewidth=0.5)
            last_plt_t = t
            last_plt_slip = slip
    plt.xlim([0, np.max(last_plt_slip)])
    plt.ylim([-40, 0])
    plt.ylabel(r"$\textrm{z (km)}$")
    plt.xlabel(r"$\textrm{slip (m)}$")
    plt.tight_layout()
    plt.savefig("halfspace.png", dpi=300)
    plt.show()
```