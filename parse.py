# -*- coding: utf-8 -*-
"""解析规范化文本为结构化题库JSON + 渲染图片"""
import re
import os
import json
import pymupdf
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (PDF_DIR, OUT_DIR, MODULES as CFG_MODULES, MODULE_ORDER,
                    MATERIAL_MODULES)

OUTDIR = OUT_DIR
IMGDIR = os.path.join(OUTDIR, 'images')
os.makedirs(IMGDIR, exist_ok=True)


def pdf_path(fname):
    """支持填绝对路径；相对路径则拼到 PDF_DIR"""
    return fname if os.path.isabs(fname) else os.path.join(PDF_DIR, fname)


# 由 config 派生（按 MODULE_ORDER 顺序，决定最终 JSON 与首页展示顺序）
MODULES = {
    k: {'name': CFG_MODULES[k]['name'],
        'q': f'lines_{k}.json',
        'a': f'lines_{k}_jx.json',
        'pdf': CFG_MODULES[k]['q']}
    for k in MODULE_ORDER if k in CFG_MODULES
}

Q_START = re.compile(r'^(\d{1,2})\s*[\.、．]\s*(.*)$')
# 选项标记：字母+点（前面允许空格、点、横线等非中文字符）
OPT_A = re.compile(r'(?:^|[^\u4e00-\u9fffA-Za-z0-9])([A-D])[\.、．]\s*')
# 选项标记：行首字母+空格（无点，如"A 渗透 杯水车薪"）
OPT_B = re.compile(r'^([A-D])(?=\s)')
OPT_LINE = re.compile(r'^[A-D][\.、．]|^[A-D]\s')
A_START = re.compile(r'^(\d{1,2})\s*[\.、．]?【答案】\s*([A-D]+)')
MATERIAL_MARK = re.compile(r'^[一二三四五六七八九十]+、')


def match_qstart(t):
    """匹配题号行，排除小数（如"3.14%""5.2万"）被误判为题号"""
    m = Q_START.match(t)
    if not m:
        return None
    rest = m.group(2)
    if rest == '':
        return m
    if re.match(r'^\d+\s*[%\u5143\u4e07\u4ebf\u500d]', rest):
        return None
    return m


def read_lines(name):
    """返回 [[text, pno, y], ...]"""
    with open(os.path.join(OUTDIR, name), encoding='utf-8') as f:
        return json.load(f)


def is_valid_qstart(lines, i, window=25):
    """该行之后、下一个候选题号行之前，必须存在选项行或图片标记
    （用于排除"注：1.xxx 2.xxx"这类材料注释被误判为题号）"""
    for j in range(i + 1, min(i + window, len(lines))):
        t = lines[j][0].strip()
        if match_qstart(t):
            break
        if OPT_LINE.match(t) or t.startswith('[IMG:'):
            return True
    return False


def parse_questions(lines):
    """按题号切分试题，返回 [{num, stem, options, imgs, lineRange}]"""
    questions = []
    cur = None
    for i, (text, pno, y) in enumerate(lines):
        t = text.strip()
        if not t:
            continue
        m = match_qstart(t)
        if m and (cur is None or int(m.group(1)) > cur['num']) and is_valid_qstart(lines, i):
            if cur:
                cur['end_idx'] = i - 1
                questions.append(cur)
            cur = {'num': int(m.group(1)), 'lines': [m.group(2)],
                   'img_lines': [], 'start_idx': i}
            continue
        if cur is None:
            continue
        cur['end_idx'] = i
        if t.startswith('[IMG:'):
            cur['img_lines'].append(t)
        else:
            cur['lines'].append(t)
    if cur:
        questions.append(cur)
    # 解析题干/选项
    for q in questions:
        options = {}
        stem_lines = []
        for line in q['lines']:
            splits = [(m.start(), m.end(), m.group(1)) for m in OPT_A.finditer(line)]
            bm = OPT_B.match(line)
            if bm and not any(s[0] == 0 for s in splits):
                splits.append((0, 1, bm.group(1)))
                splits.sort()
            if splits:
                before = line[:splits[0][0]].strip()
                if before and (options or len(before) < 60):
                    stem_lines.append(before)
                for i2, (pos, cstart, letter) in enumerate(splits):
                    end = splits[i2 + 1][0] if i2 + 1 < len(splits) else len(line)
                    content = line[cstart:end].strip()
                    if letter in options:
                        options[letter] += content
                    else:
                        options[letter] = content
            else:
                stem_lines.append(line)
        q['stem'] = '\n'.join(stem_lines).strip()
        q['options'] = options
        q['stem_imgs'] = q['img_lines']
        del q['lines'], q['img_lines']
    return questions


