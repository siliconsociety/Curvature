import pytest

from camber.gate.scaffold import new_component


def test_scaffold_pours_component_and_test(tmp_path):
    created = new_component(tmp_path, "demo/components/lap_counter")
    component, test = created
    assert component == tmp_path / "demo/components/lap_counter.py"
    assert test == tmp_path / "tests/test_lap_counter.py"
    source = component.read_text()
    assert "class LapCounterProps(Props):" in source
    assert "def lap_counter(props: LapCounterProps) -> Element:" in source
    assert 'id="lap-counter"' in source
    test_source = test.read_text()
    assert "from demo.components.lap_counter import LapCounterProps, lap_counter" in test_source


def test_scaffold_never_overwrites(tmp_path):
    new_component(tmp_path, "demo/components/gauge")
    with pytest.raises(FileExistsError, match="never overwrite"):
        new_component(tmp_path, "demo/components/gauge")


def test_scaffold_requires_a_components_tree(tmp_path):
    with pytest.raises(ValueError, match="C-600"):
        new_component(tmp_path, "demo/helpers/gauge")


def test_scaffold_requires_a_valid_name(tmp_path):
    with pytest.raises(ValueError, match="snake_case"):
        new_component(tmp_path, "demo/components/lap-counter")


def test_scaffolded_component_passes_its_own_gate(tmp_path):
    """The scaffold's output must satisfy the component signature check —
    the on-ramp may never pour off-camber concrete."""
    from camber.gate.checks import check_component_signatures

    new_component(tmp_path, "demo/components/fuel_gauge")
    assert check_component_signatures(tmp_path) == []
