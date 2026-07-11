import pytest

from camber import OffCamber, element, raw, render
from camber import html as h


def test_text_children_are_escaped():
    assert render(h.p("a < b & c")) == "<p>a &lt; b &amp; c</p>"


def test_raw_is_admitted_verbatim():
    assert render(h.p(raw("<b>bold</b>"))) == "<p><b>bold</b></p>"


def test_attribute_conventions():
    markup = render(h.div("x", class_="card", data_task_id="7", hidden=True, disabled=False))
    assert markup == '<div class="card" data-task-id="7" hidden>x</div>'


def test_none_and_false_attrs_are_omitted():
    assert render(h.span("s", title=None)) == "<span>s</span>"


def test_attr_values_are_escaped():
    assert render(h.div(title='say "hi"')) == '<div title="say &quot;hi&quot;"></div>'


def test_children_flatten_iterables_and_skip_none():
    items = (h.li(str(n)) for n in range(2))
    assert render(h.ul(items, None)) == "<ul><li>0</li><li>1</li></ul>"


def test_numbers_render_as_text():
    assert render(h.td(42)) == "<td>42</td>"


def test_void_elements_render_without_closing_tag():
    assert render(h.br()) == "<br>"


def test_void_elements_refuse_children():
    with pytest.raises(OffCamber, match="void element"):
        render(element("img", "caption", src="x.png"))


def test_unknown_child_type_is_refused():
    with pytest.raises(OffCamber, match="cannot render child"):
        render(h.p(object()))


def test_html_root_gets_doctype():
    assert render(h.html(h.body())).startswith("<!doctype html>")


def test_anchor_requires_a_real_href():
    with pytest.raises(OffCamber, match="C-200"):
        h.a("click", href="#")


def test_anchor_refuses_javascript_urls():
    with pytest.raises(OffCamber, match="C-200"):
        h.a("click", href="javascript:void(0)")


def test_anchor_href_is_keyword_required():
    with pytest.raises(TypeError):
        h.a("click")  # type: ignore[call-arg]


def test_form_requires_action():
    with pytest.raises(TypeError):
        h.form()  # type: ignore[call-arg]


def test_form_defaults_to_post_and_normalizes_method():
    assert 'method="post"' in render(h.form(action="/tasks"))
    assert 'method="get"' in render(h.form(action="/tasks", method="GET"))


def test_form_refuses_exotic_methods():
    with pytest.raises(OffCamber, match="C-200"):
        h.form(action="/tasks", method="delete")


def test_script_takes_src_only():
    assert render(h.script(src="/static/camber.js")) == (
        '<script src="/static/camber.js" defer></script>'
    )
    with pytest.raises(TypeError):
        h.script("alert(1)", src="/x.js")  # type: ignore[call-arg]


def test_element_id_property():
    assert h.div(id="task-list").id == "task-list"
    assert h.div().id is None
