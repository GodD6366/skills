#!/usr/bin/env python3
"""
Linkwarden API 命令行工具
支持链接、集合、标签的增删改查操作
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

# 尝试加载 .env 文件（仅在环境变量未设置时作为默认值）
def load_dotenv():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = value

load_dotenv()

BASE_URL = os.environ.get("LINKWARDEN_BASE_URL", "").rstrip("/")
API_TOKEN = os.environ.get("LINKWARDEN_API_TOKEN", "")

if not BASE_URL:
    print("错误: 未设置 LINKWARDEN_BASE_URL 环境变量", file=sys.stderr)
    sys.exit(1)
if not API_TOKEN:
    print("错误: 未设置 LINKWARDEN_API_TOKEN 环境变量", file=sys.stderr)
    sys.exit(1)

API_BASE = f"{BASE_URL}/api/v1"


def make_request(method: str, path: str, data: dict = None, params: dict = None) -> dict:
    """发送 API 请求"""
    import urllib.request
    import urllib.error
    import urllib.parse

    url = f"{API_BASE}{path}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"API 错误 ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"连接错误: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ==================== Links ====================

def links_list(args):
    """获取链接列表"""
    params = {}
    if args.page:
        params["page"] = args.page
    if args.limit:
        params["limit"] = args.limit
    result = make_request("GET", "/links", params=params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_get(args):
    """获取单个链接"""
    result = make_request("GET", f"/links/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_create(args):
    """创建链接"""
    data = {"url": args.url}
    if args.name:
        data["name"] = args.name
    if args.description:
        data["description"] = args.description
    if args.collection_id:
        data["collection"] = {"id": args.collection_id}
    if args.tags:
        data["tags"] = [{"name": t.strip()} for t in args.tags.split(",")]
    result = make_request("POST", "/links", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_update(args):
    """更新链接"""
    data = {}
    if args.name:
        data["name"] = args.name
    if args.description:
        data["description"] = args.description
    if args.collection_id:
        data["collection"] = {"id": args.collection_id}
    if args.tags:
        data["tags"] = [{"name": t.strip()} for t in args.tags.split(",")]
    result = make_request("PUT", f"/links/{args.id}", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_delete(args):
    """删除链接"""
    result = make_request("DELETE", f"/links/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_search(args):
    """搜索链接"""
    params = {"q": args.query}
    if args.collection_id:
        params["collectionId"] = args.collection_id
    if args.tag:
        params["tag"] = args.tag
    result = make_request("GET", "/search", params=params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def links_archive(args):
    """归档链接"""
    result = make_request("POST", f"/links/{args.id}/archive")
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ==================== Collections ====================

def collections_list(args):
    """获取所有集合"""
    result = make_request("GET", "/collections")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def collections_get(args):
    """获取单个集合"""
    result = make_request("GET", f"/collections/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def collections_create(args):
    """创建集合"""
    data = {"name": args.name}
    if args.description:
        data["description"] = args.description
    result = make_request("POST", "/collections", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def collections_update(args):
    """更新集合"""
    data = {}
    if args.name:
        data["name"] = args.name
    if args.description:
        data["description"] = args.description
    result = make_request("PUT", f"/collections/{args.id}", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def collections_delete(args):
    """删除集合"""
    result = make_request("DELETE", f"/collections/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ==================== Tags ====================

def tags_list(args):
    """获取标签列表"""
    params = {}
    if args.page:
        params["page"] = args.page
    if args.limit:
        params["limit"] = args.limit
    result = make_request("GET", "/tags", params=params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def tags_get(args):
    """获取单个标签"""
    result = make_request("GET", f"/tags/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def tags_create(args):
    """批量创建标签"""
    data = [{"name": t.strip()} for t in args.names.split(",")]
    result = make_request("POST", "/tags", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def tags_update(args):
    """更新标签"""
    data = {"name": args.name}
    result = make_request("PUT", f"/tags/{args.id}", data=data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def tags_delete(args):
    """删除标签"""
    result = make_request("DELETE", f"/tags/{args.id}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ==================== Dashboard ====================

def dashboard_get(args):
    """获取仪表板数据"""
    result = make_request("GET", "/dashboard")
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ==================== Config ====================

def config_get(args):
    """获取运行时配置"""
    result = make_request("GET", "/config")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Linkwarden API 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取链接列表
  %(prog)s links list

  # 创建链接
  %(prog)s links create --url https://example.com --name "示例" --tags "技术,教程"

  # 搜索链接
  %(prog)s links search --query "关键词"

  # 获取所有集合
  %(prog)s collections list

  # 创建集合
  %(prog)s collections create --name "我的收藏"

  # 获取标签列表
  %(prog)s tags list
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ===== Links =====
    links_parser = subparsers.add_parser("links", help="链接管理")
    links_sub = links_parser.add_subparsers(dest="action")

    # links list
    p = links_sub.add_parser("list", help="获取链接列表")
    p.add_argument("--page", type=int, help="页码")
    p.add_argument("--limit", type=int, help="每页数量")
    p.set_defaults(func=links_list)

    # links get
    p = links_sub.add_parser("get", help="获取单个链接")
    p.add_argument("id", help="链接 ID")
    p.set_defaults(func=links_get)

    # links create
    p = links_sub.add_parser("create", help="创建链接")
    p.add_argument("--url", required=True, help="链接 URL")
    p.add_argument("--name", help="链接名称")
    p.add_argument("--description", help="链接描述")
    p.add_argument("--collection-id", type=int, help="集合 ID")
    p.add_argument("--tags", help="标签（逗号分隔）")
    p.set_defaults(func=links_create)

    # links update
    p = links_sub.add_parser("update", help="更新链接")
    p.add_argument("id", help="链接 ID")
    p.add_argument("--name", help="链接名称")
    p.add_argument("--description", help="链接描述")
    p.add_argument("--collection-id", type=int, help="集合 ID")
    p.add_argument("--tags", help="标签（逗号分隔）")
    p.set_defaults(func=links_update)

    # links delete
    p = links_sub.add_parser("delete", help="删除链接")
    p.add_argument("id", help="链接 ID")
    p.set_defaults(func=links_delete)

    # links search
    p = links_sub.add_parser("search", help="搜索链接")
    p.add_argument("--query", required=True, help="搜索关键词")
    p.add_argument("--collection-id", type=int, help="限定集合 ID")
    p.add_argument("--tag", help="限定标签")
    p.set_defaults(func=links_search)

    # links archive
    p = links_sub.add_parser("archive", help="归档链接")
    p.add_argument("id", help="链接 ID")
    p.set_defaults(func=links_archive)

    # ===== Collections =====
    collections_parser = subparsers.add_parser("collections", help="集合管理")
    collections_sub = collections_parser.add_subparsers(dest="action")

    # collections list
    p = collections_sub.add_parser("list", help="获取所有集合")
    p.set_defaults(func=collections_list)

    # collections get
    p = collections_sub.add_parser("get", help="获取单个集合")
    p.add_argument("id", help="集合 ID")
    p.set_defaults(func=collections_get)

    # collections create
    p = collections_sub.add_parser("create", help="创建集合")
    p.add_argument("--name", required=True, help="集合名称")
    p.add_argument("--description", help="集合描述")
    p.set_defaults(func=collections_create)

    # collections update
    p = collections_sub.add_parser("update", help="更新集合")
    p.add_argument("id", help="集合 ID")
    p.add_argument("--name", help="集合名称")
    p.add_argument("--description", help="集合描述")
    p.set_defaults(func=collections_update)

    # collections delete
    p = collections_sub.add_parser("delete", help="删除集合")
    p.add_argument("id", help="集合 ID")
    p.set_defaults(func=collections_delete)

    # ===== Tags =====
    tags_parser = subparsers.add_parser("tags", help="标签管理")
    tags_sub = tags_parser.add_subparsers(dest="action")

    # tags list
    p = tags_sub.add_parser("list", help="获取标签列表")
    p.add_argument("--page", type=int, help="页码")
    p.add_argument("--limit", type=int, help="每页数量")
    p.set_defaults(func=tags_list)

    # tags get
    p = tags_sub.add_parser("get", help="获取单个标签")
    p.add_argument("id", help="标签 ID")
    p.set_defaults(func=tags_get)

    # tags create
    p = tags_sub.add_parser("create", help="批量创建标签")
    p.add_argument("--names", required=True, help="标签名称（逗号分隔）")
    p.set_defaults(func=tags_create)

    # tags update
    p = tags_sub.add_parser("update", help="更新标签")
    p.add_argument("id", help="标签 ID")
    p.add_argument("--name", required=True, help="新标签名称")
    p.set_defaults(func=tags_update)

    # tags delete
    p = tags_sub.add_parser("delete", help="删除标签")
    p.add_argument("id", help="标签 ID")
    p.set_defaults(func=tags_delete)

    # ===== Dashboard =====
    dashboard_parser = subparsers.add_parser("dashboard", help="仪表板")
    dashboard_sub = dashboard_parser.add_subparsers(dest="action")

    p = dashboard_sub.add_parser("get", help="获取仪表板数据")
    p.set_defaults(func=dashboard_get)

    # ===== Config =====
    config_parser = subparsers.add_parser("config", help="配置")
    config_sub = config_parser.add_subparsers(dest="action")

    p = config_sub.add_parser("get", help="获取运行时配置")
    p.set_defaults(func=config_get)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    else:
        # 如果只指定了命令没有指定 action，打印子命令帮助
        if args.command == "links":
            links_parser.print_help()
        elif args.command == "collections":
            collections_parser.print_help()
        elif args.command == "tags":
            tags_parser.print_help()
        elif args.command == "dashboard":
            dashboard_parser.print_help()
        elif args.command == "config":
            config_parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
