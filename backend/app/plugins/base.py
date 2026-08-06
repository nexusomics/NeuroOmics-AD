"""Plugin base classes & registration.

Plugins let third parties extend NeuroOmics-AD without forking:
  * `AnalysisPlugin`  — add a new analysis type (registered in the analyses API).
  * `VisualizationPlugin` — add figure generators.
  * `DataSourcePlugin` — add drug/annotation data sources.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""


class NeuroOmicsPlugin(ABC):
    """Base class for all plugins."""

    manifest = PluginManifest(name="base")

    def on_load(self, app: Any) -> None:  # noqa: ANN401
        """Called once at application startup after the plugin is registered."""

    def on_shutdown(self) -> None:
        """Called at application shutdown."""

    @abstractmethod
    def register(self, registry: "PluginRegistry") -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class AnalysisPlugin(NeuroOmicsPlugin):
    """A plugin that adds a new analysis type."""

    analysis_type: str = ""

    def run(self, config: dict, artifacts: dict) -> dict:
        raise NotImplementedError

    def register(self, registry: "PluginRegistry") -> None:
        registry.register_analysis(self.analysis_type, self)


class PluginRegistry:
    """Holds plugin-provided analysis types and data sources."""

    def __init__(self) -> None:
        self.analyses: dict[str, AnalysisPlugin] = {}
        self.visualizations: dict[str, Any] = {}
        self.data_sources: dict[str, Any] = {}
        self.plugins: list[NeuroOmicsPlugin] = []

    def register_analysis(self, analysis_type: str, plugin: AnalysisPlugin) -> None:
        self.analyses[analysis_type] = plugin

    def register_visualization(self, name: str, fn: Any) -> None:  # noqa: ANN401
        self.visualizations[name] = fn

    def register_data_source(self, name: str, source: Any) -> None:  # noqa: ANN401
        self.data_sources[name] = source

    def load(self, plugin_paths: list[str]) -> None:
        """Import plugin modules listed in settings.PLUGINS (dotted paths)."""
        import importlib

        for path in plugin_paths:
            try:
                module = importlib.import_module(path)
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, type) and issubclass(obj, NeuroOmicsPlugin) and obj is not NeuroOmicsPlugin:
                        instance = obj()
                        instance.register(self)
                        self.plugins.append(instance)
            except Exception as exc:  # noqa: BLE001
                import logging

                logging.getLogger(__name__).warning("failed to load plugin %s: %s", path, exc)


registry = PluginRegistry()
