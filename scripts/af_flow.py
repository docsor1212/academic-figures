# -*- coding: utf-8 -*-
"""af_flow — 流程图布局/路由引擎（v8.0.0，第 42 号图型 flow + diagram 共用）。

设计来源（2026-11 SOTA 研究，全部 🟡 技术文档层验证）：
- ELK Layered 语义：回边由 cycle-breaking 归为「绕行通道」（图上方/下方 lane，
  多回边错层），边标签参与布局（dummy-node 思想→本引擎=标签包围盒参与碰撞检测）。
- TALA（2026-09 开源，D2 v0.9.0）：正交路由=白板级观感的 SOTA——本引擎采纳
  「磁吸框边 + 逐段折线 + 专用 lane」三件套，禁用 arc3/rad 手调（fig2 v3 失败根因）。
- adjustText / d3-labeler：measure-then-resolve 范式——先 get_window_extent 测量
  再画（所有溢出类问题在测量步消灭）。
- 期刊规格：Nature 89/183mm、sans-serif、600dpi 线稿（引擎 journal 预设沿用）。

铁律（与 FLOW_SKILL_DEV_SPEC 对齐）：
1. 箭头永不进入任何节点内部（磁吸框边+逐段吸附）。
2. 回边/跨位边走专用 lane（上/下，多回边错层），虚线样式必须生效。
3. 边标签包围盒与一切节点/其他标签零交集；放不下→引线。
4. 文本测量先行：fit_block_text 缩放+换行，低于字号下限→ValueError（exit 3）而非溢出。
5. 画布自裁剪：内容包围盒+统一边距重设 xlim/ylim。
6. strict 闸：三层 bbox 断言（节点×边标签×箭头线段）任一非零交集→报违规清单。
"""
import math
import re
import sys

# ── 常量 ────────────────────────────────────────────────────────────────
LANE_GAP = 0.55          # 回边 lane 与节点外缘的最小间距（数据单位）
LANE_STAGGER = 0.5       # 多条回边错层步距
MAGNET_PAD = 0.03        # 箭头端点与框边的微距
EDGE_NIB = 0.10          # 终点向目标框内咬合量（尖端视觉落在框缘线上：
                         #  悬在圆角白描边外=9px 空隙+mutation 半透明尾三角 ghost 的根因）
LABEL_PAD = 0.12         # 标签与任意元素的强制间隙
FONT_FLOOR = 8.0         # 文本缩放下限（pt）——低于即报错不溢出
EDGE_STAGGER = 0.16      # 同一条目标框边上多箭头的错位步距


def _bbox(b):
    """块 dict → (x0, y0, x1, y1)。"""
    return (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])


def _overlap(a, b, pad=0.0):
    """两 (x0,y0,x1,y1) 是否相交（含 pad 膨胀）。"""
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0]
                or a[3] + pad <= b[1] or b[3] + pad <= a[1])


# ── R3 文本测量与自适应 ────────────────────────────────────────────────
def measure(ax, s, fontsize, fp=None, weight="normal", ls=1.15):
    """测量字符串在当前坐标系下的 (w, h)（数据单位；测量先行铁律）。
    ls 与绘制时 linespacing 一致，多行文本测高才准。"""
    fig = ax.figure
    t = ax.text(0, 0, s, fontsize=fontsize, fontproperties=fp,
                fontweight=weight, alpha=0, linespacing=ls)
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    t.remove()
    inv = ax.transData.inverted()
    (x0, y0) = inv.transform((bb.x0, bb.y0))
    (x1, y1) = inv.transform((bb.x1, bb.y1))
    return abs(x1 - x0), abs(y1 - y0)


def _line_metrics(ax, fs, fp):
    """返回 (cap, adv)：单行可见高与行进距（数据单位）。n 行块高=(n-1)*adv+cap。"""
    cap = measure(ax, "X", fs, fp)[1]
    adv = measure(ax, "X\nX", fs, fp)[1] - cap
    return cap, adv


def _wrap_cjk(s, max_chars):
    """按显示宽度断行（规格 R3 的 CJK 2:1 加权）。词元化：ASCII 连续段=不可拆词、
    CJK 单字=可断词元；**数字+紧随 CJK 单位粘成单 token**（「48周」「12.5mg每日」
    不得把数字与单位拆到两行）；单 ASCII 词超宽才硬拆（缩字号由外层兜底）。"""
    s = str(s)
    toks, cur, cur_lat = [], "", False
    _prev_digit = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == " ":
            if cur:
                toks.append((cur, cur_lat))
                cur, cur_lat = "", False
            _prev_digit = False
            i += 1
            continue
        is_lat = ord(ch) <= 0x2E80
        if cur and _prev_digit and not is_lat:
            cur += ch          # 数字+单位粘合（48周 / 12.5mg 的「周」不得另起行）
            cur_lat = False
            _prev_digit = False
        elif is_lat == cur_lat or not cur:
            cur += ch
            cur_lat = is_lat
        else:
            toks.append((cur, cur_lat))
            cur, cur_lat = ch, is_lat
        _prev_digit = ch.isdigit()
        i += 1
    if cur:
        toks.append((cur, cur_lat))
    tw = [(t, sum(2 if ord(c) > 0x2E80 else 1 for c in t)) for t, _lat in toks]
    out, cur, w = [], "", 0
    for _ti, (t, cw) in enumerate(tw):
        # 数字词元 + 紧随 CJK 词元：CJK 侧去空格粘合（「48 周主要终点」→「48周主要终点」
        # 整体宽度判定，避免数字孤立成行——CJK 排版数字与单位间不靠空格）
        if (_ti + 1 < len(tw) and t.replace(".", "").isdigit()
                and tw[_ti + 1][0][0] and ord(tw[_ti + 1][0][0]) > 0x2E80):
            t = t + tw[_ti + 1][0]
            cw = tw[_ti + 1][1] + cw
            tw[_ti + 1] = ("", 0)
        if not t:
            continue
        if w and w + 1 + cw > max_chars:
            out.append(cur.rstrip())
            cur, w = "", 0
        if cw > max_chars and sum(2 if ord(c) > 0x2E80 else 1 for c in t) > max_chars and \
                all(ord(c) <= 0x2E80 for c in t):
            frag = t
            while sum(2 if ord(c) > 0x2E80 else 1 for c in frag) > max_chars:
                cut = max(1, max_chars - w) if w else max(1, max_chars)
                out.append((cur + frag[:cut]).strip())
                frag = frag[cut:]
                cur, w = "", 0
            cur, w = frag, sum(2 if ord(c) > 0x2E80 else 1 for c in frag)
        else:
            if cur:
                cur += " " + t
                w += 1 + cw
            else:
                cur, w = t, cw
    if cur.strip():
        out.append(cur.rstrip())
    return out or [s]


