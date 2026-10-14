import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .models import Lead, domain_key
from .buyers import saved_exclusion


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(Exception):
    pass


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.pg = bool(settings.database_url)
        self._ready = False
        self._lock = threading.Lock()

    @contextmanager
    def connection(self):
        if self.pg:
            import psycopg
            conn = psycopg.connect(self.settings.database_url, connect_timeout=8)
        else:
            self.settings.data_dir.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.settings.data_dir / "firma.db", timeout=15)
            conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def sql(self, conn, query, args=()):
        return conn.execute(query.replace("?", "%s") if self.pg else query, args)

    def init(self):
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            with self.connection() as conn:
                self.sql(conn, "CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY, dedupe TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL)")
                self.sql(conn, "CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
                self.sql(conn, "CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, count INTEGER NOT NULL)")
                self.sql(conn, "CREATE TABLE IF NOT EXISTS search_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL)")
            self._ready = True

    def rate_limit(self, bucket, maximum, cost=1):
        self.init()
        with self.connection() as conn:
            row = self.sql(conn, "INSERT INTO limits(bucket, count) VALUES (?, ?) ON CONFLICT(bucket) DO UPDATE SET count=limits.count+? RETURNING count", (bucket,cost,cost)).fetchone()
            # Bucket begins with an hourly timestamp; keep only the newest two days.
            from time import time
            self.sql(conn, "DELETE FROM limits WHERE bucket < ?", (str(int(time() // 3600) - 48) + ":",))
            return row[0] <= maximum

    def list(self, include_legacy=False):
        self.init()
        with self.connection() as conn:
            rows = self.sql(conn, "SELECT id,payload,created_at,updated_at,version FROM leads ORDER BY updated_at DESC").fetchall()
        result = [dict(json.loads(r[1]), id=r[0], created_at=r[2], updated_at=r[3], version=r[4]) for r in rows]
        return result if include_legacy else [r for r in result if not r.get("is_demo") and not saved_exclusion(r)]

    def save(self, lead: Lead, lead_id=None, version=None):
        self.init()
        key = ("demo:" if lead.is_demo else "real:") + (domain_key(lead.website) if lead.website else lead.name.casefold() + ":" + lead.city.casefold() + ":" + lead.country.casefold())
        payload = lead.model_dump_json()
        stamp = now()
        with self.connection() as conn:
            duplicate = self.sql(conn, "SELECT id FROM leads WHERE dedupe=?", (key,)).fetchone()
            if duplicate and duplicate[0] != lead_id:
                raise Conflict("Bu firma zaten kayıtlı. Mevcut kaydı düzenleyin.")
            if lead_id:
                cur = self.sql(conn, "UPDATE leads SET dedupe=?,payload=?,updated_at=?,version=version+1 WHERE id=? AND version=?", (key, payload, stamp, lead_id, version))
                if not cur.rowcount:
                    raise Conflict("Kayıt başka bir pencerede değişti veya silindi. Listeyi yenileyin.")
            else:
                lead_id = str(uuid.uuid4())
                result = self.sql(conn, "INSERT INTO leads(id,dedupe,payload,created_at,updated_at,version) VALUES (?,?,?,?,?,1) ON CONFLICT(dedupe) DO NOTHING", (lead_id, key, payload, stamp, stamp))
                if not result.rowcount:
                    raise Conflict("Bu firma zaten kayıtlı.")
        return next(x for x in self.list(include_legacy=True) if x["id"] == lead_id)

    def delete(self, lead_id, version):
        self.init()
        with self.connection() as conn:
            result = self.sql(conn, "DELETE FROM leads WHERE id=? AND version=?", (lead_id, version))
            if not result.rowcount:
                raise Conflict("Kayıt değişti veya silindi. Listeyi yenileyin.")

    def add_history(self, payload):
        self.init()
        with self.connection() as conn:
            self.sql(conn, "INSERT INTO history(id,payload,created_at) VALUES (?,?,?)", (str(uuid.uuid4()), json.dumps(payload, ensure_ascii=False), now()))
            self.sql(conn, "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY created_at DESC LIMIT 100)")

    def history(self):
        self.init()
        with self.connection() as conn:
            rows = self.sql(conn, "SELECT id,payload,created_at FROM history ORDER BY created_at DESC LIMIT 100").fetchall()
        return [dict(json.loads(r[1]), id=r[0], created_at=r[2]) for r in rows if json.loads(r[1]).get("provider") != "demo"]

    def restore(self, leads):
        self.init()
        added = 0
        with self.connection() as conn:
            for lead in leads:
                if lead.is_demo:
                    continue
                key = ("demo:" if lead.is_demo else "real:") + (domain_key(lead.website) if lead.website else lead.name.casefold() + ":" + lead.city.casefold() + ":" + lead.country.casefold())
                stamp = now()
                result = self.sql(conn, "INSERT INTO leads(id,dedupe,payload,created_at,updated_at,version) VALUES (?,?,?,?,?,1) ON CONFLICT(dedupe) DO NOTHING", (str(uuid.uuid4()), key, lead.model_dump_json(), stamp, stamp))
                added += result.rowcount
        return added, len(leads) - added

    def cached(self, key):
        import time
        self.init()
        with self.connection() as conn:
            self.sql(conn,"DELETE FROM search_cache WHERE expires < ?",(time.time(),))
            row = self.sql(conn,"SELECT payload FROM search_cache WHERE key=?",(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache(self, key, result):
        import time
        self.init()
        with self.connection() as conn:
            self.sql(conn,"INSERT INTO search_cache(key,payload,expires) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,expires=excluded.expires",(key,json.dumps(result,ensure_ascii=False),time.time()+900))
