"""Markup is built, not templated (C-102).

Elements are plain immutable trees. Text children are escaped on render;
`raw()` is the single, greppable opt-out. Attribute names follow Python
conventions and render as HTML ones: a trailing underscore is stripped
(class_ -> class), remaining underscores become hyphens
(data_task_id -> data-task-id). True renders a bare attribute; False and
None render nothing.
"""

from __future__ import annotations

from collections.abc import Iterable
from html import escape

from curvature.errors import FlatSpot

type AttrValue = str | int | float | bool | None
type Child = "Element | Raw | str | int | float | None | Iterable[Child]"

VOID_TAGS = frozenset(
    ["area", "base", "br", "col", "embed", "hr", "img", "input", "link",
     "meta", "source", "track", "wbr"]
)


class Raw:
    """Pre-rendered HTML admitted verbatim. Every call site is a finding
    census entry (FLAT-122): use it for trusted, already-escaped markup only."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


def raw(text: str) -> Raw:
    return Raw(text)


class Element:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs: dict[str, AttrValue], children: tuple) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children = children

    @property
    def id(self) -> str | None:
        value = self.attrs.get("id")
        return value if isinstance(value, str) else None

    def __str__(self) -> str:
        return render(self)


def _attr_name(name: str) -> str:
    return name.removesuffix("_").replace("_", "-")


def _render_attrs(attrs: dict[str, AttrValue]) -> str:
    parts: list[str] = []
    for name, value in attrs.items():
        if value is None or value is False:
            continue
        html_name = _attr_name(name)
        if value is True:
            parts.append(f" {html_name}")
        else:
            parts.append(f' {html_name}="{escape(str(value), quote=True)}"')
    return "".join(parts)


def _render_children(children: tuple, out: list[str]) -> None:
    for child in children:
        match child:
            case None:
                continue
            case Element():
                out.append(render(child))
            case Raw():
                out.append(child.text)
            case str():
                out.append(escape(child))
            case int() | float():
                out.append(escape(str(child)))
            case Iterable():
                _render_children(tuple(child), out)
            case _:
                raise FlatSpot(
                    f"cannot render child of type {type(child).__name__}; "
                    "children are Elements, strings, numbers, raw(), or iterables of those"
                )


def render(element: Element) -> str:
    """Render an element tree to markup. An <html> root gets its doctype."""
    open_tag = f"<{element.tag}{_render_attrs(element.attrs)}>"
    if element.tag in VOID_TAGS:
        if element.children:
            raise FlatSpot(f"<{element.tag}> is a void element and takes no children")
        rendered = open_tag
    else:
        body: list[str] = []
        _render_children(element.children, body)
        rendered = f"{open_tag}{''.join(body)}</{element.tag}>"
    if element.tag == "html":
        return f"<!doctype html>{rendered}"
    return rendered


def element(tag: str, *children: Child, **attrs: AttrValue) -> Element:
    """The generic constructor. Prefer the named factories below; this is
    the escape hatch for exotic tags (and the gate greps its call sites)."""
    return Element(tag, attrs, children)


def _factory(tag: str):
    def make(*children: Child, **attrs: AttrValue) -> Element:
        return Element(tag, attrs, children)

    make.__name__ = make.__qualname__ = tag
    make.__doc__ = f"Build a <{tag}> element."
    return make


# Document structure
html = _factory("html")
head = _factory("head")
body = _factory("body")
title = _factory("title")
main = _factory("main")
header = _factory("header")
footer = _factory("footer")
nav = _factory("nav")
section = _factory("section")
article = _factory("article")
aside = _factory("aside")

# Grouping and text
div = _factory("div")
p = _factory("p")
span = _factory("span")
h1 = _factory("h1")
h2 = _factory("h2")
h3 = _factory("h3")
h4 = _factory("h4")
ul = _factory("ul")
ol = _factory("ol")
li = _factory("li")
dl = _factory("dl")
dt = _factory("dt")
dd = _factory("dd")
table = _factory("table")
thead = _factory("thead")
tbody = _factory("tbody")
tr = _factory("tr")
th = _factory("th")
td = _factory("td")
figure = _factory("figure")
figcaption = _factory("figcaption")
blockquote = _factory("blockquote")
pre = _factory("pre")
code = _factory("code")
small = _factory("small")
strong = _factory("strong")
em = _factory("em")
time = _factory("time")

# Void elements
br = _factory("br")
hr = _factory("hr")
img = _factory("img")
meta = _factory("meta")
link = _factory("link")

# Form vocabulary (a and form have contract signatures below)
label = _factory("label")
select = _factory("select")
option = _factory("option")
textarea = _factory("textarea")
button = _factory("button")
fieldset = _factory("fieldset")
legend = _factory("legend")
output = _factory("output")
datalist = _factory("datalist")

# Interactive, no JS required
details = _factory("details")
summary = _factory("summary")
dialog = _factory("dialog")
menu = _factory("menu")


def a(*children: Child, href: str, **attrs: AttrValue) -> Element:
    """A real link (C-200). href is required and must go somewhere."""
    if href == "#" or href.startswith("javascript:"):  # curvature-allow: enforcement
        raise FlatSpot(
            f'href={href!r} is flat (C-200): a link that goes nowhere '
            "is a button wearing a costume; use a form or a real URL"
        )
    return Element("a", {"href": href, **attrs}, children)


def form(*children: Child, action: str, method: str = "post", **attrs: AttrValue) -> Element:
    """A real form (C-200). action and method are the contract, not decoration."""
    normalized = method.lower()
    if normalized not in {"get", "post"}:
        raise FlatSpot(
            f"form method {method!r} is flat (C-200): browsers submit "
            "GET and POST; other verbs belong to boosted routes via POST"
        )
    return Element("form", {"action": action, "method": normalized, **attrs}, children)


def input_(*, type: str = "text", **attrs: AttrValue) -> Element:
    return Element("input", {"type": type, **attrs}, ())


def script(*, src: str, defer: bool = True, **attrs: AttrValue) -> Element:
    """External scripts only (C-302). There is deliberately no way to pass
    a body: inline script is invisible to the gate, so it cannot exist."""
    return Element("script", {"src": src, "defer": defer, **attrs}, ())


def style_link(href: str) -> Element:
    return Element("link", {"rel": "stylesheet", "href": href}, ())
