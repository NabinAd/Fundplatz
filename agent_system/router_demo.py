"""Terminal-Demo für Tag 8: Routing mit Ollama oder nachvollziehbaren Regeln."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from .inputs import AgentInput, InputValidationError
from .ollama_client import OllamaClient
from .router import Orchestrator

EXAMPLE_FILE = Path(__file__).resolve().parent / "examples" / "tag7_input.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fundplatz Tag 8: Agenten-Router")
    parser.add_argument("--datei", type=Path, default=EXAMPLE_FILE, help="Tag-7-JSON-Eingabe")
    parser.add_argument("--frage", help="Eigene Kundenfrage")
    parser.add_argument("--modell", help="Optionaler Ollama-Modellname")
    parser.add_argument("--offline", action="store_true", help="Nur Regelrouter, kein Ollama")
    args = parser.parse_args(argv)

    try:
        raw = json.loads(args.datei.read_text(encoding="utf-8"))
        if args.frage is not None:
            if not isinstance(raw, dict) or not isinstance(raw.get("request"), dict):
                raise InputValidationError("root.request: JSON-Objekt erwartet.")
            raw["request"]["message"] = args.frage
        input_data = AgentInput.from_dict(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, InputValidationError) as exc:
        print(f"EINGABEFEHLER: {exc}")
        return 1

    router = Orchestrator(llm=OllamaClient(model=args.modell), use_llm=not args.offline)
    started = perf_counter()
    decision = router.route(input_data)
    print("Routerentscheidung:")
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
    print(f"Dauer: {perf_counter() - started:.2f} Sekunden")
    if decision.warning:
        print("ACHTUNG: Ollama konnte nicht korrekt klassifizieren. Fallback ist nur heuristisch.")
    if decision.needs_clarification:
        print("Ergebnis: Bitte Anliegen präzisieren; kein Agent ausgewählt.")
    print("Hinweis: Noch keine Agentenantwort, keine Validierung der Produktfakten und keine Freigabe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
