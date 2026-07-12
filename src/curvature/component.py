"""Components are functions of props (C-100, C-101).

A component is a plain function: it takes one Props subclass and returns
an Element. No base class to extend, no registry to join, no decorator to
remember. The contract is the signature, and the gate reads signatures.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Props(BaseModel):
    """The explicit interface of a component.

    Frozen: a component cannot mutate its inputs. Closed: a typo'd or
    surplus prop fails loudly at the call site (C-101). Both are
    inherited; subclasses just declare fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
