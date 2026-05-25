#!/usr/bin/env python3
"""
Linkwarden 书签自动分类脚本
每天凌晨3点自动将未分类书签进行分类
"""

import requests
import json
import re
import os
from datetime import datetime
from pathlib import Path

# 配置 - 从环境变量或 .env 文件读取
def load_env():
    """加载 .env 文件（如果存在）"""
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
    print("错误：请设置环境变量 LINKWARDEN_URL 和 LINKWARDEN_API_TOKEN")
    print("或在当前 skill 目录下创建 .env 文件：")
    print('LINKWARDEN_URL=https://your-instance.example.com')
    print('LINKWARDEN_API_TOKEN=your_token_here')
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 收藏夹映射 (关键词 -> 收藏夹ID)
# 优先级：关键词越具体越靠前
COLLECTION_KEYWORDS = {
    6: ['ai', '人工智能', 'machine learning', 'ml', 'deep learning', 'gpt', 'llm', 'openai', 'anthropic', 'claude', 'chatgpt', '大模型', '神经网络', 'transformer', '量化', 'quant', 'quantaxis', 'backtrader'],
    4: ['编程', 'programming', 'code', 'python', 'javascript', 'typescript', 'rust', 'go', 'java', 'react', 'vue', 'node', 'css', 'html', '前端', '后端', 'api', '框架', 'sdk', 'git', 'github', '开发', 'webpack', 'vite', 'npm', '教程', 'guide', 'docs', 'documentation', '源码', '源码解析'],
    9: ['selfhost', 'self-host', '自托管', 'docker', 'kubernetes', 'k8s', '容器', 'container', '部署', 'deploy', 'server', '服务器', 'linux', 'ubuntu', 'debian', 'centos', 'pve', 'proxmox', 'esxi', 'nas', 'synology', 'unraid', 'homelab', 'nas教程'],
    3: ['折腾', 'homelab', 'diy', '改装', '黑群晖', '虚拟机', 'lxc', '刷机', 'openwrt', '树莓派', 'raspberry', '软路由', '路由器'],
    7: ['软件', 'app', 'application', '工具', 'tool', '下载', 'download', 'apk', 'mac', 'windows', 'ios', 'android', 'chrome', '扩展', '插件', 'extension', 'vps', '云服务', 'cloud', '浏览器', 'webapp', '客户端'],
    1: ['网络', 'network', 'dns', 'proxy', 'vpn', 'tcp', 'udp', 'http', 'cdn', '路由', 'router', 'frp', 'clash', 'wireguard', 'zerotier', 'nginx', 'ssl', '证书', 'ip', '内网穿透', '代理', '抓包'],
    2: ['博客', 'blog', '文章', '随笔', '思考', '观点', '评论', '豆瓣', 'douban', '知乎', 'zhihu', '微博', 'weibo', 'newsletter', '笔记', 'notes'],
}

# 标签关键词映射
TAG_KEYWORDS = {
    'Network': ['网络', 'network', 'dns', 'proxy', 'vpn', 'tcp', 'udp', 'http', 'cdn'],
    'AI': ['ai', '人工智能', 'machine learning', 'ml', 'gpt', 'llm', '大模型'],
    'Android': ['android', 'apk', '安卓'],
    'Docker': ['docker', 'container', '容器', 'kubernetes', 'k8s'],
    'Linux': ['linux', 'ubuntu', 'debian', 'centos', 'shell', 'bash'],
    '开源': ['开源', 'open source', 'github', 'opensource', 'oss'],
    '安全': ['安全', 'security', '加密', 'encrypt', 'password', '密码', 'vpn', 'firewall'],
    '前端': ['前端', 'frontend', 'javascript', 'typescript', 'react', 'vue', 'css', 'html'],
    '后端': ['后端', 'backend', 'api', 'server', 'database', '数据库'],
    'Python': ['python', 'pip', 'django', 'flask', 'fastapi'],
    '教程': ['教程', 'tutorial', '指南', 'guide', '入门', '学习', 'learn'],
    '工具': ['工具', 'tool', 'utility', '效率'],
}

# 未分类收藏夹ID
UNORGANIZED_ID = 1
# 其他收藏夹ID（无法匹配时使用）
OTHER_COLLECTION_NAME = "其他"


def get_all_collections():
    """获取所有收藏夹"""
    r = requests.get(f"{BASE_URL}/api/v1/collections", headers=HEADERS)
    if r.status_code == 200:
        return r.json().get('response', [])
    return []


