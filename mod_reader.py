"""Read ETS2 mod metadata from .scs files (ZIP archives)."""

import os
import re
import zipfile


def get_default_mod_dir() -> str:
    return os.path.join(
        os.path.expanduser("~"), "Documents", "Euro Truck Simulator 2", "mod"
    )


def get_default_profiles_dir() -> str:
    return os.path.join(
        os.path.expanduser("~"), "Documents", "Euro Truck Simulator 2", "profiles"
    )


def parse_entry(entry: str) -> tuple:
    """Split 'mod_id|Display Name' into (mod_id, display_name)."""
    if "|" in entry:
        idx = entry.index("|")
        return entry[:idx], entry[idx + 1:]
    return entry, entry


def entry_id(entry: str) -> str:
    return parse_entry(entry)[0]


def read_mod_folder(mod_dir: str) -> list:
    """
    Scan mod_dir for .scs files.
    Returns list of dicts: {id, display_name, entry, path}
    sorted by display_name.
    """
    mods = []
    if not os.path.isdir(mod_dir):
        return mods

    for fname in os.listdir(mod_dir):
        if not fname.lower().endswith(".scs"):
            continue
        mod_id = os.path.splitext(fname)[0]
        path = os.path.join(mod_dir, fname)
        display_name = _read_display_name(path) or mod_id
        mods.append({
            "id":           mod_id,
            "display_name": display_name,
            "entry":        f"{mod_id}|{display_name}",
            "path":         path,
        })

    mods.sort(key=lambda m: m["display_name"].lower())
    return mods


def _read_display_name(scs_path: str) -> str | None:
    try:
        with zipfile.ZipFile(scs_path, "r") as z:
            for name in z.namelist():
                if name.lower().lstrip("/") == "manifest.sii":
                    data = z.read(name)
                    text = _decode(data)
                    m = re.search(r'display_name\s*:\s*"([^"]+)"', text)
                    if m:
                        return m.group(1)
    except Exception:
        pass
    return None


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")
