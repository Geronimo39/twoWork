"""
=============================================================================
nb_check_completeness.py
AS/400 Reverse Engineering – Vollständigkeits-Check
=============================================================================
Prüft:
    1. RW-Matrix (Chart 05) – warum dünn?
    2. Write-Heavy (Chart 11) – warum leer?
    3. DSPPGMREF – Vollständigkeit über alle Libraries
=============================================================================
"""

import sqlite3
import pandas as pd
from pathlib import Path

# =============================================================================
# ── Konfiguration ─────────────────────────────────────────────────────────────
# =============================================================================

PTH      = Path(r"C:\Users\Stadtherr\Documents\SndBx\4Reporting\DB2_DataLineage")
SQLITE_DB = PTH / "as400_analysis.sqlite"

# =============================================================================
# ── Verbindung ────────────────────────────────────────────────────────────────
# =============================================================================

db = sqlite3.connect(SQLITE_DB)
print("=" * 65)
print("VOLLSTÄNDIGKEITS-CHECK  –  as400_analysis.sqlite")
print("=" * 65)

# =============================================================================
# 1. CHART 05 – RW-HEATMAP
# =============================================================================

print("\n── 1. RW-Heatmap (Chart 05) ────────────────────────────────")

# 1a. Nutzungsarten in v_data_access
df = pd.read_sql("""
    SELECT usage, usage_label, COUNT(*) AS n
    FROM v_data_access
    GROUP BY usage, usage_label
    ORDER BY n DESC
""", db)
print("\nNutzungsarten in v_data_access:")
print(df.to_string(index=False))

# 1b. RW-Matrix Größe
try:
    n_rw = db.execute("SELECT COUNT(*) FROM rw_matrix").fetchone()[0]
    print(f"\nRW-Matrix Zeilen: {n_rw:,}")
except Exception as e:
    print(f"\nRW-Matrix: {e}")

# 1c. Wie viele Programme haben überhaupt Schreibzugriffe?
df = pd.read_sql("""
    SELECT
        COUNT(DISTINCT pgm_key) AS pgms_mit_write
    FROM v_data_access
    WHERE is_write = 1
""", db)
print(f"Programme mit Schreibzugriffen: {df.iloc[0,0]:,}")

# 1d. Wie viele Tabellen werden geschrieben?
df = pd.read_sql("""
    SELECT
        COUNT(DISTINCT table_key) AS tabellen_mit_write
    FROM v_data_access
    WHERE is_write = 1
""", db)
print(f"Tabellen mit Schreibzugriffen: {df.iloc[0,0]:,}")

# =============================================================================
# 2. CHART 11 – WRITE-HEAVY
# =============================================================================

print("\n── 2. Write-Heavy Programme (Chart 11) ─────────────────────")

df = pd.read_sql("""
    SELECT
        SUM(CASE WHEN tables_written > 0   THEN 1 ELSE 0 END) AS hat_writes,
        SUM(CASE WHEN tables_written = 0   THEN 1 ELSE 0 END) AS keine_writes,
        SUM(CASE WHEN tables_written IS NULL THEN 1 ELSE 0 END) AS null_writes,
        COUNT(*) AS gesamt
    FROM v_pgm_profile
""", db)
print("\nVerteilung tables_written in v_pgm_profile:")
print(df.to_string(index=False))

# Top 10 nach tables_written
df = pd.read_sql("""
    SELECT pgm_lib, pgm_name, pgm_attribute,
           tables_written, tables_read, total_file_refs
    FROM v_pgm_profile
    ORDER BY tables_written DESC
    LIMIT 10
""", db)
print("\nTop 10 Programme nach tables_written:")
print(df.to_string(index=False))

# =============================================================================
# 3. DSPPGMREF – VOLLSTÄNDIGKEIT
# =============================================================================

print("\n── 3. DSPPGMREF Vollständigkeit ────────────────────────────")

# 3a. Libraries in DSPPGMREF
df_pgmref_libs = pd.read_sql("""
    SELECT pgm_lib, COUNT(DISTINCT pgm_name) AS pgm_count
    FROM dsppgmref_clean
    GROUP BY pgm_lib
    ORDER BY pgm_count DESC
""", db)
print(f"\nLibraries in DSPPGMREF: {len(df_pgmref_libs)}")
print(df_pgmref_libs.to_string(index=False))

# 3b. Vergleich DSPOBJD vs. DSPPGMREF
df_vergleich = pd.read_sql("""
    SELECT
        o.pgm_lib,
        COUNT(DISTINCT o.pgm_name)                         AS in_objd,
        COUNT(DISTINCT r.pgm_name)                         AS in_pgmref,
        COUNT(DISTINCT o.pgm_name) -
        COUNT(DISTINCT r.pgm_name)                         AS differenz
    FROM dspobjd_clean o
    LEFT JOIN dsppgmref_clean r ON o.pgm_lib = r.pgm_lib
                                AND o.pgm_name = r.pgm_name
    GROUP BY o.pgm_lib
    ORDER BY in_objd DESC
""", db)
print("\nDSPOBJD vs. DSPPGMREF je Library:")
print(df_vergleich.to_string(index=False))

# 3c. Zusammenfassung
total_objd   = df_vergleich["in_objd"].sum()
total_pgmref = df_vergleich["in_pgmref"].sum()
total_diff   = df_vergleich["differenz"].sum()
abdeckung    = round(total_pgmref / total_objd * 100, 1) if total_objd > 0 else 0

print(f"\n── Zusammenfassung ─────────────────────────────────────────")
print(f"  Programme in DSPOBJD:     {total_objd:>8,}")
print(f"  Programme in DSPPGMREF:   {total_pgmref:>8,}")
print(f"  Fehlend in DSPPGMREF:     {total_diff:>8,}")
print(f"  Abdeckung:                {abdeckung:>7.1f}%")

# Libraries die komplett fehlen
df_fehlend = df_vergleich[df_vergleich["in_pgmref"] == 0]
if not df_fehlend.empty:
    print(f"\n  Libraries komplett ohne DSPPGMREF ({len(df_fehlend)}):")
    print(df_fehlend[["pgm_lib","in_objd"]].to_string(index=False))
else:
    print("\n  ✓ Alle Libraries in DSPPGMREF abgedeckt")

# =============================================================================
# ── Abschluss ─────────────────────────────────────────────────────────────────
# =============================================================================

db.close()
print("\n" + "=" * 65)
print("✓ Check abgeschlossen")
print("=" * 65)
