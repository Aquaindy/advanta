"""Traffic Genie — the traffic-source planning module.

`catalog.py` holds the global reference data (categories, sources, recipes)
that powers the source cards, the AI traffic-recommendation agent, and the
parametric asset generator. It is reference data, not tenant data, so it lives
in code like the integration registry and agent catalog — not in a per-tenant
table."""