def fit_block_text(ax, b, fs_main, fs_sub, fp_label=None, fp_sub=None):
    """R3：框内文本测量驱动自适应——换行+缩放（CJK 2:1），低于字号下限报错。
    返回 (label_lines, sub_lines, fs_main, fs_sub)。超限抛 ValueError（exit 3）。"""
    avail_w = b["w"] - 0.24   # 内边距 0.12×2
    avail_h = b["h"] - 0.16
    label = b.get("label", b.get("id", ""))
    sub = b.get("sublabel", None)

    def _fit_one(s, fs, fp, weight, floor):
        """返回 (lines, fs)；先换行后缩放；都放不下→None。"""
        f = fs
        while f >= floor:
            w, _h = measure(ax, s if "\n" not in s else s.split("\n")[0], f, fp, weight)
            max_chars = max(4, int(avail_w / max(w / max(len(s.split("\n")[0]), 1), 1e-6)))
            lines = _wrap_cjk(s, max_chars)
            _lw = max((measure(ax, ln, f, fp, weight)[0] for ln in lines), default=0)
            _lh = measure(ax, "\n".join(lines), f, fp, weight)[1]   # 实测整串高
            if _lw <= avail_w and _lh <= avail_h:
                return lines, f
            f -= 0.5
        return None, floor

    lab_fit, fs_main = _fit_one(label, fs_main, fp_label, "bold", FONT_FLOOR)
    if lab_fit is None:
        raise ValueError(
            f"flow: 节点「{b.get('id')}」label 在字号下限 {FONT_FLOOR:g}pt 下仍超出框宽"
            f"（{b['w']:g}×{b['h']:g}）——请加宽框体/精简文案（拒绝溢出渲染）")
    sub_fit, fs_sub = (None, fs_sub)
    if sub:
        sub_fit, fs_sub = _fit_one(sub, fs_sub, fp_sub, "normal", FONT_FLOOR - 0.5)
        if sub_fit is None:
            raise ValueError(
                f"flow: 节点「{b.get('id')}」sublabel 低于字号下限仍超出框——请精简文案")
    # 联合总高适配：label 行+sub 行+间隙 ≤ 可用高（原各自独立判→两行 sub 上探入主标签）
    if sub_fit:
        while fs_main > FONT_FLOOR or fs_sub > FONT_FLOOR - 0.5:
            total = (measure(ax, "\n".join(lab_fit), fs_main, fp_label)[1]
                     + measure(ax, "\n".join(sub_fit), fs_sub, fp_sub)[1]) + 0.07
            if total <= avail_h:
                break
            fs_main = max(FONT_FLOOR, fs_main - 0.5)
            fs_sub = max(FONT_FLOOR - 0.5, fs_sub - 0.5)
            if fs_main <= FONT_FLOOR and fs_sub <= FONT_FLOOR - 0.5 and total > avail_h:
                raise ValueError(
                    f"flow: 节点「{b.get('id')}」主副文本联合高度超框——请精简文案或加高框体")
    return lab_fit, (sub_fit or []), fs_main, fs_sub


# ── R1 磁吸与路由 ──────────────────────────────────────────────────────
def magnet(src, dst, attach_in=0, attach_out=0):
    """R1：按两框相对位置吸附框边（永不入框）。
    attach_in/out：同一条边上多箭头的错位序号（沿边平移 EDGE_STAGGER×序号）。"""
    sx0, sy0, sx1, sy1 = _bbox(src)
    dx0, dy0, dx1, dy1 = _bbox(dst)
    scx, scy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    dcx, dcy = (dx0 + dx1) / 2, (dy0 + dy1) / 2
    if abs(dcx - scx) >= abs(dcy - scy):        # 横向主导
        if dcx >= scx:   # 向右：源右缘→目标左缘（终点咬入框缘 EDGE_NIB）
            sy = scy + attach_out * EDGE_STAGGER
            dy = dcy - attach_in * EDGE_STAGGER
            return (sx1, sy), (dx0 + EDGE_NIB, dy)
        sy = scy + attach_out * EDGE_STAGGER
        dy = dcy - attach_in * EDGE_STAGGER
        return (sx0, sy), (dx1 - EDGE_NIB, dy)
    if dcy >= scy:       # 向上：源上缘→目标下缘
        sx = scx + attach_out * EDGE_STAGGER
        dx = dcx - attach_in * EDGE_STAGGER
        return (sx, sy1), (dx, dy0 + EDGE_NIB)
    sx = scx + attach_out * EDGE_STAGGER
    dx = dcx - attach_in * EDGE_STAGGER
    return (sx, sy0), (dx, dy1 - EDGE_NIB)


