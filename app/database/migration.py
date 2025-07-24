# """
# 数据库迁移管理器
# 处理数据库结构变更和数据迁移
# """

# import json
# import asyncio
# from pathlib import Path
# from typing import Dict, List, Any, Optional
# from datetime import datetime
# from sqlalchemy import text, inspect
# from sqlalchemy.ext.asyncio import AsyncEngine

# class DatabaseMigration:
#     """数据库迁移管理器"""
    
#     def __init__(self, engine: AsyncEngine, data_path: Path):
#         self.engine = engine
#         self.data_path = data_path
#         self.migrations_dir = data_path / "migrations"
#         self.migrations_dir.mkdir(exist_ok=True)
        
#         # 迁移版本记录文件
#         self.version_file = self.migrations_dir / "version.json"
        
#     async def get_current_version(self) -> str:
#         """获取当前数据库版本"""
#         if self.version_file.exists():
#             try:
#                 with open(self.version_file, 'r', encoding='utf-8') as f:
#                     version_info = json.load(f)
#                     return version_info.get("version", "0.0.0")
#             except Exception:
#                 pass
#         return "0.0.0"
    
#     async def set_current_version(self, version: str):
#         """设置当前数据库版本"""
#         version_info = {
#             "version": version,
#             "updated_at": datetime.now().isoformat(),
#             "migrations": []
#         }
        
#         if self.version_file.exists():
#             try:
#                 with open(self.version_file, 'r', encoding='utf-8') as f:
#                     existing_info = json.load(f)
#                     version_info["migrations"] = existing_info.get("migrations", [])
#             except Exception:
#                 pass
        
#         with open(self.version_file, 'w', encoding='utf-8') as f:
#             json.dump(version_info, f, indent=2, ensure_ascii=False)
    
#     async def add_migration_record(self, migration_name: str, version: str):
#         """添加迁移记录"""
#         migration_record = {
#             "name": migration_name,
#             "version": version,
#             "executed_at": datetime.now().isoformat()
#         }
        
#         version_info = {"version": version, "migrations": []}
#         if self.version_file.exists():
#             try:
#                 with open(self.version_file, 'r', encoding='utf-8') as f:
#                     version_info = json.load(f)
#             except Exception:
#                 pass
        
#         version_info["migrations"].append(migration_record)
#         version_info["version"] = version
#         version_info["updated_at"] = datetime.now().isoformat()
        
#         with open(self.version_file, 'w', encoding='utf-8') as f:
#             json.dump(version_info, f, indent=2, ensure_ascii=False)
    
#     async def check_table_exists(self, table_name: str) -> bool:
#         """检查表是否存在"""
#         async with self.engine.begin() as conn:
#             result = await conn.execute(text("""
#                 SELECT name FROM sqlite_master 
#                 WHERE type='table' AND name=:table_name
#             """), {"table_name": table_name})
#             return result.fetchone() is not None
    
#     async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
#         """获取表结构"""
#         async with self.engine.begin() as conn:
#             result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
#             columns = []
#             for row in result.fetchall():
#                 columns.append({
#                     "cid": row[0],
#                     "name": row[1],
#                     "type": row[2],
#                     "notnull": row[3],
#                     "dflt_value": row[4],
#                     "pk": row[5]
#                 })
#             return columns
    
#     async def migrate_to_version(self, target_version: str):
#         """迁移到指定版本"""
#         current_version = await self.get_current_version()
#         print(f"当前数据库版本: {current_version}")
#         print(f"目标版本: {target_version}")
        
#         if current_version == target_version:
#             print("数据库已是最新版本")
#             return
        
#         # 执行迁移
#         if current_version == "0.0.0" and target_version == "1.0.0":
#             await self._migrate_0_0_0_to_1_0_0()
#         elif current_version == "1.0.0" and target_version == "1.1.0":
#             await self._migrate_1_0_0_to_1_1_0()
#         else:
#             raise ValueError(f"不支持从版本 {current_version} 迁移到 {target_version}")
        
#         await self.set_current_version(target_version)
#         print(f"数据库迁移完成: {current_version} -> {target_version}")
    
#     async def _migrate_0_0_0_to_1_0_0(self):
#         """从0.0.0迁移到1.0.0（初始化数据库）"""
#         print("执行初始化数据库迁移...")
        
#         async with self.engine.begin() as conn:
#             # 创建消息表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS messages (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     message_id TEXT,
#                     self_id TEXT NOT NULL,
#                     user_id TEXT,
#                     group_id TEXT,
#                     message_type TEXT NOT NULL,
#                     sub_type TEXT,
#                     post_type TEXT,
#                     raw_message TEXT,
#                     message_content TEXT,
#                     sender_info TEXT,
#                     timestamp DATETIME NOT NULL,
#                     direction TEXT NOT NULL,
#                     connection_id TEXT,
#                     processed BOOLEAN DEFAULT FALSE,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             """))
            
#             # 创建用户表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS users (
#                     user_id TEXT PRIMARY KEY,
#                     nickname TEXT,
#                     card TEXT,
#                     role TEXT,
#                     first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
#                     last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
#                     message_count INTEGER DEFAULT 0
#                 )
#             """))
            
#             # 创建群组表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS groups (
#                     group_id TEXT PRIMARY KEY,
#                     group_name TEXT,
#                     first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
#                     last_message_time DATETIME,
#                     message_count INTEGER DEFAULT 0,
#                     member_count INTEGER DEFAULT 0
#                 )
#             """))
            
