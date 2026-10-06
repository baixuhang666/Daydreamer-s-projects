# -*- coding: utf-8 -*-
"""从银行行测PDF提取规范化文本：坐标排序 + 表格识别 + 水印过滤"""
import pymupdf
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (PDF_DIR, OUT_DIR, MODULES, MODULE_ORDER,
                    WATERMARKS as _WM, CELL_WATERMARK_CHARS as _CWC)

WATERMARKS = set(_WM)
# 表格单元格内的水印单字（"职业人小店"水印被拆成单字散布）
CELL_WATERMARK_CHARS = set(_CWC)
os.makedirs(OUT_DIR, exist_ok=True)

# 由 config.MODULES 派生：{模块key: 试题文件名, 模块key+'_jx': 解析文件名}
FILES = {}
for _k in MODULE_ORDER:
    if _k in MODULES:
        FILES[_k] = MODULES[_k]['q']
        FILES[_k + '_jx'] = MODULES[_k]['a']


def pdf_path(fname):
    """支持填绝对路径；相对路径则拼到 PDF_DIR"""
    return fname if os.path.isabs(fname) else os.path.join(PDF_DIR, fname)


def clean_cell(cell):
    if cell is None:
        return ''
    s = str(cell).strip()
    if s in ('职', '店'):
        return ''
    parts = s.split('\n')
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 纯水印单字组合片段，整段剔除
        if p and all(ch in CELL_WATERMARK_CHARS for ch in p):
            continue
        # 数字前混入的水印单字：如 店1.26 → 1.26
        p = re.sub(r'^[职店小人业]+(?=[\d\-])', '', p)
        cleaned.append(p)
    return ''.join(cleaned)





def table_to_markdown(ext):
    """表格二维数组转markdown，清理空行空列"""
    rows = [[clean_cell(c) for c in row] for row in ext]
    rows = [r for r in rows if any(x for x in r)]
    if not rows:
        return ''
    ncols = max(len(r) for r in rows)
    for r in rows:
        r.extend([''] * (ncols - len(r)))
    # 删除全空列
    keep = [j for j in range(ncols) if any(r[j] for r in rows)]
    if not keep:
        return ''
    rows = [[r[j] for j in keep] for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |',
           '|' + '---|' * len(rows[0])]
    for r in rows[1:]:
        out.append('| ' + ' | '.join(x for x in r) + ' |')
    return '\n'.join(out)


def _cluster_boxes(boxes, gap=10.0):
    """简单图簇合并：间距<gap的框合并"""
    merged = True
    while merged:
        merged = False
        out = []
        while boxes:
            b = boxes.pop()
            grown = False
            for o in out:
                if not (b[2] + gap < o[0] or o[2] + gap < b[0]
                        or b[3] + gap < o[1] or o[3] + gap < b[1]):
                    o[0] = min(o[0], b[0]); o[1] = min(o[1], b[1])
                    o[2] = max(o[2], b[2]); o[3] = max(o[3], b[3])
                    grown = True
                    merged = True
                    break
            if not grown:
                out.append(b)
        boxes = out
    return boxes


