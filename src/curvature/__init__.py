"""Curvature — a web framework for code that agents maintain.

The contract pieces live here. The HTML vocabulary is deliberately a
separate import (`from curvature import html as h`) so markup reads as
markup at every call site.
"""

import sys

from curvature.core import component as _component
from curvature.core import errors as _errors
from curvature.core import fragments as _fragments
from curvature.core.component import Props
from curvature.core.errors import Anomaly
from curvature.core.fragments import BOOST_HEADER, is_boosted, redirect, respond
from curvature.html import Element, element, raw, render

sys.modules[f"{__name__}.component"] = _component
sys.modules[f"{__name__}.errors"] = _errors
sys.modules[f"{__name__}.fragments"] = _fragments

__all__ = [
    "BOOST_HEADER",
    "Element",
    "Anomaly",
    "Props",
    "element",
    "is_boosted",
    "raw",
    "redirect",
    "render",
    "respond",
]
