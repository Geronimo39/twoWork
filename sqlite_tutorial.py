"""
=============================================================================
sqlite_tutorial.py
SQLite – Praxis-Tutorial für AS/400 Reverse Engineering
=============================================================================
Themen:
    1. Verbindung aufbauen / schließen
    2. Datenbank inspizieren (PRAGMA)
    3. Tabellen und Views abfragen
    4. DataFrames lesen und schreiben
    5. Nützliche Abfrage-Patterns
    6. Views erstellen und löschen
    7. Gimmicks & Tipps
=============================================================================
"""

import sqlite3
import pandas as pd
from pathlib import Path

# =============================================================================
# 1. VERBINDUNG AUFBAUEN
# =============================================================================

# Einfachste Form – Datei wird automatisch erstellt wenn nicht vorhanden
db_path = Path("as400_analysis.sqlite")   # << deinen Pfad anpassen
conn = sqlite3.connect(db_path)

print(f"✓ Verbunden mit: {db_path}")
print(f"  SQLite-Version: {sqlite3.sqlite_version}")

# Tipp: Mit context manager – conn wird automatisch geschlossen
# with sqlite3.connect(db_path) as conn:
#     df = pd.read_sql("SELECT ...", conn)
# Danach ist conn automatisch zu – kein conn.close() nötig

# Für pandas-Abfragen: offen lassen und am Ende schließen
# conn.close()   ← erst ganz am Ende aufrufen!


# =============================================================================
# 2. DATENBANK INSPIZIEREN – PRAGMA
# =============================================================================

print("\n" + "="*60)
print("PRAGMA – Die wichtigsten Inspektions-Befehle")
print("="*60)

# 2a. Alle Tabellen und Views anzeigen
df_objects = pd.read_sql("""
    SELECT name, type 
    FROM sqlite_master 
    WHERE type IN ('table', 'view')
    ORDER BY type, name
""", conn)
print("\n── Alle Tabellen und Views ─────────────────────────────")
print(df_objects.to_string(index=False))

# 2b. Spalten einer Tabelle anzeigen
tabelle = "dspobjd_clean"   # << anpassen
df_cols = pd.read_sql(f"PRAGMA table_info({tabelle})", conn)
print(f"\n── Spalten von '{tabelle}' ──────────────────────────────")
print(df_cols[["cid","name","type","notnull","dflt_value","pk"]].to_string(index=False))

# 2c. Indizes einer Tabelle
df_idx = pd.read_sql(f"PRAGMA index_list({tabelle})", conn)
print(f"\n── Indizes von '{tabelle}' ──────────────────────────────")
if df_idx.empty:
    print("  (keine Indizes)")
else:
    print(df_idx.to_string(index=False))

# 2d. Datenbankgröße und Statistiken
df_stats = pd.read_sql("PRAGMA page_count", conn)
page_size = pd.read_sql("PRAGMA page_size", conn).iloc[0,0]
page_count = pd.read_sql("PRAGMA page_count", conn).iloc[0,0]
db_size_mb = (page_size * page_count) / 1024 / 1024
print(f"\n── Datenbankgröße ──────────────────────────────────────")
print(f"  Page Size:   {page_size:,} Bytes")
print(f"  Page Count:  {page_count:,}")
print(f"  DB-Größe:    {db_size_mb:.2f} MB")

# 2e. Fremdschlüssel-Status
fk_status = pd.read_sql("PRAGMA foreign_keys", conn).iloc[0,0]
print(f"\n  Foreign Keys aktiv: {'Ja' if fk_status else 'Nein'}")

# 2f. View-Definition anzeigen
view_name = "v_pgm_profile"   # << anpassen
df_view = pd.read_sql(f"""
    SELECT sql FROM sqlite_master 
    WHERE name = '{view_name}'
""", conn)
print(f"\n── Definition von View '{view_name}' ───────────────────")
if not df_view.empty:
    print(df_view.iloc[0,0])


# =============================================================================
# 3. TABELLEN ABFRAGEN – NÜTZLICHE PATTERNS
# =============================================================================

print("\n" + "="*60)
print("ABFRAGE-PATTERNS")
print("="*60)

