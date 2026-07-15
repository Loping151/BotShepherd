"""发言榜出图,配色对齐 BS Web 后台(templates/base.html)"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 2x 超采样绘制,最终缩到 720 宽
W = 1440
PAD = 44
NAV_H = 148
RADIUS = 36

_FNT = Path(__file__).parent / "assets" / "MiSans-Regular.ttf"

C_BG = (241, 248, 233)        # --bs-light #f1f8e9
C_NAV_A = (102, 187, 106)     # --bs-primary #66bb6a
C_NAV_B = (85, 139, 47)       # #558b2f
C_DARKG = (51, 105, 30)       # --bs-dark #33691e
C_TEXT = (69, 90, 100)        # #455a64
C_GRAY = (120, 144, 156)      # #78909c
C_LGRAY = (144, 164, 174)     # #90a4ae
C_LINE = (232, 238, 227)
C_BAR_A = (220, 237, 200)     # #dcedc8, 同 web 激活项渐变
C_BAR_B = (241, 248, 233)     # #f1f8e9
RANK_C = {1: (255, 202, 40), 2: (144, 164, 174), 3: (141, 110, 99)}  # 金/银灰/棕(--bs-secondary)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FNT), size)


def _sanitize(name: str) -> str:
    out = []
    for ch in name:
        o = ord(ch)
        if o < 0x20 or o == 0xFE0F or o == 0x200B or o == 0x200D:
            continue
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF:
            continue
        out.append(ch)
    return "".join(out).strip()


def _truncate(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return text + "…"


def _fit_font(text: str, sizes: tuple, max_w: int):
    """字号从大到小选首个放得下的,最小号仍超宽则截断"""
    for size in sizes:
        f = _font(size)
        if f.getlength(text) <= max_w:
            return f, text
    f = _font(sizes[-1])
    return f, _truncate(text, f, max_w)


def _fit_parts(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    """按 " · " 分隔的片段从前往后装,放不下的整项丢弃不截断"""
    out = ""
    for p in text.split(" · "):
        cand = f"{out} · {p}" if out else p
        if font.getlength(cand) > max_w:
            break
        out = cand
    return out


def _hgrad(w: int, h: int, left: tuple, right: tuple) -> Image.Image:
    row = Image.new("RGBA", (w, 1))
    for x in range(w):
        t = x / (w - 1) if w > 1 else 0
        row.putpixel((x, 0), (
            round(left[0] + (right[0] - left[0]) * t),
            round(left[1] + (right[1] - left[1]) * t),
            round(left[2] + (right[2] - left[2]) * t),
            255,
        ))
    return row.resize((w, h))


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale) + 1, int(ih * scale) + 1
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _card(canvas: Image.Image, x: int, y: int, w: int, h: int, radius: int = 28):
    """白卡片 + 轻投影,同 web 的 card 样式"""
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x, y + 5, x + w, y + h + 5], radius, fill=(60, 90, 60, 34))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([x, y, x + w, y + h], radius, fill=(255, 255, 255, 255))
    canvas.alpha_composite(layer)


def _flatten_white(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, img).convert("RGB")
    return img.convert("RGB")


def _circle_avatar(data, size: int, ring: tuple | None = None, ring_w: int = 0) -> Image.Image:
    img = None
    if data:
        try:
            img = _flatten_white(Image.open(BytesIO(data)))
        except Exception:
            img = None
    if img is None:
        img = Image.new("RGB", (size, size), (207, 216, 220))
    img = _cover(img, size, size)

    ss = 4
    mask = Image.new("L", (size * ss, size * ss), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * ss - 1, size * ss - 1], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)

    out_size = size + ring_w * 2
    out = Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
    if ring and ring_w:
        rmask = Image.new("L", (out_size * ss, out_size * ss), 0)
        ImageDraw.Draw(rmask).ellipse([0, 0, out_size * ss - 1, out_size * ss - 1], fill=255)
        rmask = rmask.resize((out_size, out_size), Image.LANCZOS)
        ring_img = Image.new("RGBA", (out_size, out_size), ring + (255,))
        out.paste(ring_img, (0, 0), rmask)
    out.paste(img, (ring_w, ring_w), mask)
    return out


def _pill(canvas: Image.Image, draw: ImageDraw.ImageDraw, text: str, x: int, cy: int,
          font: ImageFont.FreeTypeFont, bg: tuple, fg: tuple):
    tw = font.getlength(text)
    h = font.size + 14
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([x, cy - h // 2, int(x + tw + 26), cy + h // 2], h // 2, fill=bg + (255,))
    canvas.alpha_composite(layer)
    draw.text((x + 13, cy), text, font=font, fill=fg, anchor="lm")
    return int(x + tw + 26)


def draw_rank_card(payload: dict) -> bytes:
    entries: list[dict] = payload["entries"]
    max_total = max((e["total"] for e in entries), default=1)

    f_badge = _font(38)
    f_title = _font(50)
    f_date = _font(42)
    f_stat = _font(32)
    f_rank = _font(36)
    f_rank_s = _font(28)
    f_sub = _font(27)
    f_count = _font(46)
    f_unit = _font(28)
    f_tag = _font(25)
    f_head = _font(29)
    f_foot = _font(27)

    # ---- 高度计算 ----
    y_info = NAV_H + 36
    info_h = 166
    y_list = y_info + info_h + 36
    head_h = 68
    row_h = 116
    list_h = 20 * 2 + head_h + row_h * len(entries)
    y_foot = y_list + list_h + 34
    H = y_foot + 40 + 38

    canvas = Image.new("RGBA", (W, H), C_BG + (255,))
    draw = ImageDraw.Draw(canvas)

    # ---- 导航条 ----
    canvas.paste(_hgrad(W, NAV_H, C_NAV_A, C_NAV_B), (0, 0))
    nav_cy = NAV_H // 2
    bh = f_badge.size + 22
    bw = int(f_badge.getlength("BS") + 34)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([PAD, nav_cy - bh // 2, PAD + bw, nav_cy + bh // 2], 14,
                                            fill=(255, 255, 255, 240))
    canvas.alpha_composite(layer)
    draw.text((PAD + bw // 2, nav_cy), "BS", font=f_badge, fill=C_NAV_B, anchor="mm", stroke_width=1,
              stroke_fill=C_NAV_B)
    draw.text((PAD + bw + 26, nav_cy), payload.get("header_text", "发言榜"), font=f_title,
              fill=(255, 255, 255), anchor="lm", stroke_width=1, stroke_fill=(255, 255, 255))
    draw.text((W - PAD, nav_cy), payload["date_str"], font=f_date, fill=(255, 255, 255, 235), anchor="rm")

    # ---- 概览卡片 ----
    _card(canvas, PAD, y_info, W - PAD * 2, info_h)
    f_gn, gname = _fit_font(_sanitize(payload["group_name"]) or payload["group_id"], (50, 44, 38), W - PAD * 2 - 80)
    draw.text((PAD + 40, y_info + 30 + (50 - f_gn.size) // 2), gname, font=f_gn, fill=C_DARKG, stroke_width=1,
              stroke_fill=C_DARKG)
    stat = ""
    if payload["group_name"] != payload["group_id"]:
        stat += f"群 {payload['group_id']} · "
    stat += f"共 {payload['total_speakers']} 人发言 · {payload['total_msgs']} 条消息" + payload.get("stat_extra", "")
    draw.text((PAD + 40, y_info + 108), stat, font=f_stat, fill=C_GRAY)

    # ---- 榜单卡片 ----
    _card(canvas, PAD, y_list, W - PAD * 2, list_h)
    x0 = PAD + 28
    x_right = W - PAD - 36
    rank_cx = x0 + 36
    av_size = 80
    av_x = x0 + 84
    name_x = av_x + av_size + 26

    hy = y_list + 20 + head_h // 2
    draw.text((rank_cx, hy), "排名", font=f_head, fill=C_LGRAY, anchor="mm")
    draw.text((name_x, hy), "成员", font=f_head, fill=C_LGRAY, anchor="lm")
    draw.text((x_right, hy), "发言数", font=f_head, fill=C_LGRAY, anchor="rm")
    draw.line([(x0, y_list + 20 + head_h - 2), (x_right, y_list + 20 + head_h - 2)], fill=C_LINE, width=2)

    ry = y_list + 20 + head_h
    for e in entries:
        cy = ry + row_h // 2
        rank = e["rank"]

        # 行背景 = 水平渐变条,长度按发言数占比(同 web 激活项配色)
        bar_x0 = x0 + 76
        bar_full = x_right - bar_x0
        bw_ = max(56, round(bar_full * e["total"] / max_total))
        grad = _hgrad(bw_, row_h - 16, C_BAR_A, C_BAR_B)
        gmask = Image.new("L", (bw_, row_h - 16), 0)
        ImageDraw.Draw(gmask).rounded_rectangle([0, 0, bw_ - 1, row_h - 17], 20, fill=255)
        canvas.paste(grad, (bar_x0, ry + 8), gmask)

        # 名次徽章
        rc = RANK_C.get(rank)
        r = 30
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([rank_cx - r, cy - r, rank_cx + r, cy + r],
                                      fill=(rc + (255,)) if rc else C_BG + (255,))
        canvas.alpha_composite(layer)
        f_r = f_rank if rank < 100 else f_rank_s
        draw.text((rank_cx, cy), str(rank), font=f_r,
                  fill=(255, 255, 255) if rc else C_NAV_B, anchor="mm")

        # 头像(前三名带奖牌色描边)
        av = _circle_avatar(e.get("avatar"), av_size, ring=rc, ring_w=5 if rc else 0)
        canvas.alpha_composite(av, (av_x - (5 if rc else 0), cy - av.height // 2))

        # 发言数(先画,名字宽度给它让位)
        cnt = str(e["total"])
        unit_w = f_unit.getlength(" 条")
        draw.text((x_right - unit_w, cy - 26), cnt, font=f_count, fill=C_DARKG, anchor="rm",
                  stroke_width=1, stroke_fill=C_DARKG)
        draw.text((x_right, cy - 20), " 条", font=f_unit, fill=C_GRAY, anchor="rm")

        # 名字 + BOT 标 + 分类明细
        name_max = x_right - name_x - int(f_count.getlength(cnt) + unit_w) - 36
        tag_w = int(f_tag.getlength("BOT") + 26 + 12) if e.get("is_bot") else 0
        f_nm, name = _fit_font(_sanitize(e["name"]) or e["user_id"], (38, 33, 29), name_max - tag_w)
        draw.text((name_x, cy - 26), name, font=f_nm, fill=C_TEXT, anchor="lm")
        if e.get("is_bot"):
            _pill(canvas, draw, "BOT", int(name_x + f_nm.getlength(name) + 12), cy - 26, f_tag,
                  C_NAV_A, (255, 255, 255))
        sub = _fit_parts(e["sub"], f_sub, name_max)
        if sub:
            draw.text((name_x, cy + 26), sub, font=f_sub, fill=C_LGRAY, anchor="lm")

        ry += row_h

    # ---- 页脚 ----
    foot = f"统计区间 {payload['window_str']} · 周期以每日 08:00 为界 · BotShepherd"
    draw.text((W / 2, y_foot), foot, font=f_foot, fill=C_LGRAY, anchor="ma")

    # ---- 圆角输出 ----
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], RADIUS, fill=255)
    canvas.putalpha(mask)
    canvas = canvas.resize((W // 2, H // 2), Image.LANCZOS)
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
