class OffCamber(Exception):
    """The construction-grade refusal (SPEC.md enforcement grade 1).

    Raised when code tries to build something the contract forbids —
    an href="#", an inline script body, a fragment root without an id.
    The message always names the invariant so the traceback teaches.
    """
