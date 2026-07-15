import re
from datetime import datetime, timedelta

# 日期表达式最长字符数,超过直接不认
MAX_EXPR_LEN = 15

_REL_DAY = {
    "": 0, "今日": 0, "今天": 0,
    "昨日": 1, "昨天": 1,
    "前天": 2, "前日": 2,
    "大前天": 3,
}
_RE_DAYS_AGO = re.compile(r"(\d{1,3})天前")
_RE_MONTH = re.compile(r"(?:(\d{4})年)?(\d{1,2})月")
_RE_DATE = re.compile(r"(?:(\d{4})[年.\-/])?(\d{1,2})[月.\-/](\d{1,2})[日号]?")
_RE_DATE8 = re.compile(r"(\d{8})")


def cycle_day(now: datetime) -> datetime:
    """当前周期的起点: 以每天 08:00 为界"""
    base = now - timedelta(hours=8)
    return datetime(base.year, base.month, base.day, 8)


def _next_month(d: datetime) -> datetime:
    return d.replace(year=d.year + 1, month=1) if d.month == 12 else d.replace(month=d.month + 1)


def parse_expr(expr: str, now: datetime):
    """解析日期表达式,返回 (start, end, label, title) 或 None(不认识)。

    end 为名义终点,可能在未来(进行中的周期),由调用方截断到 now。
    """
    e = expr.strip().strip("的").strip()
    if len(e) > MAX_EXPR_LEN:
        return None
    day0 = cycle_day(now)

    if e in _REL_DAY:
        shift = _REL_DAY[e]
        s = day0 - timedelta(days=shift)
        title = {0: "今日发言榜", 1: "昨日发言榜", 2: "前天发言榜", 3: "大前天发言榜"}[shift]
        return s, s + timedelta(days=1), s.strftime("%m/%d"), title
    m = _RE_DAYS_AGO.fullmatch(e)
    if m:
        s = day0 - timedelta(days=int(m.group(1)))
        return s, s + timedelta(days=1), s.strftime("%m/%d"), "发言榜"

    if e in ("本周", "这周", "这一周"):
        s = day0 - timedelta(days=day0.weekday())
        return s, s + timedelta(days=7), "本周", "本周发言榜"
    if e in ("上周", "上一周"):
        s = day0 - timedelta(days=day0.weekday() + 7)
        return s, s + timedelta(days=7), "上周", "上周发言榜"
    if e in ("本月", "这个月", "当月"):
        s = day0.replace(day=1)
        return s, _next_month(s), f"{s.month}月", "本月发言榜"
    if e in ("上月", "上个月"):
        first = day0.replace(day=1)
        s = (first - timedelta(days=1)).replace(day=1, hour=8)
        return s, first, f"{s.month}月", "上月发言榜"

    m = _RE_MONTH.fullmatch(e)
    if m:
        year = int(m.group(1)) if m.group(1) else now.year
        month = int(m.group(2))
        if not 1 <= month <= 12:
            return None
        s = datetime(year, month, 1, 8)
        if not m.group(1) and s > now:
            s = s.replace(year=year - 1)
        label = f"{s.year}年{s.month}月" if s.year != now.year else f"{s.month}月"
        return s, _next_month(s), label, f"{label}发言榜"

    m = _RE_DATE.fullmatch(e) or _RE_DATE8.fullmatch(e)
    if m:
        try:
            if m.re is _RE_DATE8:
                raw = m.group(1)
                s = datetime(int(raw[:4]), int(raw[4:6]), int(raw[6:8]), 8)
            else:
                year = int(m.group(1)) if m.group(1) else now.year
                s = datetime(year, int(m.group(2)), int(m.group(3)), 8)
                if not m.group(1) and s > now:
                    s = s.replace(year=year - 1)
        except ValueError:
            return None
        return s, s + timedelta(days=1), s.strftime("%m/%d"), "发言榜"

    return None
