#!/usr/bin/env python3
"""
从本地 _worker.js 提取 nginx()，用上游覆盖 _worker.js 后，再把本地 nginx() 替换回去。

提取/替换逻辑：
- 定位 `async function nginx()` 的起始位置；
- 用花括号配对找到函数体的结束位置（正确处理字符串、模板字符串、转义）；
- 整体替换，不依赖行号或固定内容。
"""

import re
import sys
import pathlib

WORKER = pathlib.Path('_worker.js')
LOCAL_NGINX = pathlib.Path('/tmp/local_nginx.txt')

# 匹配 async function nginx() 的函数声明开头
NGINX_DECL_RE = re.compile(r'async\s+function\s+nginx\s*\(\s*\)\s*')


def find_function_span(text: str):
    """
    返回 (start, end)：
      - start 是 `async` 关键字的起始索引；
      - end 是函数体右花括号 `}` 之后的位置（不含）。
    找不到返回 None。
    """
    m = NGINX_DECL_RE.search(text)
    if not m:
        return None

    # 找函数体的左花括号
    brace_start = text.find('{', m.end())
    if brace_start == -1:
        return None

    depth = 0
    in_string = None
    escape = False
    i = brace_start

    while i < len(text):
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == in_string:
                in_string = None
        else:
            if c in ('"', "'", '`'):
                in_string = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return m.start(), i + 1
        i += 1

    return None


def extract_nginx(text: str):
    span = find_function_span(text)
    if not span:
        return None
    start, end = span
    return text[start:end]


def cmd_extract():
    if not WORKER.exists():
        print('[WARN] 本地没有 _worker.js，跳过提取')
        return 0

    local = WORKER.read_text(encoding='utf-8')
    fn = extract_nginx(local)
    if not fn:
        print('[WARN] 本地 _worker.js 未找到 nginx()，跳过替换')
        return 0

    LOCAL_NGINX.write_text(fn, encoding='utf-8')
    print(f'[INFO] 已提取本地 nginx()，长度 {len(fn)}')
    return 0


def cmd_replace():
    if not LOCAL_NGINX.exists():
        print('[WARN] 没有本地 nginx() 备份，跳过替换')
        return 0

    local_nginx = LOCAL_NGINX.read_text(encoding='utf-8')
    upstream = WORKER.read_text(encoding='utf-8')

    span = find_function_span(upstream)
    if not span:
        print('[WARN] 上游 _worker.js 未找到 nginx()，跳过替换')
        return 0

    start, end = span
    new_content = upstream[:start] + local_nginx + upstream[end:]
    WORKER.write_text(new_content, encoding='utf-8')
    print('[INFO] 已用本地 nginx() 整体替换上游 nginx()')
    return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('extract', 'replace'):
        print('Usage: keep_nginx.py {extract|replace}')
        return 2

    if sys.argv[1] == 'extract':
        return cmd_extract()
    return cmd_replace()


if __name__ == '__main__':
    sys.exit(main())
