#!/usr/bin/env python3
"""
Linkwarden 标签合并脚本
将旧标签合并到目标标签，更新所有关联的书签，然后删除旧标签。
"""
import os, sys, requests, json
from pathlib import Path

# ── 加载环境变量 ──
env_path = Path(__file__).parent.parent / '.env'
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            k, v = key.strip(), value.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

BASE_URL = os.environ['LINKWARDEN_URL'].rstrip('/')
api_token = os.environ['LINKWARDEN_API_TOKEN']
HEADERS = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}

# ── 合并规则: 旧标签 → 目标标签 ──
MERGE_MAP = {
    # → AI
    'AI 工具': 'AI',
    'HuggingFace': 'AI',
    'LLM': 'AI',
    'LLM工具': 'AI',
    '3D生成': 'AI',
    'Hermes': 'AI',
    # → 工具
    '生产力': '工具',
    '验证码': '工具',
    '临时号码': '工具',
    '地图': '工具',
    '流媒体': '工具',
    '短信': '工具',
    'SKILLS': '工具',
    '浏览器': '工具',
    '浏览器同步': '工具',
    # → Network
    '网络': 'Network',
    # → 开发
    'Python': '开发',
    '前端': '开发',
    '后端': '开发',
    'developer': '开发',
    'API优化': '开发',
    'terminal-ui': '开发',
    'WebUI': '开发',
    # → macOS
    'Mac': 'macOS',
    'Mac 工具': 'macOS',
    # → iOS
    'IPA': 'iOS',
    # → 自托管
    'SelfHost': '自托管',
    # → 设计
    'design-tools': '设计',
    '海报': '设计',
    '字体': '设计',
    # → 阅读
    '小说': '阅读',
    '文学': '阅读',
    '教程': '阅读',
    '社区 / 博客': '阅读',
    # → 知识管理
    '笔记': '知识管理',
}

def api_get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params)
    if r.status_code != 200:
        print(f"API 错误 [{r.status_code}]: {r.text[:200]}", file=sys.stderr)
        return None
    resp = r.json()
    data = resp.get('data', resp.get('response', None))
    return data

def api_put(path, data):
    r = requests.put(f"{BASE_URL}{path}", headers=HEADERS, json=data)
    return r.json().get('response', None) if r.status_code == 200 else None

def api_delete(path):
    r = requests.delete(f"{BASE_URL}{path}", headers=HEADERS)
    return r.status_code in (200, 204)

# ── 主流程 ──
def main():
    dry_run = '--dry-run' in sys.argv

    # 1. 获取所有标签，建立 name→id 映射
    r = requests.get(f"{BASE_URL}/api/v1/tags", headers=HEADERS, params={'take': 200, 'skip': 0})
    if r.status_code != 200:
        print(f"错误：获取标签失败 [{r.status_code}]", file=sys.stderr)
        return 1
    resp = r.json()
    # Linkwarden API returns {data: {tags: [...]}}
    data = resp.get('data', resp.get('response', {}))
    if isinstance(data, dict):
        all_tags = data.get('tags', [])
    elif isinstance(data, list):
        all_tags = data
    else:
        print("错误：无法解析标签响应", file=sys.stderr)
        return 1

    tag_map = {t['name']: t['id'] for t in all_tags}
    print(f"当前标签数: {len(tag_map)}")

    # 检查目标标签是否存在
    targets = set(MERGE_MAP.values())
    for t in targets:
        if t not in tag_map:
            print(f"错误：目标标签 '{t}' 不存在", file=sys.stderr)
            return 1

    # 2. 获取所有书签（分页）
    all_links = []
    skip = 0
    while True:
        links = api_get('/api/v1/links', {'take': 100, 'skip': skip})
        if not links:
            break
        all_links.extend(links)
        if len(links) < 100:
            break
        skip += 100
    print(f"书签总数: {len(all_links)}")

    # 3. 遍历书签，更新需要合并的标签
    updated = 0
    deleted_tags = 0

    for link in all_links:
        link_id = link['id']
        old_tags = [t['name'] for t in link.get('tags', [])]
        if not old_tags:
            continue

        new_tags = set(old_tags)
        changed = False

        for old_name in old_tags:
            if old_name in MERGE_MAP:
                target = MERGE_MAP[old_name]
                new_tags.discard(old_name)
                new_tags.add(target)
                changed = True

        if changed and not dry_run:
            data = {
                'id': link_id,
                'name': link.get('name', ''),
                'url': link.get('url', ''),
                'description': link.get('description', ''),
                'tags': [{'name': t} for t in sorted(new_tags)],
            }
            # 保留原有 collection
            col = link.get('collection')
            if col and col.get('id'):
                data['collection'] = {'id': col['id'], 'ownerId': col.get('ownerId', 1)}

            result = api_put(f'/api/v1/links/{link_id}', data)
            if result:
                updated += 1
                print(f"  ✓ #{link_id} {link.get('name','')[:40]}  [{','.join(old_tags)}] → [{','.join(sorted(new_tags))}]")
            else:
                print(f"  ✗ #{link_id} 更新失败", file=sys.stderr)
        elif changed:
            updated += 1
            print(f"  [DRY] #{link_id} [{','.join(old_tags)}] → [{','.join(sorted(new_tags))}]")

    # 4. 删除已合并的旧标签
    for old_name in MERGE_MAP:
        if old_name in tag_map and old_name not in targets:
            tid = tag_map[old_name]
            if not dry_run:
                ok = api_delete(f'/api/v1/tags/{tid}')
                if ok:
                    deleted_tags += 1
                    print(f"  🗑 删除标签: {old_name} (id={tid})")
                else:
                    print(f"  ✗ 删除标签失败: {old_name}", file=sys.stderr)
            else:
                deleted_tags += 1
                print(f"  [DRY] 🗑 删除标签: {old_name} (id={tid})")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}完成: 更新 {updated} 个书签, 删除 {deleted_tags} 个旧标签")
    return 0

if __name__ == '__main__':
    sys.exit(main())