def _edge_between(src, dst):
    """回边方向键：'H'（横向）/'V'（纵向）+ 符号（lane 应去的一侧）。"""
    sx0, sy0, sx1, sy1 = _bbox(src)
    dx0, dy0, dx1, dy1 = _bbox(dst)
    scx, scy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    dcx, dcy = (dx0 + dx1) / 2, (dy0 + dy1) / 2
    if abs(dcx - scx) >= abs(dcy - scy):
        return "H", (1 if dcx >= scx else -1)
    return "V", (1 if dcy >= scy else -1)


def _lane_y(blocks, side, level):
    """R4：lane 的 y 坐标——主链最外缘之外 LANE_GAP，多回边错层。"""
    tops = max(_bbox(b)[3] for b in blocks)
    bots = min(_bbox(b)[1] for b in blocks)
    return (tops + LANE_GAP + LANE_STAGGER * level) if side > 0 else \
           (bots - LANE_GAP - LANE_STAGGER * level)


def _seg_hits(p0, p1, blocks, skip_ids):
    """线段（轴对齐 bbox 近似）是否穿过任何非端点节点。"""
    sb = (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))
    for b in blocks:
        if b["id"] in skip_ids:
            continue
        if _overlap(sb, _bbox(b), -0.02):
            return True
    return False


def route(src, dst, blocks, lane_level=0, side=None, orthogonal=False):
    """R1/R4：边路由——磁吸段不穿框则直连（离轴→3 段正交肘），否则走主导轴
    法向绕行 lane（横向边=上/下 lane，纵向边=左/右 lane；多回边错层）。
    返回 (points 列表, used_side)。points 首尾已磁吸框边。"""
    key, sgn = _edge_between(src, dst)
    if side is None:
        side = sgn
    p0, p1 = magnet(src, dst)
    if lane_level == 0 and not orthogonal and not _seg_hits(p0, p1, blocks, (src["id"], dst["id"])):
        if key == "H" and abs(p0[1] - p1[1]) > 0.05:    # 离轴直连→3 段正交肘
            gx = (p0[0] + p1[0]) / 2
            return [(p0[0], p0[1]), (gx, p0[1]), (gx, p1[1]), (p1[0], p1[1])], side
        if key == "V" and abs(p0[0] - p1[0]) > 0.05:
            # 横段 y=两端点的 y 中点（间隙中央——源出缘与目标入缘的正中）
            gy = (p0[1] + p1[1]) / 2
            return [(p0[0], p0[1]), (p0[0], gy), (p1[0], gy), (p1[0], p1[1])], side
        return [p0, p1], side
    # 绕行 lane：从面向 lane 一侧的框缘中点出→lane→入目标同侧框缘
    sx0, sy0, sx1, sy1 = _bbox(src)
    dx0, dy0, dx1, dy1 = _bbox(dst)
    if key == "H":
        ly = _lane_y(blocks, side, max(lane_level, 1))
        pts = [((sx0 + sx1) / 2, sy1 if side > 0 else sy0),
               ((sx0 + sx1) / 2, ly),
               ((dx0 + dx1) / 2, ly),
               ((dx0 + dx1) / 2, dy1 if side > 0 else dy0)]
    else:
        lx = (max(_bbox(b)[2] for b in blocks) + LANE_GAP + LANE_STAGGER * max(lane_level, 1)) \
            if side > 0 else \
            (min(_bbox(b)[0] for b in blocks) - LANE_GAP - LANE_STAGGER * max(lane_level, 1))
        pts = [(sx1 if side > 0 else sx0, (sy0 + sy1) / 2),
               (lx, (sy0 + sy1) / 2),
               (lx, (dy0 + dy1) / 2),
               (dx1 if side > 0 else dx0, (dy0 + dy1) / 2)]
    return pts, side


def assign_lanes(blocks, edges):
    """R4：cycle-breaking（ELK 语义）——DFS 找回边；磁吸直连会穿框的边也归 lane。
    返回 {edge_idx: (lane_level, side)}；直连边不在表内。"""
    ids = [b["id"] for b in blocks]
    bmap = {b["id"]: b for b in blocks}
    fwd = {}
    for e in edges:
        fwd.setdefault(e["from"], []).append(e["to"])
    back_pairs = set()
    seen, stack = set(), []

    def _dfs(u):
        seen.add(u)
        stack.append(u)
        for v in fwd.get(u, []):
            if v not in seen:
                _dfs(v)
            elif v in stack:
                back_pairs.add((u, v))
        stack.pop()

    for r in ids:
        if r not in seen:
            _dfs(r)
    out = {}
    lvl = 0
    for i, e in enumerate(edges):
        s_, t_ = bmap.get(e["from"]), bmap.get(e["to"])
        if s_ is None or t_ is None:
            continue
        is_back = (e["from"], e["to"]) in back_pairs
        p0, p1 = magnet(s_, t_)
        blocked = is_back or _seg_hits(p0, p1, blocks, (e["from"], e["to"]))
        if blocked:
            _, sgn = _edge_between(s_, t_)
            out[i] = (lvl + 1, sgn)
            lvl += 1
    return out


