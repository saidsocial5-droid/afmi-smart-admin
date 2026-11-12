"""Mesure de la précision d'extraction des relevés par rapport à une vérité terrain (<nom>.truth.json).

Une ligne est correcte si sa date, son débit et son crédit sont exacts et si son libellé est reconnu à 80 % au moins
(caractères, sans casse ni accents). Utilisable sur les relevés synthétiques comme sur de vrais relevés anonymisés.

Usage : python -m tests.tools.statement_accuracy <dossier contenant les *.truth.json>
"""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from backend.tools.statements.pipeline import process, process_pages
from backend.tools.statements.templates import normalize


def label_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def compare(truth: dict, extracted) -> dict:
    expected = truth["lines"]
    got = list(extracted.lines)
    correct, used = 0, set()
    errors = []
    for e in expected:
        match = None
        for i, g in enumerate(got):
            if i in used:
                continue
            if g.date == e["date"] and g.debit == e["debit"] and g.credit == e["credit"] and label_ratio(g.label, e["label"]) >= 0.8:
                match = i
                break
        if match is None:
            errors.append(e)
        else:
            used.add(match)
            correct += 1
    return {
        "expected": len(expected), "extracted": len(got), "correct": correct,
        "header_ok": extracted.opening == truth["opening"] and extracted.closing == truth["closing"],
        "balance_ok": extracted.balance_ok(), "errors": errors,
        "extra": [g for i, g in enumerate(got) if i not in used],
    }


def evaluate(folder: Path, verbose: bool = False) -> dict:
    totals = {"expected": 0, "correct": 0, "documents": 0, "headers_ok": 0}
    details = []
    for tf in sorted(folder.glob("*.truth.json")):
        truth = json.loads(tf.read_text(encoding="utf-8"))
        files = truth.get("files", {})
        variants = []
        if files.get("native_pdf"):
            variants.append(("pdf", [files["native_pdf"]]))
        if files.get("scan_pages"):
            variants.append(("scan", files["scan_pages"]))
        if files.get("hard_scan_pages"):
            variants.append(("photo", files["hard_scan_pages"]))
        if files.get("documents"):  # vrais relevés : liste libre de fichiers (un document = une liste de pages)
            variants += [("doc", d if isinstance(d, list) else [d]) for d in files["documents"]]
        for kind, names in variants:
            blobs = [((folder / n).read_bytes(), n) for n in names]
            result = process(*blobs[0]) if len(blobs) == 1 else process_pages(blobs)
            r = compare(truth, result.statement)
            totals["expected"] += r["expected"]
            totals["correct"] += r["correct"]
            totals["documents"] += 1
            totals["headers_ok"] += int(r["header_ok"])
            details.append((tf.stem.replace(".truth", ""), kind, r))
            if verbose:
                print(f"{tf.stem:28} {kind:5} {r['correct']:3}/{r['expected']:3}  soldes {'ok' if r['header_ok'] else 'KO'}  équilibre {r['balance_ok']}")
                for e in r["errors"]:
                    print("    manquante :", e)
                for g in r["extra"]:
                    print("    lue       :", g.date, g.label, g.debit, g.credit)
    totals["accuracy"] = totals["correct"] / totals["expected"] if totals["expected"] else 0.0
    totals["details"] = details
    return totals


if __name__ == "__main__":
    t = evaluate(Path(sys.argv[1]), verbose=True)
    print(f"\nLignes correctes : {t['correct']}/{t['expected']} = {t['accuracy']:.1%} ; soldes corrects : {t['headers_ok']}/{t['documents']} documents")
