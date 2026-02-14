"""Data model for metro map graphs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetroLine:
    """A metro line (colored route through the graph)."""

    id: str
    display_name: str
    color: str


@dataclass
class Station:
    """A node/station in the metro map."""

    id: str
    label: str
    # Populated by layout engine
    x: float = 0.0
    y: float = 0.0
    layer: int = 0
    track: float = 0.0


@dataclass
class Edge:
    """A directed edge between stations, belonging to a metro line."""

    source: str
    target: str
    line_id: str


@dataclass
class Section:
    """A visual grouping of stations (background rectangle)."""

    number: int
    name: str
    start_node: str
    end_node: str


@dataclass
class RouteSegment:
    """A segment of a routed edge path (populated by routing engine)."""

    x1: float
    y1: float
    x2: float
    y2: float
    line_id: str
    edge: Edge | None = None


@dataclass
class MetroGraph:
    """Complete metro map graph definition."""

    title: str = ""
    style: str = "dark"
    lines: dict[str, MetroLine] = field(default_factory=dict)
    stations: dict[str, Station] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def add_line(self, line: MetroLine) -> None:
        self.lines[line.id] = line

    def add_station(self, station: Station) -> None:
        self.stations[station.id] = station

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def add_section(self, section: Section) -> None:
        self.sections.append(section)

    def station_lines(self, station_id: str) -> list[str]:
        """Return line IDs that pass through a station."""
        line_ids = set()
        for edge in self.edges:
            if edge.source == station_id or edge.target == station_id:
                line_ids.add(edge.line_id)
        return sorted(line_ids)

    def line_stations(self, line_id: str) -> list[str]:
        """Return station IDs on a line, in edge order."""
        stations = []
        seen = set()
        for edge in self.edges:
            if edge.line_id == line_id:
                if edge.source not in seen:
                    stations.append(edge.source)
                    seen.add(edge.source)
                if edge.target not in seen:
                    stations.append(edge.target)
                    seen.add(edge.target)
        return stations
