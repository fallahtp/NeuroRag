"""
Optional LangSmith tracing.

NeuroRag runs fully locally with no hosted dependencies by default. If you
want request traces — per-stage latency, inputs/outputs, the full query tree —
LangSmith can capture them, and the ``traced`` decorator below turns those
traces on. When LangSmith is not installed or tracing is not enabled, the
decorator is a zero-overhead no-op, so it is always safe to leave in place.

Enable it by installing the optional dependencies::

    pip install -r requirements-optional.txt

and setting these environment variables before running anything::

    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=ls__...
    LANGSMITH_PROJECT=neurorag        # optional, defaults to "default"
"""

from __future__ import annotations

import os


def tracing_enabled() -> bool:
    """True when LangSmith tracing has been explicitly switched on."""
    flag = os.environ.get("LANGSMITH_TRACING") or os.environ.get("LANGCHAIN_TRACING_V2")
    return str(flag).lower() in {"1", "true", "yes", "on"}


def traced(func=None, *, name=None):
    """Trace the wrapped function with LangSmith when tracing is enabled.

    Usable bare (``@traced``) or with a name (``@traced(name="retrieve")``).
    Falls back to returning the function unchanged when LangSmith is not
    installed or ``LANGSMITH_TRACING`` is not set.
    """

    def decorator(f):
        if not tracing_enabled():
            return f
        try:
            from langsmith import traceable
        except ImportError:
            return f
        return traceable(name=name or f.__name__)(f)

    if func is not None:
        return decorator(func)
    return decorator
