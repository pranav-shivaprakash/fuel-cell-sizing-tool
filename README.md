# Fuel Cell System Sizing Tool

A first-order sizing tool for hydrogen fuel cell propulsion systems. Given a mission's power and energy requirements, it sizes the fuel cell stack, battery buffer, and hydrogen tank — and shows where the mass trade-offs actually lie, including a direct comparison against a battery-only system.

## Why this matters

Hydrogen fuel cells are often pitched as the answer to battery range limits in aviation and long-duration mobility applications, but *when* that's actually true depends on mission length, power profile, and component choices. This tool makes those trade-offs visible and quantifiable, rather than just asserting "hydrogen is better for long range."

## How it works

**1. Define a mission profile** (`src/mission_profile.py`)
A mission is modeled as a sequence of phases (e.g. takeoff, climb, cruise, descent, landing), each with a duration and power demand. From this, the tool derives total energy required and peak power demand.

**2. Size the system** (`src/fuel_cell_sizing.py`)
- **Fuel cell stack**: sized to cover a chosen fraction of peak power continuously (stacks respond too slowly for sudden spikes)
- **Battery buffer**: covers the remaining power gap during short peak-demand phases like takeoff
- **Hydrogen tank**: sized by total mission energy, accounting for realistic tank structure mass, not just the hydrogen itself
- **Battery-only comparison**: sizes an equivalent pure-battery system for the same mission, for direct comparison

**3. Explore trade-offs** (`src/plot_results.py`)
Two sweeps are run automatically:
- How total system mass splits between fuel cell stack and battery buffer, as the stack sizing choice changes
- How total system mass scales with mission duration, for both the hydrogen system and a battery-only equivalent

## Results

For an example long-range UAV mission (3.3 hours total, 4kW peak power at takeoff):

**Stack sizing trade-off**: a smaller fuel cell stack paired with a larger battery buffer produces the lightest overall system for this mission — because batteries have much higher specific power (W/kg) than fuel cell stacks, even though fuel cells win on energy density.

![Stack sizing trade-off](notebooks/stack_fraction_tradeoff.png)

**Mission duration scaling**: this is the core insight. Fuel cell + battery mass stays flat regardless of mission duration (it's sized only by peak power), while hydrogen tank mass grows with mission length — but far more slowly than an equivalent battery-only system, whose mass is directly capped by battery specific energy (~200 Wh/kg vs. hydrogen's ~33,000 Wh/kg).

![Duration trade-off vs battery-only](notebooks/duration_tradeoff.png)

For this mission profile, the hydrogen system's mass advantage over a battery-only system grows substantially as mission duration increases — the crossover point and growing gap are visible directly in the plot.

## What I'd improve with more time
- Replace fixed specific power/energy assumptions with real component datasheets (specific PEM stacks, specific battery cells)
- Add balance-of-plant mass (compressors, humidifiers, cooling) to the fuel cell system — currently only stack mass is modeled
- Validate hydrogen tank gravimetric fraction assumption against real Type III/IV composite tank data
- Extend mission profiles to support variable/continuous power curves instead of discrete phases
- Connect this to the [Battery-SOC-estimator](https://github.com/pranav-shivaprakash/Battery-SOC-estimator) repo's SOH model, to account for battery degradation over the system's operational life

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
```

Run the full pipeline:
```bash
python src/mission_profile.py
python src/fuel_cell_sizing.py
python src/plot_results.py
```

## Project structure
```
fuel-cell-sizing-tool/
├── data/
│   └── mission_profiles.csv
├── src/
│   ├── mission_profile.py
│   ├── fuel_cell_sizing.py
│   └── plot_results.py
├── notebooks/
│   ├── stack_fraction_tradeoff.png
│   └── duration_tradeoff.png
└── requirements.txt
```