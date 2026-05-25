import os
import time
import logging
from db.database import DB_PATH
from pathlib import Path

logger = logging.getLogger("CastScout_V3")
HF_DATASET_ID = os.getenv("HF_DATASET_ID", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

DB_FILENAME = os.path.basename(DB_PATH)
DB_DIR = str(Path(DB_PATH).parent)

_last_push_time = 0.0

def push_to_hf():
    global _last_push_time

    if not HF_DATASET_ID or not HF_TOKEN:
        return

    try:
        mtime = os.path.getmtime(DB_PATH)
        if mtime <= _last_push_time:
            return
        _last_push_time = mtime
    except OSError:
        return

    try:
        from huggingface_hub import HfApi
        HfApi().upload_file(path_or_fileobj=DB_PATH, path_in_repo=DB_FILENAME, repo_id=HF_DATASET_ID, repo_type="dataset", token=HF_TOKEN)
        logger.info(f"📊 活源库已成功同步至云端 Dataset")
    except Exception as e:
        logger.warning(f"🚨 同步远程备份失败: {e}")

def pull_from_hf():
    if not HF_DATASET_ID or not HF_TOKEN: return False
    try:
        from huggingface_hub import hf_hub_download
        # 下载到数据库文件所在目录
        local_path = hf_hub_download(
            repo_id=HF_DATASET_ID,
            filename=DB_FILENAME,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir=DB_DIR
        )
        # hf_hub_download 下载到 {local_dir}/{DB_FILENAME}
        # 确保文件在正确的位置
        target = DB_PATH
        if local_path != target:
            import shutil
            shutil.move(local_path, target)
        logger.info(f"📥 成功从云端恢复历史健康数据库 ({DB_PATH})")
        return True
    except Exception as e:
        logger.warning(f"📥 从云端恢复数据库失败: {e}")
        return False
