# AS/400 Reverse Engineering – Analyse-Report
## Ergebnisse nb_02 | Stand: 16.04.2026

---

## 1. Übersicht Systembestand

| Kennzahl | Wert |
|---|---|
| Programme gesamt (DSPOBJD) | 11.419 |
| Programm-Referenzen (DSPPGMREF) | 114.439 |
| Datei-Zugriffe | 65.211 |
| Call-Graph-Kanten | 47.368 |
| Unique referenzierte Tabellen | 11.053 |
| Trigger | 135 |
| SQL-Routinen | 513 |
| Indizes | 577 |
| Tabellen (SYSTABLES) | 42.733 |
| Libraries | 145 |

---

## 2. Programme – Wichtigkeits-Kategorien

| Kategorie | Anzahl | Anteil |
|---|---|---|
| HIGH | 0 | 0% |
| MEDIUM | 1 | <1% |
| LOW | 77 | 1% |
| UNUSED | 11.363 | 99% |
| **Gesamt** | **11.441** | |

### Interpretation
Der hohe UNUSED-Anteil ist **nicht** gleichbedeutend mit totem Code. Er erklärt sich durch zwei Faktoren:

1. **SYSPROGRAMSTAT erfasst nur direkte Aufrufe** – Programme die indirekt (via CALL-Kette) aufgerufen werden, erscheinen dort mit `days_used_count = 0`
2. **DSPPGMREF-Abdeckung** – noch nicht alle Libraries sind vollständig in DSPPGMREF erfasst, daher fehlen `tables_written`-Werte in der Score-Berechnung

→ **Maßnahme:** Nach vollständigem DSPPGMREF-Lauf über alle Libraries werden die Scores deutlich differenzierter.

---

## 3. Top 10 Programme – Importance Score

| Rang | Library | Programm | Typ | Score | Nutzungstage | calls_out |
|---|---|---|---|---|---|---|
| 1 | NOMAX | MXSETASPGP | CLE | 100.0 | 2.015 | 5 |
| 2 | QUSROND | BAA1UPDTRG | CLE | 93.3 | 1.880 | 4 |
| 3 | ODINTERDAT | CRTDOCID | CLE | 85.3 | 1.718 | 4 |
| 4 | QUSROND | BAA1INSTRG | CLE | 85.3 | 1.718 | 3 |
| 5 | ODINTERLIB | SRCHFCDOC | RPGLE | 77.5 | 1.560 | 6 |
| 6 | ODINTERLIB | CHKEXFR | RPGLE | 77.4 | 1.558 | 5 |
| 7 | ODINTERLIB | GETODMETAD | RPGLE | 76.3 | 1.536 | 5 |
| 8 | VRBSTI | SV10IMW | RPGLE | 75.1 | 1.511 | 5 |
| 9 | DOCUMINTS | PRDINSTRRG | CLE | 72.9 | 1.469 | 8 |

### Interpretation
- **MXSETASPGP** (NOMAX) ist das meistgenutzte Programm im System – 2.015 Nutzungstage
- **BAA1UPDTRG / BAA1INSTRG** (QUSROND) – der Name deutet auf Trigger-Programme hin (`UPDTRG` = Update Trigger, `INSTRG` = Insert Trigger) → **versteckte Geschäftslogik**
- Die Library **ODINTERLIB** taucht dreifach auf – offensichtlich ein zentrales Modul für Dokumenten-/Objekt-Interaktion
- Auffällig: alle Top-Programme sind **CLE oder RPGLE** – modernere Kompilate, aktiv im Einsatz

---

## 4. Tabellen – Wichtigkeits-Kategorien

| Kategorie | Anzahl | Anteil |
|---|---|---|
| HOT | 0 | 0% |
| MEDIUM | 3 | <1% |
| LOW | 706 | 6% |
| COLD | 10.344 | 94% |
| **Gesamt** | **11.053** | |

---

## 5. Top 5 Tabellen – Importance Score

