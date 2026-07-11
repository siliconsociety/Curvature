"""Camber — a web framework for code that agents maintain.

The contract pieces live here. The HTML vocabulary is deliberately a
separate import (`from camber import html as h`) so markup reads as
markup at every call site.
"""

from camber.component import Props
from camber.errors import OffCamber
from camber.fragments import BOOST_HEADER, is_boosted, redirect, respond
from camber.html import Element, element, raw, render

__all__ = [
    "BOOST_HEADER",
    "Element",
    "OffCamber",
    "Props",
    "element",
    "is_boosted",
    "raw",
    "redirect",
    "render",
    "respond",
]
