"""Vergleicht zwei Szenario-Evaluationen aus Tag 14/15 (ohne Modellaufruf)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BEFORE = Path("evaluation_reports/tag15_before/report.json")
AFTER = Path("evaluation_reports/tag15_after/report.json")


def load_summary(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("summary"), dict):
        raise ValueError(f"Ungültiger Bericht: {path}")
    required = {"count", "route_exact_pct", "all_checks_passed", "failures", "sources"}
    if not required.issubset(data["summary"]):
        raise ValueError(f"Bericht ohne benötigte Kennzahlen: {path}")
    return data["summary"]


def compare(before: dict, after: dict) -> str:
    """Zeigt Verbesserung; verhindert irreführende Vergleiche verschiedener Mengen."""
    if before["count"] != after["count"]:
        raise ValueError("Unterschiedliche Fallzahlen: Vergleich nicht zulässig.")
    return (f"Szenarien: {after['count']}\n"
            f"Exaktes Routing: {before['route_exact_pct']:.1f} % -> {after['route_exact_pct']:.1f} %\n"
            f"Vollständig bestanden: {before['all_checks_passed']}/{before['count']}"
            f" -> {after['all_checks_passed']}/{after['count']}\n"
            f"Vorher auffällig: {', '.join(before['failures']) or 'keine'}\n"
            f"Nachher auffällig: {', '.join(after['failures']) or 'keine'}\n"
            f"Router-Quellen vorher: {before['sources']} | nachher: {after['sources']}\n"
            "Hinweis: Offline-Regelrouter, kein Qwen-Leistungstest; keine automatische Freigabe.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tag 15: Vorher-Nachher-Vergleich der 40 Offline-Szenarien")
    parser.add_argument("--before", type=Path, default=BEFORE)
    parser.add_argument("--after", type=Path, default=AFTER)
    args = parser.parse_args(argv)
    try:
        print(compare(load_summary(args.before), load_summary(args.after)))
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