| Rang | Library | Tabelle | Score | Kategorie | Zugreifende Programme |
|---|---|---|---|---|---|
| 1 | VRDAT | $DIVPPF | 45.5 | MEDIUM | 1.251 |
| 2 | QUSROND | BAA1 | 36.3 | MEDIUM | 849 (est.) |
| 3 | VRDAT | STADRP | 34.3 | MEDIUM | 849 |
| 4 | VRDAT | FIRMAP | 29.8 | LOW | 688 |
| 5 | VRDAT | VTRGP | 27.3 | LOW | 599 |

### Interpretation
- **$DIVPPF** (VRDAT) – 1.251 Programme greifen auf diese Tabelle zu → **zentrale Kerntabelle**, wahrscheinlich Vertrags- oder Divisionsstammdaten
- **BAA1** (QUSROND) – korrespondiert mit den Top-Programmen BAA1UPDTRG/BAA1INSTRG → zentraler Geschäftsprozess-Bereich
- **STADRP, FIRMAP, VTRGP** (alle VRDAT) – Stammdaten-Tabellen (Adressen, Firmen, Verträge?)
- Die Library **VRDAT** dominiert die Top-Tabellen → Kern-Datenhaltung des Systems

---

## 6. Call-Graph – Degrees

| Kennzahl | Wert |
|---|---|
| Programme mit ausgehenden Aufrufen | Teil der 12.371 |
| Programme mit eingehenden Aufrufen | Teil der 12.371 |
| Call-Graph-Kanten gesamt | 47.368 |

→ Detaillierte Visualisierung folgt in nb_03

---

## 7. Dead-Code-Kandidaten

| Kennzahl | Wert |
|---|---|
| Kandidaten gesamt | 11.279 |

**Wichtiger Hinweis:** Diese Zahl ist eine **obere Schranke**. Nach vollständigem DSPPGMREF-Lauf und Berücksichtigung indirekter Aufrufe wird die tatsächliche Zahl deutlich geringer sein.

---

## 8. Trigger-Impact

| Kennzahl | Wert |
|---|---|
| Trigger gesamt | 135 |
| Trigger-Impact-Einträge | 135 |

→ 135 Trigger bedeuten **versteckte Geschäftslogik** die in DSPPGMREF nicht sichtbar ist. Diese Programme müssen separat analysiert werden.

---

## 9. Read/Write-Matrix

Aktuell: **15 × 15** (begrenzt durch fehlende `tables_written`-Werte)

Nach vollständigem DSPPGMREF-Lauf: **30 × 30** geplant

---

## 10. Offene Punkte & nächste Schritte

| Priorität | Maßnahme |
|---|---|
| 🔴 Hoch | DSPPGMREF vollständig über alle Libraries laufen lassen |
| 🔴 Hoch | nb_03 Visualisierungen erstellen |
| 🟡 Mittel | Dead-Code-Kandidaten nach DSPPGMREF-Vollständigkeit neu bewerten |
| 🟡 Mittel | Trigger-Programme in Call-Graph integrieren |
| 🟢 Später | RPG/CL Source-Code in SQLite laden |
| 🟢 Später | Score-Gewichtung nach erstem Review anpassen |

---

## 11. Score-Berechnung (Referenz)

### Programm-Score (0–100)
```
Score = norm(days_used_count)  × 0.30
      + norm(tables_written)   × 0.25
      + norm(total_file_refs)  × 0.20
      + norm(calls_out)        × 0.15
      + norm(called_by_n)      × 0.10
```

### Tabellen-Score (0–100)
```
Score = norm(pgm_count)   × 0.35
      + norm(writers)     × 0.30
      + norm(days_used)   × 0.20
      + norm(indexes)     × 0.15
```

*norm() = Normalisierung auf 0–100 relativ zum Maximum*

---

*Erstellt mit: nb_01_extract.py + nb_02_analyse.py*
*Datenbasis: AS/400 IBM Power i (pre-V7)*
*SQLite: as400_analysis.sqlite*
