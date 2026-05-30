import os
import time
import logging
from db.database import DB_PATH, CACHE_DB_PATH, IPTV_DB_PATH
from pathlib import Path

logger = logging.getLogger("udpxy_radar")
HF_DATASET_ID = os.getenv("HF_DATASET_ID", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

DB_FILENAME = os.path.basename(DB_PATH)
CACHE_FILENAME = os.path.basename(CACHE_DB_PATH)
IPTV_FILENAME = os.path.basename(IPTV_DB_PATH)
DB_DIR = str(Path(DB_PATH).parent)

_last_push_time = 0.0
_last_cache_push_time = 0.0
_last_iptv_push_time = 0.0

def _sync_file(path: str, filename: str, last_time_key: str):
    global _last_push_time, _last_cache_push_time, _last_iptv_push_time

    if not HF_DATASET_ID or not HF_TOKEN:
        return

    try:
        mtime = os.path.getmtime(path)
        if last_time_key == 'db':
            current_last = _last_push_time
        elif last_time_key == 'cache':
            current_last = _last_cache_push_time
        else:
            current_last = _last_iptv_push_time
        if mtime <= current_last:
            return
        if last_time_key == 'db':
            _last_push_time = mtime
        elif last_time_key == 'cache':
            _last_cache_push_time = mtime
        else:
            _last_iptv_push_time = mtime
    except OSError:
        return

    try:
        from huggingface_hub import HfApi
        HfApi().upload_file(path_or_fileobj=path, path_in_repo=filename, repo_id=HF_DATASET_ID, repo_type="dataset", token=HF_TOKEN)
        logger.info(f"📊 {filename} 已同步至云端 Dataset")
    except Exception as e:
        logger.warning(f"🚨 同步远程备份失败 ({filename}): {e}")

def push_to_hf():
    _sync_file(DB_PATH, DB_FILENAME, 'db')
    _sync_file(CACHE_DB_PATH, CACHE_FILENAME, 'cache')
    _sync_file(IPTV_DB_PATH, IPTV_FILENAME, 'iptv')

def pull_from_hf():
    if not HF_DATASET_ID or not HF_TOKEN:
        return False
    ok = True
    try:
        from huggingface_hub import hf_hub_download
        import shutil

        # 拉取主库
        local_path = hf_hub_download(
            repo_id=HF_DATASET_ID,
            filename=DB_FILENAME,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir=DB_DIR
        )
        target = DB_PATH
        if local_path != target:
            shutil.move(local_path, target)
        logger.info(f"📥 成功从云端恢复历史健康主数据库 ({DB_PATH})")
    except Exception as e:
        logger.warning(f"📥 从云端恢复主数据库失败: {e}")
        ok = False

    try:
        from huggingface_hub import hf_hub_download
        import shutil

        local_path = hf_hub_download(
            repo_id=HF_DATASET_ID,
            filename=CACHE_FILENAME,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir=DB_DIR
        )
        target = CACHE_DB_PATH
        if local_path != target:
            shutil.move(local_path, target)
        logger.info(f"📥 成功从云端恢复缓存数据库 ({CACHE_DB_PATH})")
    except Exception as e:
        logger.warning(f"📥 从云端恢复缓存数据库失败: {e}")
        # 缓存库不存在不视为失败
        ok = ok or True

    try:
        from huggingface_hub import hf_hub_download
        import shutil

        local_path = hf_hub_download(
            repo_id=HF_DATASET_ID,
            filename=IPTV_FILENAME,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir=DB_DIR
        )
        target = IPTV_DB_PATH
        if local_path != target:
            shutil.move(local_path, target)
        logger.info(f"📥 成功从云端恢复活源池数据库 ({IPTV_DB_PATH})")
    except Exception as e:
        logger.warning(f"📥 从云端恢复活源池数据库失败: {e}")
        # iptv 库不存在不视为失败
        ok = ok or True

    return ok
