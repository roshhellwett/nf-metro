"""Edge routing for metro map layout.

Routes edges as horizontal segments with 45-degree diagonal transitions.
For folded layouts, cross-row edges route through the fold edge with a
clean vertical drop.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from nf_metro.parser.model import Edge, MetroGraph


@dataclass
class RoutedPath:
    """A routed path for an edge, consisting of (x, y) waypoints."""

    edge: Edge
    line_id: str
    points: list[tuple[float, float]]


def route_edges(
    graph: MetroGraph,
    diagonal_run: float = 30.0,
) -> list[RoutedPath]:
    """Route all edges with smooth direction changes.

    Detects cross-row edges (large Y gap relative to X gap) and routes
    them through a vertical connector at the fold edge.
    """
    routes: list[RoutedPath] = []

    # Detect fold: find the max X position (fold edge)
    all_x = [s.x for s in graph.stations.values()]
    fold_x = max(all_x) if all_x else 0

    for edge in graph.edges:
        src = graph.stations[edge.source]
        tgt = graph.stations[edge.target]

        sx, sy = src.x, src.y
        tx, ty = tgt.x, tgt.y
        dx = tx - sx
        dy = ty - sy

        # Detect cross-row edge: target is to the left (only in folded layouts)
        is_cross_row = dx <= 0 and abs(dy) > 80

        if is_cross_row:
            # Route through fold edge: horizontal to fold, vertical drop,
            # horizontal to target
            fold_margin = 30
            fold_right = fold_x + fold_margin
            routes.append(RoutedPath(
                edge=edge, line_id=edge.line_id,
                points=[
                    (sx, sy),
                    (fold_right, sy),
                    (fold_right, ty),
                    (tx, ty),
                ],
            ))
        elif abs(sy - ty) < 0.01:
            # Same track: straight line
            routes.append(RoutedPath(
                edge=edge, line_id=edge.line_id,
                points=[(sx, sy), (tx, ty)],
            ))
        else:
            # Different tracks: horizontal, diagonal, horizontal
            if abs(dx) < 1.0:
                routes.append(RoutedPath(
                    edge=edge, line_id=edge.line_id,
                    points=[(sx, sy), (tx, ty)],
                ))
                continue

            sign = 1.0 if dx > 0 else -1.0
            half_diag = diagonal_run / 2

            mid_x = (sx + tx) / 2
            diag_start_x = mid_x - sign * half_diag
            diag_end_x = mid_x + sign * half_diag

            if sign > 0:
                diag_start_x = max(diag_start_x, sx + 10)
                diag_end_x = min(diag_end_x, tx - 10)
            else:
                diag_start_x = min(diag_start_x, sx - 10)
                diag_end_x = max(diag_end_x, tx + 10)

            routes.append(RoutedPath(
                edge=edge, line_id=edge.line_id,
                points=[
                    (sx, sy),
                    (diag_start_x, sy),
                    (diag_end_x, ty),
                    (tx, ty),
                ],
            ))

    return routes


def compute_station_offsets(
    graph: MetroGraph,
    offset_step: float = 3.0,
) -> dict[tuple[str, str], float]:
    """Compute per-station Y offsets for each line.

    At each station, lines are stacked in definition order: the first
    line sits at offset 0, subsequent lines stack below. This keeps
    each line at a consistent position as it passes through a station,
    so transitions between bundles of different sizes are smooth.

    Returns dict mapping (station_id, line_id) -> y_offset.
    """
    line_order = list(graph.lines.keys())
    line_priority = {lid: i for i, lid in enumerate(line_order)}

    offsets: dict[tuple[str, str], float] = {}
    for sid in graph.stations:
        lines = graph.station_lines(sid)
        lines.sort(key=lambda l: line_priority.get(l, 999))
        for i, lid in enumerate(lines):
            offsets[(sid, lid)] = i * offset_step

    return offsets
