"""
Non-Linear Trade-off Approximations
---------------------------------------
plot_results.py's two sweeps are straight lines because every underlying
equation in fuel_cell_sizing.py is a fixed-ratio scaling: constant
specific power, constant specific energy, constant efficiency, constant
gravimetric fraction. None of those depend on HOW HARD a component is
being run, so mass scales perfectly linearly with frac or duration.

This module replaces two of those constants with something closer to
real hardware behaviour, for both sweeps:

  1. Stack-fraction sweep: fuel cell efficiency is modelled as a function
     of load fraction instead of a fixed number. This is an ILLUSTRATIVE
     approximation, not a fitted polarization curve -- the UL500/S800
     datasheets only give a single efficiency figure at rated power, not
     a full current-voltage sweep. The approximation is calibrated so
     that at full load (stack_fraction_of_peak = 1.0) it matches that
     datasheet number, and rises at lower load -- consistent with the
     general shape of PEM polarization curves reported in the
     literature (voltage, and therefore efficiency, falls as current
     rises due to growing ohmic and concentration losses).

  2. Duration sweep: hydrogen tank and battery-only mass are computed
     against REAL discrete components (cylinder_profiles.py,
     battery_profiles.py) instead of the smooth generic gravimetric
     fraction / specific-energy formulas. This produces genuine
     staircase jumps as mission duration grows and another whole
     cylinder or battery cell is needed -- not a fabricated curve, just
     the real component data already in this repo being used here too.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w
from fuel_cell_sizing import (
    size_fuel_cell_stack, size_battery_buffer, size_hydrogen_tank_real, size_full_system,
)
from cylinder_profiles import get_cylinder, h2_capacity_kg
from battery_profiles import get_battery

# Resolve the notebooks/ folder relative to THIS FILE's location on disk,
# not relative to whatever directory the script happens to be launched
# from. "../notebooks/..." (the convention plot_results.py uses) only
# works if you `cd src` first -- running `python src/nonlinear_tradeoffs.py`
# from the repo root breaks it. This works from anywhere.
NOTEBOOKS_DIR = Path(__file__).resolve().parent.parent / "notebooks"
NOTEBOOKS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# 1. Stack-fraction sweep with load-dependent efficiency
# ---------------------------------------------------------------------

def pem_efficiency_approx(load_fraction, eta_rated, low_load_boost=0.12, curve_power=2):
    """
    Approximate PEM fuel cell efficiency as a function of load fraction.

    load_fraction = stack_fraction_of_peak, i.e. how much of the stack's
    own assumed max continuous capability it is being asked to deliver.
    At load_fraction = 1.0 this returns eta_rated (matches the datasheet
    figure at rated power). At lower load it rises smoothly, reflecting
    lower ohmic/concentration losses when the stack isn't being pushed
    hard -- the same qualitative shape as a PEM polarization curve, not
    a fit to actual UL500/S800 test data (which isn't published).
    """
    load_fraction = min(max(load_fraction, 0.0), 1.0)
    return eta_rated + low_load_boost * (1 - load_fraction) ** curve_power


def sweep_stack_fraction_nonlinear(peak_power_w, total_energy_wh, fractions=None,
                                    eta_rated=0.5, low_load_boost=0.12, curve_power=2):
    """Same sweep as plot_results.sweep_stack_fraction(), but with efficiency
    varying by load fraction instead of held constant."""
    if fractions is None:
        fractions = np.linspace(0.2, 1.0, 17)

    rows = []
    for frac in fractions:
        efficiency = pem_efficiency_approx(frac, eta_rated, low_load_boost, curve_power)
        result = size_full_system(peak_power_w, total_energy_wh,
                                   stack_fraction_of_peak=frac, system_efficiency=efficiency)
        result["stack_fraction_of_peak"] = frac
        result["system_efficiency"] = efficiency
        rows.append(result)

    return pd.DataFrame(rows)


def plot_stack_fraction_comparison(df_linear, df_nonlinear,
                                    save_path=None):
    if save_path is None:
        save_path = NOTEBOOKS_DIR / "stack_fraction_nonlinear.png"
    """Overlay the constant-efficiency (linear) and load-dependent-efficiency
    (non-linear) total mass curves, so the divergence is visible directly."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(df_linear["stack_fraction_of_peak"], df_linear["total_system_mass_kg"],
            label="Total mass (constant efficiency -- original)",
            marker="o", markersize=3, linestyle="--", color="gray")
    ax.plot(df_nonlinear["stack_fraction_of_peak"], df_nonlinear["total_system_mass_kg"],
            label="Total mass (load-dependent efficiency -- approximation)",
            marker="o", markersize=3, linewidth=2.5, color="black")

    ax.set_xlabel("Fraction of peak power covered by fuel cell stack")
    ax.set_ylabel("Mass (kg)")
    ax.set_title("System Mass Trade-off: Constant vs. Load-Dependent Efficiency")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot to {save_path}")
    plt.close(fig)


