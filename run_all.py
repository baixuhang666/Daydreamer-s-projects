# -*- coding: utf-8 -*-
"""
一键重建题库 —— 新增/更换 PDF 后，只改 config.py，然后运行本脚本

    python run_all.py

流程：config 检查 → extract.py（PDF转文本）→ parse.py（结构化+渲染图片）
      → build_html.py（打包成单文件HTML）

可选参数：
    python run_all.py --no-clean   不清除旧图片（保留已有图片，增量渲染）
"""
import os
import sys
import shutil
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import config
from config import OUT_DIR, OUT_HTML, MODULES, MODULE_ORDER

PY = sys.executable
IMGDIR = os.path.join(OUT_DIR, 'images')


def step(title):
    print('\n' + '=' * 58)
    print(' ' + title)
    print('=' * 58)


def run(script):
    r = subprocess.run([PY, os.path.join(HERE, script)], cwd=HERE)
    if r.returncode != 0:
        print(f'\n✗ {script} 执行失败（退出码 {r.returncode}），流程中止')
        sys.exit(r.returncode)


def main():
    t0 = time.time()

    step('0/3 检查配置')
    miss = config.check_config()
    if miss:
        print('✗ 以下文件找不到，请检查 config.py 的 PDF_DIR 和文件名：')
        for k, role, p in miss:
            print(f'   模块 [{k}] 的 {"试题" if role == "q" else "解析"}PDF: {p}')
        print('\n提示：运行 `python config.py` 可列出目录下的所有 PDF')
        sys.exit(1)
    print('✔ 配置检查通过，模块：')
    for k in MODULE_ORDER:
        if k in MODULES:
            print(f'   - {k}: {MODULES[k]["name"]}')

    if '--no-clean' not in sys.argv and os.path.isdir(IMGDIR):
        step('0.5/3 清除旧图片')
        shutil.rmtree(IMGDIR)
        print(f'✔ 已清空 {IMGDIR}')
    os.makedirs(IMGDIR, exist_ok=True)

    step('1/3 提取 PDF 文本（extract.py）')
    run('extract.py')

    step('2/3 解析题目并渲染图片（parse.py）')
    run('parse.py')

    step('3/3 生成单文件 HTML（build_html.py）')
    run('build_html.py')

    out = os.path.join(os.path.dirname(OUT_DIR), OUT_HTML)
    print('\n' + '=' * 58)
    print(f'✔ 全部完成，用时 {time.time() - t0:.1f}s')
    print(f'  输出文件：{out}')
    if os.path.exists(out):
        print(f'  文件大小：{os.path.getsize(out) // 1024} KB')
    print('  双击该文件即可用浏览器打开刷题')
    print('=' * 58)


if __name__ == '__main__':
    main()
