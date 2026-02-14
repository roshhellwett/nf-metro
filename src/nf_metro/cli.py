"""CLI for nf-metro."""

from __future__ import annotations

from pathlib import Path

import click

from nf_metro import __version__
from nf_metro.layout import compute_layout
from nf_metro.parser import parse_metro_mermaid
from nf_metro.render import render_svg
from nf_metro.themes import THEMES


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """nf-metro: Generate metro-map-style SVG diagrams from Mermaid definitions."""


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output SVG file path. Defaults to <input>.svg")
@click.option("--theme", type=click.Choice(list(THEMES.keys())), default="nfcore",
              help="Visual theme (default: nfcore)")
@click.option("--width", type=int, default=None, help="SVG width in pixels")
@click.option("--height", type=int, default=None, help="SVG height in pixels")
@click.option("--x-spacing", type=float, default=160.0,
              help="Horizontal spacing between layers (default: 160)")
@click.option("--y-spacing", type=float, default=50.0,
              help="Vertical spacing between tracks (default: 50)")
@click.option("--max-layers-per-row", type=int, default=None,
              help="Max layers before folding to next row (default: auto)")
def render(
    input_file: Path,
    output: Path | None,
    theme: str,
    width: int | None,
    height: int | None,
    x_spacing: float,
    y_spacing: float,
    max_layers_per_row: int | None,
) -> None:
    """Render a Mermaid metro map definition to SVG."""
    text = input_file.read_text()
    graph = parse_metro_mermaid(text)

    compute_layout(graph, x_spacing=x_spacing, y_spacing=y_spacing,
                   max_layers_per_row=max_layers_per_row)

    theme_obj = THEMES[theme]
    svg = render_svg(graph, theme_obj, width=width, height=height)

    if output is None:
        output = input_file.with_suffix(".svg")

    output.write_text(svg)
    click.echo(f"Rendered {len(graph.stations)} stations, "
               f"{len(graph.edges)} edges, "
               f"{len(graph.lines)} lines -> {output}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
def validate(input_file: Path) -> None:
    """Validate a Mermaid metro map definition."""
    text = input_file.read_text()
    try:
        graph = parse_metro_mermaid(text)
    except Exception as e:
        click.echo(f"Parse error: {e}", err=True)
        raise SystemExit(1)

    errors = []

    # Check that all edge line_ids reference defined lines
    for edge in graph.edges:
        if edge.line_id != "default" and edge.line_id not in graph.lines:
            errors.append(f"Edge {edge.source} -> {edge.target} references "
                          f"undefined line '{edge.line_id}'")

    # Check that legacy section nodes exist
    for section in graph.legacy_sections:
        if section.start_node not in graph.stations:
            errors.append(f"Section '{section.name}' references unknown "
                          f"start node '{section.start_node}'")
        if section.end_node not in graph.stations:
            errors.append(f"Section '{section.name}' references unknown "
                          f"end node '{section.end_node}'")

    # Check that first-class section station IDs exist
    for section in graph.sections.values():
        for sid in section.station_ids:
            if sid not in graph.stations:
                errors.append(f"Section '{section.name}' references unknown "
                              f"station '{sid}'")

    if errors:
        click.echo("Validation errors:", err=True)
        for err in errors:
            click.echo(f"  - {err}", err=True)
        raise SystemExit(1)

    total_sections = len(graph.sections) + len(graph.legacy_sections)
    click.echo(f"Valid: {len(graph.stations)} stations, "
               f"{len(graph.edges)} edges, "
               f"{len(graph.lines)} lines, "
               f"{total_sections} sections")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
def info(input_file: Path) -> None:
    """Show information about a Mermaid metro map definition."""
    text = input_file.read_text()
    graph = parse_metro_mermaid(text)

    click.echo(f"Title: {graph.title or '(none)'}")
    click.echo(f"Style: {graph.style}")
    click.echo(f"Stations: {len(graph.stations)}")
    click.echo(f"Edges: {len(graph.edges)}")
    click.echo(f"Lines: {len(graph.lines)}")
    for lid, line in graph.lines.items():
        stations = graph.line_stations(lid)
        click.echo(f"  {line.display_name} ({line.color}): "
                    f"{len(stations)} stations")
    total_sections = len(graph.sections) + len(graph.legacy_sections)
    click.echo(f"Sections: {total_sections}")
    for section in graph.sections.values():
        click.echo(f"  [{section.number}] {section.name}: "
                    f"{len(section.station_ids)} stations")
    for section in graph.legacy_sections:
        click.echo(f"  [{section.number}] {section.name}: "
                    f"{section.start_node} -> {section.end_node}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output file path. Defaults to <input>_sections.mmd")
def convert(input_file: Path, output: Path | None) -> None:
    """Convert a legacy-format metro map to the new subgraph format.

    Reads a .mmd file using %%metro section: directives and rewrites it
    using Mermaid subgraph syntax with %%metro entry/exit directives.
    """
    from nf_metro.layout.layers import assign_layers

    text = input_file.read_text()
    graph = parse_metro_mermaid(text)

    if not graph.legacy_sections:
        click.echo("No legacy sections found - file may already use subgraph format.")
        return

    # We need layer assignments to determine section membership
    layers = assign_layers(graph)

    # Build section membership using flood-fill (same as rendering)
    from nf_metro.layout.engine import _section_stations
    section_membership: dict[str, int] = {}  # station_id -> section_number
    section_station_sets: dict[int, set[str]] = {}
    for section in graph.legacy_sections:
        ids = _section_stations(graph, section, layers)
        section_station_sets[section.number] = ids
        for sid in ids:
            section_membership[sid] = section.number

    # Determine inter-section edges for entry/exit directives
    section_exits: dict[int, set[str]] = {}  # section_number -> set of line_ids exiting
    section_entries: dict[int, set[str]] = {}  # section_number -> set of line_ids entering
    for edge in graph.edges:
        src_sec = section_membership.get(edge.source)
        tgt_sec = section_membership.get(edge.target)
        if src_sec and tgt_sec and src_sec != tgt_sec:
            section_exits.setdefault(src_sec, set()).add(edge.line_id)
            section_entries.setdefault(tgt_sec, set()).add(edge.line_id)

    # Generate output
    out_lines: list[str] = []

    # Copy header directives
    for line in text.strip().split("\n"):
        stripped = line.strip()
        if stripped.startswith("%%metro title:") or stripped.startswith("%%metro style:") or stripped.startswith("%%metro line:"):
            out_lines.append(stripped)
        elif stripped.startswith("%%metro section:"):
            continue  # Skip legacy sections
        elif stripped == "":
            continue

    out_lines.append("")
    out_lines.append("graph LR")

    # Output each section as a subgraph
    for section in graph.legacy_sections:
        ids = section_station_sets.get(section.number, set())
        if not ids:
            continue

        section_id = section.name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
        out_lines.append(f"    subgraph {section_id} [{section.name}]")

        # Entry directive
        entries = section_entries.get(section.number)
        if entries:
            out_lines.append(f"        %%metro entry: left | {', '.join(sorted(entries))}")

        # Exit directive
        exits = section_exits.get(section.number)
        if exits:
            out_lines.append(f"        %%metro exit: right | {', '.join(sorted(exits))}")

        # Station definitions
        for sid in sorted(ids, key=lambda s: layers.get(s, 0)):
            station = graph.stations[sid]
            if station.label != sid:
                out_lines.append(f"        {sid}[{station.label}]")
            else:
                out_lines.append(f"        {sid}")

        out_lines.append("")

        # Internal edges
        for edge in graph.edges:
            if edge.source in ids and edge.target in ids:
                out_lines.append(f"        {edge.source} -->|{edge.line_id}| {edge.target}")

        out_lines.append("    end")
        out_lines.append("")

    # Inter-section edges
    out_lines.append("    %% Inter-section edges")
    for edge in graph.edges:
        src_sec = section_membership.get(edge.source)
        tgt_sec = section_membership.get(edge.target)
        if src_sec and tgt_sec and src_sec != tgt_sec:
            out_lines.append(f"    {edge.source} -->|{edge.line_id}| {edge.target}")

    # Unsectioned stations and edges
    unsectioned = [sid for sid in graph.stations if sid not in section_membership]
    if unsectioned:
        out_lines.append("")
        out_lines.append("    %% Unsectioned stations")
        for sid in unsectioned:
            station = graph.stations[sid]
            if station.label != sid:
                out_lines.append(f"    {sid}[{station.label}]")
            else:
                out_lines.append(f"    {sid}")
        for edge in graph.edges:
            if edge.source in unsectioned or edge.target in unsectioned:
                if not (edge.source in section_membership and edge.target in section_membership):
                    out_lines.append(f"    {edge.source} -->|{edge.line_id}| {edge.target}")

    result = "\n".join(out_lines) + "\n"

    if output is None:
        output = input_file.with_name(input_file.stem + "_sections.mmd")

    output.write_text(result)
    click.echo(f"Converted {len(graph.legacy_sections)} legacy sections -> {output}")
