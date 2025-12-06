# EO Drought Intelligence

Earth-observation–based *drought & irrigation intelligence* platform.  
Turns satellite and environmental data into *actionable insights* for farmers, agronomists, and water managers – not just pretty maps.

> Built as a hackathon prototype with a *production-style, layered architecture* ready to grow beyond the demo stage.

---

## 🚜 What is EO Drought Intelligence?

EO Drought Intelligence aims to answer questions like:

- Where is *drought stress* starting to appear?
- Which fields should I *irrigate first*, given limited water?
- How has *vegetation health* changed over the last weeks?

The platform combines:

- *Earth Observation (EO) data* – vegetation and moisture indicators  
- *Weather & environmental data* – temperature, precipitation, etc.  
- *Analytics & ML* – drought scores, trends, and irrigation priorities  

…to produce *clear, field-level intelligence* instead of raw data layers.

---

## 🧱 Key Ideas

- *Architecture-first*: A clean, modular Python package instead of one-off notebooks.
- *EO-aware pipelines*: From ingestion → processing → analytics → ML → interfaces.
- *Actionable outputs*: Drought indices, stress maps, and irrigation priority suggestions.
- *Hackathon-ready, production-minded*: Built fast, but designed to scale.

---

## 🏗️ Project Architecture

The core Python package is:

```text
eo_drought/
  config/          # Central configuration (paths, keys, environment settings)
  core/            # Domain models, shared utilities, drought concepts
  ingest/          # Data ingestion from EO & weather sources
  processing/      # Preprocessing, feature engineering, indices (e.g. vegetation, moisture)
  analytics/       # Drought scores, temporal trends, regional summaries
  ml/
    datasets/      # Dataset definitions for ML
    models/        # Model architectures / wrappers
    training/      # Training logic & experiment setup
    evaluation/    # Metrics, validation, model comparison
    inference/     # Running trained models on new data
    registry/      # Model registry, versions, metadata
  pipelines/       # End-to-end workflows (ingest → process → analyze → export)
  interfaces/
    cli/           # Command-line interface entrypoints
