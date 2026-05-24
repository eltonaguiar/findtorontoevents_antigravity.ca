"""Base class for all audit tests."""


class AuditTest:
    """Base class for all audit tests.

    Subclasses must set:
        name: str          — human-readable test name
        severity: str      — one of 'critical', 'high', 'medium', 'low', 'info'
    and implement run() -> dict.
    """

    name = ""
    severity = "info"  # critical, high, medium, low, info

    def run(self) -> dict:
        """Run the test and return a result dict.

        Returns
        -------
        dict with keys:
            passed  : bool   — True if the test passed
            message : str    — human-readable summary
            data    : dict   — raw data / metrics collected during the test
        """
        raise NotImplementedError(f"{self.__class__.__name__}.run() not implemented")

    def __repr__(self) -> str:
        return f"<AuditTest name={self.name!r} severity={self.severity!r}>"