# ---------------------------------------------------------------------
# 2. Duration sweep with real, discrete (stepped) components
# ---------------------------------------------------------------------

def size_battery_only_real(peak_power_w, total_energy_wh, battery_key, depth_of_discharge=0.8):
    """Battery-only system mass using a real, discrete cell count -- same
    method as emergency_battery_sizing.size_emergency_battery_real(), just
    applied to the full mission instead of the failure contingency."""
    battery = get_battery(battery_key)
    usable_energy_wh = total_energy_wh / depth_of_discharge

    num_by_power = math.ceil(peak_power_w / battery["max_continuous_power_w"])
    num_by_energy = math.ceil(usable_energy_wh / (battery["capacity_ah"] * battery["voltage_v"]))
    num_batteries = max(1, num_by_power, num_by_energy)

    return num_batteries * battery["mass_kg"]


def sweep_mission_duration_real(cruise_power_w, cruise_hours_list,
                                 cylinder_key="xfiber_s2", battery_key="ovonic_150c_1400mah",
                                 system_efficiency=0.5):
    """Same sweep as plot_results.sweep_mission_duration(), but hydrogen
    storage and the battery-only comparison both use real, discrete
    components instead of smooth generic formulas."""
    rows = []
    for hours in cruise_hours_list:
        phases = [
            {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
            {"name": "cruise", "duration_hours": hours, "power_w": cruise_power_w},
            {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
        ]
        mission = multi_phase_mission(phases)
        peak_power_w = mission_peak_power_w(mission)
        total_energy_wh = mission_energy_wh(mission)

        result = size_full_system(peak_power_w, total_energy_wh,
                                   cylinder_profile=get_cylinder(cylinder_key),
                                   system_efficiency=system_efficiency)
        result["battery_only_mass_kg"] = size_battery_only_real(
            peak_power_w, total_energy_wh, battery_key)
        result["cruise_hours"] = hours
        result["total_mission_hours"] = mission["time_s"].max() / 3600
        rows.append(result)

    return pd.DataFrame(rows)


def plot_duration_comparison(df, save_path=None):
    if save_path is None:
        save_path = NOTEBOOKS_DIR / "duration_nonlinear.png"
    """Same style as plot_results.plot_duration_tradeoff(), but the tank and
    battery-only lines now show real staircase jumps instead of smooth
    curves, since they're built from whole cylinders/cells."""
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.step(df["total_mission_hours"], df["tank_system_mass_kg"], where="post",
             label="Hydrogen tank system mass (real cylinders)", marker="o", markersize=3)
    ax.plot(df["total_mission_hours"], df["fuel_cell_stack_mass_kg"] + df["battery_mass_kg"],
            label="Fuel cell + battery mass", marker="o", markersize=3)
    # Total mass = a step function (tank) + flat lines (stack, battery), so it
    # is itself a step function -- plot it with step, not a connecting line,
    # or the jump gets drawn as a misleading diagonal ramp.
    ax.step(df["total_mission_hours"], df["total_system_mass_kg"], where="post",
             label="Total system mass (H2, real cylinders)",
             marker="o", markersize=3, linewidth=2.5, color="black")
    ax.step(df["total_mission_hours"], df["battery_only_mass_kg"], where="post",
             label="Battery-only system mass (real cells)",
             marker="s", markersize=3, linewidth=2.5, linestyle="--", color="red")

    ax.set_xlabel("Total mission duration (hours)")
    ax.set_ylabel("Mass (kg)")
    ax.set_title("System Mass vs. Mission Duration: Real Discrete Components")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"Saved plot to {save_path}")
    plt.close(fig)


if __name__ == "__main__":
    from plot_results import sweep_stack_fraction

    phases = [
        {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
        {"name": "cruise", "duration_hours": 59.5 / 60, "power_w": 10 * 22.2},
        {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
    ]
    mission = multi_phase_mission(phases)
    peak_power_w = mission_peak_power_w(mission)
    total_energy_wh = mission_energy_wh(mission)

    print("=== Sweep 1: Stack sizing, constant vs. load-dependent efficiency ===")
    df_linear = sweep_stack_fraction(peak_power_w, total_energy_wh)
    df_nonlinear = sweep_stack_fraction_nonlinear(peak_power_w, total_energy_wh)
    plot_stack_fraction_comparison(df_linear, df_nonlinear)

    print("\n=== Sweep 2: Mission duration, real discrete components ===")
    df_duration_real = sweep_mission_duration_real(
        cruise_power_w=222, cruise_hours_list=np.arange(0.5, 4.5, 0.5))
    plot_duration_comparison(df_duration_real)