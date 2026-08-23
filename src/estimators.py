"""Traffic state estimators."""

import numpy as np

# Default ASM parameters (Treiber & Helbing 2002).
# Units: speeds in mph, sigma in miles, tau in hours.
ASM_DEFAULTS = dict(
    c_free=50.0,      # downstream propagation speed in free flow
    c_cong=-12.0,     # upstream propagation speed in congestion (negative)
    sigma=0.3,        # spatial smoothing width, miles
    tau=3.0 / 60,     # temporal smoothing width, hours (3 minutes)
    v_thresh=37.0,    # midpoint of free/congested transition
    delta_v=12.0,     # width of that transition
)


def _smooth_along(obs_speed, obs_t, obs_x, grid_t, grid_x, c_prop, sigma, tau):
    """
    Smooth scattered observations onto a grid along one characteristic speed.

    The kernel is TILTED in the time-space plane: an observation dx miles
    away counts as contemporary if it occurred dx/c_prop hours offset from
    now, because that is how fast information physically travels.
    """
    out = np.full((len(grid_x), len(grid_t)), np.nan)
    for i, x in enumerate(grid_x):
        dx = obs_x - x
        for j, t in enumerate(grid_t):
            dt_shifted = (obs_t - t) - dx / c_prop
            w = np.exp(-(dx ** 2) / (2 * sigma ** 2)
                       - (dt_shifted ** 2) / (2 * tau ** 2))
            m = w > 1e-4              # drop negligible weights
            if m.any() and w[m].sum() > 0:
                out[i, j] = (w[m] * obs_speed[m]).sum() / w[m].sum()
    return out


def asm_estimate(obs_speed, obs_t, obs_x, grid_t, grid_x, **params):
    """
    Adaptive Smoothing Method (Treiber & Helbing 2002).

    Smooths twice -- once along free-flow characteristics, once along
    congested ones -- then blends the two based on how congested the local
    estimate is. Returns a (space, time) array of estimated speeds.
    """
    p = {**ASM_DEFAULTS, **params}

    v_free = _smooth_along(obs_speed, obs_t, obs_x, grid_t, grid_x,
                           p["c_free"], p["sigma"], p["tau"])
    v_cong = _smooth_along(obs_speed, obs_t, obs_x, grid_t, grid_x,
                           p["c_cong"], p["sigma"], p["tau"])

    # Use the slower of the two to judge congestion; tanh gives a smooth
    # 0-to-1 blend weight. w near 1 -> congested -> trust v_cong.
    v_min = np.fmin(v_free, v_cong)
    w = 0.5 * (1 + np.tanh((p["v_thresh"] - v_min) / p["delta_v"]))
    return w * v_cong + (1 - w) * v_free
