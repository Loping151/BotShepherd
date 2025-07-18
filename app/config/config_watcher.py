# """
# 配置文件监控器
# 监控配置文件变化并自动重新加载
# """

# import asyncio
# import json
# import time
# from pathlib import Path
# from typing import Dict, Any, Callable, Optional
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# class ConfigFileHandler(FileSystemEventHandler):
#     """配置文件变化处理器"""
    
#     def __init__(self, callback: Callable[[str], None]):
#         self.callback = callback
#         self.last_modified = {}
        
#     def on_modified(self, event):
#         if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.json'):
#             # 防止重复触发
#             current_time = time.time()
#             if (event.src_path not in self.last_modified or
#                 current_time - self.last_modified[event.src_path] > 30.0):

#                 self.last_modified[event.src_path] = current_time
#                 self.callback(event.src_path)

# class ConfigWatcher:
#     """配置监控器"""
    
#     def __init__(self, config_manager):
#         self.config_manager = config_manager
#         self.observer = Observer()
#         self.handlers = {}
#         self.running = False
        
#     async def start(self):
#         """启动配置监控"""
#         if self.running:
#             return
        
#         self.running = True
        
#         # 监控全局配置文件
#         global_config_file = self.config_manager.config_dir / "global_config.json"
#         if global_config_file.exists():
#             handler = ConfigFileHandler(self._on_global_config_changed)
#             self.observer.schedule(handler, str(self.config_manager.config_dir), recursive=False)
#             self.handlers['global'] = handler
        
#         # 监控连接配置目录
#         if self.config_manager.connections_dir.exists():
#             handler = ConfigFileHandler(self._on_connection_config_changed)
#             self.observer.schedule(handler, str(self.config_manager.connections_dir), recursive=False)
#             self.handlers['connections'] = handler
        
#         # 监控账号配置目录
#         if self.config_manager.account_dir.exists():
#             handler = ConfigFileHandler(self._on_account_config_changed)
#             self.observer.schedule(handler, str(self.config_manager.account_dir), recursive=False)
#             self.handlers['accounts'] = handler
        
#         # 监控群组配置目录
#         if self.config_manager.group_dir.exists():
#             handler = ConfigFileHandler(self._on_group_config_changed)
#             self.observer.schedule(handler, str(self.config_manager.group_dir), recursive=False)
#             self.handlers['groups'] = handler
        
#         self.observer.start()
#         print("配置文件监控已启动")
    
#     async def stop(self):
#         """停止配置监控"""
#         if not self.running:
#             return
        
#         self.running = False
#         self.observer.stop()
#         self.observer.join()
#         self.handlers.clear()
#         print("配置文件监控已停止")
        
#     def run_async_safe(self, async_func):
#         async def wrapper():
#             try:
#                 await async_func()
#             except Exception as e:
#                 print(f"An error occurred in the async task: {e}")

#         try:
#             loop = asyncio.get_running_loop()
#         except RuntimeError:
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             try:
#                 loop.run_until_complete(wrapper())
#             finally:
#                 loop.close()
#                 asyncio.set_event_loop(None)
#             return

#         if loop.is_running():
#             loop.call_soon_threadsafe(asyncio.create_task, wrapper())
#         else:
#             loop.run_until_complete(wrapper())

#     def _on_global_config_changed(self, file_path: str):
#         print(f"检测到全局配置文件变化: {file_path}")
#         try:
#             self.run_async_safe(self.config_manager._load_global_config)
#         except Exception as e:
#             print(f"重新加载全局配置失败: {e}")
            
#     def _on_connection_config_changed(self, file_path: str):
#         print(f"检测到连接配置文件变化: {file_path}")
#         try:
#             self.run_async_safe(self.config_manager._load_connections_config)
#         except Exception as e:
#             print(f"重新加载连接配置失败: {e}")
            
#     def _on_account_config_changed(self, file_path: str):
#         print(f"检测到账号配置文件变化: {file_path}")
#         try:
#             self.run_async_safe(self.config_manager._load_account_configs)
#         except Exception as e:
#             print(f"重新加载账号配置失败: {e}")
            
#     def _on_group_config_changed(self, file_path: str):
#         print(f"检测到群组配置文件变化: {file_path}")
#         try:
#             self.run_async_safe(self.config_manager._load_group_configs)
#         except Exception as e:
#             print(f"重新加载群组配置失败: {e}")


# # class ConfigBackup:
# #     """配置备份管理器"""
    
# #     def __init__(self, config_dir: Path):
# #         self.config_dir = config_dir
# #         self.backup_dir = config_dir / "backups"
# #         self.backup_dir.mkdir(exist_ok=True)
    
# #     async def create_backup(self, backup_name: Optional[str] = None):
# #         """创建配置备份"""
# #         import shutil
# #         from datetime import datetime
        
# #         if backup_name is None:
# #             backup_name = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
        
# #         backup_path = self.backup_dir / backup_name
# #         backup_path.mkdir(exist_ok=True)
        
