"""Layout coordinator: combines layer assignment, ordering, and coordinate mapping.

Supports folding: when a diagram exceeds max_layers_per_row, it wraps
onto a new row with reversed direction (like the original nf-core metro
maps that flow L->R then fold down and go R->L).
"""

from __future__ import annotations

import math
from collections import defaultdict, deque

from nf_metro.layout.layers import assign_layers
from nf_metro.layout.ordering import assign_tracks
from nf_metro.parser.model import MetroGraph


def _section_stations(graph: MetroGraph, section, layers: dict[str, int]) -> set[str]:
    """Find stations belonging to a section via flood-fill within the layer range."""
    start = graph.stations.get(section.start_node)
    end = graph.stations.get(section.end_node)
    if not start or not end:
        return set()

    min_layer = min(layers.get(section.start_node, 0), layers.get(section.end_node, 0))
    max_layer = max(layers.get(section.start_node, 0), layers.get(section.end_node, 0))

    adj: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        sl = layers.get(edge.source, -1)
        tl = layers.get(edge.target, -1)
        if min_layer <= sl <= max_layer and min_layer <= tl <= max_layer:
            adj[edge.source].add(edge.target)
            adj[edge.target].add(edge.source)

    visited: set[str] = set()
    queue: deque[str] = deque([section.start_node])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        nl = layers.get(node, -1)
        if nl < min_layer or nl > max_layer:
            continue
        visited.add(node)
        for nb in adj[node]:
            if nb not in visited:
                queue.append(nb)

    return visited


def compute_layout(
    graph: MetroGraph,
    x_spacing: float = 140.0,
    y_spacing: float = 45.0,
    x_offset: float = 80.0,
    y_offset: float = 120.0,
    max_layers_per_row: int | None = None,
    row_gap: float = 120.0,
    section_gap: float = 3.0,
) -> None:
    """Compute layout positions for all stations in the graph.

    Modifies the Station objects in-place, setting their x, y, layer,
    and track attributes.

    Args:
        graph: The metro graph to lay out.
        x_spacing: Horizontal distance between layers.
        y_spacing: Vertical distance between tracks.
        x_offset: Left margin.
        y_offset: Top margin.
        max_layers_per_row: Max layers before folding to next row.
            None = auto-calculate to target roughly 2:1 aspect ratio.
        row_gap: Vertical gap between folded rows.
        section_gap: Extra track units to insert between section boxes.
    """
    # Step 1: Assign layers (horizontal position)
    layers = assign_layers(graph)

    # Step 2: Assign tracks (vertical position within layer)
    tracks = assign_tracks(graph, layers)

    if not layers:
        return

    # Step 2b: Insert vertical gaps between sections so boxes don't overlap
    if graph.sections and section_gap > 0:
        _insert_section_gaps(graph, layers, tracks, section_gap)

    max_layer = max(layers.values())

    # Auto-calculate fold point for roughly 2:1 aspect ratio
    if max_layers_per_row is None:
        total = max_layer + 1
        if total <= 10:
            max_layers_per_row = total  # no fold for small diagrams
        else:
            max_layers_per_row = math.ceil(total / 2)

    # Compute the track span for row height calculation
    all_tracks = list(tracks.values())
    min_track = min(all_tracks) if all_tracks else 0
    max_track = max(all_tracks) if all_tracks else 0
    track_span = max_track - min_track
    row_pixel_height = track_span * y_spacing + row_gap

    # Step 3: Map to pixel coordinates with folding
    for sid, station in graph.stations.items():
        station.layer = layers.get(sid, 0)
        station.track = tracks.get(sid, 0)

        # Which row and position within the row
        row = station.layer // max_layers_per_row
        layer_in_row = station.layer % max_layers_per_row

        # Alternate direction: even rows L->R, odd rows R->L
        if row % 2 == 0:
            station.x = x_offset + layer_in_row * x_spacing
        else:
            station.x = x_offset + (max_layers_per_row - 1 - layer_in_row) * x_spacing

        station.y = y_offset + (station.track - min_track) * y_spacing + row * row_pixel_height



def _insert_section_gaps(
    graph: MetroGraph,
    layers: dict[str, int],
    tracks: dict[str, float],
    gap: float,
) -> None:
    """Add extra track spacing between non-overlapping sections.

    Finds pairs of sections that are vertically adjacent (no track overlap)
    and pushes the lower section's stations down to create a gap.
    """
    # Compute section membership and track ranges
    section_info: list[tuple[set[str], float, float]] = []  # (station_ids, min_track, max_track)
    for section in graph.sections:
        ids = _section_stations(graph, section, layers)
        if not ids:
            continue
        trks = [tracks[sid] for sid in ids if sid in tracks]
        if trks:
            section_info.append((ids, min(trks), max(trks)))

    # Sort by min_track (top to bottom)
    section_info.sort(key=lambda x: x[1])

    # For each pair of adjacent sections, check if they need a gap
    cumulative_shift = 0.0
    shifted_stations: set[str] = set()

    for i in range(1, len(section_info)):
        prev_ids, prev_min, prev_max = section_info[i - 1]
        curr_ids, curr_min, curr_max = section_info[i]

        # Only add gap if sections don't overlap in tracks
        if curr_min > prev_max:
            actual_gap = curr_min - prev_max
            if actual_gap < gap:
                extra = gap - actual_gap
                cumulative_shift += extra

        # Shift all stations at or below the current section's min track
        if cumulative_shift > 0:
            threshold = curr_min  # original min track (before any shifts)
            for sid, trk in tracks.items():
                if trk >= threshold and sid not in shifted_stations:
                    tracks[sid] = trk + cumulative_shift
                    shifted_stations.add(sid)

            # Update section_info for subsequent comparisons
            section_info[i] = (curr_ids, curr_min + cumulative_shift, curr_max + cumulative_shift)


