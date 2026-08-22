import pandas as pd

FAC = "26FLIG6O"

# ============================================================
# 1. OSBAL (Data 2) - sumber CCOS_BAL_DUE
# ============================================================
print("=" * 60)
print("  OSBAL (Data 2) - osbal_clean_aca.xlsx")
print("=" * 60)

df_osbal = pd.read_excel("data/osbal_clean_aca.xlsx", dtype=str)
print(f"Total baris OSBAL: {len(df_osbal):,}")
print(f"Kolom: {list(df_osbal.columns)}\n")

# Cari kolom fac code
fac_col = None
for c in df_osbal.columns:
    if "CCOS_REF_CODE" in c:
        fac_col = c
        break
if not fac_col:
    for c in df_osbal.columns:
        if "REF_CODE" in c or "FAC_CODE" in c:
            fac_col = c
            break

print(f"FAC col di OSBAL: {fac_col}")

if fac_col:
    mask = df_osbal[fac_col].str.strip().str.upper() == FAC.upper()
    df_fac = df_osbal[mask].copy()
    print(f"Jumlah baris FAC '{FAC}': {len(df_fac)}")

    if len(df_fac) > 0:
        bal_cols = [c for c in df_fac.columns if "BAL" in c]
        curr_cols = [c for c in df_fac.columns if "CURR" in c]
        show_cols = [fac_col] + bal_cols + curr_cols

        for col in bal_cols:
            df_fac[col] = pd.to_numeric(df_fac[col], errors="coerce")
            total = df_fac[col].sum()
            print(f"\n  {col}:")
            print(f"    Per baris: {df_fac[col].tolist()}")
            print(f"    TOTAL    : {total:,.0f}")

        print("\n  Detail rows:")
        print(df_fac[show_cols].to_string())
    else:
        print(f"  [!] FAC '{FAC}' TIDAK DITEMUKAN di OSBAL!")


# ============================================================
# 2. Output V2 - final_output_v2.xlsx
# ============================================================
print("\n")
print("=" * 60)
print("  OUTPUT V2 - final_output_v2.xlsx")
print("=" * 60)

df_v2 = pd.read_excel("data/final_output_v2.xlsx", dtype=str)
print(f"Total baris V2: {len(df_v2):,}")

fac_col_v2 = None
for c in df_v2.columns:
    if "CCOS_REF_CODE" in c or "REF_CODE" in c:
        fac_col_v2 = c
        break

print(f"FAC col di V2: {fac_col_v2}")

if fac_col_v2:
    mask2 = df_v2[fac_col_v2].str.strip().str.upper() == FAC.upper()
    df_v2_fac = df_v2[mask2].copy()
    print(f"Jumlah baris FAC '{FAC}' di V2: {len(df_v2_fac)}")

    if len(df_v2_fac) > 0:
        for col in ["CCOS_BAL_DUE", "CCOS_OR_BAL", "AMOUNT ORI", "AMOUNT_ORI_MIN1", "DIFERENCE"]:
            if col in df_v2_fac.columns:
                df_v2_fac[col] = pd.to_numeric(df_v2_fac[col], errors="coerce")
                print(f"  {col}: {df_v2_fac[col].tolist()}  => total {df_v2_fac[col].sum():,.0f}")

        show_cols2 = [c for c in ["CCOS_REF_CODE", "CCOS_BAL_DUE", "CCOS_OR_BAL",
                                   "AMOUNT ORI", "SKENARIO", "FLAG_PROD",
                                   "RECEIPT NO", "RECEIPT DATE", "CCOS_CURR"] if c in df_v2_fac.columns]
        print("\n  Detail V2:")
        print(df_v2_fac[show_cols2].to_string())
    else:
        print(f"  [!] FAC '{FAC}' TIDAK DITEMUKAN di output V2!")


# ============================================================
# 3. Suspend - suspend_clean_aca.xlsx
# ============================================================
print("\n")
print("=" * 60)
print("  SUSPEND (Data 3) - suspend_clean_aca.xlsx")
print("=" * 60)

df_sus = pd.read_excel("data/suspend_clean_aca.xlsx", dtype=str)
print(f"Total baris Suspend: {len(df_sus):,}")
print(f"Kolom: {list(df_sus.columns)}\n")
