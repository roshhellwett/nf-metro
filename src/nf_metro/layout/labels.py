"""Label placement for station names.

Uses horizontal labels (like the reference nf-core metro maps) with
above/below alternation and collision avoidance.
"""

from __future__ import annotations

from dataclasses import dataclass

from nf_metro.parser.model import MetroGraph


@dataclass
class LabelPlacement:
    """Placement information for a station label."""

    station_id: str
    text: str
    x: float
    y: float
    above: bool
    angle: float = 0.0  # Horizontal by default
    text_anchor: str = "middle"
    dominant_baseline: str = ""  # Empty means use above/below logic


def _label_bbox(
    placement: LabelPlacement,
    char_width: float = 7.0,
    font_height: float = 14.0,
) -> tuple[float, float, float, float]:
    """Return (x_min, y_min, x_max, y_max) bounding box for a label."""
    text_width = len(placement.text) * char_width
    half_w = text_width / 2

    if placement.above:
        return (
            placement.x - half_w,
            placement.y - font_height,
            placement.x + half_w,
            placement.y,
        )
    else:
        return (
            placement.x - half_w,
            placement.y,
            placement.x + half_w,
            placement.y + font_height,
        )


def _boxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    margin: float = 2.0,
) -> bool:
    """Check if two bounding boxes overlap."""
    return not (
        a[2] + margin < b[0] or
        b[2] + margin < a[0] or
        a[3] + margin < b[1] or
        b[3] + margin < a[1]
    )


def place_labels(
    graph: MetroGraph,
    label_offset: float = 16.0,
) -> list[LabelPlacement]:
    """Place horizontal labels alternating above/below stations.

    Strategy:
    1. Default: alternate above/below based on layer index.
    2. If it collides with an existing label, try the other side.
    3. If still colliding, push further away.
    """
    sorted_stations = sorted(
        (s for s in graph.stations.values() if not s.is_port),
        key=lambda s: (s.layer, s.track),
    )

    placements: list[LabelPlacement] = []

    for i, station in enumerate(sorted_stations):
        # Check if this is a TB section vertical station (layer > 0)
        is_tb_vert = False
        if station.section_id:
            sec = graph.sections.get(station.section_id)
            if sec and sec.direction == "TB" and station.layer > 0:
                is_tb_vert = True

        if is_tb_vert:
            # Place label to the left of the horizontal pill
            n_lines = len(graph.station_lines(station.id))
            offset_span = (n_lines - 1) * 3.0
            pill_left = station.x - offset_span / 2 - 5
            candidate = LabelPlacement(
                station_id=station.id,
                text=station.label,
                x=pill_left - 6,
                y=station.y,
                above=True,
                text_anchor="end",
                dominant_baseline="central",
            )
            placements.append(candidate)
            continue

        # Alternate by layer (column): even layers below, odd layers above
        start_above = (station.layer % 2 == 1)

        candidate = _try_place(station, label_offset, start_above, placements)

        if _has_collision(candidate, placements):
            # Try the other side
            candidate = _try_place(station, label_offset, not start_above, placements)

            if _has_collision(candidate, placements):
                # Push further in the non-default direction
                direction = -1 if not start_above else 1
                candidate = LabelPlacement(
                    station_id=station.id,
                    text=station.label,
                    x=station.x,
                    y=station.y + direction * label_offset * 2.2,
                    above=(direction < 0),
                )

        placements.append(candidate)

    return placements


def _try_place(
    station,
    label_offset: float,
    above: bool,
    existing: list[LabelPlacement],
) -> LabelPlacement:
    """Create a label placement above or below a station."""
    if above:
        return LabelPlacement(
            station_id=station.id,
            text=station.label,
            x=station.x,
            y=station.y - label_offset,
            above=True,
        )
    else:
        return LabelPlacement(
            station_id=station.id,
            text=station.label,
            x=station.x,
            y=station.y + label_offset,
            above=False,
        )


def _has_collision(
    candidate: LabelPlacement,
    existing: list[LabelPlacement],
) -> bool:
    """Check if a candidate label collides with any existing placement."""
    cbox = _label_bbox(candidate)
    for placed in existing:
        if _boxes_overlap(cbox, _label_bbox(placed)):
            return True
    return False
