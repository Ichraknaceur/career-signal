from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "MediumPipeline",
    "LinkedInSchedulingPipeline",
    "OutreachPipeline",
    "LinkedInAutoPublishPipeline",
]


def __getattr__(name: str) -> Any:
    mapping = {
        "MediumPipeline": ("pipelines.medium_pipeline", "MediumPipeline"),
        "LinkedInSchedulingPipeline": (
            "pipelines.linkedin_scheduling_pipeline",
            "LinkedInSchedulingPipeline",
        ),
        "OutreachPipeline": ("pipelines.outreach_pipeline", "OutreachPipeline"),
        "LinkedInAutoPublishPipeline": (
            "pipelines.linkedin_autopublish_pipeline",
            "LinkedInAutoPublishPipeline",
        ),
    }
    if name not in mapping:
        raise AttributeError(f"module 'pipelines' has no attribute {name!r}")

    module_name, attr_name = mapping[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
