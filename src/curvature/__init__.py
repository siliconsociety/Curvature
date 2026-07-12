"""Curvature — a web framework for code that agents maintain.

The contract pieces live here. The HTML vocabulary is deliberately a
separate import (`from curvature import html as h`) so markup reads as
markup at every call site.
"""

from curvature.component import Props
from curvature.errors import Anomaly
from curvature.fragments import BOOST_HEADER, is_boosted, redirect, respond
from curvature.html import Element, element, raw, render

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
