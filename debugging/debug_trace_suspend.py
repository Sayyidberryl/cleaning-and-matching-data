"""
debug_trace_suspend.py — Step-by-step trace for a single Suspend row.

Usage:
    1. Set TARGET_SLIP below (slip value, polis, or RECEIPT NO substring).
    2. Run: python debug_trace_suspend.py

The script replicates the exact same lookup indexes as main.py (by importing
from it), finds all raw SUSPEND rows matching the target, then runs each
pipeline pass (Pass 1 OSBAL, Pass 3 SLIPDB, Pass 5 FACUL, Pass 7 Insured)
and prints detailed diagnostics including raw vs narrowed scenario, source,
and resolved fac codes.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.modules['numexpr'] = None
sys.modules['bottleneck'] = None

import re
import pandas as pd

from prod_sus_1 import (
    SUSPEND_FILE, OSBAL_FILE, FACUL_FILE, SLIPDB_FILE,
    OSBAL_FACODE_COL, FACUL_FACODE_COL, SLIPDB_FACODE_COL,
    _load_excel, _get_clean_cols, _build_lookup,
    _match_polis_slip, _match_insured,
    _narrow,
    _resolve_facode, _normalize, _map_scenario,
    _collect_clean_values, _collect_all_values,
)


# =============================================================================
# CONFIG — change this to trace a different row
# =============================================================================
TARGET_SLIP = "70001062503003793"


def _safe_load_excel(path: str, label: str, optional: bool = False) -> tuple:
    """Load Excel via _load_excel, auto-delete stale cache on failure."""
    try:
        return _load_excel(path, label, optional)
    except Exception as e:
        print(f"  [!] Cache read failed for {label}: {e}")
        cache = path + ".cache.pkl"
        if os.path.exists(cache):
            try:
                os.remove(cache)
                print(f"  -> Deleted stale cache: {cache}")
            except Exception:
                pass
        return _load_excel(path, label, optional)


def _row_matches_target(sus: dict, target: str, slip_cols: list) -> bool:
    """True if target is a substring of slip_ori, any clean slip col, or RECEIPT NO."""
    t = str(target).strip().upper()
    if not t:
        return False
    if t in str(sus.get("slip_ori", "")).strip().upper():
        return True
    if any(t in str(sus.get(c, "")).strip().upper() for c in slip_cols):
        return True
    if t in str(sus.get("RECEIPT NO", "")).strip().upper():
        return True
    return False


def _get_fac_codes(rows: list, indices: list, fac_col: str) -> list:
    """Return sorted unique FAC_CODE values from given row indices."""
    codes = {_normalize(rows[i].get(fac_col, "")) for i in indices}
    codes.discard("")
    return sorted(codes)


def _trace_row(
    row_idx: int,
    sus: dict,
    osbal_rows: list,
    facul_rows: list,
    slipdb_rows: list,
    lkp_osbal: tuple,
    lkp_facul: tuple,
    lkp_slipdb: tuple,
    polis_sus: list, slip_sus: list, insured_sus: list,
    polis_osbal: list, slip_osbal: list, insured_osbal: list,
    polis_facul: list, slip_facul: list, insured_facul: list,
    polis_slipdb: list, slip_slipdb: list, insured_slipdb: list,
    facode_osbal_idx: dict,
):
    """Run and print the full matching trace for one Suspend row."""

    print("\n" + "=" * 90)
    print(f"  [RAW SUSPEND ROW #{row_idx + 1}]")
    print("=" * 90)
    for label, key in [
        ("RECEIPT NO",        "RECEIPT NO"),
        ("CREDIT NOTES",      "CREDIT NOTES"),
        ("DETAIL RINCIAN NO", "DETAIL RINCIAN NO"),
        ("RECEIPT DATE",      "RECEIPT DATE"),
        ("CEDANT NAME",       "CEDANT NAME"),
        ("INSURED ORI",       "insured_ori"),
        ("CLEAN INSURED 1",   "clean insured 1"),
        ("POLIS ORI",         "polis_ori"),
        ("CLEAN POLIS 1",     "clean polis 1"),
        ("SLIP ORI",          "slip_ori"),
        ("CLEAN SLIP 1",      "clean slip 1"),
        ("AMOUNT ORI",        "AMOUNT ORI"),
    ]:
        print(f"  {label:<20}: {sus.get(key, '')}")
    print("-" * 90)
    print("  PIPELINE TRACE:")
    print("-" * 90)

    winning_pass = None
    winning_info = None

    # ------------------------------------------------------------------
    # Pass 1: OSBAL (Polis/Slip)
    # ------------------------------------------------------------------
    lkp = lkp_osbal
    m1, lbl1 = _match_polis_slip(
        sus,
        lkp[0], lkp[1], lkp[3], lkp[4],
        polis_sus, slip_sus,
        rows=osbal_rows,
        slip_ref_cols=slip_osbal, polis_ref_cols=polis_osbal,
        token_slip=lkp[6], token_polis=lkp[7],
    )
    print("\n[PASS 1] OSBAL (Polis/Slip Exact & LIKE)")
    if m1:
        raw_fac = _get_fac_codes(osbal_rows, m1, OSBAL_FACODE_COL)
        n1, nlbl1 = _narrow(sus, m1, osbal_rows, lbl1, polis_osbal, slip_osbal, polis_sus, slip_sus)
        final_fac = _get_fac_codes(osbal_rows, n1, OSBAL_FACODE_COL)
        print(f"  Match    : {len(m1)} raw -> {len(n1)} narrowed | Scenario: {lbl1} -> {nlbl1}")
        print(f"  FAC code : raw={raw_fac}  final={final_fac}")
        print(f"  Suspend polis values: {_collect_all_values(sus, polis_sus, 'polis_ori')}")
        for i in m1:
            r = osbal_rows[i]
            print(f"    [OSBAL idx {i}] FAC={r.get(OSBAL_FACODE_COL,'')} | polis_ori={r.get('polis_ori','')} | clean polis 1={r.get('clean polis 1','')}")

        if not winning_pass:
            winning_pass = "Pass 1 (OSBAL)"
            winning_info = {"source": "OSBAL", "scenario": nlbl1, "fac_codes": final_fac, "osbal_idx": n1}
    else:
        print("  Match    : NO MATCH")

    # ------------------------------------------------------------------
    # Pass 3: SLIPDB (Polis/Slip -> OSBAL resolution)
    # ------------------------------------------------------------------
    lkp = lkp_slipdb
    print("\n[PASS 3] R/I Slip DB (Polis/Slip Exact & LIKE -> OSBAL resolution)")
    if slipdb_rows:
        m3, lbl3 = _match_polis_slip(
            sus,
            lkp[0], lkp[1], lkp[3], lkp[4],
            polis_sus, slip_sus,
            rows=slipdb_rows,
            slip_ref_cols=slip_slipdb, polis_ref_cols=polis_slipdb,
            token_slip=lkp[6], token_polis=lkp[7],
        )
        if m3:
            raw_fac3 = _get_fac_codes(slipdb_rows, m3, SLIPDB_FACODE_COL)
            n3, nlbl3 = _narrow(sus, m3, slipdb_rows, lbl3, polis_slipdb, slip_slipdb, polis_sus, slip_sus)
            narrow_fac3 = _get_fac_codes(slipdb_rows, n3, SLIPDB_FACODE_COL)
            res3, ok3 = _resolve_facode([slipdb_rows[i] for i in n3], SLIPDB_FACODE_COL, facode_osbal_idx, osbal_rows)
            osbal_fac3 = _get_fac_codes(osbal_rows, res3, OSBAL_FACODE_COL) if ok3 else []
            print(f"  Match    : {len(m3)} raw -> {len(n3)} narrowed | Scenario: {lbl3} -> {nlbl3}")
            print(f"  SLIPDB FAC : raw={raw_fac3}  narrowed={narrow_fac3}")
            for i in n3:
                r = slipdb_rows[i]
                print(f"    [idx {i}] FAC={r.get(SLIPDB_FACODE_COL,'')} | slip={r.get('slip_ori','')} | polis={r.get('polis_ori','')}")
            print(f"  OSBAL resolve: {'OK' if ok3 else 'FAILED'} | OSBAL FAC={osbal_fac3}")
            if not winning_pass and ok3:
                winning_pass = "Pass 3 (SLIPDB)"
                winning_info = {"source": "SLIPDB", "scenario": nlbl3, "fac_codes": osbal_fac3, "osbal_idx": res3}
        else:
            print("  Match    : NO MATCH")
    else:
        print("  Match    : SKIPPED (SLIPDB empty)")

    # ------------------------------------------------------------------
    # Pass 5: FACUL (Polis/Slip -> OSBAL resolution)
    # ------------------------------------------------------------------
    lkp = lkp_facul
    print("\n[PASS 5] FACUL (Polis/Slip Exact & LIKE -> OSBAL resolution)")
    if facul_rows:
        m5, lbl5 = _match_polis_slip(
            sus,
            lkp[0], lkp[1], lkp[3], lkp[4],
            polis_sus, slip_sus,
            rows=facul_rows,
            slip_ref_cols=slip_facul, polis_ref_cols=polis_facul,
            token_slip=lkp[6], token_polis=lkp[7],
        )
        if m5:
            raw_fac5 = _get_fac_codes(facul_rows, m5, FACUL_FACODE_COL)
            n5, nlbl5 = _narrow(sus, m5, facul_rows, lbl5, polis_facul, slip_facul, polis_sus, slip_sus)
            narrow_fac5 = _get_fac_codes(facul_rows, n5, FACUL_FACODE_COL)
            res5, ok5 = _resolve_facode([facul_rows[i] for i in n5], FACUL_FACODE_COL, facode_osbal_idx, osbal_rows)
            osbal_fac5 = _get_fac_codes(osbal_rows, res5, OSBAL_FACODE_COL) if ok5 else []
            print(f"  Match    : {len(m5)} raw -> {len(n5)} narrowed | Scenario: {lbl5} -> {nlbl5}")
            print(f"  FACUL FAC : raw={raw_fac5}  narrowed={narrow_fac5}")
            for i in n5:
                r = facul_rows[i]
                print(f"    [idx {i}] FAC={r.get(FACUL_FACODE_COL,'')} | slip={r.get('slip_ori','')} | polis={r.get('polis_ori','')}")
            print(f"  OSBAL resolve: {'OK' if ok5 else 'FAILED'} | OSBAL FAC={osbal_fac5}")
            if not winning_pass and ok5:
                winning_pass = "Pass 5 (FACUL)"
                winning_info = {"source": "FACUL", "scenario": nlbl5, "fac_codes": osbal_fac5, "osbal_idx": res5}
        else:
            print("  Match    : NO MATCH")
    else:
        print("  Match    : SKIPPED (FACUL empty)")

    # ------------------------------------------------------------------
    # Pass 7: Insured fallback
    # ------------------------------------------------------------------
    print("\n[PASS 7] Insured Fallback (OSBAL -> SLIPDB -> FACUL)")

    m7a, lbl7a = _match_insured(sus, lkp_osbal[2], lkp_osbal[5], insured_sus,
                                rows=osbal_rows, insured_ref_cols=insured_osbal, token_insured=lkp_osbal[8])
    if m7a:
        fac7a = _get_fac_codes(osbal_rows, m7a, OSBAL_FACODE_COL)
        lbl7a_mapped = _map_scenario(lbl7a)
        print(f"  [7a OSBAL]  : MATCH {len(m7a)} rows | Scenario: {lbl7a_mapped} | FAC={fac7a}")
        if not winning_pass:
            winning_pass = "Pass 7a (OSBAL Insured)"
            winning_info = {"source": "OSBAL", "scenario": lbl7a_mapped, "fac_codes": fac7a, "osbal_idx": m7a}
    else:
        print("  [7a OSBAL]  : NO MATCH")

    if slipdb_rows:
        m7b, lbl7b = _match_insured(sus, lkp_slipdb[2], lkp_slipdb[5], insured_sus,
                                    rows=slipdb_rows, insured_ref_cols=insured_slipdb, token_insured=lkp_slipdb[8])
        if m7b:
            fac7b_slipdb = _get_fac_codes(slipdb_rows, m7b, SLIPDB_FACODE_COL)
            res7b, ok7b = _resolve_facode([slipdb_rows[i] for i in m7b], SLIPDB_FACODE_COL, facode_osbal_idx, osbal_rows)
            fac7b_osbal = _get_fac_codes(osbal_rows, res7b, OSBAL_FACODE_COL) if ok7b else []
            print(f"  [7b SLIPDB] : MATCH {len(m7b)} rows | Scenario: {_map_scenario(lbl7b)} | SLIPDB FAC={fac7b_slipdb} | OSBAL={fac7b_osbal}")
            if not winning_pass and ok7b:
                winning_pass = "Pass 7b (SLIPDB Insured)"
                winning_info = {"source": "SLIPDB", "scenario": _map_scenario(lbl7b), "fac_codes": fac7b_osbal, "osbal_idx": res7b}
        else:
            print("  [7b SLIPDB] : NO MATCH")

    if facul_rows:
        m7c, lbl7c = _match_insured(sus, lkp_facul[2], lkp_facul[5], insured_sus,
                                    rows=facul_rows, insured_ref_cols=insured_facul, token_insured=lkp_facul[8])
        if m7c:
            fac7c_facul = _get_fac_codes(facul_rows, m7c, FACUL_FACODE_COL)
            res7c, ok7c = _resolve_facode([facul_rows[i] for i in m7c], FACUL_FACODE_COL, facode_osbal_idx, osbal_rows)
            fac7c_osbal = _get_fac_codes(osbal_rows, res7c, OSBAL_FACODE_COL) if ok7c else []
            print(f"  [7c FACUL]  : MATCH {len(m7c)} rows | Scenario: {_map_scenario(lbl7c)} | FACUL FAC={fac7c_facul} | OSBAL={fac7c_osbal}")
            if not winning_pass and ok7c:
                winning_pass = "Pass 7c (FACUL Insured)"
                winning_info = {"source": "FACUL", "scenario": _map_scenario(lbl7c), "fac_codes": fac7c_osbal, "osbal_idx": res7c}
        else:
            print("  [7c FACUL]  : NO MATCH")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("  WINNING PASS SUMMARY:")
    print("-" * 90)
    if winning_pass:
        facs = winning_info["fac_codes"]
        if len(facs) == 1:
            status = "DEFINITE (1 FAC Code)"
            mark   = facs[0]
        elif len(facs) > 1:
            status = "AMBIGUOUS (>1 FAC Codes -> 'facode lebih dari 1')"
            mark   = "facode lebih dari 1"
        else:
            status = "UNMATCHED (OSBAL resolution failed)"
            mark   = ""
        print(f"  Winning Pass     : {winning_pass}")
        print(f"  Source           : {winning_info['source']}")
        print(f"  Final Scenario   : {winning_info['scenario']}")
        print(f"  FAC Code Status  : {status}")
        print(f"  FAC Code(s)      : {facs}")
        print(f"  Mark Admin FC    : '{mark}'")
    else:
        print("  Winning Pass     : Pass 8 (Fallback — Unmatching)")
        print("  FAC Code(s)      : []")
    print("=" * 90)


def main():
    print("=" * 90)
    print(f"  DEBUG TRACE — TARGET: '{TARGET_SLIP}'")
    print("=" * 90)

    print("\n[1/3] Loading data ...")
    suspend_rows, suspend_cols = _safe_load_excel(SUSPEND_FILE, "SUSPEND")
    osbal_rows,   osbal_cols   = _safe_load_excel(OSBAL_FILE,   "OSBAL")
    facul_rows,   facul_cols   = _safe_load_excel(FACUL_FILE,   "FACUL")
    slipdb_rows,  slipdb_cols  = _safe_load_excel(SLIPDB_FILE,  "SLIPDB", optional=True)

    print("\n[2/3] Detecting clean columns ...")
    polis_sus   = _get_clean_cols(suspend_cols, "clean polis")
    slip_sus    = _get_clean_cols(suspend_cols, "clean slip")
    insured_sus = _get_clean_cols(suspend_cols, "clean insured")

    polis_osbal   = _get_clean_cols(osbal_cols, "clean polis")
    slip_osbal    = _get_clean_cols(osbal_cols, "clean slip")
    insured_osbal = _get_clean_cols(osbal_cols, "clean insured")

    polis_facul   = _get_clean_cols(facul_cols, "clean polis")
    slip_facul    = _get_clean_cols(facul_cols, "clean slip")
    insured_facul = _get_clean_cols(facul_cols, "clean insured")

    polis_slipdb   = _get_clean_cols(slipdb_cols, "clean polis")
    slip_slipdb    = _get_clean_cols(slipdb_cols, "clean slip")
    insured_slipdb = _get_clean_cols(slipdb_cols, "clean insured")

    print("\n[3/3] Building lookup indexes ...")
    lkp_osbal  = _build_lookup(osbal_rows,  polis_osbal,  slip_osbal,  insured_osbal,  OSBAL_FACODE_COL)
    lkp_facul  = _build_lookup(facul_rows,  polis_facul,  slip_facul,  insured_facul,  FACUL_FACODE_COL)
    lkp_slipdb = _build_lookup(slipdb_rows, polis_slipdb, slip_slipdb, insured_slipdb, SLIPDB_FACODE_COL)
    facode_osbal_idx = lkp_osbal[9]

    print(f"\n[Search] Looking for '{TARGET_SLIP}' in SUSPEND ...")
    hits = [(i, r) for i, r in enumerate(suspend_rows) if _row_matches_target(r, TARGET_SLIP, slip_sus)]
    print(f"-> Found {len(hits)} matching row(s).")

    if not hits:
        print(f"\n[INFO] No row found for '{TARGET_SLIP}'. Check the query.")
        return

    for idx, sus in hits:
        _trace_row(
            idx, sus,
            osbal_rows, facul_rows, slipdb_rows,
            lkp_osbal, lkp_facul, lkp_slipdb,
            polis_sus, slip_sus, insured_sus,
            polis_osbal, slip_osbal, insured_osbal,
            polis_facul, slip_facul, insured_facul,
            polis_slipdb, slip_slipdb, insured_slipdb,
            facode_osbal_idx,
        )


if __name__ == "__main__":
    main()
