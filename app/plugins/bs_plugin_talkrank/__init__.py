"""BS 发言榜插件
统计 botshepherd.db 里某群的发言排行并出图,指令: bs发言榜 [日期] [刷新]
"""

import asyncio
import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

from app.commands.base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from app.commands.permission_manager import PermissionLevel
from app.onebotv11.message_segment import MessageSegmentBuilder
from app.onebotv11.models import Event

from .data import query_rank
from .draw import draw_rank_card
from .parse import parse_expr

CACHE_DIR = Path("./data/talkrank/cache")
LIVE_TTL = 600  # 进行中周期的缓存时效
TOP_N = 50


class RankEmpty(Exception):
    pass


def _fetch_avatar(uid: str):
    # qlogo.cn 本机直连黑洞,走 thirdqq
    try:
        resp = requests.get(f"https://thirdqq.qlogo.cn/g?b=qq&nk={uid}&s=140", timeout=6)
        if resp.status_code == 200:
            return uid, resp.content
    except Exception:
        pass
    return uid, None


async def fetch_avatars(uids: List[str]) -> Dict[str, bytes]:
    loop = asyncio.get_running_loop()
    results = await asyncio.gather(*(loop.run_in_executor(None, _fetch_avatar, u) for u in uids))
    return dict(results)


def _cache_valid(path: Path, window_end: datetime) -> bool:
    if not path.exists():
        return False
    mtime = path.stat().st_mtime
    if window_end <= datetime.now():
        return mtime >= window_end.timestamp()  # 周期结束后渲染的才算完整
    return time.time() - mtime < LIVE_TTL


class TalkRankCommand(BaseCommand):
    """发言榜指令"""

    def __init__(self):
        super().__init__()
        self.name = "发言榜"
        self.description = "统计本群发言排行并出图"
        self.usage = "发言榜 [今天|昨天|N天前|本周|上周|本月|上月|7月5日|20250705] [刷新]"
        self.example = "bs发言榜 昨天"
        self.aliases = ["水群榜", "talkrank"]
        self.required_permission = PermissionLevel.ADMIN
        self.group_only = True

    def _setup_parser(self):
        super()._setup_parser()

    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        force = "刷新" in args
        expr = " ".join(a for a in args if a != "刷新")
        window = parse_expr(expr, datetime.now())
        if not window:
            return self.format_error(f"不认识的日期: {expr}\n用法: {self.usage}")
        if window[0] >= datetime.now():
            return self.format_error("未来的发言榜画不出来")

        try:
            img = await self._render(str(event.group_id), window, context, force)
        except RankEmpty as e:
            return self.format_response(str(e))
        except Exception as e:
            context["logger"].command.error(f"发言榜生成失败: {e}")
            return self.format_error("发言榜生成失败,请稍后再试")

        image_seg = MessageSegmentBuilder.image(
            file="base64://" + base64.b64encode(img).decode("utf-8"))
        return self.format_response([image_seg])

    async def _render(self, gid: str, window: tuple, context: Dict[str, Any], force: bool) -> bytes:
        start, end, label, title = window
        now = datetime.now()
        cache_file = CACHE_DIR / f"{gid}_{start:%Y%m%d}_{end:%Y%m%d}.png"
        if not force and _cache_valid(cache_file, end):
            return cache_file.read_bytes()

        ongoing = end > now
        query_end = min(end, now)
        db_path = str(context["database_manager"].db_path)
        loop = asyncio.get_running_loop()
        ranked, total_msgs = await loop.run_in_executor(
            None, query_rank, db_path, gid, int(start.timestamp()), int(query_end.timestamp()))
        if not ranked:
            raise RankEmpty(f"{label} 这个统计区间内没有发言记录")

        # BS 拿不到真实群名,群配置里有非占位符的备注就用,否则直接群号
        group_name = gid
        try:
            group_config = await context["config_manager"].get_group_config(gid)
            desc = (group_config or {}).get("description") or ""
            if desc and desc != f"群组_{gid}":
                group_name = desc
        except Exception:
            pass

        top = ranked[:TOP_N]
        avatars = await fetch_avatars([s.user_id for s in top])

        payload = {
            "group_id": gid,
            "group_name": group_name,
            "header_text": title,
            "date_str": label,
            "window_str": f"{start:%m/%d %H:%M} — {end:%m/%d %H:%M}",
            "stat_extra": f" · 统计中 · 截至 {now:%H:%M}" if ongoing else "",
            "total_speakers": len(ranked),
            "total_msgs": total_msgs,
            "entries": [{
                "rank": i + 1,
                "user_id": s.user_id,
                "name": s.name,
                "total": s.total,
                "sub": s.sub_text(),
                "avatar": avatars.get(s.user_id),
                "is_bot": s.is_bot,
            } for i, s in enumerate(top)],
        }

        img = await loop.run_in_executor(None, draw_rank_card, payload)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cutoff = time.time() - 7 * 86400
        for old in CACHE_DIR.glob("*.png"):
            if old.stat().st_mtime < cutoff:
                old.unlink(missing_ok=True)
        cache_file.write_bytes(img)
        return img


command_registry.register(TalkRankCommand())