# 3a. Einfache Abfrage
df = pd.read_sql("""
    SELECT pgm_lib, pgm_name, pgm_attribute
    FROM dspobjd_clean
    LIMIT 5
""", conn)
print("\n── Einfache Abfrage ────────────────────────────────────")
print(df.to_string(index=False))

# 3b. Mit WHERE und ORDER BY
df = pd.read_sql("""
    SELECT pgm_lib, pgm_name, pgm_attribute, obj_size
    FROM dspobjd_clean
    WHERE pgm_attribute IN ('RPGLE', 'RPG')
    ORDER BY obj_size DESC
    LIMIT 10
""", conn)
print("\n── Top 10 größte RPG-Programme ─────────────────────────")
print(df.to_string(index=False))

# 3c. Aggregation / GROUP BY
df = pd.read_sql("""
    SELECT 
        pgm_lib,
        pgm_attribute,
        COUNT(*)           AS anzahl,
        SUM(obj_size)      AS gesamtgroesse,
        AVG(obj_size)      AS durchschnitt,
        MAX(obj_size)      AS groesste,
        MIN(obj_size)      AS kleinste
    FROM dspobjd_clean
    GROUP BY pgm_lib, pgm_attribute
    ORDER BY anzahl DESC
    LIMIT 15
""", conn)
print("\n── Programme je Library und Sprache ────────────────────")
print(df.to_string(index=False))

# 3d. JOIN zwischen Tabellen
df = pd.read_sql("""
    SELECT 
        o.pgm_lib,
        o.pgm_name,
        o.pgm_attribute,
        COUNT(DISTINCT r.ref_object) AS referenzen
    FROM dspobjd_clean o
    LEFT JOIN dsppgmref_clean r ON o.pgm_key = r.pgm_key
    GROUP BY o.pgm_lib, o.pgm_name, o.pgm_attribute
    HAVING referenzen > 0
    ORDER BY referenzen DESC
    LIMIT 10
""", conn)
print("\n── Top 10 Programme nach Referenzanzahl (JOIN) ─────────")
print(df.to_string(index=False))

# 3e. Subquery
df = pd.read_sql("""
    SELECT pgm_lib, pgm_name, score
    FROM pgm_importance
    WHERE score > (SELECT AVG(score) FROM pgm_importance)
    ORDER BY score DESC
    LIMIT 10
""", conn)
print("\n── Programme über Durchschnittsscore (Subquery) ────────")
print(df.to_string(index=False))

# 3f. CASE WHEN – bedingte Spalten
df = pd.read_sql("""
    SELECT 
        pgm_lib,
        pgm_name,
        pgm_attribute,
        obj_size,
        CASE 
            WHEN obj_size > 1000000 THEN 'GROSS'
            WHEN obj_size > 100000  THEN 'MITTEL'
            WHEN obj_size > 0       THEN 'KLEIN'
            ELSE 'UNBEKANNT'
        END AS groesse_kategorie
    FROM dspobjd_clean
    ORDER BY obj_size DESC
    LIMIT 10
""", conn)
print("\n── Größen-Kategorisierung mit CASE WHEN ─────────────────")
print(df.to_string(index=False))

# 3g. Parameter-Abfrage – sicher gegen SQL-Injection
pgm_lib_filter = "VRDAT"
df = pd.read_sql("""
    SELECT table_name, pgm_count, score
    FROM table_importance
    WHERE table_lib = ?
    ORDER BY score DESC
    LIMIT 10
""", conn, params=(pgm_lib_filter,))
print(f"\n── Tabellen in Library '{pgm_lib_filter}' (Parameter-Query) ──")
print(df.to_string(index=False))


# =============================================================================
# 4. DATAFRAMES SCHREIBEN
# =============================================================================

print("\n" + "="*60)
print("DATAFRAMES SCHREIBEN")
print("="*60)

# 4a. Neuen DataFrame erstellen und speichern
df_neu = pd.DataFrame({
    "bezeichnung": ["Test A", "Test B", "Test C"],
    "wert":        [100, 200, 300],
    "aktiv":       [True, False, True]
})

df_neu.to_sql("mein_test", conn, if_exists="replace", index=False)
print("✓ Tabelle 'mein_test' geschrieben")

