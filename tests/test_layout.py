"""Tests for the layout engine."""

from nf_metro.layout.engine import compute_layout
from nf_metro.layout.layers import assign_layers
from nf_metro.layout.ordering import assign_tracks
from nf_metro.parser.mermaid import parse_metro_mermaid


def _make_simple_graph():
    return parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a[A]\n"
        "    b[B]\n"
        "    c[C]\n"
        "    a -->|main| b\n"
        "    b -->|main| c\n"
    )


def _make_branching_graph():
    return parse_metro_mermaid(
        "%%metro line: main | Main | #ff0000\n"
        "%%metro line: alt | Alt | #0000ff\n"
        "graph LR\n"
        "    a[A]\n"
        "    b[B]\n"
        "    c[C]\n"
        "    d[D]\n"
        "    a -->|main| b\n"
        "    b -->|main| d\n"
        "    a -->|alt| c\n"
        "    c -->|alt| d\n"
    )


def test_layer_assignment_linear():
    graph = _make_simple_graph()
    layers = assign_layers(graph)
    assert layers["a"] == 0
    assert layers["b"] == 1
    assert layers["c"] == 2


def test_layer_assignment_branching():
    graph = _make_branching_graph()
    layers = assign_layers(graph)
    assert layers["a"] == 0
    # b and c both have a as predecessor, so both at layer 1
    assert layers["b"] == 1
    assert layers["c"] == 1
    # d has b and c as predecessors (both at layer 1), so at layer 2
    assert layers["d"] == 2


def test_track_assignment():
    graph = _make_branching_graph()
    layers = assign_layers(graph)
    tracks = assign_tracks(graph, layers)
    # a is alone in layer 0
    assert tracks["a"] == 0
    # b and c are in layer 1 - should be on different tracks
    assert tracks["b"] != tracks["c"]


def test_compute_layout_sets_coordinates():
    graph = _make_simple_graph()
    compute_layout(graph, x_spacing=100, y_spacing=50, x_offset=10, y_offset=10)
    # Check that coordinates were set
    assert graph.stations["a"].x == 10  # layer 0
    assert graph.stations["b"].x == 110  # layer 1
    assert graph.stations["c"].x == 210  # layer 2


def test_compute_layout_branching():
    graph = _make_branching_graph()
    compute_layout(graph, x_spacing=100, y_spacing=50, x_offset=10, y_offset=10)
    # a at layer 0
    assert graph.stations["a"].layer == 0
    # d at layer 2
    assert graph.stations["d"].layer == 2
    # b and c at same layer but different tracks
    assert graph.stations["b"].layer == graph.stations["c"].layer == 1
    assert graph.stations["b"].track != graph.stations["c"].track
