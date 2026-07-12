"""The site's faces: shell and home. Docs stay in the repo where they
version; the site links, it does not mirror."""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h

REPO = "https://github.com/siliconsociety/Curvature"


def shell(*fragments: Element) -> Element:
    return h.html(
        h.head(
            h.meta(charset="utf-8"),
            h.meta(name="viewport", content="width=device-width, initial-scale=1"),
            h.title("Curvature — the right path is free fall"),
            h.style_link("/static/manifold.css"),
            h.script(src="/static/lib/curvature.js"),
        ),
        h.body(
            h.header(
                h.h1("Curvature"),
                h.nav(
                    h.a("Home", href="/"),
                    h.a("Roadmap", href="/roadmap"),
                    h.a("Atlas", href="/atlas"),
                    h.a("GitHub", href=REPO),
                    class_="site-nav",
                ),
            ),
            h.main(*fragments),
            data_boost=True,
        ),
        lang="en",
    )


class HomeProps(Props):
    version: str


def home(props: HomeProps) -> Element:
    return h.section(
        h.p("A web framework for code that agents maintain.", class_="tagline"),
        h.p(
            "Server-rendered Python. Components as typed functions. Real links, "
            "real forms, one small boost script — and a gate that makes the "
            "maintainable path the only path that builds.",
        ),
        h.pre(h.code(
            "uvx curvature new app pitstop\n"
            "cd pitstop\n"
            "./gate.sh    # green before you write a line\n"
            "./run.sh",
        ), class_="quickstart"),
        h.p(
            "Agents don't parse this page — they ask for its ",
            h.a("chart", href=f"{REPO}/blob/main/SPEC.md"),
            ". Humans can read the ",
            h.a("manifesto", href=f"{REPO}/blob/main/MANIFESTO.md"),
            " and the ",
            h.a("spec", href=f"{REPO}/blob/main/SPEC.md"),
            "; the ",
            h.a("living roadmap", href="/roadmap"),
            " is a Curvature app, and this site is one too.",
        ),
        h.p(f"v{props.version} · MIT · pip install curvature", class_="colophon"),
        id="home",
    )
