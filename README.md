# Fuel Cell System Sizing Tool

A Python tool for sizing hydrogen fuel cell propulsion systems. Starting from a general-purpose sizing calculator, this repo also includes a real applied case study: sizing a fuel cell retrofit for an Evolonic (Fraunhofer IISB) VTOL UAV, using real datasheet specifications for every major component.

## Why this matters

Hydrogen fuel cells are often pitched as the answer to battery range limits in aviation, but *when* that's actually true depends on mission length, power profile, and real component specs — not just theory. This tool makes those trade-offs visible and quantifiable, and the case study below shows the full process applied to a real retrofit project.

---

## Part 1: General Sizing Tool

### How it works

**1. Define a mission profile** (`src/mission_profile.py`)
A mission is modeled as a sequence of phases (e.g. takeoff, cruise, landing), each with a duration and power demand. From this, the tool derives total energy required and peak power demand.

**2. Size the system** (`src/fuel_cell_sizing.py`)
| Component | How it's sized |
|---|---|
| Fuel cell stack | Covers a chosen fraction of peak power continuously, OR capped at a real product's rated power |
| Battery buffer | Covers the remaining power gap during short peak-demand phases (e.g. takeoff) |
| Hydrogen tank | Sized by total mission energy — either a generic gravimetric-fraction estimate, or real cylinder products |
| Balance of plant | Power electronics, wiring, hoses — as a fraction of stack mass, or included in real product mass |

**3. Explore trade-offs** (`src/plot_results.py`)
Two general sweeps show how design choices affect total mass:

![Stack sizing trade-off](notebooks/stack_fraction_tradeoff.png)
*A smaller fuel cell stack paired with a larger battery buffer can produce a lighter overall system, since batteries have much higher specific power (W/kg) than fuel cell stacks.*

![Duration trade-off vs battery-only](notebooks/duration_tradeoff.png)
*Fuel cell + battery mass stays flat regardless of mission duration, while a battery-only system's mass grows much faster — this is where hydrogen's energy density advantage shows up for longer missions.*

---

## Part 2: Real Case Study — Evolonic VTOL UAV Retrofit

This applies the tool to a real fuel cell retrofit project: adding a hydrogen fuel cell system to an existing battery-powered VTOL UAV, using measured flight data and real component datasheets throughout.

### The mission (measured, not estimated)

| Phase | Duration | Current draw | Power (at 22.2V) |
|---|---|---|---|
| Takeoff/hover | 1.25 min | 60 A | 1332 W |
| Cruise | 59.5 min | 10 A | 222 W |
| Landing | 1.0 min | 27.5 A | 611 W |
| **Total** | **~61.75 min** | — | **Peak: 1332 W, Energy: 247 Wh** |

Source: measured flight data from the existing battery-powered aircraft (62 min flight, 65.69 km, 249.4 Wh charging energy) — the model's 247 Wh result lines up closely with this, validating the mission model.

### Aircraft mass budget

- Airframe (with original battery): 9595 g
- Original battery: 1890 g → **airframe alone: 7705 g**
- Target maximum takeoff weight: 12,000 g (for a thrust-to-weight ratio of 1.7:1)
- **Mass budget for the entire new fuel cell system: 4000 g (4 kg)**

### Real components considered

**Fuel cell candidates:**

| Spec | Horizon FCS-UL500 | Intelligent Energy S800 |
|---|---|---|
| Rated power | 500 W | 800 W |
| Measured/rated mass | 1750 g (stack+housing+blowers+valves: 1332g, controller+cables+LCD+dissipation plate: 346g, tubes/screws/fittings/H2 connectors: 72g) | 1490 g (combined mass with cabling) |
| Specific power | 285.7 W/kg | 536.9 W/kg |
| System efficiency | 40% (datasheet minimum) | 48.5% (back-calculated from 50g H2/hr at 800W) |
| Output voltage range | 22.5–44.1 V | 25–50 V |

**Hydrogen cylinder candidates (X-Fiber):**