def place_edge_label(ax, fig, text, route_pts, blocks, placed_boxes, fp=None,
                     fs=9.0, color="#444444", dashed_hint=False,
                     line_segs=()):
    """R2：边标签放置（v8.0.0 简化版）。

    布局层已为带标签的边预留空间（ELK edgeLabels 语义）→ 锚点=边长直段
    中点，候选=上方→下方→左侧→右侧，画后墨迹实测过检才收；窄间隙自动
    折两行；全部失败才远置并画引线（仅此一处画引线，意图明确）。
    返回 (artist, real_bbox)。"""
    # 锚点=最长直线段的中点，并记录段方向（横段→标签上下；竖段→左右——线旁范式）
    _orient = "H"
    if len(route_pts) >= 4:
        _bs, _be, _blen = route_pts[1], route_pts[2], -1.0
        for k in range(1, len(route_pts) - 1):   # 含末段（箭头前的最后一段）
            (ax_, ay_), (bx_, by_) = route_pts[k], route_pts[k + 1]
            _L = abs(bx_ - ax_) + abs(by_ - ay_)
            if _L > _blen:
                _blen, _bs, _be = _L, (ax_, ay_), (bx_, by_)
        mid = ((_bs[0] + _be[0]) / 2, (_bs[1] + _be[1]) / 2)
        _orient = "H" if abs(_be[0] - _bs[0]) >= abs(_be[1] - _bs[1]) else "V"
    else:
        mid = ((route_pts[0][0] + route_pts[-1][0]) / 2,
               (route_pts[0][1] + route_pts[-1][1]) / 2)
        _orient = ("H" if abs(route_pts[-1][0] - route_pts[0][0])
                   >= abs(route_pts[-1][1] - route_pts[0][1]) else "V")

    def _ink_bb(t):
        fig.canvas.draw()
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        inv = ax.transData.inverted()
        (x0, y0) = inv.transform((bb.x0, bb.y0))
        (x1, y1) = inv.transform((bb.x1, bb.y1))
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def _hit(bb):
        for b in blocks:
            if _overlap(bb, _bbox(b), 0.08):
                return True
        for pb in placed_boxes:
            if _overlap(bb, pb, 0.03):
                return True
        for (q0, q1) in line_segs:
            if _overlap(bb, (min(q0[0], q1[0]), min(q0[1], q1[1]),
                             max(q0[0], q1[0]), max(q0[1], q1[1])), 0.04):
                return True
        return False

    _w, _h = measure(ax, text, fs, fp)
    _fp = fp if fp and has_cjk_local(text) else None

    # 窄间隙预判：锚点贴近某框缘（间隙 < 行高×2.4）→ 直接折两行竖排
    _txt = text
    if "\n" not in _txt and " " in _txt:
        for b in blocks:
            x0, y0, x1, y1 = _bbox(b)
            if x0 - 0.3 <= mid[0] <= x1 + 0.3 and min(abs(mid[1] - y0),
                                                      abs(mid[1] - y1)) < _h * 2.4:
                _txt = _txt.replace(" ", "\n", 1)
                break

    _h2 = measure(ax, _txt, fs, fp)[1]
    _w2 = max((measure(ax, ln, fs, fp)[0] for ln in _txt.split("\n")), default=_w)
    # 候选序列（带引线标记）：段上/下（无需引线）→ 框行上/下（垂直引线穿间隙——
    # 链图标签宽必然跨框体 x 域，这是 fig2 PASS 形态的标准位）→ 折行 → 远置
    _bt = max(_bbox(b)[3] for b in blocks)   # 框行顶
    _bb_ = min(_bbox(b)[1] for b in blocks)  # 框行底
    # 候选按段方向（铁律：候选不得骑线——横段禁同高侧移位、竖段禁上下重叠位）
    if _orient == "H":
        attempts = [
            (0.0, _h2 / 2 + 0.09, "bottom", False),                # 横段上方
            (0.0, -_h2 / 2 - 0.09, "top", False),                  # 横段下方
            (0.0, _bt + _h2 / 2 + 0.14 - mid[1], "bottom", True),  # 框行上方+垂直引线
            (0.0, _bb_ - _h2 / 2 - 0.14 - mid[1], "top", True),    # 框行下方+垂直引线
        ]
    else:   # 竖段：标签放左右两侧（线旁范式，零引线）
        attempts = [
            (_w2 / 2 + 0.26, 0.0, "center", False),                # 竖段右侧
            (-_w2 / 2 - 0.26, 0.0, "center", False),               # 竖段左侧
        ]
    for (dx, dy, va, _leader) in attempts:
        cx, cy = mid[0] + dx, mid[1] + dy
        t = ax.text(cx, cy, _txt, ha="center", va=va, fontsize=fs, color=color,
                    style="italic", linespacing=1.15, fontproperties=_fp, zorder=6)
        bb = _ink_bb(t)
        if _txt.split(chr(10))[0] == "合格":
            print(f"DBG dx={dx} dy={dy:.2f} va={va} bb y[{bb[1]:.2f}~{bb[3]:.2f}] "
                  f"x[{bb[0]:.2f}~{bb[2]:.2f}] hit={_hit(bb)}", file=sys.stderr)
        if not _hit(bb):
            placed_boxes.append(bb)
            if _leader:   # 垂直引线：从边中点连到标签近侧缘（单一明确意图）
                _ly0 = mid[1]
                _ly1 = bb[1] if va == "bottom" else bb[3]
                ax.plot([mid[0], mid[0]], [_ly0, _ly1], color=color, lw=0.7,
                        alpha=0.75, zorder=5)
            return t, bb
        t.remove()
    # 折行重试（框行上方位）
    if "\n" not in _txt and " " in _txt:
        _txt2 = _txt.replace(" ", "\n", 1)
        _h3 = measure(ax, _txt2, fs, fp)[1]
        _w3 = max((measure(ax, ln, fs, fp)[0] for ln in _txt2.split("\n")),
                  default=_w)
        cy = _bt + _h3 / 2 + 0.14
        t = ax.text(mid[0], cy, _txt2, ha="center", va="bottom", fontsize=fs,
                    color=color, style="italic", linespacing=1.15,
                    fontproperties=_fp, zorder=6)
        bb = _ink_bb(t)
        if not _hit(bb):
            placed_boxes.append(bb)
            ax.plot([mid[0], mid[0]], [mid[1], bb[1]], color=color, lw=0.7,
                    alpha=0.75, zorder=5)
            return t, bb
        t.remove()
    # 全失败→沿边方向滑动搜索（同高逐格外移，首个合法白区即收——紧邻无引线）
    _mid_x_all = [(_bbox(b)[0] + _bbox(b)[2]) / 2 for b in blocks]
    _dir = -1.0 if mid[0] > (sum(_mid_x_all) / len(_mid_x_all)) else 1.0
    for _k in range(1, 16):
        cx = mid[0] + _dir * (0.3 * _k)
        cy = mid[1]
        t = ax.text(cx, cy, _txt, ha="center", va="center", fontsize=fs,
                    color=color, style="italic", linespacing=1.15,
                    fontproperties=_fp, zorder=6)
        bb = _ink_bb(t)
        if not _hit(bb):
            placed_boxes.append(bb)
            return t, bb
        t.remove()
    # 滑动也失败→远置左侧+引线（真正最后手段，引线意图明确）
    cx, cy = mid[0] - _w2 - 0.7, mid[1]
    t = ax.text(cx, cy, _txt, ha="center", va="center", fontsize=fs, color=color,
                style="italic", linespacing=1.15, fontproperties=_fp, zorder=6)
    bb = _ink_bb(t)
    ax.plot([bb[2] + 0.04, mid[0]], [cy, mid[1]], color=color, lw=0.7,
            alpha=0.75, zorder=5)
    placed_boxes.append(bb)
    return t, bb


