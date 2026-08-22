"""
Mission Profile
-----------------
Defines a "mission" as a power demand curve over time -- the amount of
power (in Watts) the propulsion/electrical system needs at each moment
during a flight or drive.

This is the starting point for sizing: before you can size a fuel cell
stack, hydrogen tank, or battery buffer, you need to know how much power
is needed, and for how long.
"""

import numpy as np
import pandas as pd


def constant_power_mission(duration_hours, power_w, timestep_s=60):
    """
    Simplest mission: constant power draw for the whole duration.
    Useful for a first sizing pass, e.g. cruise-only flight.

    Parameters
    ----------
    duration_hours : float
        Total mission duration in hours.
    power_w : float
        Constant power demand in Watts.
    timestep_s : float
        Time resolution of the profile, in seconds.

    Returns
    -------
    pd.DataFrame with columns: time_s, power_w
    """
    duration_s = duration_hours * 3600
    time_s = np.arange(0, duration_s, timestep_s)
    power = np.full_like(time_s, power_w, dtype=float)
    return pd.DataFrame({"time_s": time_s, "power_w": power})


def multi_phase_mission(phases, timestep_s=60):
    """
    Build a mission profile from multiple phases, e.g. takeoff / climb /
    cruise / descent, each with its own duration and power demand.

    Parameters
    ----------
    phases : list of dict
        Each dict needs: {"name": str, "duration_hours": float, "power_w": float}
        Example:
            [
                {"name": "takeoff", "duration_hours": 0.05, "power_w": 4000},
                {"name": "cruise",  "duration_hours": 2.0,  "power_w": 1200},
                {"name": "landing", "duration_hours": 0.05, "power_w": 3000},
            ]
    timestep_s : float
        Time resolution of the profile, in seconds.

    Returns
    -------
    pd.DataFrame with columns: time_s, power_w, phase
    """
    rows = []
    t_offset = 0.0

    for phase in phases:
        duration_s = phase["duration_hours"] * 3600
        phase_time = np.arange(0, duration_s, timestep_s)
        for t in phase_time:
            rows.append({
                "time_s": t_offset + t,
                "power_w": phase["power_w"],
                "phase": phase["name"],
            })
        t_offset += duration_s

    return pd.DataFrame(rows)


def mission_energy_wh(mission_df):
    """
    Total energy required for the mission, in Watt-hours.
    Uses trapezoidal integration of the power curve over time.
    """
    time_h = mission_df["time_s"] / 3600.0
    # np.trapz was renamed to np.trapezoid in newer numpy versions;
    # this works across both old and new numpy installs.
    trapz_fn = getattr(np, "trapezoid", None) or np.trapz
    energy_wh = trapz_fn(mission_df["power_w"], time_h)
    return energy_wh


def mission_peak_power_w(mission_df):
    """Peak instantaneous power demand -- used for sizing the fuel cell stack's max output."""
    return mission_df["power_w"].max()


if __name__ == "__main__":
    # Real mission profile: Evolonic VTOL UAV fuel cell retrofit thesis
    # Based on measured flight data: 22.2V system, 60A takeoff/landing draw,
    # 10A cruise draw, ~62 min total flight time, 65.69 km distance
    phases = [
        {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},    # 1332 W
        {"name": "cruise", "duration_hours": 59.5 / 60, "power_w": 10 * 22.2},     # 222 W
        {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},   # 611 W (avg of 25-30A)
    ]

    mission = multi_phase_mission(phases)

    print(mission.groupby("phase")["power_w"].agg(["mean", "count"]))
    print(f"\nTotal mission duration: {mission['time_s'].max() / 3600 * 60:.2f} minutes")
    print(f"Total energy required:  {mission_energy_wh(mission):.1f} Wh")
    print(f"Peak power demand:      {mission_peak_power_w(mission):.0f} W")

    mission.to_csv("data/mission_profiles.csv", index=False)
    print("\nSaved mission profile to data/mission_profiles.csv")