| Spec | X-Fiber S2 | X-Fiber S3 |
|---|---|---|
| Volume | 2 L | 3 L |
| Empty mass | 1.3 kg | 1.6 kg |
| Max pressure | 300 bar | 300 bar |
| H2 capacity (at 300 bar, ~15°C, real-gas density ≈20.7 kg/m³) | 41.4 g | 62.1 g |
| Real gravimetric fraction (H2 mass ÷ total filled mass) | 3.1% | 3.7% |

**Battery buffer:**

| Spec | Ovonic 150C Racing Series |
|---|---|
| Configuration | 6S1P, 1400 mAh, 22.2V nominal |
| Discharge rate | 150C continuous (210 A / 4662 W max continuous) |
| Mass | 227 g |
| Real specific energy | ~137 Wh/kg |
| Connector | XT60 |

### Results: three configurations compared

![Fuel cell comparison](notebooks/fuel_cell_comparison.png)

| Configuration | Stack mass | Battery mass | Tank mass | BoP mass | **Total mass** | vs. 4 kg budget |
|---|---|---|---|---|---|---|
| 1× Horizon UL500 (500W cap, bigger battery buffer) | 1.750 kg | 0.227 kg | 1.319 kg | 0.000 kg | **3.296 kg** | Within, 0.704 kg margin |
| 2× Horizon UL500 in parallel (1000W combined) | 3.500 kg | 0.227 kg | 1.319 kg | 0.000 kg | **5.046 kg** | Over by 1.046 kg |
| 1× Intelligent Energy S800 (800W cap) | 1.490 kg | 0.227 kg | 1.315 kg | 0.149 kg | **3.181 kg** | Within, 0.819 kg margin |

**Key findings:**
- Both single-unit configurations fit comfortably within the 4 kg budget. Doubling up the Horizon UL500 to cover more peak power outright is the *heaviest* option — the extra stack mass costs more than the battery buffer it saves.
- Hydrogen tank mass is dominated by the cylinder's own structural weight, not the fuel: the mission only needs 15–19 g of H2, but the smallest available cylinder (X-Fiber S2) weighs 1.3 kg empty. This system is **tank-mass-dominated**, not fuel-mass-dominated, at this mission's energy scale.
- The single Ovonic 227 g battery covers the buffer requirement in every configuration with wide margin — even the most demanding case (832 W) uses only ~18% of its rated continuous power capability.

### Assumptions and what to validate further
- Hydrogen density at 300 bar (20.7 kg/m³) is a standard literature reference value — confirm against the exact cylinder manufacturer's fill charts if available.
- Balance-of-plant mass for the Horizon UL500 configuration is assumed to be fully captured in its measured 1750 g (including tubes/fittings) — worth double-checking once wiring/mounting hardware for the specific airframe integration is finalized.
- The battery buffer's 120-second sustain duration is a first-order estimate matching the combined takeoff+landing time; refine against the exact overlap between fuel cell response time and peak demand once real component response curves are available.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Run the general sizing pipeline:
```bash
python3 src/mission_profile.py
python3 src/fuel_cell_sizing.py
python3 src/plot_results.py
```

Run the real case study comparison:
```bash
python3 src/compare_fuel_cells.py
```

## Project structure
```
fuel-cell-sizing-tool/
├── data/
│   └── mission_profiles.csv
├── src/
│   ├── mission_profile.py         # Mission power/energy profile
│   ├── fuel_cell_sizing.py        # Core sizing calculations
│   ├── plot_results.py            # General trade-off analysis & plots
│   ├── fuel_cell_profiles.py      # Real fuel cell datasheet specs (Horizon, IE)
│   ├── cylinder_profiles.py       # Real H2 cylinder specs (X-Fiber)
│   ├── battery_profiles.py        # Real battery specs (Ovonic)
│   └── compare_fuel_cells.py      # Real case study: 3-way comparison
├── notebooks/
│   ├── stack_fraction_tradeoff.png
│   ├── duration_tradeoff.png
│   └── fuel_cell_comparison.png
└── requirements.txt
```