import os
from datetime import datetime
from queue import Queue
from threading import Thread, Lock
from concurrent.futures import ProcessPoolExecutor, as_completed

# ── Konfiguration (wird vom Notebook gesetzt) ─────────────────────────────
SKIP_PREFIX  = ('core',)
MAX_THREADS  = 16     # Threads pro Queue-Scan
SCHWELLWERT  = 50     # Kinder-Anzahl: ab hier gilt Dir als "groß"


# ── Hilfsfunktion ─────────────────────────────────────────────────────────

def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')


# ── Kinder zählen (für Klassifizierung klein/groß) ────────────────────────

def count_children(path: str) -> int:
    """
    Zählt direkte Kinder eines Verzeichnisses (ein einziger scandir-Aufruf).
    Symlinks und gefilterte Namen werden ausgeschlossen.
    Gibt 0 zurück bei Fehler.
    """
    try:
        return sum(
            1 for e in os.scandir(path)
            if not e.is_symlink()
            and not any(e.name.startswith(p) for p in SKIP_PREFIX)
        )
    except OSError:
        return 0


# ── Worker-Funktion für dynamische Queue ──────────────────────────────────

def _queue_worker(q: Queue, results: list, errors: dict, lock: Lock):
    """
    Consumer-Thread: holt Pfade aus der Queue, scannt sie,
    legt gefundene Subdirs sofort wieder in die Queue.
    Beendet sich bei 'None' (Poison Pill).
    """
    while True:
        path = q.get()

        if path is None:        # Poison Pill → sauber beenden
            q.task_done()
            break

        try:
            with os.scandir(path) as scn:
                for x in scn:

                    if x.is_symlink():
                        continue
                    if any(x.name.startswith(p) for p in SKIP_PREFIX):
                        continue

                    try:
                        if x.is_dir(follow_symlinks=False):
                            q.put(x.path)      # ← sofort neuen Task einreihen!

                        elif x.is_file(follow_symlinks=False):
                            st = x.stat(follow_symlinks=False)
                            entry = {
                                'Name':      x.name,
                                'Path':      x.path,
                                'ext':       x.name.rsplit('.', 1)[-1].lower() if '.' in x.name else '',
                                'Type':      st.st_mode,
                                'Inode':     st.st_ino,
                                'IO_Nbr':    st.st_dev,
                                'NbrLinks':  st.st_nlink,
                                'UID':       st.st_uid,
                                'GrID':      st.st_gid,
                                'Size_MB':   round(st.st_size / 1024**2, 4),
                                'MRAcc_Tme': _fmt(st.st_atime),
                                'MRMod_Tme': _fmt(st.st_mtime),
                                'MRCr_Tme':  _fmt(st.st_ctime),
                            }
                            with lock:
                                results.append(entry)

                    except OSError as e:
                        with lock:
                            errors[x.path] = str(e)

        except OSError as e:
            with lock:
                errors[path] = str(e)

        finally:
            q.task_done()


# ── Kern: dynamischer Thread-Queue-Scan ab einem Startpfad ───────────────

def scan_with_queue(start_path: str, n_threads: int = MAX_THREADS) -> tuple:
    """
    Scannt rekursiv ab start_path mit dynamischer Queue + Thread-Pool.
    Kein Level-by-Level — Threads arbeiten kontinuierlich ohne Pausen.
    Gibt zurück: (all_entries, all_errors)
    """
    q       = Queue()
    results = []
    errors  = {}
    lock    = Lock()

    q.put(start_path)

    threads = [
        Thread(target=_queue_worker, args=(q, results, errors, lock), daemon=True)
        for _ in range(n_threads)
    ]
    for t in threads:
        t.start()

    q.join()    # blockiert bis Queue leer UND alle task_done() gerufen

    # Threads sauber beenden via Poison Pills
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()

    return results, errors


# ── Erste Ebene klassifizieren: klein vs. groß ────────────────────────────

def classify_root_dirs(root_dirs: list, schwellwert: int = SCHWELLWERT) -> tuple:
    """
    Teilt Root-Dirs in zwei Gruppen:
      klein: wenige direkte Kinder → gemeinsame Queue + Threads
      groß:  viele direkte Kinder  → je eigener Prozess + Queue + Threads
    Gibt zurück: (kleine_dirs, grosse_dirs)
    """
    kleine = []
    grosse = []

    print(f"  Klassifiziere {len(root_dirs)} Root-Verzeichnisse (Schwellwert: {schwellwert} Kinder) ...")
    for d in root_dirs:
        n = count_children(d)
        if n >= schwellwert:
            grosse.append(d)
            print(f"    GROSS  ({n:>5} Kinder): {d}")
        else:
            kleine.append(d)
            print(f"    klein  ({n:>5} Kinder): {d}")

    print(f"\n  → {len(grosse)} große Dirs  (je eigener Prozess + {MAX_THREADS} Threads)")
    print(f"  → {len(kleine)} kleine Dirs (gemeinsame Queue + {MAX_THREADS} Threads)")
    return kleine, grosse


# ── Prozess-Einstiegspunkt (muss auf Modul-Ebene stehen für Pickling) ────

def scan_root_process(start_path: str) -> tuple:
    """
    Wird als eigener PROZESS für große Dirs aufgerufen.
    Startet intern scan_with_queue mit vollem Thread-Pool.
    """
    return scan_with_queue(start_path, n_threads=MAX_THREADS)


# ── Root-Verzeichnisse ermitteln ──────────────────────────────────────────

def get_root_dirs(base: str, skip_prefix: tuple = SKIP_PREFIX) -> list:
    """
    Ermittelt alle direkten Unterverzeichnisse ab 'base'.
    Symlinks und gefilterte Namen werden ausgeschlossen.
    """
    try:
        return [
            e.path for e in os.scandir(base)
            if not e.is_symlink()
            and e.is_dir(follow_symlinks=False)
            and not any(e.name.startswith(p) for p in skip_prefix)
        ]
    except OSError:
        return [base]
