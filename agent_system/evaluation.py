"""Tag 14: messbare, reproduzierbare Evaluation des Agentensystems.

Die Erwartungen stehen in einer separat gepflegten JSON-Datei und werden NICHT
vom Router abgeleitet. Keine Nachrichten werden an Kunden gesendet.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .inputs import AgentInput, InputValidationError
from .pipeline import AgentPipeline
from .router import AGENTS
from .validation import DRAFT_BLOCK, _COMMITMENT, _NUMBERS, _UNAUTHORIZED_DELIVERY

DEFAULT_CASES = Path(__file__).resolve().parent / "examples" / "tag14_scenarios.json"
DEFAULT_REPORT_DIR = Path("evaluation_reports") / "tag14_offline"


class EvaluationDataError(ValueError):
    """Ein Evaluationsdatensatz ist fehlerhaft oder unvollständig."""


def load_cases(path: Path = DEFAULT_CASES) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvaluationDataError(f"Testszenarien konnten nicht geladen werden: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise EvaluationDataError("Szenario-Datei benötigt version=1.")
    base = data.get("base_product")
    scenarios = data.get("scenarios")
    if not isinstance(base, dict) or not isinstance(scenarios, list) or not scenarios:
        raise EvaluationDataError("base_product-Objekt und nichtleere scenarios-Liste erforderlich.")
    required = {"id", "category", "question", "expected_agents", "product_overrides",
                "expected_text_fragments", "expected_audit_codes", "expected_blocked_agents"}
    unique: set[str] = set()
    for idx, case in enumerate(scenarios, 1):
        if not isinstance(case, dict) or not required.issubset(case):
            raise EvaluationDataError(f"Fall {idx}: erwartete Felder fehlen.")
        if not isinstance(case["id"], str) or not re.fullmatch(r"[A-Z]\d{2}", case["id"]):
            raise EvaluationDataError(f"Fall {idx}: ungültige Fall-ID.")
        if case["id"] in unique:
            raise EvaluationDataError(f"Doppelte Fall-ID: {case['id']}.")
        unique.add(case["id"])
        if not isinstance(case["category"], str) or not case["category"].strip():
            raise EvaluationDataError(f"Fall {idx}: category muss Text sein.")
        if not isinstance(case["question"], str) or not case["question"].strip():
            raise EvaluationDataError(f"Fall {idx}: Frage fehlt.")
        if not isinstance(case["product_overrides"], dict):
            raise EvaluationDataError(f"Fall {idx}: product_overrides muss Objekt sein.")
        for key in ("expected_agents", "expected_text_fragments", "expected_audit_codes", "expected_blocked_agents"):
            seq = case[key]
            if not isinstance(seq, list) or len(set(map(repr, seq))) != len(seq) or any(not isinstance(v, str) for v in seq):
                raise EvaluationDataError(f"Fall {idx}: {key} muss eine Liste eindeutiger Texte sein.")
        if any(a not in AGENTS for a in case["expected_agents"] + case["expected_blocked_agents"]):
            raise EvaluationDataError(f"Fall {idx}: unbekannter Agent in den Erwartungen.")
        if not set(case["expected_blocked_agents"]).issubset(case["expected_agents"]):
            raise EvaluationDataError(f"Fall {idx}: Blockierung nur für erwartete Agenten erlaubt.")
        # Zusätzlich Schema des Agentensystems auf jeden einzelnen Testfall anwenden.
        try:
            AgentInput.from_dict({
                "product": {**base, **case["product_overrides"]},
                "request": {"message": case["question"]},
            })
        except (InputValidationError, TypeError) as exc:
            raise EvaluationDataError(f"Fall {case['id']}: ungültige Eingabe: {exc}") from exc
    return base, scenarios


def _numbers_in_facts(product: dict[str, Any]) -> set[str]:
    raw = " ".join(str(v) for v in product.values() if v is not None and not isinstance(v, bool))
    return {m.group().replace(",", ".") for m in _NUMBERS.finditer(raw)}


def evaluate_case(base: dict[str, Any], case: dict[str, Any], pipeline: AgentPipeline) -> dict[str, Any]:
    """Führt EINEN Fall aus, sammelt beobachtete Ergebnisse, misst ohne Selbstbenotung."""
    product = {**base, **case["product_overrides"]}
    data = AgentInput.from_dict({"product": product, "request": {"message": case["question"]}})
    expected_agents = set(case["expected_agents"])
    start = time.perf_counter()
    error = None
    result = None
    try:
        result = pipeline.run(data)
    except Exception as exc:  # Fehlender Pipeline-Schutz soll als Scheitern sichtbar sein.
        error = f"{type(exc).__name__}: {exc}"
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    if result is None:
        return {
            "id": case["id"], "category": case["category"], "question": case["question"],
            "expected_agents": sorted(expected_agents), "actual_agents": [], "source": "exception",
            "route_exact": False, "clarification_correct": False, "audit_ok": False,
            "blocked_ok": False, "text_ok": False, "unsafe_commitment": False,
            "unexpected_numbers": [], "expected_audit_codes": case["expected_audit_codes"],
            "actual_audit_codes": [], "expected_blocked_agents": case["expected_blocked_agents"],
            "actual_blocked_agents": [], "missing_text": case["expected_text_fragments"],
            "duration_ms": duration_ms, "review_required": False,
            "result_ok": False, "error": error,
        }
    actual_agents = set(result.route.agents)
    actual_audit = {issue.code for issue in result.audit}
    actual_blocked = {item.agent for item in result.validation if item.draft_status == DRAFT_BLOCK}
    text_lower = result.combined_draft.casefold()
    missing_text = [s for s in case["expected_text_fragments"] if s.casefold() not in text_lower]
    unexpected_numbers = sorted({m.group().replace(",", ".") for m in _NUMBERS.finditer(result.combined_draft)}
                                - _numbers_in_facts(product))
    unsafe_commitment = bool(_COMMITMENT.search(result.combined_draft)
                             or _UNAUTHORIZED_DELIVERY.search(result.combined_draft))
    route_exact = actual_agents == expected_agents
    clarification_correct = result.route.needs_clarification == (not expected_agents)
    audit_ok = set(case["expected_audit_codes"]).issubset(actual_audit)
    blocked_ok = set(case["expected_blocked_agents"]).issubset(actual_blocked)
    text_ok = not missing_text
    review_required = result.review_status == "seller_review_required"
    result_ok = all((route_exact, clarification_correct, audit_ok, blocked_ok, text_ok,
                     review_required, not unsafe_commitment, not unexpected_numbers))
    return {
        "id": case["id"], "category": case["category"], "question": case["question"],
        "expected_agents": sorted(expected_agents), "actual_agents": sorted(actual_agents),
        "source": result.route.source, "route_exact": route_exact,
        "clarification_correct": clarification_correct, "audit_ok": audit_ok,
        "blocked_ok": blocked_ok, "text_ok": text_ok, "unsafe_commitment": unsafe_commitment,
        "unexpected_numbers": unexpected_numbers,
        "expected_audit_codes": case["expected_audit_codes"],
        "actual_audit_codes": sorted(actual_audit),
        "expected_blocked_agents": case["expected_blocked_agents"],
        "actual_blocked_agents": sorted(actual_blocked),
        "missing_text": missing_text, "duration_ms": duration_ms,
        "review_required": review_required, "result_ok": result_ok, "error": error,
    }


def summarize(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    if not rows:
        raise EvaluationDataError("Mindestens ein ausgewerteter Testfall erforderlich.")
    tp = sum(len(set(r["expected_agents"]) & set(r["actual_agents"])) for r in rows)
    predicted = sum(len(r["actual_agents"]) for r in rows)
    expected = sum(len(r["expected_agents"]) for r in rows)
    percent = lambda n, d: round(100 * n / d, 1) if d else None
    failures = [r["id"] for r in rows if not r["result_ok"]]
    source_counts = Counter(r["source"] for r in rows)
    audit_subset = [r for r in rows if r["expected_audit_codes"]]
    block_subset = [r for r in rows if r["expected_blocked_agents"]]
    categories: dict[str, dict[str, Any]] = {}
    for category in sorted(set(r["category"] for r in rows)):
        group = [r for r in rows if r["category"] == category]
        categories[category] = {
            "count": len(group), "passed": sum(r["result_ok"] for r in group),
            "route_exact_pct": percent(sum(r["route_exact"] for r in group), len(group)),
        }
    return {
        "mode": mode, "count": len(rows), "all_checks_passed": sum(r["result_ok"] for r in rows),
        "failures": failures, "route_exact_pct": percent(sum(r["route_exact"] for r in rows), len(rows)),
        "agent_precision_pct": percent(tp, predicted), "agent_recall_pct": percent(tp, expected),
        "clarification_correct_pct": percent(sum(r["clarification_correct"] for r in rows), len(rows)),
        "expected_audit_detected_pct": percent(sum(r["audit_ok"] for r in audit_subset), len(audit_subset)),
        "audit_expected_case_count": len(audit_subset),
        "expected_blocking_detected_pct": percent(sum(r["blocked_ok"] for r in block_subset), len(block_subset)),
        "blocking_expected_case_count": len(block_subset),
        "text_fragments_pass_pct": percent(sum(r["text_ok"] for r in rows), len(rows)),
        "unsafe_commitment_detected_in_draft_count": sum(r["unsafe_commitment"] for r in rows),
        "unexpected_number_cases": sum(bool(r["unexpected_numbers"]) for r in rows),
        "seller_review_required_pct": percent(sum(r["review_required"] for r in rows), len(rows)),
        "sources": dict(sorted(source_counts.items())),
        "mean_duration_ms": round(statistics.mean(r["duration_ms"] for r in rows), 2),
        "categories": categories,
    }


def run_suite(base: dict[str, Any], cases: list[dict[str, Any]], *, offline: bool = True,
              pipeline: AgentPipeline | None = None) -> dict[str, Any]:
    engine = pipeline if pipeline is not None else AgentPipeline(offline=offline)
    rows = [evaluate_case(base, case, engine) for case in cases]
    return {"summary": summarize(rows, "offline" if offline else "llm"), "cases": rows}


def markdown_report(report: dict[str, Any]) -> str:
    m = report["summary"]
    lines = [f"# Fundplatz – Tag 14 Evaluation ({m['mode']})", "",
             f"**Ausgewertet:** {m['count']} Szenarien; vollständig bestandene Prüfpakete: {m['all_checks_passed']}.", "",
             "## Kennzahlen", "",
             "| Messgröße | Wert |", "|---|---:|",
             f"| Exakte Agentenmengen | {m['route_exact_pct']} % |",
             f"| Agenten-Präzision / Recall | {m['agent_precision_pct']} % / {m['agent_recall_pct']} % |",
             f"| Rückfragen richtig erkannt | {m['clarification_correct_pct']} % |",
             f"| Erwartete Audit-Codes gefunden (n={m['audit_expected_case_count']}) | {m['expected_audit_detected_pct']} % |",
             f"| Erwartete Blockierungen gefunden (n={m['blocking_expected_case_count']}) | {m['expected_blocking_detected_pct']} % |",
             f"| Stichwort-Prüfungen bestanden | {m['text_fragments_pass_pct']} % |",
             f"| Riskante Zusage-Muster im sichtbaren Entwurf | {m['unsafe_commitment_detected_in_draft_count']} |",
             f"| Fälle mit unerwarteten Zahlen | {m['unexpected_number_cases']} |",
             f"| Verkäuferfreigabe erforderlich | {m['seller_review_required_pct']} % |", "",
             f"Router-Herkunft: `{json.dumps(m['sources'], ensure_ascii=False)}`", "",
             "## Kategorien", "", "| Kategorie | Fälle | Komplett bestanden | Exaktes Routing |",
             "|---|---:|---:|---:|"]
    for label, c in m["categories"].items():
        lines.append(f"| {label} | {c['count']} | {c['passed']} | {c['route_exact_pct']} % |")
    lines += ["", "## Auffällige Fälle", ""]
    failed = [r for r in report["cases"] if not r["result_ok"]]
    if not failed:
        lines.append("Keine Abweichung gegenüber diesen vordefinierten Prüfkriterien gefunden.")
    else:
        for r in failed:
            differences = []
            if not r["route_exact"]:
                differences.append(f"Routing erwartet `{','.join(r['expected_agents']) or '-'}`, gefunden `{','.join(r['actual_agents']) or '-'}`")
            if not r["clarification_correct"]:
                differences.append("Rückfrage-Entscheidung falsch")
            if not r["audit_ok"]:
                differences.append("erwarteter Audit-Code fehlt")
            if not r["blocked_ok"]:
                differences.append("erwartete Blockierung fehlt")
            if r["missing_text"]:
                differences.append("Stichwörter fehlen: " + ", ".join(r["missing_text"]))
            if r["unexpected_numbers"]:
                differences.append("unerwartete Zahlen: " + ", ".join(r["unexpected_numbers"]))
            if r["unsafe_commitment"]:
                differences.append("verdächtiges Zusage-Muster")
            if r["error"]:
                differences.append("Ausnahme: " + r["error"])
            lines.append(f"- **{r['id']}** ({r['category']}): " + "; ".join(differences))
    lines += ["", "## Aussagegrenzen", "",
              "- Erwartete Agenten und Stichwörter wurden vor dem Test manuell festgelegt; der Router hat sie nicht erzeugt.",
              "- Stichwort-, Zahlen- und Regex-Prüfungen sind **keine** vollständige semantische Faktenprüfung.",
              "- Offline-Messungen bewerten das regelbasierte Routing, **nicht** die Qualität von Qwen.",
              "- Im LLM-Modus stammen einzelne Entscheidungen ggf. aus `fallback`; die Spalte `source` zeigt das an.",
              "- Die Agenten senden keine Nachrichten und geben nichts automatisch frei; Verkäuferprüfung bleibt Pflicht.", ""]
    return "\n".join(lines)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(markdown_report(report), encoding="utf-8")
    keys = ["id", "category", "question", "expected_agents", "actual_agents", "source", "route_exact",
            "clarification_correct", "audit_ok", "blocked_ok", "text_ok", "unsafe_commitment",
            "unexpected_numbers", "expected_audit_codes", "actual_audit_codes", "expected_blocked_agents",
            "actual_blocked_agents", "missing_text", "duration_ms", "review_required", "result_ok", "error"]
    with (out_dir / "report.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in report["cases"]:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (list, dict)) else row[k] for k in keys})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fundplatz Tag 14: 40 manuell gelabelte Szenarien auswerten")
    parser.add_argument("--mode", choices=("offline", "llm"), default="offline",
                        help="offline = Regelrouter; llm = lokales Ollama/Qwen mit dokumentiertem Fallback")
    parser.add_argument("--limit", type=int, help="Erste N Szenarien ausführen, z.B. --limit 5 für einen Ollama-Schnelltest")
    parser.add_argument("--category", help="Nur eine Kategorie aus der Szenario-Datei ausführen")
    parser.add_argument("--per-category", type=int, help="Je N Fälle aus jeder Kategorie (z.B. 1 = 10 breit gestreute Fälle)")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out-dir", type=Path, help="Zielordner für CSV, JSON und Markdown-Bericht")
    args = parser.parse_args(argv)
    try:
        base, scenarios = load_cases(args.cases)
    except EvaluationDataError as exc:
        parser.error(str(exc))
    if args.category:
        choices = {s["category"] for s in scenarios}
        if args.category not in choices:
            parser.error("Unbekannte Kategorie. Erlaubt: " + ", ".join(sorted(choices)))
        scenarios = [s for s in scenarios if s["category"] == args.category]
    if args.per_category is not None:
        if args.per_category < 1:
            parser.error("--per-category muss mindestens 1 sein.")
        seen = Counter()
        chosen = []
        for case in scenarios:
            if seen[case["category"]] < args.per_category:
                chosen.append(case)
                seen[case["category"]] += 1
        scenarios = chosen
    if args.limit is not None:
        if not 1 <= args.limit <= len(scenarios):
            parser.error(f"--limit muss zwischen 1 und {len(scenarios)} liegen.")
        scenarios = scenarios[:args.limit]
    target = args.out_dir or Path("evaluation_reports") / ("tag14_llm" if args.mode == "llm" else "tag14_offline")
    print(f"Starte {len(scenarios)} Szenarien, Modus: {args.mode}.", flush=True)
    report = run_suite(base, scenarios, offline=args.mode == "offline")
    write_report(report, target)
    metrics = report["summary"]
    print(f"Exaktes Routing: {metrics['route_exact_pct']} %; Agenten-Recall: {metrics['agent_recall_pct']} %")
    print(f"Vollständig bestandene Fallprüfungen: {metrics['all_checks_passed']}/{metrics['count']}")
    print(f"Auffällige Fälle: {', '.join(metrics['failures']) or 'keine'}")
    print(f"Router-Herkunft: {metrics['sources']}")
    print(f"Berichte: {target / 'report.md'}, {target / 'report.csv'}, {target / 'report.json'}")
    print("Hinweis: Keine automatische Freigabe; Stichwort-Checks ersetzen keine Faktenprüfung.")
    return 0  # Qualitätsabweichungen sind ein Evaluationsergebnis, kein Programmabsturz.


if __name__ == "__main__":
    sys.exit(main())
