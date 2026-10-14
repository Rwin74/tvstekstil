"""Windows DPAPI keeps the search key bound to the current Windows user."""
import base64
import ctypes
import json
import os
from ctypes import wintypes


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_char))]


def crypt(value: bytes, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Windows dışında kalıcı anahtar için ortam değişkeni kullanın.")
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError("Anahtar Windows kasasına kaydedilemedi.")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


def load(settings):
    path = settings.data_dir / "search-settings.json"
    if settings.cloud or settings.api_key or not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        settings.provider = data["provider"]
        settings.api_key = crypt(base64.b64decode(data["key"]), decrypt=True).decode()
    except (ValueError, KeyError, OSError, RuntimeError):
        pass


def save(settings, provider, key):
    encrypted = base64.b64encode(crypt(key.encode())).decode()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / "search-settings.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"provider": provider, "key": encrypted}), encoding="utf-8")
    temp.replace(path)
    settings.provider, settings.api_key = provider, key
