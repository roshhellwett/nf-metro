"""Icon helpers for metro map rendering (future use)."""

from __future__ import annotations


def train_icon_path(x: float, y: float, size: float = 12.0) -> str:
    """Generate an SVG path string for a small train icon. Placeholder for future."""
    # Simple diamond shape as placeholder
    hs = size / 2
    return (
        f"M {x} {y - hs} "
        f"L {x + hs} {y} "
        f"L {x} {y + hs} "
        f"L {x - hs} {y} Z"
    )
