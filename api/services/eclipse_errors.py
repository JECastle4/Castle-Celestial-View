"""Domain failures raised by eclipse calculations."""


class EclipseCalculationError(RuntimeError):
    """A confirmed eclipse could not be resolved within numerical tolerances.

    Transport boundaries may translate this into a safe user-facing failure.
    Programming errors and cancellation must not be represented by this type.
    """
