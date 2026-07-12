import pydantic
import pytest

from curvature import Props


class CardProps(Props):
    title: str
    count: int = 0


def test_props_are_frozen():
    props = CardProps(title="x")
    with pytest.raises(pydantic.ValidationError):
        props.title = "y"


def test_props_are_closed_to_extras():
    with pytest.raises(pydantic.ValidationError):
        CardProps(title="x", surplus=True)


def test_props_validate_types():
    with pytest.raises(pydantic.ValidationError):
        CardProps(title="x", count="many")
