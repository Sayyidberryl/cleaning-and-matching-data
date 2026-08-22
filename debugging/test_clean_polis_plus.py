"""
Unit tests for Entry vs Non-Entry logic in clean_polis.

Kasus yang diverifikasi:
  1. Skenario A — ada entry terpisah (double-space gap), dua kasus dari prompt
  2. Skenario B — tidak ada entry terpisah, expand suffix-replace penuh
  3. Fallback — nilai tanpa '+' tidak berubah perilakunya
  4. _expand_plus_suffix edge cases

Jalankan:
    python test_clean_polis_plus.py
"""

import sys
import os

# Patch numpy-incompatible optional deps before importing anything that pulls pandas
sys.modules['numexpr'] = None   # type: ignore
sys.modules['bottleneck'] = None  # type: ignore

# Pastikan script bisa diimport tanpa pandas error (hanya fungsi helper yang diuji)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore

# Import dari cleaning_osbal (fungsi identik dengan cleaning_facul)
from cleaning_osbal import clean_polis, clean_slip, _expand_plus_suffix


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

_total = _passed = 0


def check(label: str, got, expected):
    global _total, _passed
    _total += 1
    ok = got == expected
    if ok:
        _passed += 1
        status = PASS
    else:
        status = FAIL
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         expected: {expected}")
        print(f"         got     : {got}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. _expand_plus_suffix — unit tests
# ─────────────────────────────────────────────────────────────────────────────

print("\n[1] _expand_plus_suffix() " + "-" * 45)

check(
    "Skenario B full — 7 segments",
    _expand_plus_suffix("100010324110001373 + 362 + 384+64+75+166+166"),
    [
        "100010324110001373",
        "100010324110001362",
        "100010324110001384",
        "100010324110001364",
        "100010324110001375",
        "100010324110001166",
        "100010324110001166",
    ],
)

check(
    "Skenario B compact — 2 segments",
    _expand_plus_suffix("100090325110000155+188+202"),
    [
        "100090325110000155",
        "100090325110000188",
        "100090325110000202",
    ],
)

check(
    "Return None jika BASE bukan digit murni",
    _expand_plus_suffix("100090A325110000155+188"),
    None,
)

check(
    "Return None jika BASE < 10 digit",
    _expand_plus_suffix("12345678+123"),
    None,
)

check(
    "Return None jika segment non-numerik",
    _expand_plus_suffix("100090325110000155+ABC"),
    None,
)

check(
    "Return None jika segment >= panjang BASE",
    _expand_plus_suffix("100090325110000155+100090325110000999"),
    None,
)

check(
    "Return None jika hanya BASE tanpa segment",
    _expand_plus_suffix("100090325110000155"),
    None,
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. clean_polis & clean_slip — Skenario A (ada entry terpisah)
# ─────────────────────────────────────────────────────────────────────────────

print("\n[2] clean_polis() & clean_slip() -- Skenario A (ada entry, abaikan blok '+') " + "-" * 10)

# Contoh 1 dari prompt: spasi ganda 6 karakter
check(
    "A1 clean_polis: blok '+' diabaikan, hanya entry terpisah yang diambil",
    clean_polis("100010324110001373 + 362 + 384+64+75+166+166      100010324110001362"),
    ["100010324110001362"],
)

check(
    "A1 clean_slip: blok '+' diabaikan, hanya entry terpisah yang diambil",
    clean_slip("100010324110001373 + 362 + 384+64+75+166+166      100010324110001362"),
    ["100010324110001362"],
)

# Contoh 2 dari prompt
check(
    "A2 clean_polis: compact blok '+' diabaikan, hanya entry terpisah yang diambil",
    clean_polis("100090325110000155+188+202                        100010325120000237"),
    ["100010325120000237"],
)

check(
    "A2 clean_slip: compact blok '+' diabaikan, hanya entry terpisah yang diambil",
    clean_slip("100090325110000155+188+202                        100010325120000237"),
    ["100010325120000237"],
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. clean_polis — Skenario B (tidak ada entry, expand suffix-replace)
# ─────────────────────────────────────────────────────────────────────────────

print("\n[3] clean_polis() -- Skenario B (expand suffix-replace) " + "-" * 14)

check(
    "B1: 7 token > MAX_SPLIT_COLS=5 -> di-join koma dalam 1 kolom",
    clean_polis("100010324110001373 + 362 + 384+64+75+166+166"),
    [
        "100010324110001373,100010324110001362,100010324110001384,"
        "100010324110001364,100010324110001375,100010324110001166,"
        "100010324110001166"
    ],
)

check(
    "B2: 3 token compact",
    clean_polis("100090325110000155+188+202"),
    [
        "100090325110000155",
        "100090325110000188",
        "100090325110000202",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fallback — logic lama tidak terganggu
# ─────────────────────────────────────────────────────────────────────────────

print("\n[4] clean_polis() -- Fallback / existing logic tidak berubah " + "-" * 9)

check(
    "Polis tunggal tanpa '+'",
    clean_polis("100010324110001373"),
    ["100010324110001373"],
)

check(
    "Polis dengan dash — _strip_polis_base masih aktif",
    clean_polis("21001032011000063-066-517-552-418"),
    ["21001032011000063"],
)

check(
    "VARIOUS tetap dikembalikan as-is",
    clean_polis("VARIOUS"),
    ["VARIOUS"],
)

check(
    "TBA tetap dikembalikan as-is",
    clean_polis("TBA"),
    ["TBA"],
)

check(
    "Polis dengan CANCEL masuk exception path",
    clean_polis("CANCEL"),
    ["CANCEL"],
)

check(
    "'+' non-numerik BASE fallback ke _extract_polis_tokens",
    # BASE bukan pure digit → expand_plus_suffix return None → fallback
    clean_polis("ACA100010324110001373+ACA100010324110001374"),
    # fallback: _extract_polis_tokens splits on '+', keduanya valid polis token
    ["ACA100010324110001373", "ACA100010324110001374"],
)


# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print("\n" + "-" * 60)
print(f"  Result: {_passed}/{_total} tests passed")
if _passed == _total:
    print("  All tests PASSED")
else:
    failed = _total - _passed
    print(f"  {failed} test(s) FAILED")
print("-" * 60 + "\n")

sys.exit(0 if _passed == _total else 1)
