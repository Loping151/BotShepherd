"""
消息统计功能模块
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import json

from .database import DatabaseManager
from .onebot.event import MessageEvent, EventParser
from .onebot.message import MessageParser


class MessageStatistics:
    """消息统计类"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.daily_cache: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.keyword_cache: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    async def process_message_event(self, self_id: int, event: MessageEvent, 
                                   monitored_keywords: List[str]) -> bool:
        """处理消息事件，进行统计"""
        try:
            # 添加消息记录到数据库
            await self.db.add_message_record(self_id, event)
            
            # 检查关键词
            keywords_found = self.extract_keywords(event, monitored_keywords)
            if keywords_found:
                await self.db.add_keyword_records(self_id, event, keywords_found)
            
            # 更新缓存
            date_str = event.get_datetime().strftime('%Y-%m-%d')
            cache_key = f"{self_id}_{date_str}"
            
            # 更新消息计数缓存
            self.daily_cache[cache_key]["total"] += 1
            if event.is_group_message():
                self.daily_cache[cache_key][f"group_{event.group_id}"] += 1
            else:
                self.daily_cache[cache_key]["private"] += 1
            
            # 更新关键词缓存
            for keyword in keywords_found:
                keyword_key = f"{self_id}_{date_str}_{keyword}"
                self.keyword_cache[keyword_key]["count"] += 1
                if event.is_group_message():
                    self.keyword_cache[keyword_key][f"group_{event.group_id}"] += 1
            
            return True
            
        except Exception as e:
            print(f"Error processing message event for statistics: {e}")
            return False
    
    def extract_keywords(self, event: MessageEvent, monitored_keywords: List[str]) -> List[str]:
        """提取消息中的关键词"""
        text = event.get_plain_text().lower()
        found_keywords = []
        
        for keyword in monitored_keywords:
            if text.startswith(keyword.lower()):
                found_keywords.append(keyword)
        
        return found_keywords
    
    async def get_today_stats(self, self_id: int) -> Dict[str, Any]:
        """获取今日统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        return await self.get_daily_stats(self_id, today)
    
    async def get_yesterday_stats(self, self_id: int) -> Dict[str, Any]:
        """获取昨日统计"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return await self.get_daily_stats(self_id, yesterday)
    
    async def get_daily_stats(self, self_id: int, date_str: str) -> Dict[str, Any]:
        """获取指定日期的统计"""
        try:
            # 从数据库获取消息数量
            total_messages = await self.db.get_daily_message_count(self_id, date_str)
            group_messages = await self.db.get_daily_message_count(self_id, date_str, group_id=0)  # 需要修改查询逻辑
            private_messages = total_messages - group_messages  # 简化计算
            
            return {
                "date": date_str,
                "total_messages": total_messages,
                "group_messages": group_messages,
                "private_messages": private_messages,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting daily stats: {e}")
            return {
                "date": date_str,
                "total_messages": 0,
                "group_messages": 0,
                "private_messages": 0,
                "error": str(e)
            }
    
    async def get_keyword_stats(self, self_id: int, keyword: str, days: int = 7) -> Dict[str, Any]:
        """获取关键词统计"""
        try:
            stats = {}
            
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                count = await self.db.get_keyword_count(self_id, keyword, date_str)
                stats[date_str] = count
            
            total_count = sum(stats.values())
            
            return {
                "keyword": keyword,
                "days": days,
                "total_count": total_count,
                "daily_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting keyword stats: {e}")
            return {
                "keyword": keyword,
                "days": days,
                "total_count": 0,
                "daily_stats": {},
                "error": str(e)
            }
    
    async def search_keyword_usage(self, self_id: int, keyword: str, 
                                  days: int = 7, group_id: Optional[int] = None) -> Dict[str, Any]:
        """搜索关键词使用情况"""
        try:
            records = await self.db.search_keyword_records(self_id, keyword, days, group_id)
            
            # 按日期分组统计
            daily_counts = defaultdict(int)
            user_counts = defaultdict(int)
            group_counts = defaultdict(int)
            
            for record in records:
                daily_counts[record["date_str"]] += 1
                user_counts[record["user_id"]] += 1
                if record["group_id"]:
                    group_counts[record["group_id"]] += 1
            
            return {
                "keyword": keyword,
                "total_found": len(records),
                "days_searched": days,
                "daily_counts": dict(daily_counts),
                "top_users": dict(Counter(user_counts).most_common(10)),
                "top_groups": dict(Counter(group_counts).most_common(10)),
                "recent_records": records[:20],  # 最近20条记录
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error searching keyword usage: {e}")
            return {
                "keyword": keyword,
                "total_found": 0,
                "error": str(e)
            }
    
    async def get_weekly_summary(self, self_id: int) -> Dict[str, Any]:
        """获取周统计摘要"""
        try:
            summary = await self.db.get_statistics_summary(self_id, days=7)
            
            # 获取每日详细统计
            daily_details = {}
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                daily_stats = await self.get_daily_stats(self_id, date_str)
                daily_details[date_str] = daily_stats
            
            summary["daily_details"] = daily_details
            summary["timestamp"] = datetime.now().isoformat()
            
            return summary
            
        except Exception as e:
            print(f"Error getting weekly summary: {e}")
            return {
                "total_messages": 0,
                "total_keywords": 0,
                "active_groups": 0,
                "error": str(e)
            }
    
    async def get_group_ranking(self, self_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取群组活跃度排名"""
        try:
            # 这里需要实现群组排名逻辑
            # 暂时返回空列表，后续可以扩展
            return []
            
        except Exception as e:
            print(f"Error getting group ranking: {e}")
            return []
    
    async def get_user_ranking(self, self_id: int, days: int = 7, 
                              group_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取用户活跃度排名"""
        try:
            # 这里需要实现用户排名逻辑
            # 暂时返回空列表，后续可以扩展
            return []
            
        except Exception as e:
            print(f"Error getting user ranking: {e}")
            return []
    
    async def cleanup_old_cache(self):
        """清理旧的缓存数据"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            # 清理日统计缓存
            keys_to_remove = []
            for key in self.daily_cache.keys():
                if key.split('_')[-1] < cutoff_date:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.daily_cache[key]
            
            # 清理关键词缓存
            keys_to_remove = []
            for key in self.keyword_cache.keys():
                parts = key.split('_')
                if len(parts) >= 3 and parts[1] < cutoff_date:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.keyword_cache[key]
                
        except Exception as e:
            print(f"Error cleaning up cache: {e}")


class StatisticsReporter:
    """统计报告生成器"""
    
    def __init__(self, statistics: MessageStatistics):
        self.stats = statistics
    
    async def generate_daily_report(self, self_id: int, date_str: Optional[str] = None) -> str:
        """生成日报"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            daily_stats = await self.stats.get_daily_stats(self_id, date_str)
            
            report = f"📊 {date_str} 消息统计报告\n\n"
            report += f"📝 总消息数: {daily_stats['total_messages']}\n"
            report += f"👥 群聊消息: {daily_stats['group_messages']}\n"
            report += f"💬 私聊消息: {daily_stats['private_messages']}\n"
            
            return report
            
        except Exception as e:
            return f"❌ 生成日报失败: {str(e)}"
    
    async def generate_weekly_report(self, self_id: int) -> str:
        """生成周报"""
        try:
            weekly_summary = await self.stats.get_weekly_summary(self_id)
            
            report = f"📊 近7天消息统计报告\n\n"
            report += f"📝 总消息数: {weekly_summary['total_messages']}\n"
            report += f"🔍 关键词触发: {weekly_summary['total_keywords']}\n"
            report += f"👥 活跃群组: {weekly_summary['active_groups']}\n\n"
            
            report += "📈 每日详情:\n"
            daily_details = weekly_summary.get('daily_details', {})
            for date_str in sorted(daily_details.keys(), reverse=True):
                daily = daily_details[date_str]
                report += f"  {date_str}: {daily['total_messages']}条消息\n"
            
            return report
            
        except Exception as e:
            return f"❌ 生成周报失败: {str(e)}"
    
    async def generate_keyword_report(self, self_id: int, keyword: str, days: int = 7) -> str:
        """生成关键词报告"""
        try:
            keyword_stats = await self.stats.search_keyword_usage(self_id, keyword, days)
            
            report = f"🔍 关键词 '{keyword}' 统计报告\n\n"
            report += f"📊 近{days}天总计: {keyword_stats['total_found']}次\n\n"
            
            if keyword_stats['daily_counts']:
                report += "📈 每日统计:\n"
                for date_str in sorted(keyword_stats['daily_counts'].keys(), reverse=True):
                    count = keyword_stats['daily_counts'][date_str]
                    report += f"  {date_str}: {count}次\n"
            
            if keyword_stats['top_users']:
                report += "\n👤 使用用户TOP5:\n"
                for user_id, count in list(keyword_stats['top_users'].items())[:5]:
                    report += f"  {user_id}: {count}次\n"
            
            return report
            
        except Exception as e:
            return f"❌ 生成关键词报告失败: {str(e)}"
