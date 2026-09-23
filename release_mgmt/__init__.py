"""release_mgmt: hypothesis-driven release measurement for product managers.

Every release declares its hypothesis and success metrics UP FRONT.
Post-release data is then scored against those targets, producing a
structured post-launch review. Stdlib only.
"""

__version__ = "0.1.0"

from .models import MetricDef, Reading, Release
from .scoring import ReleaseScore, MetricScore, score_release
from .sources import MetricSource, SOURCES

__all__ = [
    "MetricDef",
    "Reading",
    "Release",
    "MetricScore",
    "ReleaseScore",
    "MetricSource",
    "SOURCES",
    "score_release",
    "__version__",
]
