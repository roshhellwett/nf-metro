"""Tests for SVG rendering."""

import xml.etree.ElementTree as ET

from nf_metro.layout.engine import compute_layout
from nf_metro.parser.mermaid import parse_metro_mermaid
from nf_metro.render.svg import render_svg
from nf_metro.themes import NFCORE_THEME, LIGHT_THEME


def _render_simple():
    graph = parse_metro_mermaid(
        "%%metro title: Test\n"
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a[Input]\n"
        "    b[Output]\n"
        "    a -->|main| b\n"
    )
    compute_layout(graph)
    return render_svg(graph, NFCORE_THEME)


def test_render_produces_valid_svg():
    svg = _render_simple()
    # Should be valid XML
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") or "svg" in root.tag


def test_render_contains_title():
    svg = _render_simple()
    assert "Test" in svg


def test_render_contains_station_labels():
    svg = _render_simple()
    assert "Input" in svg
    assert "Output" in svg


def test_render_contains_line_color():
    svg = _render_simple()
    assert "#ff0000" in svg


def test_render_nfcore_theme_background():
    svg = _render_simple()
    assert NFCORE_THEME.background_color in svg


def test_render_light_theme():
    graph = parse_metro_mermaid(
        "%%metro title: Light Test\n"
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a --> b\n"
    )
    compute_layout(graph)
    svg = render_svg(graph, LIGHT_THEME)
    assert LIGHT_THEME.background_color in svg


def test_render_empty_graph():
    graph = parse_metro_mermaid("graph LR\n")
    svg = render_svg(graph, NFCORE_THEME)
    assert "svg" in svg


def test_render_with_sections():
    graph = parse_metro_mermaid(
        "%%metro title: Sections Test\n"
        "%%metro line: main | Main | #ff0000\n"
        "%%metro section: 1 | Processing | a | b\n"
        "graph LR\n"
        "    a[Input]\n"
        "    b[Output]\n"
        "    a -->|main| b\n"
    )
    compute_layout(graph)
    svg = render_svg(graph, NFCORE_THEME)
    assert "Processing" in svg


def test_render_legend():
    svg = _render_simple()
    # Legend should contain the line display name
    assert "Main" in svg


def test_render_file_size():
    """SVG output should be reasonably small."""
    graph = parse_metro_mermaid(
        "%%metro title: Size Test\n"
        "%%metro line: main | Main | #ff0000\n"
        "%%metro line: alt | Alt | #0000ff\n"
        "graph LR\n"
        "    a[A]\n    b[B]\n    c[C]\n    d[D]\n    e[E]\n"
        "    a -->|main| b\n    b -->|main| c\n    c -->|main| d\n    d -->|main| e\n"
        "    a -->|alt| c\n    c -->|alt| e\n"
    )
    compute_layout(graph)
    svg = render_svg(graph, NFCORE_THEME)
    # Should be well under 50KB for a small graph
    assert len(svg) < 50000