def parse_answers(lines):
    """解析解析文件，返回 {num: {'answer': 'D', 'explanation': str}}"""
    answers = {}
    cur = None
    for text, pno, y in lines:
        t = text.strip()
        if not t:
            continue
        m = A_START.match(t)
        if m:
            if cur:
                answers[cur['num']] = cur
            tail = re.sub(r'^\s*[。.．]?\s*解\s*析\s*[：:]\s*', '', t[m.end():])
            cur = {'num': int(m.group(1)), 'answer': m.group(2), 'explanation': tail}
            continue
        if cur is None:
            continue
        if t.startswith('[IMG:'):
            cur['explanation'] += '\n' + t
        elif MATERIAL_MARK.match(t):
            continue
        else:
            cur['explanation'] += '\n' + t
    if cur:
        answers[cur['num']] = cur
    return answers


def parse_materials(qlines):
    """资料分析：把材料（含表格/图）关联到该材料下的所有题目"""
    blocks = []
    cur_mat, cur_nums = [], []
    for i, (text, pno, y) in enumerate(qlines):
        t = text.strip()
        if not t:
            continue
        m = match_qstart(t)
        if m and is_valid_qstart(qlines, i):
            cur_nums.append(int(m.group(1)))
            continue
        if MATERIAL_MARK.match(t):
            if cur_mat or cur_nums:
                blocks.append(('\n'.join(cur_mat).strip(), cur_nums))
            cur_mat, cur_nums = [t], []
            continue
        if not cur_nums:
            cur_mat.append(t)
    if cur_mat or cur_nums:
        blocks.append(('\n'.join(cur_mat).strip(), cur_nums))
    return {n: mat for mat, nums in blocks for n in nums}


def render_region(doc, pno, y0, y1, outname, dpi=150):
    """渲染页面指定y范围（整宽）"""
    page = doc[pno]
    w = page.rect.width
    clip = (0, max(0, y0 - 3), w, min(page.rect.height, y1 + 12))
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    pix.save(os.path.join(IMGDIR, outname))
    return f'images/{outname}'


def render_images(all_tags):
    """渲染所有IMG标记为PNG，返回 {tag: 相对路径}"""
    pdfs = {}
    mapping = {}
    for key, tag in all_tags:
        m = re.match(r'IMG:p(\d+)_(\d+)_(\d+)_(\d+)_(\d+)', tag)
        if not m:
            continue
        pno, x0, y0, x1, y1 = map(int, m.groups())
        if key not in pdfs:
            pdfs[key] = pymupdf.open(pdf_path(MODULES[key]['pdf']))
        pix = pdfs[key][pno].get_pixmap(clip=(x0, y0, x1, y1), dpi=150)
        fname = f'{key}_{tag[4:]}.png'
        pix.save(os.path.join(IMGDIR, fname))
        mapping[tag] = f'images/{fname}'
    return mapping, pdfs


