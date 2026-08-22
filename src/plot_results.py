"""
Trade-off Analysis & Plots
-----------------------------
Explores how design choices affect total system mass -- this is the
"so what" of the sizing tool: showing an engineer WHERE the trade-offs
are, not just a single answer.

Two trade-offs explored:
  1. stack_fraction_of_peak -- how much of peak power the fuel cell
     stack covers vs. leaving it to the battery buffer. A bigger stack
     costs more mass upfront but shrinks the battery buffer needed.
  2. Mission duration -- how total system mass scales as mission
     duration (and therefore hydrogen needed) increases. This is where
     hydrogen's mass advantage over pure-battery systems shows up.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w
from fuel_cell_sizing import size_full_system, size_battery_only_system


def sweep_stack_fraction(peak_power_w, total_energy_wh, fractions=None):
    """
    Sweep the stack_fraction_of_peak parameter and record how total
    system mass and its components change.
    """
    if fractions is None:
        fractions = np.linspace(0.2, 1.0, 17)

    rows = []
    for frac in fractions:
        result = size_full_system(peak_power_w, total_energy_wh, stack_fraction_of_peak=frac)
        result["stack_fraction_of_peak"] = frac
        rows.append(result)

    return pd.DataFrame(rows)


def plot_stack_fraction_tradeoff(df, save_path="stack_fraction_tradeoff.png"):
    """Plot how mass splits between fuel cell, battery, and tank as stack sizing changes."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(df["stack_fraction_of_peak"], df["fuel_cell_stack_mass_kg"],
            label="Fuel cell stack mass", marker="o", markersize=3)
    ax.plot(df["stack_fraction_of_peak"], df["battery_mass_kg"],
            label="Battery buffer mass", marker="o", markersize=3)
    ax.plot(df["stack_fraction_of_peak"], df["total_system_mass_kg"],
            label="Total system mass", marker="o", markersize=3, linewidth=2.5, color="black")

    ax.set_xlabel("Fraction of peak power covered by fuel cell stack")
    ax.set_ylabel("Mass (kg)")
    ax.set_title("System Mass Trade-off vs. Fuel Cell Stack Sizing")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot to {save_path}")
    plt.close(fig)

    # report the sizing that minimizes total mass
    best_idx = df["total_system_mass_kg"].idxmin()
    best_frac = df.loc[best_idx, "stack_fraction_of_peak"]
    best_mass = df.loc[best_idx, "total_system_mass_kg"]
    print(f"Lightest total system: {best_mass:.2f} kg at stack_fraction_of_peak = {best_frac:.2f}")


def sweep_mission_duration(cruise_powers_w, cruise_hours_list):
    """
    Sweep cruise duration to see how total system mass scales with
    mission length -- this is where hydrogen's energy density advantage
    over batteries becomes visible for longer missions.
    """
    rows = []
    for hours in cruise_hours_list:
        phases = [
            {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
            {"name": "cruise", "duration_hours": hours, "power_w": cruise_powers_w},
            {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
        ]
        mission = multi_phase_mission(phases)
        peak_power_w = mission_peak_power_w(mission)
        total_energy_wh = mission_energy_wh(mission)

        result = size_full_system(peak_power_w, total_energy_wh)
        battery_only = size_battery_only_system(peak_power_w, total_energy_wh)
        result["battery_only_mass_kg"] = battery_only["battery_only_mass_kg"]
        result["cruise_hours"] = hours
        result["total_mission_hours"] = mission["time_s"].max() / 3600
        rows.append(result)

    return pd.DataFrame(rows)


def plot_duration_tradeoff(df, save_path="duration_tradeoff.png"):
    """Plot how total system mass scales with mission duration."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(df["total_mission_hours"], df["tank_system_mass_kg"],
            label="Hydrogen tank system mass", marker="o", markersize=3)
    ax.plot(df["total_mission_hours"], df["fuel_cell_stack_mass_kg"] + df["battery_mass_kg"],
            label="Fuel cell + battery mass", marker="o", markersize=3)
    ax.plot(df["total_mission_hours"], df["total_system_mass_kg"],
            label="Total system mass (H2)", marker="o", markersize=3, linewidth=2.5, color="black")
    ax.plot(df["total_mission_hours"], df["battery_only_mass_kg"],
            label="Battery-only system mass", marker="s", markersize=3,
            linewidth=2.5, linestyle="--", color="red")

    ax.set_xlabel("Total mission duration (hours)")
    ax.set_ylabel("Mass (kg)")
    ax.set_title("System Mass vs. Mission Duration: Hydrogen Fuel Cell vs. Battery-Only")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot to {save_path}")
    plt.close(fig)


if __name__ == "__main__":
    # Real mission: Evolonic VTOL UAV fuel cell retrofit thesis
    phases = [
        {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
        {"name": "cruise", "duration_hours": 59.5 / 60, "power_w": 10 * 22.2},
        {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
    ]
    mission = multi_phase_mission(phases)
    peak_power_w = mission_peak_power_w(mission)
    total_energy_wh = mission_energy_wh(mission)

    print("=== Sweep 1: Fuel cell stack sizing trade-off ===")
    df_stack = sweep_stack_fraction(peak_power_w, total_energy_wh)
    plot_stack_fraction_tradeoff(df_stack, save_path="notebooks/stack_fraction_tradeoff.png")

    print("\n=== Sweep 2: Mission duration scaling ===")
    # Using the real cruise power (222W = 10A x 22.2V); sweeping cruise duration
    # from 30 min to 4 hours to see how far this system could fly with a bigger tank
    df_duration = sweep_mission_duration(cruise_powers_w=222, cruise_hours_list=np.arange(0.5, 4.5, 0.5))
    plot_duration_tradeoff(df_duration, save_path="notebooks/duration_tradeoff.png")
