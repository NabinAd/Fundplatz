"""Gemeinsame Terminal-Demo für Information, Negotiation und Logistics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from .inputs import AgentInput, CustomerRequest, InputValidationError
from .ollama_client import OllamaClient
from .pipeline import AgentPipeline

DEFAULT_FILE = Path(__file__).resolve().parent / "examples" / "tag7_input.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fundplatz Phase 2: Agenten Tag 9–11")
    parser.add_argument("--datei", type=Path, default=DEFAULT_FILE, help="Produkt-/Kunden-JSON")
    parser.add_argument("--frage", help="Kundenfrage für den Test überschreiben")
    parser.add_argument("--offline", action="store_true", help="Nur Regelrouter und sichere Basisentwürfe")
    parser.add_argument("--beispiele", action="store_true", help="Vier Fragen nacheinander testen")
    parser.add_argument("--modell", help="Optionaler Ollama-Modellname")
    args = parser.parse_args(argv)

    try:
        raw = json.loads(args.datei.read_text(encoding="utf-8"))
        if args.frage is not None:
            if not isinstance(raw, dict) or not isinstance(raw.get("request"), dict):
                raise InputValidationError("root.request: JSON-Objekt erwartet.")
            raw["request"]["message"] = args.frage
        data = AgentInput.from_dict(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, InputValidationError) as exc:
        print(f"EINGABEFEHLER: {exc}")
        return 1

    pipeline = AgentPipeline(
        llm=None if args.offline else OllamaClient(model=args.modell),
        offline=args.offline,
    )
    if args.beispiele:
        examples = [
            ("Information", "Wie ist der Zustand des Laptops?"),
            ("Negotiation", "Wäre 100 Euro okay?"),
            ("Logistics", "Ist Versand möglich?"),
            ("Alle drei", "Wie ist der Zustand, ist Versand möglich und wäre 100 Euro okay?"),
        ]
        for label, question in examples:
            result = pipeline.run(AgentInput(data.product, CustomerRequest(question)))
            print(f"\n[{label}] {question}")
            print("Gewählt:", ", ".join(result.route.agents) or "Rückfrage")
            print(result.combined_draft)
        print("\nACHTUNG: Alle Texte sind Entwürfe ohne Verkäuferfreigabe.")
        return 0

    started = perf_counter()
    result = pipeline.run(data)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print(f"\nDauer: {perf_counter() - started:.2f} Sekunden")
    print("HINWEIS: Nur Entwurf. Keine faktische LLM-Validierung, keine Freigabe, kein Nachrichtenversand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
