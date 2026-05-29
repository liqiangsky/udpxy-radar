import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "udpxy_radar.db")
CACHE_DB_PATH = os.getenv("CACHE_DB_PATH", "source_cache.db")
IPTV_DB_PATH = os.getenv("IPTV_DB_PATH", "iptv_list.db")


def init_cache_db():
    """初始化源缓存数据库（source_cache 表）"""
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS source_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sourceType TEXT NOT NULL,
            host TEXT NOT NULL,
            geoRegion TEXT DEFAULT '',
            geoOperator TEXT DEFAULT '',
            createdAt TEXT DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_source_cache_unique ON source_cache(sourceType, host);
    """)
    conn.commit()
    conn.close()


def init_iptv_db():
    """初始化活源池数据库（iptv_list 表），自动从 source_cache.db 迁移历史数据"""
    conn = sqlite3.connect(IPTV_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS iptv_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            sourceType TEXT DEFAULT '',
            sourceName TEXT DEFAULT '',
            region TEXT NOT NULL,
            operator TEXT NOT NULL,
            geoRegion TEXT DEFAULT '',
            geoOperator TEXT DEFAULT '',
            delay INTEGER NOT NULL,
            protocol TEXT NOT NULL,
            target TEXT NOT NULL,
            channelName TEXT NOT NULL,
            createTime INTEGER NOT NULL,
            updateTime INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_iptv_unique ON iptv_list(host, target, channelName);
        CREATE INDEX IF NOT EXISTS idx_region_operator ON iptv_list(region, operator);
        CREATE INDEX IF NOT EXISTS idx_geo ON iptv_list(geoRegion, geoOperator);
    """)

    # 数据迁移：如果 iptv_list 在 source_cache.db 中存在但当前库为空，则迁移
    count = conn.execute("SELECT COUNT(*) FROM iptv_list").fetchone()[0]
    if count == 0:
        try:
            src = sqlite3.connect(CACHE_DB_PATH)
            src.row_factory = sqlite3.Row
            tables = src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='iptv_list'").fetchall()
            if tables:
                rows = src.execute("SELECT * FROM iptv_list").fetchall()
                if rows:
                    for row in rows:
                        conn.execute("""
                            INSERT OR IGNORE INTO iptv_list (
                                id, host, ip, port, sourceType, sourceName,
                                region, operator, geoRegion, geoOperator,
                                delay, protocol, target, channelName,
                                createTime, updateTime
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (row["id"], row["host"], row["ip"], row["port"],
                              row["sourceType"], row["sourceName"],
                              row["region"], row["operator"],
                              row["geoRegion"], row["geoOperator"],
                              row["delay"], row["protocol"], row["target"],
                              row["channelName"], row["createTime"], row["updateTime"]))
                    conn.commit()
                    logger = logging.getLogger("udpxy_radar")
                    logger.info(f"📦 [数据迁移] {len(rows)} 条活源数据已从 source_cache.db 迁移至 iptv_list.db")
            src.close()
        except Exception as e:
            logging.getLogger("udpxy_radar").warning(f"⚠️ [数据迁移] 迁移失败: {e}")

    conn.commit()
    conn.close()


def init_db():
    """初始化主数据库（settings + scan_config + templates + sessions）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 高并发优化
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            templateId INTEGER NOT NULL,
            dataSource TEXT NOT NULL,
            templateRegion TEXT DEFAULT '',
            templateOperator TEXT DEFAULT '',
            templateTargetName TEXT DEFAULT '',
            templateTargetAddress TEXT DEFAULT '',
            searchDepth INTEGER DEFAULT 30,
            enabled INTEGER DEFAULT 1,
            createdAt TEXT DEFAULT (datetime('now')),
            updatedAt TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS config_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            operator TEXT NOT NULL,
            targetName TEXT NOT NULL,
            targetAddress TEXT NOT NULL,
            createdAt TEXT DEFAULT (datetime('now')),
            updatedAt TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL
        );
    """)

    # 删除旧错误索引
    conn.execute("DROP INDEX IF EXISTS idx_unique_source")

    # 初始化默认密码
    row = conn.execute(
        "SELECT value FROM settings WHERE key='password_hash'"
    ).fetchone()

    if not row:
        import hashlib

        default_hash = hashlib.sha256(
            os.getenv("UDPXY_RADAR_PASSWORD", "admin").encode()
        ).hexdigest()

        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('password_hash', ?)",
            (default_hash,)
        )

    # 初始化默认配置
    default_settings = {
        "github_enabled": "1",
        "github_token": "",
        "ozone_enabled": "0",
        "ozone_fetch_cron": "",
        "zoomeye_enabled": "0",
        "zoomeye_fetch_cron": "",
        "daydaymap_enabled": "0",
        "daydaymap_fetch_cron": "",
        "hunter_enabled": "0",
        "hunter_api_key": "",
        "hunter_fetch_cron": "",
        "scan_cron": "",
        "concurrency": "64",
        "timeout": "2000",
        "config_delay": "3",
        "janitor_cron": ""
    }

    for k, v in default_settings.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (k, v)
        )

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """主数据库连接管理"""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@contextmanager
def get_cache_db():
    """缓存数据库连接管理（source_cache 表）"""
    conn = sqlite3.connect(
        CACHE_DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@contextmanager
def get_iptv_db():
    """活源池数据库连接管理（iptv_list 表）"""
    conn = sqlite3.connect(
        IPTV_DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_setting(key: str, default: str) -> str:
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?",
                (key,)
            ).fetchone()

            return row["value"] if row else default

    except Exception:
        return default
