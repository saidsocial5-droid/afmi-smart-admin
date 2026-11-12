"""Générateur déterministe de relevés bancaires de TEST (fictifs).

Produit, pour chaque relevé : un PDF natif, un scan dégradé (JPEG incliné, bruité, flou) et la vérité terrain
(<nom>.truth.json). Sert à développer et mesurer le pipeline OCR tant que l'AFMI n'a pas fourni de relevés réels
anonymisés ; les résultats sur ces relevés synthétiques ne garantissent PAS ceux sur de vrais relevés.

Usage : python -m tests.tools.statement_fixtures <dossier_de_sortie>
"""
import io
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter

LABELS_DEBIT = [
    "PRLV LOYER SIEGE AZROU", "CHQ N° {n}", "FRAIS TENUE DE COMPTE", "COMMISSION SUR VIREMENT",
    "RETRAIT GAB IFRANE", "PAIEMENT TPE PAPETERIE ATLAS", "VIR EMIS SALAIRES {m}", "PRLV CNSS {m}",
    "VIR EMIS PEPINIERE MOYEN ATLAS", "PAIEMENT TPE STATION SERVICE", "AGIOS TRIMESTRIELS",
    "VIR EMIS COOPERATIVE TIMAHDITE", "PRLV MAROC TELECOM", "CHQ N° {n} TRANSPORT ATELIER",
]
LABELS_CREDIT = [
    "VIR RECU BAILLEUR CONVENTION {n}", "VERSEMENT ESPECES COTISATIONS", "VIR RECU DON ASSOCIATION AMIS",
    "VIR RECU PRESTATION FORMATION", "REMISE CHQ N° {n}", "INTERETS CREDITEURS",
]

LAYOUTS = {
    "bp": {
        "bank": "BANQUE POPULAIRE", "title": "RELEVE DE COMPTE",
        "period": "Période du {start} au {end}", "rib": "RIB : {rib}",
        "opening": "SOLDE PRECEDENT AU {prev}", "closing": "NOUVEAU SOLDE AU {end}",
        "columns": [("DATE", 40), ("LIBELLE", 95), ("VALEUR", 330), ("DEBIT", 400), ("CREDIT", 490)],
        "order": ["date", "label", "value_date", "debit", "credit"],
    },
    "awb": {
        "bank": "ATTIJARIWAFA BANK", "title": "EXTRAIT DE COMPTE",
        "period": "Extrait du {start} au {end}", "rib": "Compte (RIB) {rib}",
        "opening": "Solde initial", "closing": "Solde final",
        "columns": [("Date opération", 40), ("Date valeur", 115), ("Libellé", 190), ("Débit", 400), ("Crédit", 490)],
        "order": ["date", "value_date", "label", "debit", "credit"],
    },
    "cih": {
        "bank": "CIH BANK", "title": "RELEVE DES OPERATIONS",
        "period": "du {start} au {end}", "rib": "R.I.B. {rib}",
        "opening": "ANCIEN SOLDE", "closing": "NOUVEAU SOLDE",
        "columns": [("Date", 40), ("Libellé de l'opération", 100), ("Débit", 400), ("Crédit", 490)],
        "order": ["date", "label", "debit", "credit"],
    },
}


def fmt_amount(minor: int) -> str:
    units, cents = divmod(minor, 100)
    s = f"{units:,}".replace(",", " ")
    return f"{s},{cents:02d}"


def rib_with_key(first22: str) -> str:
    key = 97 - (int(first22) * 100) % 97
    return first22 + f"{key:02d}"


def make_truth(layout: str, seed: int, n_lines: int, month: int):
    rnd = random.Random(seed)
    start = date(2026, month, 1)
    end = (date(2026, month + 1, 1) - timedelta(days=1)) if month < 12 else date(2026, 12, 31)
    rib = rib_with_key(f"{rnd.choice(['190', '007', '230'])}{rnd.randint(100, 999)}{rnd.randint(10**15, 10**16 - 1)}")
    opening = rnd.randint(2_000_000, 25_000_000)
    lines, balance = [], opening
    days = sorted(rnd.randint(0, (end - start).days) for _ in range(n_lines))
    for d in days:
        op = start + timedelta(days=d)
        credit = rnd.random() < 0.3
        tpl = rnd.choice(LABELS_CREDIT if credit else LABELS_DEBIT)
        label = tpl.format(n=rnd.randint(1000000, 9999999), m=start.strftime("%m/%Y"))
        amount = rnd.choice([rnd.randint(1_000, 50_000), rnd.randint(50_000, 2_500_000)])
        if "FRAIS" in label or "COMMISSION" in label or "AGIOS" in label:
            amount = rnd.randint(500, 15_000)
        balance += amount if credit else -amount
        lines.append({"date": op.isoformat(), "value_date": (op + timedelta(days=rnd.choice([0, 0, 1, 2]))).isoformat(),
                      "label": label, "debit": 0 if credit else amount, "credit": amount if credit else 0})
    return {"layout": layout, "bank": LAYOUTS[layout]["bank"], "rib": rib, "period_start": start.isoformat(),
            "period_end": end.isoformat(), "opening": opening, "closing": balance, "lines": lines}


