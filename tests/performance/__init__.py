"""Performance test package for the XTB dividend analysis pipeline.

Contains throughput, latency, memory, and scalability tests for the core
processing components.

Run all performance tests:
    pytest tests/performance/ -m performance

Run only fast (non-slow) performance tests:
    pytest tests/performance/ -m "performance and not slow"

Run only stress / scalability tests:
    pytest tests/performance/ -m slow
"""

from __future__ import annotations
