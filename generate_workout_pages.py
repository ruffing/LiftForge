#!/usr/bin/env python3
"""Generate printable workout log pages from a markdown workout plan.

The script reads a workout markdown file structured with week/day headings and
ordered exercise lists, then writes a print-first HTML document.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any


WEEK_RE = re.compile(r"^\s{0,3}#{1,6}\s+Week\s+(\d+)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
EXERCISE_RE = re.compile(r"^\s*\d+\.\s+(.*?)\s*$")
DASH_SPLIT_RE = re.compile(r"\s+[\u2013\u2014-]\s+")
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")
SET_COUNT_RE = re.compile(r"^(\d+)\s*[xX]\s*\d+")
SET_WORD_RE = re.compile(r"^(\d+)\s+set\b", re.IGNORECASE)


def clean_markdown(text: str) -> str:
    """Strip minimal markdown formatting used in workout entries."""
    unbolded = BOLD_RE.sub(r"\1", text)
    return unbolded.strip()


def parse_workout_markdown(markdown_text: str) -> list[dict[str, Any]]:
    """Parse workout markdown into weeks, days, and exercise rows."""
    weeks: list[dict[str, Any]] = []
    current_week: dict[str, Any] | None = None
    current_day: dict[str, Any] | None = None

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        week_match = WEEK_RE.match(line)
        if week_match:
            week_number = int(week_match.group(1))
            current_week = {"number": week_number, "days": []}
            weeks.append(current_week)
            current_day = None
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match and current_week is not None:
            heading_text = heading_match.group(1).strip()
            if heading_text.lower().startswith("week "):
                continue
            current_day = {"name": heading_text, "exercises": []}
            current_week["days"].append(current_day)
            continue

        exercise_match = EXERCISE_RE.match(line)
        if exercise_match and current_day is not None:
            exercise_text = clean_markdown(exercise_match.group(1))
            parts = DASH_SPLIT_RE.split(exercise_text, maxsplit=1)
            if len(parts) == 2:
                exercise_name, target = parts
            else:
                exercise_name, target = exercise_text, ""
            current_day["exercises"].append(
                {
                    "name": exercise_name.strip(),
                    "target": target.strip(),
                }
            )

    return weeks


def infer_set_count(target: str) -> int:
    """Infer number of sets from target text (e.g., 3x10 -> 3 sets)."""
    cleaned = target.strip()
    if not cleaned:
        return 1

    match = SET_COUNT_RE.match(cleaned)
    if match:
        return max(1, int(match.group(1)))

    match = SET_WORD_RE.match(cleaned)
    if match:
        return max(1, int(match.group(1)))

    return 1


def render_html(weeks: list[dict[str, Any]], cycles: int, document_title: str) -> str:
    """Render parsed workout data to print-optimized HTML."""
    escaped_title = html.escape(document_title)
    html_parts: list[str] = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        f"  <title>{escaped_title}</title>",
        "  <style>",
        "    :root {",
        "      --ink: #1f1f1f;",
        "      --muted: #666;",
        "      --line: #2f2f2f;",
        "      --bg: #fff;",
        "      --shade: #f3f3f3;",
        "      --accent: #0f766e;",
        "      --font: 'IBM Plex Sans', 'Segoe UI', Tahoma, sans-serif;",
        "    }",
        "    * { box-sizing: border-box; }",
        "    html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }",
        "    body { font-family: var(--font); line-height: 1.3; }",
        "    @page { size: Letter portrait; margin: 0.45in; }",
        "    .week-page {",
        "      page-break-after: always;",
        "      break-after: page;",
        "      min-height: 10in;",
        "      display: flex;",
        "      flex-direction: column;",
        "      gap: 0.22in;",
        "    }",
        "    .week-page:last-child { page-break-after: auto; break-after: auto; }",
        "    .page-header { border-bottom: 2px solid var(--line); padding-bottom: 0.08in; }",
        "    .week-title { margin: 0; font-size: 24px; letter-spacing: 0.3px; }",
        "    .week-subtitle { margin: 0.03in 0 0; color: var(--muted); font-size: 12px; }",
        "    .day { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; break-inside: avoid; }",
        "    .day-title { margin: 0; padding: 0.08in 0.1in; background: var(--shade); font-size: 15px; }",
        "    .date-row {",
        "      display: grid;",
        "      grid-template-columns: repeat(" + str(cycles) + ", minmax(0, 1fr));",
        "      gap: 0.08in;",
        "      padding: 0.08in 0.1in 0.06in;",
        "      border-bottom: 1px solid #999;",
        "      font-size: 12px;",
        "    }",
        "    .date-cell { border-bottom: 1px dotted #777; padding-bottom: 2px; white-space: nowrap; }",
        "    table { width: 100%; border-collapse: collapse; table-layout: fixed; }",
        "    th, td { border: 1px solid #8f8f8f; padding: 6px 6px; font-size: 11px; vertical-align: top; }",
        "    th { background: #efefef; text-align: left; }",
        "    .exercise-col { width: 28%; }",
        "    .set-col { width: 6%; }",
        "    .target-col { width: 12%; }",
        "    .weight-col, .reps-col { width: " + f"{(54 / (cycles * 2)):.2f}" + "%; }",
        "    .log-cell { height: 24px; }",
        "    .notes-grid {",
        "      display: grid;",
        "      grid-template-columns: repeat(" + str(cycles) + ", minmax(0, 1fr));",
        "      gap: 0.08in;",
        "      padding: 0.08in 0.1in 0.1in;",
        "    }",
        "    .notes-box { border: 1px solid #888; min-height: 56px; padding: 4px; }",
        "    .notes-label { font-size: 10px; font-weight: 700; color: var(--accent); margin-bottom: 2px; }",
        "    .notes-lines {",
        "      height: 42px;",
        "      background-image: linear-gradient(to bottom, transparent 93%, #d6d6d6 93%);",
        "      background-size: 100% 14px;",
        "    }",
        "    .footer-note { margin-top: auto; font-size: 10px; color: var(--muted); }",
        "    @media print {",
        "      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }",
        "    }",
        "  </style>",
        "</head>",
        "<body>",
    ]

    for week in weeks:
        week_number = week["number"]
        html_parts.extend(
            [
                "  <section class=\"week-page\">",
                "    <header class=\"page-header\">",
                f"      <h1 class=\"week-title\">Week {week_number} Workout Log</h1>",
                "      <p class=\"week-subtitle\">Record date, weight x reps, and notes each time you repeat this week.</p>",
                "    </header>",
            ]
        )

        for day in week["days"]:
            day_name = html.escape(day["name"])
            html_parts.append("    <article class=\"day\">")
            html_parts.append(f"      <h2 class=\"day-title\">{day_name}</h2>")

            html_parts.append("      <div class=\"date-row\">")
            for cycle_index in range(1, cycles + 1):
                html_parts.append(
                    f"        <div class=\"date-cell\">Cycle {cycle_index} Date: __________</div>"
                )
            html_parts.append("      </div>")

            html_parts.append("      <table>")
            html_parts.append("        <thead>")
            html_parts.append("          <tr>")
            html_parts.append("            <th class=\"exercise-col\">Exercise</th>")
            html_parts.append("            <th class=\"set-col\">Set</th>")
            html_parts.append("            <th class=\"target-col\">Target</th>")
            for cycle_index in range(1, cycles + 1):
                html_parts.append(
                    f"            <th colspan=\"2\">Cycle {cycle_index}</th>"
                )
            html_parts.append("          </tr>")
            html_parts.append("          <tr>")
            html_parts.append("            <th class=\"exercise-col\"></th>")
            html_parts.append("            <th class=\"set-col\"></th>")
            html_parts.append("            <th class=\"target-col\"></th>")
            for _ in range(cycles):
                html_parts.append("            <th class=\"weight-col\">Weight</th>")
                html_parts.append("            <th class=\"reps-col\">Reps</th>")
            html_parts.append("          </tr>")
            html_parts.append("        </thead>")
            html_parts.append("        <tbody>")

            for exercise in day["exercises"]:
                exercise_name = html.escape(exercise["name"])
                exercise_target = html.escape(exercise["target"])
                set_count = infer_set_count(exercise["target"])
                for set_index in range(1, set_count + 1):
                    html_parts.append("          <tr>")
                    if set_index == 1:
                        html_parts.append(
                            f"            <td rowspan=\"{set_count}\">{exercise_name}</td>"
                        )
                    html_parts.append(f"            <td>S{set_index}</td>")
                    if set_index == 1:
                        html_parts.append(
                            f"            <td rowspan=\"{set_count}\">{exercise_target}</td>"
                        )
                    for _ in range(cycles):
                        html_parts.append("            <td class=\"log-cell\"></td>")
                        html_parts.append("            <td class=\"log-cell\"></td>")
                    html_parts.append("          </tr>")

            html_parts.append("        </tbody>")
            html_parts.append("      </table>")

            html_parts.append("      <div class=\"notes-grid\">")
            for cycle_index in range(1, cycles + 1):
                html_parts.append("        <div class=\"notes-box\">")
                html_parts.append(
                    f"          <div class=\"notes-label\">Cycle {cycle_index} Notes</div>"
                )
                html_parts.append("          <div class=\"notes-lines\"></div>")
                html_parts.append("        </div>")
            html_parts.append("      </div>")

            html_parts.append("    </article>")

        html_parts.append(
            "    <p class=\"footer-note\">Tip: Print double-sided and keep each weekly page in a binder sleeve for reuse.</p>"
        )
        html_parts.append("  </section>")

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate printable workout log pages from markdown"
    )
    parser.add_argument(
        "--input",
        default="workout.md",
        help="Path to input markdown file (default: workout.md)",
    )
    parser.add_argument(
        "--output",
        default="workout_printable.html",
        help="Path to output HTML file (default: workout_printable.html)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=2,
        help="How many repeat cycle sections to include per week page (default: 2)",
    )
    parser.add_argument(
        "--title",
        default="Workout Log Pages",
        help="Title for generated HTML document",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.cycles < 1:
        raise SystemExit("--cycles must be at least 1")

    input_path = Path(args.input)
    output_path = Path(args.output)

    markdown_text = input_path.read_text(encoding="utf-8")
    weeks = parse_workout_markdown(markdown_text)

    if not weeks:
        raise SystemExit(
            "No week structure found. Expected headings like '# Week 1' and day/exercise lists."
        )

    rendered = render_html(weeks=weeks, cycles=args.cycles, document_title=args.title)
    output_path.write_text(rendered, encoding="utf-8")

    print(
        f"Generated {output_path} with {len(weeks)} week pages and {args.cycles} cycle columns each."
    )


if __name__ == "__main__":
    main()