def main():
    all_tags = []
    result = {}
    pdfs = {}
    for key, mod in MODULES.items():
        if not all(os.path.exists(os.path.join(OUTDIR, mod[r])) for r in ('q', 'a')):
            print(f'✗ 跳过模块 [{key}]：缺少中间文件（请先跑 extract.py）')
            continue
        qlines = read_lines(mod['q'])
        alines = read_lines(mod['a'])
        questions = parse_questions(qlines)
        answers = parse_answers(alines)
        mats = parse_materials(qlines) if key in MATERIAL_MODULES else {}
        out_q = []
        for q in questions:
            num = q['num']
            ans = answers.get(num, {})
            item = {
                'num': num,
                'stem': q['stem'],
                'options': q['options'],
                'stemImgs': q['stem_imgs'],
                'answer': ans.get('answer', ''),
                'explanation': ans.get('explanation', ''),
            }
            if num in mats:
                item['material'] = mats[num]
            # 选项异常（不足4个或内容为空）：
            # - 有内容图 → 合并该题所有内容图为一张（图形选项题）
            # - 无内容图 → 渲染原卷区域图
            opts_ok = len(q['options']) == 4 and all(
                len(v.strip()) >= 1 for v in q['options'].values())
            if not opts_ok:
                if q['stem_imgs']:
                    boxes = []
                    for tag in q['stem_imgs']:
                        mm = re.search(r'IMG:p(\d+)_(\d+)_(\d+)_(\d+)_(\d+)', tag)
                        if mm:
                            boxes.append(tuple(map(int, mm.groups())))
                    if boxes:
                        pno = boxes[0][0]
                        same = [b for b in boxes if b[0] == pno]
                        x0 = min(b[1] for b in same) - 14   # 左扩：包含选项字母
                        y0 = min(b[2] for b in same)
                        x1 = max(b[3] for b in same) + 6
                        y1 = max(b[4] for b in same)
                        if key not in pdfs:
                            pdfs[key] = pymupdf.open(pdf_path(mod['pdf']))
                        pix = pdfs[key][pno].get_pixmap(clip=(x0, y0, x1, y1), dpi=150)
                        fname = f'{key}_q{num}_merged.png'
                        pix.save(os.path.join(IMGDIR, fname))
                        item['stemImgs'] = [f'[MERGED:{fname}]']
                        item['mergedImg'] = f'images/{fname}'
                elif 'start_idx' in q:
                    if key not in pdfs:
                        pdfs[key] = pymupdf.open(pdf_path(mod['pdf']))
                    s, e = q['start_idx'], q.get('end_idx', q['start_idx'])
                    pno = qlines[s][1]
                    y0 = qlines[s][2]
                    y1 = y0 + 20
                    for j in range(s, min(e + 1, len(qlines))):
                        if qlines[j][1] == pno:
                            y1 = qlines[j][2]
                    item['origImg'] = render_region(pdfs[key], pno, y0, y1,
                                                    f'{key}_q{num}_orig.png')
                for tag in q['stem_imgs']:
                    all_tags.append((key, tag.strip('[]')))
            if ans.get('explanation'):
                for m in re.finditer(r'\[IMG:[^\]]+\]', ans['explanation']):
                    all_tags.append((key, m.group(0)[1:-1]))
            out_q.append(item)
        result[key] = {'name': mod['name'], 'questions': out_q}
        no_ans = [q['num'] for q in out_q if not q['answer']]
        bad_opt = [q['num'] for q in out_q if len(q['options']) != 4]
        print(f"{mod['name']}: {len(out_q)}题" +
              (f', 缺答案{no_ans}' if no_ans else '') +
              (f', 选项≠4: {bad_opt}' if bad_opt else '') +
              f", 原卷图{sum(1 for q in out_q if q.get('origImg'))}题")
    print(f'渲染 {len(all_tags)} 张内容图...')
    mapping, _ = render_images(all_tags)
    with open(os.path.join(OUTDIR, 'img_map.json'), 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUTDIR, 'questions_raw.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('已输出 questions_raw.json / img_map.json')


if __name__ == '__main__':
    main()
