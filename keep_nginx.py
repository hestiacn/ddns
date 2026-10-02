#!/usr/bin/env python3
"""
从本地 _worker.js 提取 nginx()，用上游覆盖 _worker.js 后，再把本地 nginx() 替换回去。
"""

import re
import sys
import pathlib

WORKER = pathlib.Path('_worker.js')
LOCAL_NGINX = pathlib.Path('/tmp/local_nginx.txt')


def extract_nginx(text: str):
    """提取 async function nginx() { ... } 整段，正确处理嵌套 {} 和模板字符串。"""
    m = re.search(r'async\s+function\s+nginx\s*\(\s*\)\s*', text)
    if not m:
        return None

    start = m.start()
    i = text.index('{', m.end() - 1)

    depth = 0
    in_string = None
    escape = False

    j = i
    while j < len(text):
        c = text[j]
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
                    return text[start:j + 1]
        j += 1
    return None


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

    upstream_nginx = extract_nginx(upstream)
    if not upstream_nginx:
        print('[WARN] 上游 _worker.js 未找到 nginx()，跳过替换')
        return 0

    upstream = upstream.replace(upstream_nginx, local_nginx, 1)
    WORKER.write_text(upstream, encoding='utf-8')
    print('[INFO] 已用本地 nginx() 替换上游 nginx()')
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
