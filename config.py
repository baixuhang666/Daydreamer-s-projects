# -*- coding: utf-8 -*-
"""
题库配置 —— 新增题库【只需要改这一个文件】

═══════════════ 新增一个题库的步骤 ═══════════════
1. 把新的「试题PDF」和「解析PDF」放到 PDF_DIR 目录下
2. 在下面的 MODULES 里复制一行，改三处：key、name、两个文件名
3. 把新的 key 加到 MODULE_ORDER（决定首页卡片显示顺序）
4. 双击/运行 run_all.py 重新生成 HTML
   （可选）运行 verify.js 检查题目数、答案、图片是否正常

═══════════════ 新 PDF 需要满足的格式 ═══════════════
· 试题 PDF：题号用「1.」「1、」开头，选项用 A. B. C. D.
· 解析 PDF：每条形如「1.【答案】C。解析：……」
· 若格式不一样，需要改 parse.py 里的 Q_START / A_START 正则

═══════════════ 常见调整 ═══════════════
· 新 PDF 有水印      → 往 WATERMARKS / CELL_WATERMARK_CHARS 里加字
· 新模块有共享材料   → 把 key 加进 MATERIAL_MODULES（如资料分析的一/二/三、大段材料）
· 想改页面标题       → 改 TITLE / H1 / SUB
· 不知道文件名       → 运行 `python config.py` 列出目录下所有 PDF
"""
import os

# ── PDF 所在目录 ──────────────────────────────────────────────
PDF_DIR = r'D:\Users\LENOVO\Desktop\银行\行测'

# ── 模块配置 ──────────────────────────────────────────────────
# key: 英文短名（2~4位，只能用字母），对应生成的中间文件与图片前缀
#   name : 首页显示的模块名
#   q    : 试题 PDF 文件名
#   a    : 解析 PDF 文件名
MODULES = {
    'pd': {
        'name': '判断推理',
        'q': '科技岗6大行行测200题-历3年考试真题-判断推理-试题.pdf',
        'a': '科技岗6大行行测200题-历3年考试真题-判断推理-试题解析.pdf',
    },
    'sl': {
        'name': '数量关系',
        'q': '科技岗6大行行测200题-历3年考试真题-数量关系-试题.pdf',
        'a': '科技岗6大行行测200题-历3年考试真题-数量关系-试题解析.pdf',
    },
    'yy': {
        'name': '言语理解',
        'q': '科技岗6大行行测200题-历3年考试真题-言语理解-试题.pdf',
        'a': '科技岗6大行行测200题-历3年考试真题-言语理解-试题解析.pdf',
    },
    'zl': {
        'name': '资料分析',
        'q': '科技岗6大行行测200题-历3年考试真题-资料分析-试题.pdf',
        'a': '科技岗6大行行测200题-历3年考试真题-资料分析-试题解析.pdf',
    },
    # ── 新增题库示例（取消注释并改成你的文件）────────────────
    # 'cs': {
    #     'name': '常识判断',
    #     'q': '常识判断-试题.pdf',
    #     'a': '常识判断-试题解析.pdf',
    # },
}

# ── 首页模块显示顺序 ──────────────────────────────────────────
MODULE_ORDER = ['pd', 'sl', 'yy', 'zl']

# ── 哪些模块有「共享材料」（一/二/三、 大段材料+表格，多题共用）──
# 一般只有资料分析这类题型需要；没有就留空列表
MATERIAL_MODULES = ['zl']

# ── 水印 / 干扰文字（换 PDF 时按实际情况改，没有就设为空）──────
WATERMARKS = ['职业人小店祝您上岸', '职业人小店', '祝您上岸', '职业人']
# 表格单元格里被拆散的水印单字（如"店1.26""职1681.9"里的前缀）
CELL_WATERMARK_CHARS = '职店小人业'

# ── 输出 ──────────────────────────────────────────────────────
OUT_DIR = r'C:/Users/LENOVO/WorkBuddy/2026-10-05-16-35-35/quiz_app'
OUT_HTML = '银行行测200题刷题.html'   # 生成在 OUT_DIR 的上一级目录
TITLE = '银行行测200题 · 刷题'        # 浏览器标签页标题
H1    = '银行行测 200 题'              # 首页大标题
SUB   = '科技岗六大行 · 近3年真题 · 本地刷题（进度自动保存）'  # 首页副标题


def check_config():
    """检查配置：文件是否存在，返回缺失清单"""
    missing = []
    for k, m in MODULES.items():
        for role in ('q', 'a'):
            p = m[role]
            full = p if os.path.isabs(p) else os.path.join(PDF_DIR, p)
            if not os.path.exists(full):
                missing.append((k, role, p))
    return missing


def list_pdfs():
    """列出 PDF_DIR 下所有 PDF，方便填写配置"""
    print(f'PDF 目录: {PDF_DIR}\n')
    for f in sorted(os.listdir(PDF_DIR)):
        if f.lower().endswith('.pdf'):
            print(' ', f)


if __name__ == '__main__':
    list_pdfs()
    miss = check_config()
    print()
    if miss:
        print('⚠ 以下配置的文件找不到：')
        for k, role, p in miss:
            print(f'   模块 {k} 的 {"试题" if role=="q" else "解析"}: {p}')
    else:
        print('✔ 所有配置的文件都能找到')
