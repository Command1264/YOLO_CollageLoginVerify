from typing import Any

__all__ = ["ScholarshipApp", "run"]
ScholarshipApp: Any


def run() -> Any:
    from UI.main_window import run as _run
    return _run()


def __getattr__(name: str) -> Any:
    if name in {"ScholarshipApp", "run"}:
        from UI.main_window import ScholarshipApp, run

        exports = {
            "ScholarshipApp": ScholarshipApp,
            "run": run,
        }
        return exports[name]
    raise AttributeError(f"module 'UI' has no attribute '{name}'")