# ── R5 画布自裁剪 ──────────────────────────────────────────────────────
def trim_limits(ax, blocks, extra_pts=(), pad=0.5, ratio_hint=True, pad_x=None,
                pad_y=None, pad_top=None, pad_bot=None, set_lim=True):
    """R5：内容包围盒+统一边距重设 xlim/ylim（原内容占比 41% 的根修）。
    pad_x/pad_y=分轴边距（横链图纵向收紧提占比）；缺省=统一 pad。"""
    px = pad if pad_x is None else pad_x
    py = pad if pad_y is None else pad_y
    xs, ys = [], []
    for b in blocks:
        x0, y0, x1, y1 = _bbox(b)
        xs += [x0, x1]
        ys += [y0, y1]
    for (x, y) in extra_pts:
        xs.append(x)
        ys.append(y)
    x0, x1 = min(xs) - px, max(xs) + px
    y0, y1 = min(ys) - (py if pad_bot is None else pad_bot), \
        max(ys) + (py if pad_top is None else pad_top)
    if set_lim:
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
    if ratio_hint:
        fx = (max(xs) - min(xs)) / max(x1 - x0, 1e-9)
        fy = (max(ys) - min(ys)) / max(y1 - y0, 1e-9)
        return (fx + fy) / 2      # 按轴填充均值（横链图面积积会不公平压低）
    return 1.0


# ── R6 三层 bbox 闸 ────────────────────────────────────────────────────
def gate_strict(ax, fig, blocks, label_bboxes, route_lines, ratios=None,
                route_meta=None):
    """R6 strict 闸：三层 bbox 断言——节点×边标签×箭头线段。
    端点所属框豁免（EDGE_NIB 咬合段的设计语义=尖端落在框缘线上）。
    返回违规清单（空=通过）；调用方决定 exit 2。"""
    violations = []
    seg_bbs, seg_ends = [], []
    for (p0, p1) in route_lines:
        seg_bbs.append((min(p0[0], p1[0]), min(p0[1], p1[1]),
                        max(p0[0], p1[0]), max(p0[1], p1[1])))
        seg_ends.append((p0, p1))

    def _end_owner(seg_end_pts):
        """段的端点框 id（两端）；咬合设计的豁免依据。"""
        ids = set()
        for (px, py) in seg_end_pts:
            for b in blocks:
                x0, y0, x1, y1 = _bbox(b)
                if (x0 - 0.02 <= px <= x1 + 0.02 and y0 - 0.02 <= py <= y1 + 0.02):
                    ids.add(b["id"])
        return ids
    # 层1：边标签 × 节点（收缩 -0.06 判定：与放置器 _hit 的 0.08 膨胀对齐——
    # 放置器允许的 0.08 气垫位在闸上不该翻案，否则放置器与闸互相矛盾）
    for i, lb in enumerate(label_bboxes):
        for j, b in enumerate(blocks):
            if _overlap(lb, _bbox(b), -0.06):
                violations.append(f"层1 边标签#{i} 与节点「{b.get('id')}」包围盒相交")
    # 层2：边标签 × 边标签（零交集）
    for i in range(len(label_bboxes)):
        for j in range(i + 1, len(label_bboxes)):
            if _overlap(label_bboxes[i], label_bboxes[j], 0.02):
                violations.append(f"层2 边标签#{i} 与 边标签#{j} 相交")
    # 层3：箭头线段 × 无关节点（段两端点所在框=归属/目标框，豁免——
    # EDGE_NIB 咬合段终点在目标框缘内 0.10 属设计语义）
    for i, sb in enumerate(seg_bbs):
        _own = _end_owner(seg_ends[i])
        for j, b in enumerate(blocks):
            if b.get("id") in _own:
                continue
            if _overlap(sb, _bbox(b), -0.01):   # 收缩判定：容忍贴边
                violations.append(f"层3 箭头段#{i} 与节点「{b.get('id')}」相交")
    # 层4（附）：内容占比
    if ratios is not None and ratios < 0.60:
        violations.append(f"层4 内容占比 {ratios:.0%} < 60%（画布自裁剪不足）")
    return violations