def _d(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def render_pdf(truth: dict) -> bytes:
    lay = LAYOUTS[truth["layout"]]
    doc = fitz.open()
    rows = truth["lines"]
    per_page = 26
    pages = [rows[i:i + per_page] for i in range(0, len(rows), per_page)] or [[]]
    prev = (date.fromisoformat(truth["period_start"]) - timedelta(days=1)).isoformat()
    amount_cols = {"debit": None, "credit": None}
    for p_idx, chunk in enumerate(pages):
        page = doc.new_page(width=595, height=842)
        y = 50
        page.insert_text((40, y), lay["bank"], fontsize=15, fontname="hebo")
        page.insert_text((360, y), lay["title"], fontsize=11, fontname="hebo")
        y += 22
        page.insert_text((40, y), "ASSOCIATION FICTIVE DES CEDRES - TITULAIRE DU COMPTE", fontsize=9)
        y += 14
        page.insert_text((40, y), lay["rib"].format(rib=" ".join([truth["rib"][:3], truth["rib"][3:6], truth["rib"][6:22], truth["rib"][22:]])), fontsize=9)
        page.insert_text((360, y), lay["period"].format(start=_d(truth["period_start"]), end=_d(truth["period_end"])), fontsize=9)
        y += 14
        page.insert_text((360, y + 0), f"Page {p_idx + 1}/{len(pages)}", fontsize=8)
        y += 22
        if p_idx == 0:
            page.insert_text((40, y), lay["opening"].format(prev=_d(prev)), fontsize=9, fontname="hebo")
            page.insert_text((490, y), fmt_amount(truth["opening"]), fontsize=9, fontname="hebo")
            y += 20
        for name, x in lay["columns"]:
            page.insert_text((x, y), name, fontsize=9, fontname="hebo")
        page.draw_line((35, y + 4), (565, y + 4), width=0.6)
        y += 18
        xs = dict(zip(lay["order"], [x for _, x in lay["columns"]]))
        for r in chunk:
            for key in lay["order"]:
                x = xs[key]
                if key == "date":
                    page.insert_text((x, y), _d(r["date"]), fontsize=8.5)
                elif key == "value_date":
                    page.insert_text((x, y), _d(r["value_date"]), fontsize=8.5)
                elif key == "label":
                    page.insert_text((x, y), r["label"], fontsize=8.5)
                elif key in ("debit", "credit") and r[key]:
                    page.insert_text((x, y), fmt_amount(r[key]), fontsize=8.5)
            y += 17
        if p_idx == len(pages) - 1:
            page.draw_line((35, y), (565, y), width=0.6)
            y += 16
            page.insert_text((40, y), lay["closing"].format(end=_d(truth["period_end"])), fontsize=9, fontname="hebo")
            page.insert_text((490, y), fmt_amount(truth["closing"]), fontsize=9, fontname="hebo")
    data = doc.tobytes()
    doc.close()
    return data


def degrade_to_scan(pdf_bytes: bytes, seed: int, page_index: int = 0, dpi: int = 200, hard: bool = False) -> bytes:
    """Scan ordinaire, ou « difficile » (type photo au téléphone : basse résolution, forte inclinaison, bruit, JPEG fort)."""
    rnd = np.random.default_rng(seed)
    if hard:
        dpi = 150
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = doc[page_index].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    doc.close()
    angle = float(rnd.uniform(3.0, 4.5) * rnd.choice([-1, 1])) if hard else float(rnd.uniform(-2.0, 2.0))
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=255)
    arr = np.asarray(img).astype(np.float32)
    arr = arr * rnd.uniform(0.85, 0.95) + rnd.uniform(10, 30)          # contraste réduit, fond grisé
    if hard:  # éclairage inégal (dégradé), comme une photo
        arr += np.linspace(0, 45, arr.shape[1])[None, :]
    arr += rnd.normal(0, 14 if hard else 9, arr.shape)                   # bruit de numérisation
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8 if hard else 0.6))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=55 if hard else 72)
    return out.getvalue()


# (mise en page, graine, nombre de lignes, mois) — le dernier relevé tient sur deux pages
SPECS = [("bp", 11, 14, 3), ("awb", 22, 18, 4), ("cih", 33, 12, 5), ("bp", 44, 20, 6), ("awb", 55, 9, 7), ("cih", 66, 40, 8)]


HARD_SEEDS = {11, 22, 33}


def generate(out_dir: Path) -> list[Path]:
    """Écrit les relevés synthétiques et retourne la liste des fichiers de vérité terrain."""
    out_dir.mkdir(parents=True, exist_ok=True)
    truths = []
    for layout, seed, n, month in SPECS:
        truth = make_truth(layout, seed, n, month)
        base = f"synth_{layout}_{seed}"
        pdf = render_pdf(truth)
        (out_dir / f"{base}.pdf").write_bytes(pdf)
        n_pages = fitz.open(stream=pdf, filetype="pdf").page_count
        scans = []
        for p in range(n_pages):
            name = f"{base}_scan_p{p + 1}.jpg"
            (out_dir / name).write_bytes(degrade_to_scan(pdf, seed + p, p))
            scans.append(name)
        hard = []
        if seed in HARD_SEEDS:
            for p in range(n_pages):
                name = f"{base}_photo_p{p + 1}.jpg"
                (out_dir / name).write_bytes(degrade_to_scan(pdf, seed + 100 + p, p, hard=True))
                hard.append(name)
        truth["files"] = {"native_pdf": f"{base}.pdf", "scan_pages": scans}
        if hard:
            truth["files"]["hard_scan_pages"] = hard
        path = out_dir / f"{base}.truth.json"
        path.write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
        truths.append(path)
    return truths


if __name__ == "__main__":
    for t in generate(Path(sys.argv[1] if len(sys.argv) > 1 else "synthetic_statements")):
        print(t)