def get_content_images(page, pno, table_bboxes=()):
    """检测页面上的内容图区域（位图+矢量图形），返回 [(bbox, tag)]"""
    words = page.get_text('words')

    def in_tables(x0, y0, x1, y1):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for (tx0, ty0, tx1, ty1) in table_bboxes:
            if tx0 - 2 <= cx <= tx1 + 2 and ty0 - 2 <= cy <= ty1 + 2:
                return True
        return False

    candidates = []
    # 位图（排除水印小图）
    for im in page.get_image_info():
        x0, y0, x1, y1 = im['bbox']
        if (x1 - x0) < 60 and (y1 - y0) < 60:
            continue
        candidates.append([x0, y0, x1, y1])
    # 矢量图形（排除表格内线条、页眉页脚横线）
    for d in page.get_drawings():
        r = d['rect']
        if r.width < 5 and r.height < 5:
            continue
        if in_tables(r.x0, r.y0, r.x1, r.y1):
            continue
        if r.height < 2:  # 横线（页眉分隔线等）
            continue
        candidates.append([r.x0, r.y0, r.x1, r.y1])
    if not candidates:
        return []
    boxes = _cluster_boxes(candidates, gap=10)
    # 过滤：太小的簇（装饰），表格区域内的簇
    boxes = [b for b in boxes
             if (b[2] - b[0]) > 60 and (b[3] - b[1]) > 30
             and not in_tables(b[0], b[1], b[2], b[3])]
    if not boxes:
        return []
    # 扩展bbox包含紧邻的选项字母行（A B C D）、问号行、孤立字母（A. B. C. D.）
    mark_pat = re.compile(r'^([A-D][\.、]?)(\s+[A-D][\.、]?)*$|^\?$|^（\s*\）$')
    expanded = set()
    for bi, b in enumerate(boxes):
        for w in words:
            wx0, wy0, wx1, wy1, txt = w[0], w[1], w[2], w[3], w[4]
            if not mark_pat.match(txt):
                continue
            x_center = (wx0 + wx1) / 2
            # 字母中心在bbox x范围内（含容差，选项字母常在图左侧10pt左右）
            if not (b[0] - 16 <= x_center <= b[2] + 16):
                continue
            below = 0 <= wy0 - b[3] <= 22 or 0 <= b[1] - wy1 <= 22
            y_overlap = not (wy1 < b[1] or wy0 > b[3])
            x_overlap = not (wx1 < b[0] or wx0 > b[2])
            if below or (y_overlap and x_overlap):
                b[0] = min(b[0], wx0); b[1] = min(b[1], wy0)
                b[2] = max(b[2], wx1); b[3] = max(b[3], wy1)
                expanded.add(bi)
    # 二次合并（gap=30）：仅当两块间隙内无实质文本时合并
    # （同题的题干图+选项图、图形选项组之间没有文字；不同题之间必有题干文字）
    MARK_WORD = re.compile(r'\?|[A-D]|[A-D][\.、]|[A-D]\s+[A-D]|（\s*）|（\s*）')
    def is_mark_word(w):
        return bool(MARK_WORD.fullmatch(w[4].strip()))
    def gap_has_text(b1, b2):
        # 确定间隙矩形
        if b1[3] <= b2[1] or b2[3] <= b1[1]:  # 上下分布
            gy0, gy1 = min(b1[3], b2[3]), max(b1[1], b2[1])
            gx0, gx1 = min(b1[0], b2[0]), max(b1[2], b2[2])
            gap_rect = [gx0, gy0, gx1, gy1]
        elif b1[2] <= b2[0] or b2[2] <= b1[0]:  # 左右分布
            gx0, gx1 = min(b1[2], b2[2]), max(b1[0], b2[0])
            gy0, gy1 = min(b1[1], b2[1]), max(b1[3], b2[3])
            gap_rect = [gx0, gy0, gx1, gy1]
        else:
            return False
        for w in words:
            wx0, wy0, wx1, wy1, txt = w[0], w[1], w[2], w[3], w[4]
            cx, cy = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if gap_rect[0] <= cx <= gap_rect[2] and gap_rect[1] <= cy <= gap_rect[3]:
                if not is_mark_word(w):
                    return True
        return False
    boxes2 = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        out = []
        while boxes2:
            b = boxes2.pop()
            grown = False
            for o in out:
                near = (not (b[2] + 30 < o[0] or o[2] + 30 < b[0]
                             or b[3] + 30 < o[1] or o[3] + 30 < b[1]))
                if near and not gap_has_text(b, o):
                    o[0] = min(o[0], b[0]); o[1] = min(o[1], b[1])
                    o[2] = max(o[2], b[2]); o[3] = max(o[3], b[3])
                    grown = True
                    changed = True
                    break
            if not grown:
                out.append(b)
        boxes2 = out
    boxes = boxes2
    result = []
    for b in boxes:
        tag = f'IMG:p{pno}_{b[0]:.0f}_{b[1]:.0f}_{b[2]:.0f}_{b[3]:.0f}'
        result.append((tuple(b), tag))
    return result


