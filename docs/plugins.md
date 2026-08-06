# Plugin Architecture

NeuroOmics-AD is extensible without forking. Plugins are plain Python modules
discovered at startup from `PLUGINS` (comma-separated dotted paths).

## 1. Concepts

| Concept | Purpose |
|---|---|
| `NeuroOmicsPlugin` | Base class with `on_load(app)`, `on_shutdown()`, `register(registry)` |
| `AnalysisPlugin` | Adds a new `analysis_type` consumable via the analyses API |
| `PluginRegistry` | Central registry: `analyses`, `visualizations`, `data_sources` |

## 2. Minimal analysis plugin

```python
# my_plugin.py
from app.plugins.base import AnalysisPlugin

class MyModulePlugin(AnalysisPlugin):
    analysis_type = "my_module"

    def run(self, config: dict, artifacts: dict) -> dict:
        genes = config.get("gene_list", [])
        return {"n_genes": len(genes), "genes": genes, "module": "hello"}

registry  # auto-registered via the import in app.plugins.base
```

Enable it:

```bash
# .env
PLUGINS=my_plugin
```

The new type becomes available in `dispatch_analysis` automatically (it checks
`registry.analyses`), and you can launch it via:

```
POST /api/v1/analyses/{project_id}/create
{ "analysis_type": "my_module", "config": { "gene_list": ["APP", "APOE"] } }
```

## 3. Registering visualizations & data sources

```python
class VizPlugin(NeuroOmicsPlugin):
    def register(self, registry):
        def my_plot(data):
            return {"figure_paths": {}, "plotly_json": {"data": [], "layout": {}}}
        registry.register_visualization("my_plot", my_plot)
```

## 4. Conventions

- Keep plugins **stateless**; persist via `ResultArtifact`/JSON result.
- Follow the result-envelope convention (`{"table": [...], "summary": {...}}`)
  so reports and the assistant can render them.
- Ship tests alongside the plugin; CI runs them via `pytest plugins/`.

## 5. Extending to other diseases

Because genes, gene sets, drug knowledge, and signatures are **data**, adapting
the platform to Parkinson's / ALS / Huntington's / cancer means:

1. New project (`disease` label).
2. Disease gene list (e.g. `SNCA, LRRK2, PINK1, GBA` for PD).
3. Optional: plugin providing disease-specific gene sets (enrichment) and
   drug–target annotations (drug scoring).
4. Re-run the same pipelines — DE, meta-analysis, network, ML, drugs, reports.
