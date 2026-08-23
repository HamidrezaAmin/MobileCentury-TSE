"""Data loading and grid construction for the Mobile Century TSE project."""

import numpy as np
import pandas as pd


def load_trip(path, direction):
    """Load one trip file (a single directional pass by one vehicle)."""
    df = pd.read_csv(path, skipinitialspace=True)
    df = df.rename(columns={"unix time": "unixtime"})
    df["postmile_abs"] = df["postmile"].abs()
    # Prefix with direction: both folders contain a file named veh_1.csv.
    df["trip_id"] = f"{direction}_{path.stem}"
    df["direction"] = direction
    return df


def load_all_trips(folder, direction):
    """Load every trip file in a folder into one DataFrame."""
    frames = [load_trip(f, direction) for f in sorted(folder.glob("*.csv"))]
    return pd.concat(frames, ignore_index=True)


def add_time_axis(df, t0=None):
    """Add hours_elapsed relative to t0 (defaults to the earliest timestamp)."""
    if t0 is None:
        t0 = df["unixtime"].min()
    df = df.copy()
    df["hours_elapsed"] = (df["unixtime"] - t0) / 3600.0
    return df, t0


def make_grid(pm_min, pm_max, t_max, dt_min=1.0, dx_mile=0.1):
    """
    Build space-time grid edges and centers.

    Returns (t_edges, x_edges, t_centers, x_centers). Estimation happens at
    cell centers; edges define the bin boundaries.
    """
    t_edges = np.arange(0, t_max + dt_min / 60, dt_min / 60)
    x_edges = np.arange(pm_min, pm_max + dx_mile, dx_mile)
    t_centers = (t_edges[:-1] + t_edges[1:]) / 2
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    return t_edges, x_edges, t_centers, x_centers


def build_field(df, t_edges, x_edges, value_col="speed"):
    """
    Aggregate observations into a (space, time) mean-value grid.

    Cells with no observations are NaN -- deliberately NOT interpolated, so
    that missing data stays visible rather than being silently invented.
    Returns (field, counts).
    """
    sums, _, _ = np.histogram2d(
        df["postmile_abs"], df["hours_elapsed"],
        bins=[x_edges, t_edges], weights=df[value_col],
    )
    counts, _, _ = np.histogram2d(
        df["postmile_abs"], df["hours_elapsed"], bins=[x_edges, t_edges]
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        field = np.where(counts > 0, sums / counts, np.nan)
    return field, counts


def subsample_trips(df, rate, seed=0):
    """
    Keep a random fraction of TRIPS (not rows).

    Sampling whole trips simulates lower probe penetration honestly: a real
    deployment has a fraction of VEHICLES reporting, each sending its full
    trajectory. Dropping individual rows would simulate a lossy sensor
    instead, leaving every trip partially visible -- a much easier problem.
    """
    trips = df["trip_id"].unique()
    rng = np.random.default_rng(seed)
    n = max(1, int(len(trips) * rate))
    chosen = rng.choice(trips, size=n, replace=False)
    return df[df["trip_id"].isin(chosen)]
