"""Error metrics and validation for traffic state estimates."""

import numpy as np
import pandas as pd

# Regime boundaries in mph. Congested / transition / free-flow.
REGIMES = [("congested", -np.inf, 30.0),
           ("transition", 30.0, 50.0),
           ("free_flow", 50.0, np.inf)]


def compare_fields(estimate, truth):
    """
    Compare two (space, time) arrays on cells where BOTH are finite.

    Convention: bias = estimate - truth, so positive means the estimate
    reads high. Returns a dict of metrics including n, so a silently
    shrinking comparison set is visible.
    """
    m = np.isfinite(estimate) & np.isfinite(truth)
    if not m.any():
        return {"n": 0, "mae": np.nan, "rmse": np.nan,
                "bias": np.nan, "corr": np.nan}
    d = estimate[m] - truth[m]
    return {
        "n": int(m.sum()),
        "mae": float(np.abs(d).mean()),
        "rmse": float(np.sqrt((d ** 2).mean())),
        "bias": float(d.mean()),
        "corr": float(np.corrcoef(estimate[m], truth[m])[0, 1]),
    }


def compare_by_regime(estimate, truth, regime_source=None):
    """
    Compare fields separately within each speed regime.

    regime_source: the array used to CLASSIFY cells into regimes. Defaults
    to truth. Pass an independent field when you want the binning itself to
    be independent of the data being scored -- otherwise the regime
    definition is self-referential.

    Returns a DataFrame, one row per regime.
    """
    if regime_source is None:
        regime_source = truth

    m = np.isfinite(estimate) & np.isfinite(truth) & np.isfinite(regime_source)
    est, tru, src = estimate[m], truth[m], regime_source[m]
    d = est - tru

    rows = []
    for name, lo, hi in REGIMES:
        sel = (src >= lo) & (src < hi)
        if sel.sum() == 0:
            continue
        rows.append({
            "regime": name,
            "n": int(sel.sum()),
            "mae": float(np.abs(d[sel]).mean()),
            "rmse": float(np.sqrt((d[sel] ** 2).mean())),
            "bias": float(d[sel].mean()),
        })
    return pd.DataFrame(rows)


def sample_field_at(field, t_edges, x_edges, times, positions):
    """
    Look up field values at scattered (time, position) points.

    Used to compare a gridded estimate against point measurements such as
    loop detectors. Points outside the grid return NaN rather than raising,
    so a partially-overlapping sensor set still works.
    """
    t_idx = np.digitize(times, t_edges) - 1
    x_idx = np.digitize(positions, x_edges) - 1
    ok = ((t_idx >= 0) & (t_idx < field.shape[1])
          & (x_idx >= 0) & (x_idx < field.shape[0]))
    out = np.full(len(times), np.nan)
    out[ok] = field[x_idx[ok], t_idx[ok]]
    return out
