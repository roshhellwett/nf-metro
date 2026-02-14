"""Tests for the Mermaid + metro directive parser."""

from pathlib import Path

from nf_metro.parser.mermaid import parse_metro_mermaid


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_title():
    text = "%%metro title: My Pipeline\ngraph LR\n"
    graph = parse_metro_mermaid(text)
    assert graph.title == "My Pipeline"


def test_parse_style():
    text = "%%metro style: light\ngraph LR\n"
    graph = parse_metro_mermaid(text)
    assert graph.style == "light"


def test_parse_lines():
    text = (
        "%%metro line: main | Main Line | #ff0000\n"
        "%%metro line: alt | Alt Line | #0000ff\n"
        "graph LR\n"
    )
    graph = parse_metro_mermaid(text)
    assert len(graph.lines) == 2
    assert graph.lines["main"].display_name == "Main Line"
    assert graph.lines["main"].color == "#ff0000"
    assert graph.lines["alt"].color == "#0000ff"


def test_parse_sections():
    text = (
        "%%metro section: 1 | Preprocessing | a | b\n"
        "graph LR\n"
    )
    graph = parse_metro_mermaid(text)
    assert len(graph.sections) == 1
    assert graph.sections[0].name == "Preprocessing"
    assert graph.sections[0].start_node == "a"
    assert graph.sections[0].end_node == "b"


def test_parse_nodes_square_bracket():
    text = "graph LR\n    fastqc[FastQC]\n"
    graph = parse_metro_mermaid(text)
    assert "fastqc" in graph.stations
    assert graph.stations["fastqc"].label == "FastQC"


def test_parse_nodes_bare():
    text = "graph LR\n    mynode\n"
    graph = parse_metro_mermaid(text)
    assert "mynode" in graph.stations
    assert graph.stations["mynode"].label == "mynode"


def test_parse_edges():
    text = (
        "graph LR\n"
        "    a[Input]\n"
        "    b[Output]\n"
        "    a -->|main| b\n"
    )
    graph = parse_metro_mermaid(text)
    assert len(graph.edges) == 1
    assert graph.edges[0].source == "a"
    assert graph.edges[0].target == "b"
    assert graph.edges[0].line_id == "main"


def test_parse_edges_no_label():
    text = "graph LR\n    a --> b\n"
    graph = parse_metro_mermaid(text)
    assert len(graph.edges) == 1
    assert graph.edges[0].line_id == "default"


def test_station_lines():
    text = (
        "%%metro line: main | Main | #ff0000\n"
        "%%metro line: alt | Alt | #0000ff\n"
        "graph LR\n"
        "    a -->|main| b\n"
        "    a -->|alt| c\n"
    )
    graph = parse_metro_mermaid(text)
    lines = graph.station_lines("a")
    assert "main" in lines
    assert "alt" in lines


def test_line_stations():
    text = (
        "%%metro line: main | Main | #ff0000\n"
        "graph LR\n"
        "    a -->|main| b\n"
        "    b -->|main| c\n"
    )
    graph = parse_metro_mermaid(text)
    stations = graph.line_stations("main")
    assert stations == ["a", "b", "c"]


def test_parse_simple_fixture():
    text = (FIXTURES / "rnaseq_simple.mmd").read_text()
    graph = parse_metro_mermaid(text)
    assert graph.title == "Test Pipeline"
    assert len(graph.stations) == 4
    assert len(graph.edges) == 4
    assert len(graph.lines) == 2


def test_parse_full_fixture():
    text = (FIXTURES / "rnaseq_full.mmd").read_text()
    graph = parse_metro_mermaid(text)
    assert graph.title == "nf-core/rnaseq"
    assert len(graph.stations) == 6
    assert len(graph.edges) == 6
    assert len(graph.lines) == 3
    assert len(graph.sections) == 2


def test_ignores_comments():
    text = (
        "%% This is a regular comment\n"
        "%%metro title: Test\n"
        "graph LR\n"
        "    a --> b\n"
    )
    graph = parse_metro_mermaid(text)
    assert graph.title == "Test"
    assert len(graph.edges) == 1