# ── R4 语义布局（-t flow：用户只给语义不给坐标） ────────────────────────
def layout_semantic(nodes, edges, layout="chain", direction="TB"):
    """-t flow 自动布局：chain=单行横链；layered=Sugiyama 最长路径分层。
    返回 blocks 列表（补齐 x/y/w/h）。"""
    ids = [n["id"] for n in nodes]
    idset = set(ids)
    for e in edges:
        if e["from"] not in idset or e["to"] not in idset:
            raise ValueError(f"flow: 边 {e['from']}→{e['to']} 引用未定义节点")
    # 估宽：label+sublabel 显示宽度（CJK 2:1）→ w = max(2.0, 0.16*chars + 0.5)
    blocks = []
    for n in nodes:
        disp = n.get("label", n["id"]) + (n.get("sublabel", "") or "")
        units = sum(2 if ord(ch) > 0x2E80 else 1 for ch in disp)
        w = min(3.4, max(2.0, 0.155 * units + 0.42))
        # 高度语义自适应：无副标=紧凑档；副标预期行数（估宽）→ 1+行数 档
        # （equal-aspect 下固定值会让 fit 逐降到字号下限报错——拍脑袋值退役）
        h = 0.78
        if n.get("sublabel"):
            sub_units = sum(2 if ord(c) > 0x2E80 else 1 for c in str(n["sublabel"]))
            est_lines = max(1, math.ceil(sub_units / max(w / 0.155, 8)))
            h = max(1.16, 0.62 + 0.54 * (est_lines + 1))
        blocks.append({"id": n["id"], "label": n.get("label", n["id"]),
                       "sublabel": n.get("sublabel"), "w": w, "h": h,
                       "color": n.get("color"), "shape": n.get("shape", "round")})
    bmap = {b["id"]: b for b in blocks}
    if layout == "chain":
        x = 0.0
        gap = 0.9
        for b in blocks:
            b["x"], b["y"] = x, 0.0
            x += b["w"] + gap
        return blocks
    # layered：最长路径分层（回边不计层）→ 层内按出现顺序排
    indeg = {i: 0 for i in ids}
    back = set()
    seen, stack = set(), []

    def _dfs(u):
        seen.add(u)
        stack.append(u)
        for e in edges:
            if e["from"] == u:
                v = e["to"]
                if v not in seen:
                    _dfs(v)
                elif v in stack:
                    back.add((e["from"], e["to"]))
        stack.pop()

    for r in ids:
        if r not in seen:
            _dfs(r)
    for e in edges:
        if (e["from"], e["to"]) not in back:
            indeg[e["to"]] += 1
    layer = {}
    frontier = [i for i in ids if indeg[i] == 0]
    lv = 0
    while frontier:
        for u in frontier:
            layer[u] = lv
        nxt = []
        for u in frontier:
            for e in edges:
                if e["from"] == u and (e["from"], e["to"]) not in back:
                    indeg[e["to"]] -= 1
                    if indeg[e["to"]] == 0:
                        nxt.append(e["to"])
        frontier = nxt
        lv += 1
    for i in ids:
        layer.setdefault(i, lv)
    # v8.0.0 根因修（ELK edgeLabels 语义，2026-11 研究确认）：边标签参与布局——
    # 带标签的边在层间预留标签带（此前 0.5 间隙物理装不下 9pt 标签，
    # 被迫在放置层加引线/折叠/外推一连串补丁=全部别扭的总根源）
    _labeled = any(e.get("label") for e in edges)
    _pitch_v = 3.0 if _labeled else 2.2   # 层间距 = 框高 + 标签带（有标签时加宽）
    _pitch_h = 3.6
    if direction in ("LR",):
        rows = {}
        for i in ids:
            rows.setdefault(layer[i], []).append(i)
        for lv_i, row in rows.items():
            y = 0.0
            for i in row:
                bmap[i]["y"] = y
                y += bmap[i]["h"] + 0.55
        # 列位=层
        for i in ids:
            bmap[i]["x"] = layer[i] * _pitch_h
    else:   # TB：层=行（自上而下），层内横排
        rows = {}
        for i in ids:
            rows.setdefault(layer[i], []).append(i)
        top = (max(layer.values()) + 1) * _pitch_v
        for lv_i, row in rows.items():
            x = 0.0
            for i in row:
                bmap[i]["x"] = x
                bmap[i]["y"] = top - lv_i * _pitch_v
                x += bmap[i]["w"] + 0.7
    return blocks


