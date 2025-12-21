"""
配置备份管理器
定期备份config文件夹，支持加密和自动清理
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import pyzipper as zipfile
import zipfile as std_zipfile

logger = logging.getLogger(__name__)


class BackupManager:
    """配置备份管理器"""

    def __init__(self, config_dir: str = "./config", backup_dir: str = "./config/backup"):
        base_dir = Path(__file__).resolve().parents[2]
        config_path = Path(config_dir)
        backup_path = Path(backup_dir)
        self.config_dir = config_path if config_path.is_absolute() else (base_dir / config_path)
        self.backup_dir = backup_path if backup_path.is_absolute() else (base_dir / backup_path)

        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _create_backup_with_name(self, password: str, backup_filename: str, inner_arcname: str) -> Optional[str]:
        if not password:
            logger.error("必须提供密码进行备份加密")
            return None

        inner_tmp_path = None
        try:
            backup_path = self.backup_dir / backup_filename
            inner_tmp_path = backup_path.with_suffix(".tmp")

            # 收集所有要备份的文件
            files_to_backup = []
            for root, dirs, files in os.walk(self.config_dir):
                # 跳过backup文件夹本身
                if "backup" in Path(root).parts:
                    continue

                for file in files:
                    if file.endswith('.json'):
                        file_path = Path(root) / file
                        # 计算相对于config_dir的路径
                        rel_path = file_path.relative_to(self.config_dir)
                        files_to_backup.append((str(file_path), str(rel_path)))

            if not files_to_backup:
                logger.warning("没有找到需要备份的配置文件")
                return None

            # 创建内层普通zip文件
            with std_zipfile.ZipFile(str(inner_tmp_path), 'w', compression=std_zipfile.ZIP_DEFLATED) as zipf:
                for src, dest in files_to_backup:
                    zipf.write(src, dest)

            # 外层使用加密zip，未提供密码无法查看内容列表
            with zipfile.AESZipFile(str(backup_path), 'w', compression=zipfile.ZIP_DEFLATED,
                                    encryption=zipfile.WZ_AES) as outer_zip:
                outer_zip.setpassword(password.encode('utf-8'))
                outer_zip.write(str(inner_tmp_path), arcname=inner_arcname)

            inner_tmp_path.unlink(missing_ok=True)
            logger.info(f"成功创建加密备份: {backup_filename}")
            return str(backup_path)

        except Exception as e:
            if inner_tmp_path:
                try:
                    inner_tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
            logger.error(f"创建备份失败: {e}", exc_info=True)
            return None

    def create_backup(self, password: str) -> Optional[str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config_backup_{timestamp}.zip"
        inner_arcname = backup_filename
        return self._create_backup_with_name(password, backup_filename, inner_arcname)

    def create_startup_backup(self, password: str) -> Optional[str]:
        """创建启动备份（固定文件名，每次启动覆盖）"""
        backup_filename = "config_backup_startup.zip"
        inner_arcname = backup_filename
        return self._create_backup_with_name(password, backup_filename, inner_arcname)

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []

        try:
            for file in self.backup_dir.glob("config_backup_*.zip"):
                stat = file.stat()
                backups.append({
                    "filename": file.name,
                    "filepath": str(file),
                    "size": stat.st_size,
                    "created_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            # 按创建时间倒序排序
            backups.sort(key=lambda x: x["created_time"], reverse=True)

        except Exception as e:
            logger.error(f"列出备份文件失败: {e}")

        return backups

    def clean_old_backups(self, keep_days: int):
        try:
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0

            for file in self.backup_dir.glob("config_backup_*.zip"):
                file_mtime = datetime.fromtimestamp(file.stat().st_mtime)

                if file_mtime < cutoff_time:
                    file.unlink()
                    deleted_count += 1
                    logger.info(f"删除过期备份: {file.name}")

            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个过期备份")

        except Exception as e:
            logger.error(f"清理备份失败: {e}")

    def get_backup_path(self, filename: str) -> Optional[str]:
        backup_path = self.backup_dir / filename

        if backup_path.exists() and backup_path.is_file():
            return str(backup_path)

        return None