# Wieder lesen
df_check = pd.read_sql("SELECT * FROM mein_test", conn)
print(df_check.to_string(index=False))

# 4b. Anhängen (append)
df_mehr = pd.DataFrame({
    "bezeichnung": ["Test D"],
    "wert":        [400],
    "aktiv":       [True]
})
df_mehr.to_sql("mein_test", conn, if_exists="append", index=False)
print(f"\n✓ Nach Append: {pd.read_sql('SELECT COUNT(*) AS n FROM mein_test', conn).iloc[0,0]} Zeilen")

# 4c. Tabelle löschen
conn.execute("DROP TABLE IF EXISTS mein_test")
conn.commit()
print("✓ Tabelle 'mein_test' wieder gelöscht")


# =============================================================================
# 5. VIEWS ERSTELLEN UND LÖSCHEN
# =============================================================================

print("\n" + "="*60)
print("VIEWS")
print("="*60)

# View erstellen
conn.execute("DROP VIEW IF EXISTS v_mein_test")
conn.execute("""
    CREATE VIEW v_mein_test AS
    SELECT 
        pgm_lib,
        COUNT(*) AS anzahl,
        SUM(obj_size) AS gesamtgroesse
    FROM dspobjd_clean
    GROUP BY pgm_lib
    ORDER BY anzahl DESC
""")
conn.commit()
print("✓ View 'v_mein_test' erstellt")

df_view = pd.read_sql("SELECT * FROM v_mein_test LIMIT 5", conn)
print(df_view.to_string(index=False))

# View wieder löschen
conn.execute("DROP VIEW IF EXISTS v_mein_test")
conn.commit()
print("✓ View 'v_mein_test' wieder gelöscht")


# =============================================================================
# 6. GIMMICKS & TIPPS
# =============================================================================

print("\n" + "="*60)
print("GIMMICKS & TIPPS")
print("="*60)

# 6a. Alle Spaltennamen einer Tabelle als Liste
cols = pd.read_sql("PRAGMA table_info(dspobjd_clean)", conn)["name"].tolist()
print(f"\n── Spalten von dspobjd_clean ({len(cols)} Stück) ──────────")
print(cols)

# 6b. Schnelle Zeilenanzahl aller Tabellen
print("\n── Zeilenanzahl aller Tabellen ─────────────────────────")
tables = pd.read_sql("""
    SELECT name FROM sqlite_master WHERE type='table'
""", conn)["name"].tolist()

for tbl in tables:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<35} {n:>10,}")
    except Exception as e:
        print(f"  {tbl:<35} FEHLER: {e}")

# 6c. Duplikate finden
df_dupes = pd.read_sql("""
    SELECT pgm_lib, pgm_name, COUNT(*) AS n
    FROM dspobjd_clean
    GROUP BY pgm_lib, pgm_name
    HAVING n > 1
    ORDER BY n DESC
    LIMIT 10
""", conn)
print(f"\n── Duplikate in dspobjd_clean ──────────────────────────")
if df_dupes.empty:
    print("  Keine Duplikate gefunden ✓")
else:
    print(df_dupes.to_string(index=False))

# 6d. NULL-Werte zählen
print("\n── NULL-Werte in pgm_importance ────────────────────────")
try:
    cols_imp = pd.read_sql(
        "PRAGMA table_info(pgm_importance)", conn
    )["name"].tolist()
    for col in cols_imp[:8]:   # erste 8 Spalten
        n_null = conn.execute(
            f"SELECT COUNT(*) FROM pgm_importance WHERE {col} IS NULL"
        ).fetchone()[0]
        if n_null > 0:
            print(f"  {col:<30} {n_null:>8,} NULL-Werte")
except Exception as e:
    print(f"  ({e})")

# 6e. Datenbank optimieren
conn.execute("VACUUM")
print("\n✓ VACUUM ausgeführt – Datenbank optimiert")

# 6f. Integrity Check
result = conn.execute("PRAGMA integrity_check").fetchone()[0]
print(f"✓ Integrity Check: {result}")


# =============================================================================
# 7. VERBINDUNG SCHLIESSEN
# =============================================================================

conn.close()
print("\n✓ Verbindung geschlossen")
print("\n" + "="*60)
print("Tutorial abgeschlossen!")
print("="*60)
