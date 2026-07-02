# Saúde em Dado: an open, reproducible platform of epidemiological indicators from Brazil's Unified Health System, with an excess-mortality baseline robust to population-denominator error

**Pedro Paulo Fernandes**¹²³
ORCID: 0009-0008-6248-2486

¹ IAMSPE — MSc programme in Collective Health
² Hospital Sírio-Libanês — Postgraduate programme in AI and Data Science in Health
³ Penápolis City Government (SP, Brazil) — IT Directorate

Correspondence: pedropaulofernandes88@gmail.com

> **Status:** methods-paper draft for preprint (medRxiv / SciELO Preprints).
> Anchored on the methodology published at https://saudeemdado.com/metodologia.
> Portuguese version: `preprint.md`.

---

## Abstract

**Background.** Brazil's Unified Health System (SUS) publishes some of the largest
openly available health microdata in the world, yet the gap between raw records
and interpretable, reproducible indicators remains wide. **Objective.** To
describe an open, zero-cost platform that turns DataSUS and IBGE microdata into
validated municipal indicators with a fully reproducible pipeline, and to report a
sensitivity analysis of the excess-mortality method. **Methods.** We integrate
five information systems (SIM, SIH, SINAN, SINASC and IBGE census/projections),
applying direct age standardization (Brazil 2022 census standard), exact
confidence intervals (gamma method), and excess mortality with a 2015–2019
baseline. **Results.** The platform covers mortality (2015–2024), hospital
admissions (2022–2024), dengue (2015–2024) and births (2021–2023), plus derived
indicators (ambulatory-care-sensitive admissions [ACSC], inter-municipal patient
flow, admissions by tracer condition, hospital-level view). For excess mortality
we replaced a "mean × population-ratio" baseline with a **linear trend by
calendar month**, which captures population ageing. In a sensitivity analysis we
show that an age-standardized variant **underestimates** pandemic excess (~505,000
vs. 643,000) because of denominator contamination — the 2018 population projection
overestimates population and the post-2022-census series introduces a
discontinuity. **Conclusion.** The trend method, relying only on observed deaths,
is immune to these problems and was retained. All aggregated data (CC BY 4.0),
code (MIT) and checksums are published (concept DOI: 10.5281/zenodo.20706845;
version DOI: 10.5281/zenodo.21036341).

**Keywords:** collective health; DataSUS; mortality; excess mortality; age
standardization; open data; reproducibility; Brazil.

---

## 1. Introduction

Brazil's health surveillance produces massive, openly available microdata — the
Mortality Information System (SIM), the Hospital Information System (SIH), the
Notifiable Diseases Information System (SINAN) and the Live Births Information
System (SINASC). Turning these files into comparable, statistically honest and
reproducible indicators, however, requires technical steps (`.dbc` decoding, age
standardization, population denominators, confidence intervals) that are rarely
documented auditably in the dashboards available today.

We present *Saúde em Dado*, an open platform that (i) processes the official
microdata through an open, versioned pipeline; (ii) publishes aggregates in an
analytical format (Parquet) with checksums and via a public REST API; and (iii)
fully documents its methods. This note describes the methodological choices and
reports a sensitivity analysis of excess mortality with implications beyond this
platform.

## 2. Methods

### 2.1 Sources and processing

- **Mortality (SIM):** 2015–2024 (national OpenDataSUS CSVs for 2022+; per-state
  `.dbc` files for 2015–2021). Fetal deaths excluded (`TIPOBITO=1`); municipality
  of residence; ICD-10 underlying cause.
- **Hospital admissions (SIH/AIH):** per-state monthly RD files, 2022–2024
  (SUS-funded network).
- **Dengue (SINAN):** national `DENGBR` files, 2015–2024.
- **Live births (SINASC):** 2021–2023.
- **Population:** IBGE — 2022 Census and annual estimates (SIDRA); 2018 projection
  by age/state/year for the sensitivity analysis.

Annual totals are checked against official figures (e.g., SIM 2015 = 1,264,175
deaths) in continuous integration.

### 2.2 Standardization and uncertainty

Age-standardized rates use the **direct method**, with the Brazil 2022 census
standard population and 8 age bands; deaths with unknown age are redistributed pro
rata. Crude rates carry **95% CIs by the gamma (exact Poisson) method**.
Municipalities under 10,000 inhabitants are flagged, since their rates are
unstable.

### 2.3 Excess mortality

For each state and Brazil, the **expected** deaths for month *m* of year *a* are
obtained by **linear regression of that calendar month's deaths on year**, over
2015–2019, projected to *a*. **Excess = observed − expected.** This empirically
captures population growth and ageing — both of which raise expected deaths year
over year — without relying on a population denominator.

### 2.4 Admission-derived indicators