# ── 渲染管线（diagram/flow 共用单一事实源） ──────────────────────────────
def render(ax, fig, blocks, arrows, groups=(), annotations=(), theme=None,
           cjk_fp=None, gate="basic", orthogonal=False):
    """完整渲染：磁吸逐段箭头+lane 回边+标签避让+文本自适应+裁剪+闸。
    返回 (violations, ratio)。gate="strict" 时违规由调用方 exit 2。"""
    from matplotlib.patches import FancyBboxPatch, Rectangle

    bmap = {b["id"]: b for b in blocks}
    fs = (theme or {}).get("font_size", 11)
    text_color = "#1a1a1a"
    arrow_color = "#555555"
    fp_any = cjk_fp

    # ── 1) 组背景（最底层）──
    for grp in groups:
        gb = [bmap[i] for i in grp.get("blocks", []) if i in bmap]
        if not gb:
            continue
        pad = 0.3
        gx = min(_bbox(b)[0] for b in gb) - pad
        gy = min(_bbox(b)[1] for b in gb) - pad
        gw = max(_bbox(b)[2] for b in gb) - gx + pad
        gh = max(_bbox(b)[3] for b in gb) - gy + pad
        gc = grp.get("color", "#888888")
        ax.add_patch(Rectangle((gx, gy), gw, gh, linewidth=2, edgecolor=gc,
                               facecolor="none", linestyle=grp.get("style", "dashed"),
                               alpha=0.8, zorder=1))
        if grp.get("label"):
            ax.text(gx + 0.15, gy + gh - 0.15, grp["label"], fontsize=fs - 1,
                    color=gc, fontweight="bold", va="top", ha="left", zorder=2,
                    fontproperties=cjk_fp if cjk_fp and has_cjk_local(grp["label"]) else None)

    # ── 1.5) 一次性确定性定限（measure-then-render 铁律的根基：测量与最终
    #     渲染必须在同一 transform 下——早期粗限+终裁改限会让测量集体失真 1.665×，
    #     这是主副标压字的根因）。lane 数从边集预知，无需测量即可定终限。──
    lanes = assign_lanes(blocks, arrows)
    n_above = sum(1 for (_lv, sd) in lanes.values() if sd > 0)
    n_below = sum(1 for (_lv, sd) in lanes.values() if sd < 0)
    _lab_allow = 0.9            # 边标签向上/下方的最大外扩（候选含 +0.85 档）
    trim_limits(ax, blocks, pad_x=0.3,
                pad_top=0.45 + _lab_allow + (LANE_GAP + LANE_STAGGER * n_above
                                             if n_above else 0),
                pad_bot=0.45 + _lab_allow + (LANE_GAP + LANE_STAGGER * n_below
                                             if n_below else 0),
                ratio_hint=False)
    ax.set_aspect("equal")   # 必须先于一切测量：aspect 的 box 收缩改变 y 比例尺，
    ax.axis("off")           # 后置会让测量态与最终态差 ~1.9×（主副标压字根因）

    # ── 2) 边路由（先于块：线在块下层，端点磁吸在框边仍可见）──
    route_pts, route_lines, route_meta = [], [], []
    attach_out, attach_in = {}, {}
    for i, e in enumerate(arrows):
        s, t = bmap.get(e["from"]), bmap.get(e["to"])
        if s is None or t is None:
            continue
        lv, side = lanes.get(i, (0, 1))
        pts, side = route(s, t, blocks, lane_level=lv, side=side,
                          orthogonal=orthogonal)
        # 同一目标框边多箭头错位（双向对撞根修）
        tkey = (e["from"], e["to"])
        ao = attach_out.get((e["from"], tuple(round(v, 2) for v in pts[0])), 0)
        ai = attach_in.get((e["to"], tuple(round(v, 2) for v in pts[-1])), 0)
        if lv == 0 and len(pts) == 2:   # 仅直连重磁吸做同边错位；折线（正交/lane）保持
            p0, p1 = magnet(s, t, attach_out=ao, attach_in=ai)
            pts = [p0, p1]
            attach_out[(e["from"], tuple(round(v, 2) for v in p0))] = ao + 1
            attach_in[(e["to"], tuple(round(v, 2) for v in p1))] = ai + 1
        route_pts.append(pts)
        route_meta.append((e, pts))
        for k in range(len(pts) - 1):
            route_lines.append((pts[k], pts[k + 1]))

    # ── 3) 画块（文本自适应先行）──
    label_artists = []
    label_bboxes = []
    for b in blocks:
        fp_l = cjk_fp if cjk_fp and has_cjk_local(b.get("label", "")) else None
        fp_s = cjk_fp if cjk_fp and has_cjk_local(b.get("sublabel") or "") else None
        lab_lines, sub_lines, fs_m, fs_s = fit_block_text(
            ax, b, fs, fs - 2, fp_l, fp_s)
        bc = b.get("color") or (theme or {}).get("colors", ["#56B4E9"])[0]
        shape = b.get("shape", "round")
        if shape == "rect":
            patch = FancyBboxPatch((b["x"], b["y"]), b["w"], b["h"],
                                   boxstyle="square,pad=0", facecolor=bc,
                                   edgecolor=bc, linewidth=1.5, alpha=0.85, zorder=3)
        else:
            patch = FancyBboxPatch((b["x"], b["y"]), b["w"], b["h"],
                                   boxstyle="round,pad=0.1", facecolor=bc,
                                   edgecolor=bc, linewidth=1.0, alpha=0.9,
                                   zorder=3)   # 描边同框色（white 描边会在箭头
                                   # 咬入处截断杆=色段残迹；半透明白边无视觉价值）
        ax.add_patch(patch)
        tcol = _text_color(bc)
        # 组合垂直排版：文本块（主+副）整体居中——两行副标不再上探入主标签
        lab_h = measure(ax, "\n".join(lab_lines), fs_m, fp_l)[1]      # 实测
        if sub_lines:
            sub_h = measure(ax, "\n".join(sub_lines), fs_s, fp_s)[1]  # 实测
            mid_y = b["y"] + b["h"] / 2
            cy = mid_y + (sub_h + 0.07) / 2          # 主标签中心上移半隙
            sy = mid_y - (lab_h + 0.07) / 2          # 副标签中心下移
        else:
            cy = b["y"] + b["h"] / 2
            sy = None
        ax.text(b["x"] + b["w"] / 2, cy, "\n".join(lab_lines), ha="center",
                va="center", fontsize=fs_m, color=tcol, fontweight="bold",
                fontproperties=fp_l, zorder=4, linespacing=1.15)
        if sub_lines:
            ax.text(b["x"] + b["w"] / 2, sy, "\n".join(sub_lines), ha="center",
                    va="center", fontsize=fs_s, color=tcol, alpha=0.85,
                    fontproperties=fp_s, zorder=4, linespacing=1.1)

    # ── 4) 画箭头（lane 折线逐段+末端箭头）──
    for (e, pts) in route_meta:
        col = e.get("color", arrow_color)
        ls = (0, (5, 3)) if e.get("dashed") else "-"     # R1：虚线必须生效
        lw = 1.5 if not e.get("dashed") else 1.4
        import numpy as _np
        from matplotlib.patches import FancyArrowPatch, Polygon
        # 折线段画到倒数第二点（butt 端帽=零越界）；末段+箭头头=实体三角，
        # 免 FancyArrowPatch mutation 的半透明尾迹（ghost 三角根因）
        if len(pts) == 2:
            _head, _tail = pts[1], pts[0]
        else:
            _head, _tail = pts[-1], pts[-2]
        # 头三角基准点（head 后退边长处）——杆必须画到这里（连续无脱节：
        # 「L 形残段悬浮/箭头与虚线断开」= 旧版杆止于 pts[-2] 与 _base 脱节）
        _hs = 0.22
        _dx0, _dy0 = _head[0] - _tail[0], _head[1] - _tail[1]
        _L0 = math.hypot(_dx0, _dy0) or 1.0
        _ux0, _uy0 = _dx0 / _L0, _dy0 / _L0
        _base = (_head[0] - _ux0 * _hs, _head[1] - _uy0 * _hs)
        if len(pts) > 2:
            xs = [p[0] for p in pts[:-1]] + [_base[0]]
            ys = [p[1] for p in pts[:-1]] + [_base[1]]
            ax.plot(xs, ys, color=col, lw=lw, linestyle=ls, zorder=2,
                    solid_capstyle="butt")
        _dx, _dy = _dx0, _dy0
        _L = math.hypot(_dx, _dy) or 1.0
        _ux, _uy = _dx / _L, _dy / _L           # 单位向（tail→head）
        _px, _py = -_uy, _ux                     # 法向
        ax.add_patch(Polygon([_head, (_base[0] + _px * _hs * 0.42,
                                     _base[1] + _py * _hs * 0.42),
                                  (_base[0] - _px * _hs * 0.42,
                                   _base[1] - _py * _hs * 0.42)],
                             closed=True, facecolor=col, edgecolor=col,
                             lw=0.4, zorder=5))   # 实心三角且压框上层
        # （zorder 低于框时：咬入框内的三角被框 alpha 0.9 罩一层=「半透明 ghost」实因）
        if len(pts) == 2:
            ax.plot([_tail[0], _base[0]], [_tail[1], _base[1]],
                    color=col, lw=lw, linestyle=ls, zorder=2, solid_capstyle="butt")
        # ── 5) 边标签（避让+引线）──
        if e.get("label"):
            fp_e = cjk_fp if cjk_fp and has_cjk_local(e["label"]) else None
            _own_mid = (pts[len(pts) // 2 - 1], pts[len(pts) // 2]) if len(pts) > 2 \
                else (pts[0], pts[1])
            _other = [(q0, q1) for (q0, q1) in route_lines
                      if not (abs(q0[0] - _own_mid[0][0]) < 1e-6
                              and abs(q0[1] - _own_mid[0][1]) < 1e-6
                              and abs(q1[0] - _own_mid[1][0]) < 1e-6
                              and abs(q1[1] - _own_mid[1][1]) < 1e-6)]
            t, bb = place_edge_label(ax, fig, e["label"], pts, blocks,
                                     label_bboxes, fp=fp_e,
                                     fs=max(FONT_FLOOR, fs - 2),
                                     color=e.get("label_color", "#444444"),
                                     line_segs=_other)
            label_artists.append(t)   # bbox 已由 place_edge_label 内部登记（勿重复入闸）

    # ── 6) 自由注记 ──
    for ann in annotations:
        ax.text(ann["x"], ann["y"], ann["text"], ha=ann.get("ha", "center"),
                va=ann.get("va", "center"), fontsize=ann.get("fontsize", fs),
                color=ann.get("color", text_color),
                fontweight=ann.get("weight", "normal"),
                fontproperties=cjk_fp if cjk_fp and has_cjk_local(ann["text"]) else None,
                zorder=5)

    # ── 7) 裁剪 + 闸 ──
    extra = [p for pts in route_pts for p in pts]
    ratio = trim_limits(ax, blocks, extra, pad_x=0.3, pad_top=0.45 + _lab_allow,
                        pad_bot=0.45 + _lab_allow, set_lim=False)
    violations = []
    if gate == "strict":
        violations = gate_strict(ax, fig, blocks, label_bboxes, route_lines,
                                 ratios=ratio)
    return violations, ratio


def has_cjk_local(s):
    return any(0x2E80 <= ord(ch) <= 0x9FFF or 0x3000 <= ord(ch) <= 0x303F
               or 0xFF00 <= ord(ch) <= 0xFFEF for ch in str(s))


def _text_color(bg):
    """反色判定=af_shared.cell_text_color 单一真源（叶模块可安全 import）。"""
    from af_shared import cell_text_color
    return cell_text_color(bg)
