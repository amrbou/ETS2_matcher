"""
Native Python decryption for ETS2/ATS .sii files.

Supported formats:
  SiiNunit  — already plain text, return as-is
  ScsC      — AES-256-CBC + zlib (modern ETS2 saves)

Not supported:
  BSII      — binary SII (game resource files, not saves)
  3nK       — legacy encrypted format (pre-2013, extremely rare)

Key source: TheLazyTomcat/SII_Decrypt (MIT licence)
"""

import struct
import zlib

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# AES-256 key — hardcoded in ETS2 binary, extracted from SII_Decrypt source
_KEY = bytes([
    0x2a, 0x5f, 0xcb, 0x17, 0x91, 0xd2, 0x2f, 0xb6,
    0x02, 0x45, 0xb3, 0xd8, 0x36, 0x9e, 0xd0, 0xb2,
    0xc2, 0x73, 0x71, 0x56, 0x3f, 0xbf, 0x1f, 0x3c,
    0x9e, 0xdf, 0x6b, 0x11, 0x82, 0x5a, 0x5d, 0x0a,
])

_MAGIC_TEXT = b"SiiN"      # plaintext SiiNunit
_MAGIC_BSII = b"BSII"      # binary SII (not needed for saves)
_MAGIC_SCSC = b"ScsC"      # modern encrypted saves
_MAGIC_3NK  = b"3nK\x01"   # legacy encrypted (pre-2013)


def _decode(data: bytes) -> str:
    """Decode bytes trying UTF-8 first, then latin-1 fallback (handles accented names)."""
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")  # latin-1 accepts any byte 0x00-0xFF


def decrypt_file(path: str) -> str:
    """Return the plaintext SiiNunit content of any .sii file."""
    with open(path, "rb") as f:
        data = f.read()

    magic = data[:4]

    if magic == _MAGIC_TEXT:
        return _decode(data)

    if magic == _MAGIC_SCSC:
        return _decrypt_scsc(data)

    if magic == _MAGIC_BSII:
        raise NotImplementedError(
            "BSII binary format is not supported / "
            "Le format binaire BSII n'est pas supporté.\n"
            "(Ce format est utilisé pour les fichiers de ressources du jeu, pas les sauvegardes.)"
        )

    if magic == _MAGIC_3NK:
        raise NotImplementedError(
            "Legacy 3nK format is not supported / "
            "Le format 3nK (ancien chiffrement) n'est pas supporté.\n"
            "(Très rare — versions d'ETS2 antérieures à 2013.)"
        )

    # Last resort: try to read as text (some modded profiles have no BOM)
    text = _decode(data)
    if "SiiNunit" in text[:32]:
        return text

    raise ValueError(
        f"Unrecognised file format (magic bytes: {magic.hex()}) / "
        f"Format de fichier non reconnu (magic: {magic.hex()})."
    )


def _decrypt_scsc(data: bytes) -> str:
    """Decrypt a ScsC-format file: AES-256-CBC decrypt then zlib decompress."""
    # Header: magic(4) + hmac_sha256(32) + aes_iv(16) + decompressed_size(4) = 56 bytes
    iv            = data[36:52]
    expected_size = struct.unpack_from("<I", data, 52)[0]
    encrypted     = data[56:]

    cipher    = AES.new(_KEY, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)

    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        pass  # not padded — continue anyway

    try:
        plaintext = zlib.decompress(decrypted)
    except zlib.error:
        raise ValueError(
            "Decompression failed after decryption / "
            "La décompression a échoué après le déchiffrement.\n"
            "The AES key may be outdated (game update?) / "
            "La clé AES est peut-être obsolète (mise à jour du jeu ?)."
        )

    return _decode(plaintext)
