"""Secrets protégés par DPAPI (compte Windows courant), compatibles avec SecretProtector côté Desktop.

Même préfixe ("dpapi:") et même entropie : un secret enregistré par l'un est lisible par l'autre.
Hors Windows (développement, CI Linux), protect() lève DpapiUnavailable et unprotect() renvoie "" :
un secret n'est jamais enregistré en clair.
"""
import base64
import sys

PREFIX = "dpapi:"
_ENTROPY = b"AFMI-SmartAdmin-Secrets"


class DpapiUnavailable(RuntimeError):
    pass


def is_available() -> bool:
    return sys.platform == "win32"


if sys.platform == "win32":  # pragma: no cover - exécuté sur Windows (intégration continue)
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32

    def _blob(data: bytes) -> _Blob:
        buf = ctypes.create_string_buffer(data, len(data))
        return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    def _call(func, data: bytes) -> bytes:
        out = _Blob()
        entropy = _blob(_ENTROPY)
        if not func(ctypes.byref(_blob(data)), None, ctypes.byref(entropy), None, None, 0, ctypes.byref(out)):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            _kernel32.LocalFree(out.pbData)

    def _protect(data: bytes) -> bytes:
        return _call(_crypt32.CryptProtectData, data)

    def _unprotect(data: bytes) -> bytes:
        return _call(_crypt32.CryptUnprotectData, data)


def protect(plain: str) -> str:
    if not plain:
        return ""
    if not is_available():
        raise DpapiUnavailable("Le stockage chiffré des secrets (DPAPI) n'est disponible que sous Windows.")
    return PREFIX + base64.b64encode(_protect(plain.encode("utf-8"))).decode("ascii")


def unprotect(stored: str) -> str:
    if not stored:
        return ""
    if not stored.startswith(PREFIX):
        return stored  # valeur héritée en clair
    if not is_available():
        return ""
    try:
        return _unprotect(base64.b64decode(stored[len(PREFIX):])).decode("utf-8")
    except Exception:  # base importée d'un autre compte Windows : le secret doit être ressaisi
        return ""
