"""Parser for Mermaid graph definitions with %%metro directives.

Uses a simple line-by-line approach rather than a full grammar parser,
since the Mermaid subset we need is straightforward.
"""

from __future__ import annotations

import re

from nf_metro.parser.model import Edge, MetroGraph, MetroLine, Section, Station


def parse_metro_mermaid(text: str) -> MetroGraph:
    """Parse a Mermaid graph definition with %%metro directives."""
    graph = MetroGraph()
    lines = text.strip().split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Metro directives
        if stripped.startswith("%%metro"):
            _parse_directive(stripped, graph)
            continue

        # Skip regular comments and graph declaration
        if stripped.startswith("%%") or stripped.startswith("graph "):
            continue

        # Try edge first (contains arrow)
        if "-->" in stripped or "---" in stripped or "==>" in stripped:
            _parse_edge(stripped, graph)
            continue

        # Try node definition
        _parse_node(stripped, graph)

    return graph


def _parse_directive(line: str, graph: MetroGraph) -> None:
    """Parse a %%metro directive line."""
    # Remove %%metro prefix
    content = line[len("%%metro"):].strip()

    if content.startswith("title:"):
        graph.title = content[len("title:"):].strip()
    elif content.startswith("style:"):
        graph.style = content[len("style:"):].strip()
    elif content.startswith("line:"):
        parts = content[len("line:"):].strip().split("|")
        if len(parts) >= 3:
            graph.add_line(MetroLine(
                id=parts[0].strip(),
                display_name=parts[1].strip(),
                color=parts[2].strip(),
            ))
    elif content.startswith("section:"):
        parts = content[len("section:"):].strip().split("|")
        if len(parts) >= 4:
            graph.add_section(Section(
                number=int(parts[0].strip()),
                name=parts[1].strip(),
                start_node=parts[2].strip(),
                end_node=parts[3].strip(),
            ))


# Regex patterns for node shapes
_NODE_PATTERNS = [
    # stadium: node_id([label])
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\[(.+?)\]\)$"),
    # subroutine: node_id[[label]]
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\[\[(.+?)\]\]$"),
    # circle: node_id((label))
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\((.+?)\)\)$"),
    # square bracket: node_id[label]
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+?)\]$"),
    # round bracket: node_id(label)
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\((.+?)\)$"),
    # rhombus: node_id{label}
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\{(.+?)\}$"),
    # bare id
    re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)$"),
]

# Edge pattern: source -->|label| target  or  source --> target
_EDGE_PATTERN = re.compile(
    r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*"   # source
    r"(-->|---|==>)"                     # arrow
    r"(?:\|([^|]*)\|)?\s*"              # optional |label|
    r"([a-zA-Z_][a-zA-Z0-9_]*)$"       # target
)


def _parse_node(line: str, graph: MetroGraph) -> None:
    """Parse a node definition line."""
    for pattern in _NODE_PATTERNS:
        m = pattern.match(line)
        if m:
            node_id = m.group(1)
            label = m.group(2).strip() if m.lastindex >= 2 else node_id
            if node_id not in graph.stations:
                graph.add_station(Station(id=node_id, label=label))
            else:
                # Update label if station was auto-created from an edge
                graph.stations[node_id].label = label
            return


def _parse_edge(line: str, graph: MetroGraph) -> None:
    """Parse an edge definition line.

    Supports comma-separated line IDs: a -->|line1,line2,line3| b
    Creates a separate Edge for each line ID.
    """
    m = _EDGE_PATTERN.match(line)
    if not m:
        return

    source = m.group(1)
    label = m.group(3).strip() if m.group(3) else "default"
    target = m.group(4)

    # Ensure stations exist
    if source not in graph.stations:
        graph.add_station(Station(id=source, label=source))
    if target not in graph.stations:
        graph.add_station(Station(id=target, label=target))

    # Split comma-separated line IDs
    line_ids = [lid.strip() for lid in label.split(",")]
    for line_id in line_ids:
        graph.add_edge(Edge(source=source, target=target, line_id=line_id))