def get_all_tags():
    """获取所有标签"""
    r = requests.get(f"{BASE_URL}/api/v1/tags", headers=HEADERS)
    if r.status_code == 200:
        return r.json().get('response', [])
    return []


def get_unorganized_links(limit=50):
    """获取未分类书签"""
    params = {'collectionId': UNORGANIZED_ID, 'take': limit}
    r = requests.get(f"{BASE_URL}/api/v1/links", headers=HEADERS, params=params)
    if r.status_code == 200:
        return r.json().get('response', [])
    return []


def create_collection(name, description=''):
    """创建收藏夹"""
    data = {'name': name, 'description': description, 'color': '#0ea5e9'}
    r = requests.post(f"{BASE_URL}/api/v1/collections", headers=HEADERS, json=data)
    if r.status_code == 200:
        return r.json().get('response', {}).get('id')
    return None


def analyze_content(link):
    """分析书签内容，返回匹配的收藏夹ID和标签列表"""
    # 合并可分析的文本
    text_parts = [
        link.get('name', ''),
        link.get('description', ''),
        link.get('url', ''),
        link.get('textContent', '') or ''
    ]
    text = ' '.join(text_parts).lower()

    # 匹配收藏夹
    best_collection = None
    best_score = 0

    for col_id, keywords in COLLECTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_collection = col_id

    # 匹配标签（最多3个）
    matched_tags = []
    for tag_name, keywords in TAG_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            matched_tags.append(tag_name)
            if len(matched_tags) >= 3:
                break

    return best_collection, matched_tags


def update_link(link_id, collection_id, tags):
    """更新书签的收藏夹和标签"""
    # 先获取现有书签信息
    r = requests.get(f"{BASE_URL}/api/v1/links/{link_id}", headers=HEADERS)
    if r.status_code != 200:
        return False, "获取书签失败"

    link = r.json().get('response', {})

    data = {
        "id": link_id,
        "name": link.get("name", ""),
        "url": link.get("url", ""),
        "description": link.get("description", ""),
        "collection": {
            "id": collection_id,
            "ownerId": 1
        },
        "tags": [{"name": tag} for tag in tags]
    }

    r = requests.put(f"{BASE_URL}/api/v1/links/{link_id}", headers=HEADERS, json=data)
    if r.status_code == 200:
        return True, "成功"
    return False, r.text[:100]


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始自动分类书签...")

    # 获取现有收藏夹
    collections = get_all_collections()
    collection_map = {c['id']: c['name'] for c in collections}

    # 检查是否有"其他"收藏夹，没有则创建
    other_id = None
    for c in collections:
        if c['name'] == OTHER_COLLECTION_NAME:
            other_id = c['id']
            break

    if not other_id:
        print(f"创建 '{OTHER_COLLECTION_NAME}' 收藏夹...")
        other_id = create_collection(OTHER_COLLECTION_NAME, "无法自动分类的书签")
        if not other_id:
            print("创建收藏夹失败，使用未分类收藏夹")
            other_id = UNORGANIZED_ID

    # 获取现有标签
    existing_tags = get_all_tags()
    existing_tag_names = {t['name'].lower(): t['name'] for t in existing_tags}

    # 获取未分类书签
    links = get_unorganized_links()
    print(f"找到 {len(links)} 个未分类书签")

    if not links:
        print("没有需要分类的书签")
        print("RESULT: NO_CHANGES")
        return

    success_count = 0
    for link in links:
        link_id = link['id']
        link_name = link.get('name', '无标题')[:50]

        # 分析内容
        target_collection, suggested_tags = analyze_content(link)

        # 如果没有匹配到收藏夹，使用"其他"
        if not target_collection:
            target_collection = other_id

        # 标签名称标准化（复用现有标签）
        final_tags = []
        for tag in suggested_tags:
            tag_lower = tag.lower()
            if tag_lower in existing_tag_names:
                final_tags.append(existing_tag_names[tag_lower])
            else:
                final_tags.append(tag)

        # 更新书签
        ok, msg = update_link(link_id, target_collection, final_tags)
        if ok:
            success_count += 1
            col_name = collection_map.get(target_collection, str(target_collection))
            tags_str = ', '.join(final_tags) if final_tags else '无'
            print(f"✅ [{link_name}] -> {col_name} | 标签: {tags_str}")
        else:
            print(f"❌ [{link_name}]: {msg}")

    print(f"\n完成: {success_count}/{len(links)} 个书签已分类")
    if success_count > 0:
        print(f"RESULT: CHANGED {success_count}")
    else:
        print("RESULT: NO_CHANGES")


if __name__ == '__main__':
    main()