# #         # 备份全局配置
# #         global_config = self.config_dir / "global_config.json"
# #         if global_config.exists():
# #             shutil.copy2(global_config, backup_path / "global_config.json")
        
# #         # 备份连接配置
# #         connections_dir = self.config_dir / "connections"
# #         if connections_dir.exists():
# #             backup_connections = backup_path / "connections"
# #             shutil.copytree(connections_dir, backup_connections, dirs_exist_ok=True)
        
# #         # 备份账号配置
# #         account_dir = self.config_dir / "account"
# #         if account_dir.exists():
# #             backup_account = backup_path / "account"
# #             shutil.copytree(account_dir, backup_account, dirs_exist_ok=True)
        
# #         # 备份群组配置
# #         group_dir = self.config_dir / "group"
# #         if group_dir.exists():
# #             backup_group = backup_path / "group"
# #             shutil.copytree(group_dir, backup_group, dirs_exist_ok=True)
        
# #         print(f"配置备份已创建: {backup_path}")
# #         return backup_path
    
# #     async def restore_backup(self, backup_name: str):
# #         """恢复配置备份"""
# #         import shutil
        
# #         backup_path = self.backup_dir / backup_name
# #         if not backup_path.exists():
# #             raise FileNotFoundError(f"备份不存在: {backup_name}")
        
# #         # 恢复全局配置
# #         backup_global = backup_path / "global_config.json"
# #         if backup_global.exists():
# #             shutil.copy2(backup_global, self.config_dir / "global_config.json")
        
# #         # 恢复连接配置
# #         backup_connections = backup_path / "connections"
# #         if backup_connections.exists():
# #             connections_dir = self.config_dir / "connections"
# #             if connections_dir.exists():
# #                 shutil.rmtree(connections_dir)
# #             shutil.copytree(backup_connections, connections_dir)
        
# #         # 恢复账号配置
# #         backup_account = backup_path / "account"
# #         if backup_account.exists():
# #             account_dir = self.config_dir / "account"
# #             if account_dir.exists():
# #                 shutil.rmtree(account_dir)
# #             shutil.copytree(backup_account, account_dir)
        
# #         # 恢复群组配置
# #         backup_group = backup_path / "group"
# #         if backup_group.exists():
# #             group_dir = self.config_dir / "group"
# #             if group_dir.exists():
# #                 shutil.rmtree(group_dir)
# #             shutil.copytree(backup_group, group_dir)
        
# #         print(f"配置已从备份恢复: {backup_name}")
    
# #     def list_backups(self) -> list:
# #         """列出所有备份"""
# #         backups = []
# #         for backup_path in self.backup_dir.iterdir():
# #             if backup_path.is_dir():
# #                 backups.append({
# #                     "name": backup_path.name,
# #                     "path": str(backup_path),
# #                     "created_time": backup_path.stat().st_ctime
# #                 })
        
# #         # 按创建时间排序
# #         backups.sort(key=lambda x: x["created_time"], reverse=True)
# #         return backups
    
# #     async def cleanup_old_backups(self, keep_count: int = 10):
# #         """清理旧备份"""
# #         backups = self.list_backups()
        
# #         if len(backups) > keep_count:
# #             for backup in backups[keep_count:]:
# #                 backup_path = Path(backup["path"])
# #                 if backup_path.exists():
# #                     import shutil
# #                     shutil.rmtree(backup_path)
# #                     print(f"已删除旧备份: {backup['name']}")

# # class ConfigMigrator:
# #     """配置迁移器"""
    
# #     @staticmethod
# #     async def migrate_config(config_dir: Path, from_version: str, to_version: str):
# #         """迁移配置文件格式"""
# #         print(f"开始配置迁移: {from_version} -> {to_version}")
        
# #         # 创建备份
# #         backup = ConfigBackup(config_dir)
# #         await backup.create_backup(f"migration_backup_{from_version}_to_{to_version}")
        
# #         # 根据版本执行相应的迁移逻辑
# #         if from_version == "1.0.0" and to_version == "1.1.0":
# #             await ConfigMigrator._migrate_1_0_to_1_1(config_dir)
        
# #         print("配置迁移完成")
    
# #     @staticmethod
# #     async def _migrate_1_0_to_1_1(config_dir: Path):
# #         """从1.0.0迁移到1.1.0"""
# #         # 示例迁移逻辑
# #         global_config_file = config_dir / "global_config.json"
# #         if global_config_file.exists():
# #             with open(global_config_file, 'r', encoding='utf-8') as f:
# #                 config = json.load(f)
            
# #             # 添加新字段
# #             if "message_normalization" not in config:
# #                 config["message_normalization"] = {
# #                     "enabled": False,
# #                     "normalize_napcat_sent": True
# #                 }
            
# #             # 保存更新后的配置
# #             with open(global_config_file, 'w', encoding='utf-8') as f:
# #                 json.dump(config, f, indent=2, ensure_ascii=False)
