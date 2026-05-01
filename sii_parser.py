import re


def extract_active_mods(content: str) -> list | None:
    """Return ordered list of mod names, or None if block not found."""
    m = re.search(r"^\s*active_mods\s*:\s*(\d+)", content, re.MULTILINE)
    if not m:
        return None
    count = int(m.group(1))
    mods = []
    for i in range(count):
        entry = re.search(
            rf'^\s*active_mods\[{i}\]\s*:\s*"([^"]*)"', content, re.MULTILINE
        )
        if entry:
            mods.append(entry.group(1))
    return mods


def replace_active_mods(content: str, new_mods: list) -> str | None:
    """Return content with active_mods block replaced, or None if block not found."""
    lines = [" active_mods: {}".format(len(new_mods))]
    for i, mod in enumerate(new_mods):
        lines.append(' active_mods[{}]: "{}"'.format(i, mod))
    replacement = "\n".join(lines)

    # Match the count line followed by any number of indexed array lines.
    # Does NOT consume the trailing newline so the rest of the file is unaffected.
    pattern = (
        r"[ \t]*active_mods[ \t]*:[ \t]*\d+[ \t]*"
        r"(?:\r?\n[ \t]*active_mods\[\d+\][ \t]*:[^\r\n]*)*"
    )
    m = re.search(pattern, content)
    if not m:
        return None
    return content[: m.start()] + replacement + content[m.end():]
