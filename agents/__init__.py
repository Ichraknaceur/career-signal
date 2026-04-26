# Lazy imports — on n'importe que ce qu'on utilise explicitement.
# Cela évite de charger tous les agents (et leurs dépendances) au simple
# import du package, ce qui accélérait le démarrage de l'UI Streamlit.

from __future__ import annotations


def __getattr__(name: str):
    """Import à la demande pour chaque agent."""
    _map = {
        "IngestionAgent": ("agents.ingestion_agent", "IngestionAgent"),
        "StrategistAgent": ("agents.strategist_agent", "StrategistAgent"),
        "LinkedInAgent": ("agents.linkedin_agent", "LinkedInAgent"),
        "LinkedInContentAgent": ("agents.linkedin_content_agent", "LinkedInContentAgent"),
        "OutreachAgent": ("agents.outreach_agent", "OutreachAgent"),
        "MediumAgent": ("agents.medium_agent", "MediumAgent"),
        "QAJudgeAgent": ("agents.qa_judge_agent", "QAJudgeAgent"),
        "PublisherAgent": ("agents.publisher_agent", "PublisherAgent"),
    }
    if name in _map:
        module_path, class_name = _map[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    raise AttributeError(f"module 'agents' has no attribute {name!r}")


__all__ = [
    "IngestionAgent",
    "StrategistAgent",
    "LinkedInAgent",
    "LinkedInContentAgent",
    "OutreachAgent",
    "MediumAgent",
    "QAJudgeAgent",
    "PublisherAgent",
]