def extract_page(page, pno=0):
    """提取一页：文本行按坐标排序，表格转markdown插入对应位置。
    返回 [(text, pno, y), ...]"""
    """提取一页：文本行按坐标排序，表格转markdown插入对应位置"""
    tables = page.find_tables()
    table_bboxes = []
    table_mds = []
    for t in tables.tables:
        ext = t.extract()
        if not ext or len(ext) < 2:
            continue
        md = table_to_markdown(ext)
        if md:
            table_bboxes.append(t.bbox)
            table_mds.append(md)

    # 内容图片块
    img_blocks = get_content_images(page, pno, table_bboxes)
    img_bboxes = [b for b, _ in img_blocks]

    words = page.get_text('words')

    def in_any(w, bboxes):
        x0, y0, x1, y1 = w[:4]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for (tx0, ty0, tx1, ty1) in bboxes:
            if tx0 - 2 <= cx <= tx1 + 2 and ty0 - 2 <= cy <= ty1 + 2:
                return True
        return False

    # 过滤表格区域内的词 + 词级水印
    words = [w for w in words if not in_any(w, table_bboxes)]
    # 图片区域内的词：只丢弃短标记（A-D字母、问号等，它们会渲染进图片里），
    # 保留长文本（部分解析文字压在图片上方，过滤会丢内容）
    short_mark = re.compile(r'^[A-D?？]{1,2}[\.、]?$|^\d{1,2}$|^[（(]\s*[）)]$')
    words = [w for w in words
             if not (in_any(w, img_bboxes) and short_mark.match(w[4]))]
    words = [w for w in words if w[4] not in WATERMARKS
             and not w[4].startswith('职业人小店')
             and not w[4].endswith('祝您上岸')]
    words.sort(key=lambda w: (round(w[1], 1), w[0]))

    # 行聚类：y相近归一行，行内按x排序
    lines = []
    cur, cur_y = [], None
    for w in words:
        y = w[1]
        if cur_y is None or abs(y - cur_y) <= 3.2:
            cur.append(w)
            if cur_y is None:
                cur_y = y
        else:
            cur.sort(key=lambda t: t[0])
            lines.append((cur_y, cur[0][0], ' '.join(c[4] for c in cur)))
            cur, cur_y = [w], y
    if cur:
        cur.sort(key=lambda t: t[0])
        lines.append((cur_y, cur[0][0], ' '.join(c[4] for c in cur)))

    # 表格/图片作为块按y坐标插入
    for bbox, md in zip(table_bboxes, table_mds):
        lines.append((bbox[1], bbox[0] - 50, '[TABLE]\n' + md + '\n[/TABLE]'))
    for bbox, tag in img_blocks:
        lines.append((bbox[1], bbox[0] - 50, f'[{tag}]'))
    lines.sort(key=lambda l: (l[0], l[1]))

    out_lines = []
    for y, x, text in lines:
        t = text.strip()
        if not t:
            continue
        if re.fullmatch(r'\d{1,2}', t):  # 独立页码行
            continue
        # 行内残留水印
        t = re.sub(r'职业人小店祝您上岸|职业人小店|祝您上岸', '', t).strip()
        if not t:
            continue
        out_lines.append((t, pno, y))
    return out_lines


def merge_crosspage_tables(all_lines):
    """合并跨页续表：[/TABLE][PAGEBREAK][TABLE]且续表无表头 → 合并成一个表格
    all_lines 元素为 (text, pno, y)"""
    HEADER_PAT = re.compile(r'^\|\s*(指标|地\s*区|年份|分\s*组|业\s*分\s*组)')
    SEP_PAT = re.compile(r'^\|[-\s|]+\|$')
    out = []
    i = 0
    n = len(all_lines)
    while i < n:
        line = all_lines[i]
        # 检测 [/TABLE] [PAGEBREAK] [TABLE] 模式（跨页续表）
        if (line[0] == '[/TABLE]' and i + 2 < n and all_lines[i + 1][0] == '[PAGEBREAK]'
                and all_lines[i + 2][0] == '[TABLE]'):
            k = i + 3
            first_content = all_lines[k][0] if k < n else ''
            if first_content and not HEADER_PAT.match(first_content.strip()):
                # 是续表：跳过 [/TABLE]、[PAGEBREAK]、[TABLE]，
                # 续表内容直接追加到当前表格，跳过其中第一个|---|分隔行
                i = i + 3
                sep_skipped = False
                while i < n and all_lines[i][0] != '[/TABLE]':
                    if not sep_skipped and SEP_PAT.match(all_lines[i][0].strip()):
                        sep_skipped = True
                        i += 1
                        continue
                    out.append(all_lines[i])
                    i += 1
                continue
        out.append(line)
        i += 1
    return out


def extract_doc(path):
    doc = pymupdf.open(path)
    all_lines = []
    for pno, page in enumerate(doc):
        for text, lpno, y in extract_page(page, pno):
            # 表格块是含\n的多行文本，拆成独立行以便跨页合并检测
            for sub in text.split('\n'):
                all_lines.append((sub, lpno, y))
        if pno < len(doc) - 1:
            all_lines.append(('[PAGEBREAK]', pno, -1))
    merged = merge_crosspage_tables(all_lines)
    # 去掉剩余的PAGEBREAK标记
    return [l for l in merged if l[0] != '[PAGEBREAK]']


if __name__ == '__main__':
    for key, fname in FILES.items():
        path = pdf_path(fname)
        if not os.path.exists(path):
            print(f'✗ 跳过 {key}：找不到 {path}')
            continue
        lines = extract_doc(path)
        text = '\n'.join(l[0] for l in lines)
        with open(os.path.join(OUT_DIR, f'fmt_{key}.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
        with open(os.path.join(OUT_DIR, f'lines_{key}.json'), 'w', encoding='utf-8') as f:
            json.dump([[l[0], l[1], round(l[2], 1)] for l in lines], f, ensure_ascii=False)
        print(f'{key}: {len(text)}字符, {len(lines)}行')
