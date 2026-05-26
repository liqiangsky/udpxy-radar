import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "udpxy_radar.db")


def init_db():
    """
    初始化数据库
    """
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

        CREATE TABLE IF NOT EXISTS source_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sourceType TEXT NOT NULL,
            host TEXT NOT NULL,
            geoRegion TEXT DEFAULT '',
            geoOperator TEXT DEFAULT '',

            createdAt TEXT DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_source_cache_unique ON source_cache(sourceType, host);

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

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL
        );
    """)

    #
    # 删除旧错误索引
    #
    conn.execute("DROP INDEX IF EXISTS idx_unique_source")

    #
    # 正确唯一索引
    #
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_iptv_unique
        ON iptv_list(host, target, channelName)
    """)

    #
    # 常用查询索引
    #
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_region_operator
        ON iptv_list(region, operator)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_geo
        ON iptv_list(geoRegion, geoOperator)
    """)

    #
    # 初始化默认密码
    #
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

    #
    # 初始化默认配置
    #
    default_settings = {
        "github_enabled": "1",
        "github_token": "",
        "github_scan_cron": "",
        "ozone_enabled": "0",
        "ozone_fetch_cron": "",
        "ozone_scan_cron": "",
        "zoomeye_enabled": "0",
        "zoomeye_fetch_cron": "",
        "zoomeye_scan_cron": "",
        "daydaymap_enabled": "0",
        "daydaymap_fetch_cron": "",
        "daydaymap_scan_cron": "",
        "hunter_enabled": "0",
        "hunter_api_key": "",
        "hunter_fetch_cron": "",
        "hunter_scan_cron": "",
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
    """
    SQLite 连接管理
    """

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
