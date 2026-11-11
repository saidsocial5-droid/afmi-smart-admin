"""Prétraitement d'une image de relevé : niveaux de gris, redressement, contraste, binarisation, résolution."""
from typing import Tuple

import cv2
import numpy as np

TARGET_WIDTH = 2480  # ≈ A4 à 300 dpi


def load_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image illisible (format non reconnu ou fichier endommagé).")
    return img


def estimate_skew(gray: np.ndarray, max_angle: float = 6.0, step: float = 0.1) -> float:
    """Angle (degrés) qui rend les lignes de texte horizontales : maximise la variance du profil de projection."""
    small = cv2.resize(gray, None, fx=0.35, fy=0.35, interpolation=cv2.INTER_AREA) if gray.shape[1] > 1200 else gray
    _, bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = bw.shape
    center = (w / 2, h / 2)
    best_angle, best_score = 0.0, -1.0

    def score(angle: float) -> float:
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        profile = rotated.sum(axis=1, dtype=np.float64)
        return float(np.var(profile))

    for angle in np.arange(-max_angle, max_angle + 1e-9, 0.5):       # recherche grossière
        s = score(float(angle))
        if s > best_score:
            best_angle, best_score = float(angle), s
    for angle in np.arange(best_angle - 0.5, best_angle + 0.5 + 1e-9, step):  # affinage
        s = score(float(angle))
        if s > best_score:
            best_angle, best_score = float(angle), s
    return round(best_angle, 2)


def rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.05:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(gray, m, (nw, nh), flags=cv2.INTER_CUBIC, borderValue=255)


MODES = ("gray", "binary")


def preprocess(gray: np.ndarray, mode: str = "gray") -> Tuple[np.ndarray, float]:
    """
    Retourne l'image prête pour l'OCR et l'angle de redressement appliqué.
    « gray » (par défaut) : débruitage + contraste local, sans binarisation — Tesseract binarise mieux lui-même
    sur les scans flous ; « binary » : seuillage d'Otsu en plus (seconde lecture quand l'équilibre des soldes échoue).
    """
    if gray.shape[1] < TARGET_WIDTH * 0.8:
        scale = TARGET_WIDTH / gray.shape[1]
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    angle = estimate_skew(gray)
    gray = rotate(gray, angle)
    gray = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    if mode == "binary":
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return gray, angle


def to_png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Encodage PNG impossible.")
    return buf.tobytes()
