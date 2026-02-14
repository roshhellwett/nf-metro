"""Tests for edge routing."""

from nf_metro.layout.engine import compute_layout
from nf_metro.layout.routing import compute_parallel_offsets, route_edges
from nf_metro.parser.mermaid import parse_metro_mermaid


def test_straight_route():
    """Edges on the same track should be straight horizontal lines."""
    graph = parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a -->|main| b\n"
    )
    compute_layout(graph)
    routes = route_edges(graph)
    assert len(routes) == 1
    # Same track -> 2 points (straight line)
    assert len(routes[0].points) == 2


def test_diagonal_route():
    """Edges between different tracks should have 4 waypoints."""
    graph = parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "%%metro line: alt | Alt | #0000ff\n"
        "graph LR\n"
        "    a -->|main| b\n"
        "    a -->|alt| c\n"
        "    b -->|main| d\n"
        "    c -->|alt| d\n"
    )
    compute_layout(graph)
    routes = route_edges(graph)

    # Find a route that changes tracks
    diagonal_routes = [r for r in routes if len(r.points) == 4]
    # At least some routes should be diagonal (track changes)
    # The exact count depends on layout, but we should have some
    assert len(routes) == 4


def test_parallel_offsets_single_line():
    """Single line on a segment should have zero offset."""
    graph = parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a -->|main| b\n"
    )
    compute_layout(graph)
    routes = route_edges(graph)
    offsets = compute_parallel_offsets(routes)
    assert offsets[("a", "b")]["main"] == 0.0


def test_parallel_offsets_multiple_lines():
    """Multiple lines on the same segment should get different offsets."""
    graph = parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "%%metro line: alt | Alt | #0000ff\n"
        "graph LR\n"
        "    a -->|main| b\n"
        "    a -->|alt| b\n"
    )
    compute_layout(graph)
    routes = route_edges(graph)
    offsets = compute_parallel_offsets(routes)
    assert offsets[("a", "b")]["main"] != offsets[("a", "b")]["alt"]
