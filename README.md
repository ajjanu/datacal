# DataCal — Research Data Volume Calculator

**Version:** 0.1.0  
**Website:** https://datacal.org  
**License:** MIT  
**Phase:** 1 — Plan (calculation core)

---

## What DataCal is

DataCal calculates projected data volumes for scientific field campaigns from instrument specifications and sampling schedules. It produces:

- **DMP figures** — formatted text for the data volume section of funder DMP templates (DFG, Horizon Europe, NERC, NSF, BMBF, ERC)
- **maDMP JSON** — machine-actionable Data Management Plan (RDA DMP Common Standard v1.1) with calculated `byte_size` fields
- **Storage plan** — volume by instrument, leg, and research group for computing centre provisioning
- **Bandwidth plan** — near-real-time transmission requirements in Mbps with satellite link recommendations

Unlike template-driven DMP workflows, DataCal calculates data volumes from instrument specifications. Current DMP tools typically require researchers to enter volume estimates manually.

---

## The volume model

```
raw      = raw_rate × active_seconds × duty_cycle × count
stored   = raw ÷ compression_ratio × overhead_factor
transmit = stored × transmit_fraction
```

`raw_rate` is either declared directly (`model="rate"`, in MB/s) or derived from sensor parameters (`model="sample"`: channels × Hz × bit_depth / 8). Deployments may override `duty_cycle` and `count` per expedition leg.

All volumes use decimal SI units (1 GB = 10⁹ bytes, 1 TB = 10¹² bytes).

---

## This repository

This repository contains the **standalone Python calculation core** — the audited domain layer with no framework dependencies. The full DataCal platform (FastAPI backend, PostgreSQL, React frontend, multi-user access) wraps this core and is available separately at datacal.org.

```
datacal/
  units.py           Byte and bit conventions (decimal SI)
  models.py          Instrument, Leg, Deployment, Campaign — all validation
  engine.py          calculate(campaign) → per-device / per-leg / per-group / totals
  madmp.py           maDMP export (RDA DMP Common Standard v1.1)
  __main__.py        CLI entry point
tests/
  test_engine.py     20 unit tests — every expected number hand-verified
example_campaign.json
  MOSAiC-style 4-instrument 2-leg example (~37.3 TB total stored)
```

---

## Quick start

```bash
# No install required — uses Python stdlib only
cd datacal

# Run the test suite
python3 -m unittest discover -s tests -p "test_*.py" -v

# Calculate a campaign
python3 -m datacal example_campaign.json

# Export maDMP JSON
python3 -m datacal example_campaign.json --madmp
```

Python ≥ 3.11 required.

---

## Verified test case

The included `example_campaign.json` uses a MOSAiC-style configuration:

| Instrument | Model | Key spec | Duty | Count |
|---|---|---|---|---|
| HD observation camera | Rate | 25 MB/s | 0.5 | 1 |
| CTD profiler | Sample | 6ch × 24Hz × 24bit | 0.03 | 1 |
| ADCP current profiler | Sample | 40ch × 2Hz × 32bit | 1.0 | 1 |
| Meteorological logger | Sample | 12ch × 1Hz × 16bit | 1.0 | 3 |

Two legs: 90 days + 120 days.  
Expected result: **37.27 TB total stored, 0.748 TB transmitted, 0.501 Mbps peak bandwidth.**

**Data provenance note:** This example is not derived from any AWI system, internal database, or recorded expedition data. Instrument specifications (data rates, channel counts, sampling frequencies) are based on published manufacturer documentation and publicly available scientific literature. The campaign structure reflects the general shape of the MOSAiC expedition but uses representative values only. This example exists solely to verify that the calculation engine produces correct results.

**Instrument specification sources:**

Instrument type metadata is referenced from PANGAEA — Data Publisher for Earth and Environmental Science (managed by AWI and MARUM), and the AWI O2A sensor registry. All links below carry permanent DOIs or stable institutional identifiers.

| Instrument | Representative of | PANGAEA / AWI source |
|---|---|---|
| HD observation camera | Research-grade HD video systems used in polar atmospheric observation | ARM Instrument catalogue (DOE/ARM): https://www.arm.gov/capabilities/instruments |
| CTD profiler | Standard shipboard CTD rosette system deployed during MOSAiC | PANGAEA MOSAiC CTD buoy dataset series: https://doi.org/10.1594/PANGAEA.937271 |
| ADCP current profiler | Acoustic Doppler current profiler deployed during MOSAiC ROV surveys | PANGAEA MOSAiC ADCP collection: https://doi.org/10.1594/PANGAEA.953510 |
| Meteorological logger | Polar meteorological data acquisition system — MOSAiC instrument class | AWI O2A Sensor Registry: https://sensor.awi.de |

Full MOSAiC instrument and dataset catalogue: https://www.pangaea.de/?q=mosaic

All parameter values (data rates, channel counts, bit depths, duty cycles) are representative of the published instrument class. They are not recordings, raw data, or exports from any specific expedition deployment.

---

## Background

DataCal was conceived during planning for the MOSAiC expedition (2019–2020) at the Alfred Wegener Institute (AWI), Bremerhaven — the largest Arctic scientific expedition on record. The developer co-authored the MOSAiC Data Policy (DOI: 10.5281/zenodo.4537178), referenced in Nature Scientific Data (2022), DOI: 10.1038/s41597-022-01678-8.

---

## Citation

If you use DataCal in your research, please cite it using the `CITATION.cff` file in this repository.

> Ajjan, A. (2026). DataCal — Research Data Volume Calculator (Calculation Core) (v0.1.0). Zenodo. https://doi.org/10.5281/zenodo.20465730

---

## Scope notes (Phase 1 only)

- maDMP export is schema-shaped against RDA DMP Common Standard v1.1. Validate against the official schema before formal funder submission.
- Bandwidth is average sustained per leg, not burst or within-leg peak.
- Excel import is not in the core; the full platform handles it.
- Phase 2 (Monitor) and Phase 3 (Learn) are planned but not yet built.

---

## Contact

**Anu Ajjan** — anuajjan.com — Bremen, Germany  
Early access and pilot enquiries: datacal.org
