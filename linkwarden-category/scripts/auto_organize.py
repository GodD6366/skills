#!/usr/bin/env python3
"""
Linkwarden 书签自动分类脚本（LLM 驱动版）
脚本只提供数据查询和操作接口，分类决策由 LLM 完成。
"""

import json
import os
import sys
import argparse
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ── 环境变量加载 ──────────────────────────────────────────────

def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value

load_env()

TOKEN = os.environ.get('LINKWARDEN_API_TOKEN', '')
BASE_URL = os.environ.get('LINKWARDEN_URL', '').rstrip('/')

if not TOKEN or not BASE_URL:
    print("错误：请设置环境变量 LINKWARDEN_URL 和 LINKWARDEN_API_TOKEN", file=sys.stderr)
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def api_request(method, path, data=None, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"

    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')

    request = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode('utf-8')
            if not raw:
                return None
            payload = json.loads(raw)
            return payload.get('data', payload.get('response', payload))
    except urllib.error.HTTPError as error:
        text = error.read().decode('utf-8', errors='replace') if error.fp else str(error)
        print(f"API 错误 [{error.code}]: {text[:200]}", file=sys.stderr)
    except Exception as error:
        print(f"API 错误: {error}", file=sys.stderr)
    return None



# ── 默认初始化结构 ────────────────────────────────────────────

DEFAULT_COLLECTIONS = [
    ("AI", "人工智能、大模型、机器学习"),
    ("编程", "编程语言、开发框架、代码"),
    ("自托管", "Docker、NAS、Homelab、服务器"),
    ("折腾", "硬件改装、刷机、DIY"),
    ("工具", "软件、App、效率工具"),
    ("网络", "网络技术、VPN、代理、DNS"),
    ("阅读", "博客、文章、随笔、笔记"),
    ("其他", "无法归类的书签"),
]

DEFAULT_TAGS = [
    "AI", "Android", "Docker", "Linux", "Python",
    "Network", "安全", "开源", "前端", "后端", "教程", "工具",
]

UNORGANIZED_ID = 1

# ── API 工具函数 ──────────────────────────────────────────────

def api_get(path, params=None):
    return api_request('GET', path, params=params)

def api_post(path, data):
    return api_request('POST', path, data=data)

def api_put(path, data):
    return api_request('PUT', path, data=data)

# ── 子命令实现 ────────────────────────────────────────────────

def cmd_init(args):
    """初始化默认收藏夹和标签结构"""
    collections = api_get("/api/v1/collections") or []
    existing_cols = {c['name']: c['id'] for c in collections}

    created_cols = []
    for name, desc in DEFAULT_COLLECTIONS:
        if name not in existing_cols:
            result = api_post("/api/v1/collections", {
                'name': name, 'description': desc, 'color': '#0ea5e9'
            })
            if result and 'id' in result:
                created_cols.append(f"  + {name} (id={result['id']})")

    existing_tags_raw = api_get("/api/v1/tags") or []
    existing_tags = {t['name'].lower() for t in existing_tags_raw}

    created_tags = []
    for tag in DEFAULT_TAGS:
        if tag.lower() not in existing_tags:
            result = api_post("/api/v1/tags", [{'name': tag}])
            if result:
                created_tags.append(f"  + {tag}")

    print("初始化完成")
    if created_cols:
        print(f"创建收藏夹 ({len(created_cols)}):")
        print('\n'.join(created_cols))
    else:
        print("收藏夹：无需创建")
    if created_tags:
        print(f"创建标签 ({len(created_tags)}):")
        print('\n'.join(created_tags))
    else:
        print("标签：无需创建")

    # 输出完整结构供 LLM 参考
    all_cols = api_get("/api/v1/collections") or []
    print("\n当前所有收藏夹:")
    for c in all_cols:
        print(f"  id={c['id']}  {c['name']}")

    all_tags = api_get("/api/v1/tags") or []
    print("\n当前所有标签:")
    for t in all_tags:
        print(f"  id={t['id']}  {t['name']}")

    print("\nRESULT: INIT_DONE")


def cmd_list(args):
    """列出未分类书签（JSON 输出，供 LLM 消费）"""
    limit = args.limit or 50
    links = api_get("/api/v1/links", {'collectionId': UNORGANIZED_ID, 'take': limit}) or []

    if not links:
        print(json.dumps({"count": 0, "links": []}, ensure_ascii=False))
        return

    result = []
    for link in links:
        result.append({
            "id": link['id'],
            "name": link.get('name', ''),
            "url": link.get('url', ''),
            "description": link.get('description', ''),
            "textContent": (link.get('textContent') or '')[:500],
            "tags": [t.get('name', '') for t in link.get('tags', [])],
        })

    print(json.dumps({"count": len(result), "links": result}, ensure_ascii=False, indent=2))


def cmd_list_collections(args):
    """列出所有收藏夹"""
    collections = api_get("/api/v1/collections") or []
    for c in collections:
        print(json.dumps({"id": c['id'], "name": c['name']}, ensure_ascii=False))


def cmd_list_tags(args):
    """列出所有标签"""
    result = api_get("/api/v1/tags", {'take': 200})
    tags = result.get('tags', result) if isinstance(result, dict) else (result or [])
    for t in tags:
        print(json.dumps({"id": t['id'], "name": t['name']}, ensure_ascii=False))


def cmd_update(args):
    """更新书签的标题、摘要、收藏夹和标签"""
    link = api_get(f"/api/v1/links/{args.link_id}")
    if not link:
        print(f"书签 {args.link_id} 不存在", file=sys.stderr)
        return

    data = {
        "id": args.link_id,
        "name": args.name if args.name is not None else link.get("name", ""),
        "url": link.get("url", ""),
        "description": args.description if args.description is not None else link.get("description", ""),
        "collection": (
            {"id": args.collection_id, "ownerId": 1}
            if args.collection_id is not None
            else link.get("collection")
        ),
    }

    if args.tags is not None:
        tag_names = [t.strip() for t in args.tags.split(',') if t.strip()]
        data["tags"] = [{"name": t} for t in tag_names]
    else:
        data["tags"] = [{"name": t.get('name', '')} for t in link.get('tags', [])]

    result = api_put(f"/api/v1/links/{args.link_id}", data)
    if result is not None:
        print(json.dumps({"ok": True, "link_id": args.link_id}, ensure_ascii=False))
    else:
        print(json.dumps({"ok": False, "link_id": args.link_id, "error": "update failed"}, ensure_ascii=False))


def cmd_summary(args):
    """输出分类状态摘要"""
    collections = api_get("/api/v1/collections") or []
    unorganized = api_get("/api/v1/links", {'collectionId': UNORGANIZED_ID, 'take': 100}) or []

    print(f"未分类书签: {len(unorganized)} 个")
    print(f"收藏夹数量: {len(collections)} 个")
    for c in collections:
        links = api_get("/api/v1/links", {'collectionId': c['id'], 'take': 1}) or []
        # 用列表接口获取总数不太精确，只显示是否有内容
        marker = "✓" if links else "·"
        print(f"  {marker} {c['name']} (id={c['id']})")

    print("\nRESULT: SUMMARY")


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Linkwarden 书签分类工具（LLM 驱动）')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('init', help='初始化默认收藏夹和标签')

    p_list = sub.add_parser('list', help='列出未分类书签（JSON）')
    p_list.add_argument('--limit', type=int, default=50)

    sub.add_parser('list-collections', help='列出所有收藏夹')
    sub.add_parser('list-tags', help='列出所有标签')
    sub.add_parser('summary', help='分类状态摘要')

    p_update = sub.add_parser('update', help='更新书签标题、摘要和分类')
    p_update.add_argument('link_id', type=int)
    p_update.add_argument('--collection-id', type=int, required=False, default=None, help='收藏夹 ID；省略则保持原收藏夹')
    p_update.add_argument('--tags', type=str, default=None, help='逗号分隔的标签列表')
    p_update.add_argument('--name', type=str, default=None, help='提炼后的标题')
    p_update.add_argument('--description', type=str, default=None, help='一句话中文摘要')

    args = parser.parse_args()

    cmd_map = {
        'init': cmd_init,
        'list': cmd_list,
        'list-collections': cmd_list_collections,
        'list-tags': cmd_list_tags,
        'update': cmd_update,
        'summary': cmd_summary,
    }
    cmd_map[args.command](args)


if __name__ == '__main__':
    main()
