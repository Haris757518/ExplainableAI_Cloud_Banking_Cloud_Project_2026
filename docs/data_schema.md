# Canonical Data Schema

The same Pydantic models are used for simulation, AWS normalization, graph construction, backend input and frontend responses.

A sample contains:
- transaction context
- nodes
- directed dependency edges
- telemetry per node
- scenario label
- node-level affected labels
- root-cause node labels for evaluation