On SIH 2024 we classify each admission by principal diagnosis and derive:
**ACSC** (ambulatory-care-sensitive conditions, approximating the Brazilian List
at the 3-character ICD-10 level), with an estimate of **potentially avoidable
spending** and **outlier flagging** (lower bound of the Wilson 95% CI of the ACSC
proportion above the reference mean); **inter-municipal patient flow** (residence
→ treatment); **admissions by tracer condition** (3-character ICD-10); and a
**facility-level view (CNES)**.

## 3. Sensitivity analysis: trend vs. age standardization in excess mortality

Excess-mortality literature often recommends methods that adjust for age
structure. We tested an **age-standardized** expected: age-specific mortality
rates (pooled 2015–2019, by state and calendar month) applied to the target
year's age structure, using the population by age/state/year from the **2018 IBGE
projection** (SIDRA t/7358), in two versions — raw and rescaled to the post-census
population total.

**Result.** Both standardized versions estimate the pandemic peak (2020–2021) at
**~505,000–510,000** excess deaths — **below** both the trend method (**643,000**)
and the independent consensus for Brazil (~660,000–680,000; World Mortality
Dataset; WHO) — and yield strongly negative excess from 2023 onward (Table 1).

**Table 1.** Excess mortality in Brazil by method (deaths).

| Period | Trend (published) | Standardized (projection) | Standardized (rescaled) |
|---|--:|--:|--:|
| 2020–2021 | 643,482 | 503,913 | 510,243 |
| 2022 | 144,541 | 36,182 | 121,406 |
| 2023 | 48,065 | −88,267 | −24,681 |
| 2024 | −9,018 | −174,699 | −134,195 |
| 2020–2024 | 827,070 | 277,129 | 472,774 |

**Diagnosis.** The discrepancy is not driven by the method but by Brazil's
**annual population denominator for 2015–2024**:

1. The **2018 IBGE projection overestimates** population — the 2022 Census revised
   it downward (≈215 million projected vs. 203 million counted). An inflated
   elderly population raises the expected and understates the excess, with a bias
   that grows over time.
2. The **post-census** series corrects the level but introduces a
   **discontinuity in 2022** (≈211 million in 2020 → 203 million at the census)
   that distorts the expected around the rebasing.

Algebraically, age-standardizing with a time-invariant age structure reduces
exactly to the "mean × population-ratio" method; the gain from standardization
depends entirely on the quality of the **annual** age structure, which for Brazil
in this period is precisely the weak link.

**Decision.** The **trend method on observed deaths** never touches population and
is therefore immune to the pre-census overcount and the 2022 discontinuity. For
its agreement with independent estimates and its robustness, it was **retained as
the published method.** The code and data for this analysis are in the repository
(`scripts/sensibilidade_excesso_idade.py`).

## 4. Selected results

- Pandemic excess mortality (Brazil, 2020–2021): **643,482** deaths (~8% below the
  previous baseline, correcting for ageing); return to the historical level from
  2022; 2024 near zero (preliminary).
- National ACSC 2024: roughly one fifth of admissions, with avoidable-spending on
  the order of billions of reais (order of magnitude).
- Coverage: SIM 2015–2024; SIH 2022–2024; SINAN 2015–2024; SINASC 2021–2023.

## 5. Limitations

SIM coverage and registration quality vary regionally; ~5% of deaths have
ill-defined causes and are not redistributed. Admissions cover only the SUS
network — municipal comparisons are confounded by private-insurance coverage.
Hospital mortality is crude (not case-mix adjusted). Municipal indicators are
ecological. The excess baseline assumes continuation of the pre-pandemic trend and
does not model harvesting.

## 6. Data and code availability

- **Platform:** https://saudeemdado.com
- **Code:** https://github.com/pedropaulofernandes88-stack/saude-publica-br (MIT)
- **Aggregated data:** Parquet with SHA-256 checksums and a public REST API (CC BY 4.0)
- **DOI (concept, all versions):** 10.5281/zenodo.20706845
- **DOI (analysed version, v3.1.0):** 10.5281/zenodo.21036341
- **Original data:** public domain (DATASUS/Ministry of Health; IBGE)

Methodological inspiration credited to the LabSUS project (Lucas Amaral Dourado,
Federal University of Tocantins).

## References (to be completed at submission)

1. Brazil, Ministry of Health / DATASUS. SIM, SIH, SINAN, SINASC microdata.
2. IBGE. 2022 Demographic Census; Population Estimates and Projections.
3. Karlinsky A, Kobak D. Excess mortality during the COVID-19 pandemic: World
   Mortality Dataset. *eLife*. 2021.
4. World Health Organization. Global excess deaths associated with COVID-19.
5. Brazil, Ministry of Health. Ordinance SAS/MS 221/2008 (Brazilian List of ACSC).