#             # 创建统计表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS statistics (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     date TEXT NOT NULL,
#                     self_id TEXT NOT NULL,
#                     group_id TEXT,
#                     message_count INTEGER DEFAULT 0,
#                     command_count INTEGER DEFAULT 0,
#                     user_count INTEGER DEFAULT 0,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#                     UNIQUE(date, self_id, group_id)
#                 )
#             """))
            
#             # 创建API调用记录表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS api_calls (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     self_id TEXT NOT NULL,
#                     action TEXT NOT NULL,
#                     params TEXT,
#                     result TEXT,
#                     success BOOLEAN,
#                     timestamp DATETIME NOT NULL,
#                     response_time REAL,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             """))
            
#             # 创建索引
#             indexes = [
#                 "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
#                 "CREATE INDEX IF NOT EXISTS idx_messages_self_id ON messages(self_id)",
#                 "CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)",
#                 "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)",
#                 "CREATE INDEX IF NOT EXISTS idx_statistics_date ON statistics(date)",
#                 "CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(timestamp)",
#                 "CREATE INDEX IF NOT EXISTS idx_api_calls_self_id ON api_calls(self_id)"
#             ]
            
#             for index_sql in indexes:
#                 await conn.execute(text(index_sql))
        
#         await self.add_migration_record("initial_database", "1.0.0")
    
#     async def _migrate_1_0_0_to_1_1_0(self):
#         """从1.0.0迁移到1.1.0（添加新表和字段）"""
#         print("执行1.0.0到1.1.0迁移...")
        
#         async with self.engine.begin() as conn:
#             # 添加连接日志表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS connection_logs (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     connection_id TEXT NOT NULL,
#                     event_type TEXT NOT NULL,
#                     client_ip TEXT,
#                     target_endpoint TEXT,
#                     message TEXT,
#                     timestamp DATETIME NOT NULL,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             """))
            
#             # 添加过滤日志表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS filter_logs (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     self_id TEXT NOT NULL,
#                     user_id TEXT,
#                     group_id TEXT,
#                     filter_type TEXT NOT NULL,
#                     filter_rule TEXT,
#                     original_message TEXT,
#                     filtered_message TEXT,
#                     action TEXT,
#                     timestamp DATETIME NOT NULL,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             """))
            
#             # 添加系统指标表
#             await conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS system_metrics (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     metric_name TEXT NOT NULL,
#                     metric_value REAL NOT NULL,
#                     metric_unit TEXT,
#                     tags TEXT,
#                     timestamp DATETIME NOT NULL,
#                     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
#                 )
#             """))
            
#             # 添加新索引
#             new_indexes = [
#                 "CREATE INDEX IF NOT EXISTS idx_connection_logs_connection_id ON connection_logs(connection_id)",
#                 "CREATE INDEX IF NOT EXISTS idx_connection_logs_timestamp ON connection_logs(timestamp)",
#                 "CREATE INDEX IF NOT EXISTS idx_filter_logs_self_id ON filter_logs(self_id)",
#                 "CREATE INDEX IF NOT EXISTS idx_filter_logs_timestamp ON filter_logs(timestamp)",
#                 "CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name)",
#                 "CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)"
#             ]
            
#             for index_sql in new_indexes:
#                 await conn.execute(text(index_sql))
        
#         await self.add_migration_record("add_logging_tables", "1.1.0")
    
#     async def backup_database(self, backup_name: Optional[str] = None) -> str:
#         """备份数据库"""
#         if backup_name is None:
#             backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
#         backup_dir = self.data_path / "backups"
#         backup_dir.mkdir(exist_ok=True)
        
#         backup_file = backup_dir / f"{backup_name}.db"
        
#         # 使用SQLite的备份API
#         import sqlite3
#         import aiosqlite
        
#         # 源数据库路径
#         source_db = self.data_path / "botshepherd.db"
        
#         if source_db.exists():
#             # 同步备份
#             source_conn = sqlite3.connect(str(source_db))
#             backup_conn = sqlite3.connect(str(backup_file))
            
#             source_conn.backup(backup_conn)
            
#             source_conn.close()
#             backup_conn.close()
            
#             print(f"数据库备份完成: {backup_file}")
#             return str(backup_file)
#         else:
#             raise FileNotFoundError("源数据库文件不存在")
    
#     async def restore_database(self, backup_file: str):
#         """恢复数据库"""
#         backup_path = Path(backup_file)
#         if not backup_path.exists():
#             raise FileNotFoundError(f"备份文件不存在: {backup_file}")
        
#         # 目标数据库路径
#         target_db = self.data_path / "botshepherd.db"
        
#         import sqlite3
        
#         # 恢复数据库
#         backup_conn = sqlite3.connect(str(backup_path))
#         target_conn = sqlite3.connect(str(target_db))
        
#         backup_conn.backup(target_conn)
        
#         backup_conn.close()
#         target_conn.close()
        
#         print(f"数据库恢复完成: {target_db}")
    
#     async def optimize_database(self):
#         """优化数据库"""
#         print("开始数据库优化...")
        
#         async with self.engine.begin() as conn:
#             # 分析表统计信息
#             await conn.execute(text("ANALYZE"))
            
#             # 重建索引
#             await conn.execute(text("REINDEX"))
            
#             # 清理空间
#             await conn.execute(text("VACUUM"))
        
#         print("数据库优化完成")
