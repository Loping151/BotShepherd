"""
帮助指令
显示系统帮助信息和指令列表
"""

from typing import Dict, Any, List
from ..onebotv11.models import Event
from .permission_manager import PermissionLevel
from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from datetime import datetime, timedelta
from datetime import timezone

class QueryCommand(BaseCommand):
    """帮助指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "统计"
        self.description = "基于数据库的消息统计与查询"
        self.usage = "统计"
        self.example = """
统计 -d 2025-07-21
统计 -k 草 -t all
统计 -c ww -t recv
统计 --all"""
        self.aliases = ["query", "q", "查询"]
        self.required_permission = PermissionLevel.ADMIN # 此处ADMIN只能查看本群数据
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        self.parser.add_argument("-d", "--date", type=str, help="指定日期，如 昨天, 2024-06-01，默认今天")
        self.parser.add_argument("-g", "--group", type=str, help="可跟群号，传入all时按群统计")
        self.parser.add_argument("-c", "--command", type=str, help="指定指令前缀")
        self.parser.add_argument("-k", "--keyword", type=str, help="指定关键词，+隔开为and查询，|隔开为or查询")
        self.parser.add_argument("-t", "--type", type=str, help="消息方向，send/recv/all，默认为send")
        self.parser.add_argument("--all", action="store_true", help="统计所有bot，仅不支持-g all")
        
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行帮助指令"""
        try:
            config_manager = context["config_manager"]
            database_manager = context["database_manager"]

            if not args and config_manager.is_superuser(event.user_id):
                return await self.basic_query(event, database_manager)

            try:
                parsed_args = self.parse_args(args)
            except Exception as e:
                return self.format_error(f"参数解析失败: {e}")

            if not parsed_args or isinstance(parsed_args, str) and config_manager.is_superuser(event.user_id):
                return await self.basic_query(event, database_manager)

            if parsed_args.date:
                if parsed_args.date in ["today", "今天", "今日"]:
                    date = datetime.now(timezone.utc)
                elif parsed_args.date in ["yesterday", "昨天", "昨日"]:
                    date = datetime.now(timezone.utc) - timedelta(days=1)
                else:
                    try:
                        date = datetime.strptime(parsed_args.date, "%Y-%m-%d")
                    except ValueError:
                        return self.format_error("日期格式错误，请使用 YYYY-MM-DD 格式")
                    date = date.replace(tzinfo=timezone.utc)
            else:
                date = datetime.now(timezone.utc)
              
            if not config_manager.is_superuser(event.user_id):
                if hasattr(event, "group_id"):
                    group = str(event.group_id)
                else:
                    return self.format_error("非主人，仅支持群管在群聊中查询")
            elif parsed_args.group:
                group = parsed_args.group
            else:
                group = None
            
            if parsed_args.command:
                command = parsed_args.command
            else:
                command = None
                
            if parsed_args.keyword:
                if parsed_args.command:
                    return self.format_error("不支持同时指定指令前缀和关键词")
                keyword = parsed_args.keyword
                if '+' in keyword:
                    if '|' in keyword:
                        return self.format_error("不支持同时使用+和|")
                    keywords = keyword.split('+')
                    keyword_type = "and"
                elif '|' in keyword:
                    keywords = keyword.split('|')
                    keyword_type = "or"
                else:
                    keywords = [keyword]
                    keyword_type = None
            else:
                keywords = None
                keyword_type = None
                
            if parsed_args.type:
                direction = parsed_args.type
                if direction in ["all", "ALL", "a", "A", "全部", "全"]:
                    direction = None
                elif direction in ["SEND", "send", "s", "S", "发", "发送"]:
                    direction = "SEND"
                elif direction in ["RECV", "receive", "recv", "r", "R", "收", "接收"]:
                    direction = "RECV"
                else:
                    return self.format_error("不支持的消息方向，请使用 send/recv/all")
            else:
                if keywords or command:
                    direction = "RECV"
                else:
                    direction = "SEND"
                
            if parsed_args.all:
                self_id = None
            else:
                self_id = str(event.self_id)
                
            return await self.query_by_args(event, date, group, command, keywords, keyword_type, self_id, direction, database_manager)

        except Exception as e:
            return self.format_error(f"获取统计信息失败: {e}")
        
    async def basic_query(self, event: Event, database_manager) -> CommandResponse:
        """基础统计信息"""
        try:
            result = f"🤖 当前账号：{event.self_id}\n🕒 当前时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\n📊 统计结果：\n"
            
            now_utc = datetime.now(timezone.utc)
            today_utc_zero = datetime.combine(now_utc, datetime.min.time(), tzinfo=timezone.utc)
            today_timestamp = int(today_utc_zero.timestamp())

            yesterday_timestamp = today_timestamp - 86400
            before_yesterday_timestamp = yesterday_timestamp - 86400
            
            # 今日消息数
            today_count = await database_manager.count_messages(self_id=str(event.self_id), start_time=today_timestamp, end_time=today_timestamp + 86400)
            result += f"📅 今日消息数: {today_count}\n"
            
            # 昨日消息数
            yesterday_count = await database_manager.count_messages(self_id=str(event.self_id), start_time=yesterday_timestamp, end_time=yesterday_timestamp + 86400)
            result += f"🕰️ 昨日消息数: {yesterday_count}\n"
            
            # 前日消息数
            before_yesterday_count = await database_manager.count_messages(self_id=str(event.self_id), start_time=before_yesterday_timestamp, end_time=before_yesterday_timestamp + 86400)
            result += f"📜 前日消息数: {before_yesterday_count}\n"
            
            return self.format_info(result)
        
        except Exception as e:
            return self.format_error(f"统计失败: {e}")
        

    async def query_by_args(self, event: Event, date: datetime, group: str, command: str, keywords: str, keyword_type: str, self_id: str, direction: str, database_manager) -> CommandResponse:
        """基础统计信息"""
        try:
            if not self_id and group == 'all':
                # 不允许统计账号数量 * 群组数量的结果
                group = None
                
            result = f"当前账号：{event.self_id}\n"
            result += f"📅 指定日期：{date.strftime('%Y-%m-%d')}\n"
            if group:
                result += f"👥 群组：{group}\n"
            if command:
                result += f"💬 指令：{command}\n"
            if keywords:
                result += f"🔑 关键词：{'|'.join(keywords) if keyword_type == 'or' else '+'.join(keywords)}\n"

            result += f"📨 消息方向：{direction if direction else "ALL"}\n"
            result += f"\n📊 统计结果：\n"

            date_utc_zero = datetime.combine(date, datetime.min.time(), tzinfo=timezone.utc)
            date_timestamp = int(date_utc_zero.timestamp())
            
            if not self_id:
                count_dict = await database_manager.count_messages_group_by_self_id(group_id=group, start_time=date_timestamp, end_time=date_timestamp + 86400, prefix=command, keywords=keywords, keyword_type=keyword_type, direction=direction)
                for bot_id, count in count_dict.items():
                    result += f"{bot_id}: {count}\n"
                return self.format_info(result)
            
            if group == 'all':
                count_dict = await database_manager.count_messages_group_by_group_id(self_id=self_id, start_time=date_timestamp, end_time=date_timestamp + 86400, prefix=command, keywords=keywords, keyword_type=keyword_type, direction=direction)
                for group_id, count in count_dict.items():
                    result += f"{group_id}: {count}\n"
                return self.format_info(result)
            
            count = await database_manager.count_messages(self_id=self_id, group_id=group, start_time=date_timestamp, end_time=date_timestamp + 86400, prefix=command, keywords=keywords, keyword_type=keyword_type, direction=direction)
            result += f"符合条件的消息数: {count}\n"
            count_yesterday = await database_manager.count_messages(self_id=self_id, group_id=group, start_time=date_timestamp - 86400, end_time=date_timestamp, prefix=command, keywords=keywords, keyword_type=keyword_type, direction=direction)
            result += f"前一日消息数: {count_yesterday}\n"
            if date_utc_zero + timedelta(days=2) < datetime.now(timezone.utc):
                count_tomorrow = await database_manager.count_messages(self_id=self_id, group_id=group, start_time=date_timestamp + 86400, end_time=date_timestamp + timedelta(days=2), prefix=command, keywords=keywords, keyword_type=keyword_type, direction=direction)
                result += f"后一日消息数: {count_tomorrow}\n"
            
            return self.format_info(result)
        
        except Exception as e:
            return self.format_error(f"统计失败: {e}")
        
# 注册指令
def register_query_commands():
    """注册基础指令"""
    command_registry.register(QueryCommand())
