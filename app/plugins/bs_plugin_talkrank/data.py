import json
import sqlite3
from dataclasses import dataclass, field

CATEGORY_ORDER = ["文", "图", "声", "视", "转", "其"]
CATEGORY_LABEL = {"文": "文字", "图": "图片", "声": "语音", "视": "视频", "转": "转发", "其": "其他"}


def classify(raw: str) -> str:
    if not raw:
        return "其"
    if "[CQ:" in raw:
        if "[CQ:forward" in raw:
            return "转"
        if "[CQ:record" in raw:
            return "声"
        if "[CQ:video" in raw:
            return "视"
        if "[CQ:image" in raw or "[CQ:mface" in raw:
            return "图"
        if ("[CQ:json" in raw or "[CQ:xml" in raw or "[CQ:dice" in raw
                or "[CQ:rps" in raw or "[CQ:file" in raw):
            return "其"
        return "文"  # 纯文本及 at/reply/face
    # 部分连接的 raw_message 是渲染后的纯文本占位符
    if "[聊天记录]" in raw or "[转发消息]" in raw:
        return "转"
    if "[语音]" in raw:
        return "声"
    if "[视频]" in raw:
        return "视"
    if "[图片]" in raw or "[动画表情]" in raw or "[商城表情]" in raw:
        return "图"
    if "[卡片]" in raw or "[文件]" in raw or "[JSON]" in raw:
        return "其"
    return "文"


def is_poke(raw: str) -> bool:
    """戳一戳超级表情以 message 形式出现时不计为发言"""
    return bool(raw) and (raw.startswith("[CQ:poke") or raw.strip() == "[戳一戳]")


@dataclass
class Speaker:
    user_id: str
    total: int = 0
    breakdown: dict = field(default_factory=dict)
    is_bot: bool = False
    name: str = ""

    def add(self, raw: str):
        self.total += 1
        cat = classify(raw or "")
        self.breakdown[cat] = self.breakdown.get(cat, 0) + 1

    def sub_text(self) -> str:
        items = sorted(self.breakdown.items(), key=lambda kv: (-kv[1], CATEGORY_ORDER.index(kv[0])))
        return " · ".join(f"{CATEGORY_LABEL[k]} {v}" for k, v in items)


def query_rank(db_path: str, group_id: str, start_ts: int, end_ts: int):
    """统计一个群在 [start_ts, end_ts) 内的发言榜。

    群友发言 = direction='RECV' 的 message 事件(戳一戳等 notice 不入库);
    bot 自身发言只有 direction='SEND' 的 message_sent 记录,
    与 RECV 无交集,各计一次不会重复。
    返回 (按发言数降序的 Speaker 列表, 总消息数)。
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=15)
    speakers: dict[str, Speaker] = {}
    fallback_info: dict[str, str] = {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, raw_message, sender_info FROM messages "
            "WHERE group_id=? AND direction='RECV' AND post_type='message' "
            "AND timestamp>=? AND timestamp<? "
            "GROUP BY COALESCE(NULLIF(message_id,''), id)",
            (group_id, start_ts, end_ts),
        )
        for uid, raw, sender_info in cur:
            if not uid or is_poke(raw or ""):
                continue
            speakers.setdefault(uid, Speaker(uid)).add(raw)
            if sender_info:
                fallback_info[uid] = sender_info

        cur.execute(
            "SELECT self_id, raw_message, sender_info FROM messages "
            "WHERE group_id=? AND direction='SEND' AND post_type='message_sent' "
            "AND timestamp>=? AND timestamp<? "
            "GROUP BY COALESCE(NULLIF(message_id,''), id)",
            (group_id, start_ts, end_ts),
        )
        for sid, raw, sender_info in cur:
            if not sid or is_poke(raw or ""):
                continue
            sp = speakers.setdefault(sid, Speaker(sid, is_bot=True))
            sp.is_bot = True
            sp.add(raw)
            if sender_info and sid not in fallback_info:
                fallback_info[sid] = sender_info
    finally:
        conn.close()

    for uid, info in fallback_info.items():
        try:
            d = json.loads(info)
            speakers[uid].name = d.get("card") or d.get("nickname") or ""
        except Exception:
            pass

    ranked = sorted(speakers.values(), key=lambda s: s.total, reverse=True)
    total_msgs = sum(s.total for s in ranked)
    return ranked, total_msgs
