#!/usr/bin/env python3
"""
Figma 资源批量下载和裁剪脚本
使用 Figma API 下载设计稿中的所有图层并导出为图片
"""

import os
import requests
import json
from pathlib import Path

# Figma API 配置（敏感信息请用环境变量 FIGMA_ACCESS_TOKEN、FIGMA_FILE_KEY）
FIGMA_TOKEN = os.environ.get("FIGMA_ACCESS_TOKEN", "")
FILE_KEY = os.environ.get("FIGMA_FILE_KEY", "5nY83QTlPDrMkzG7hxQYXQ")
BASE_URL = "https://api.figma.com/v1"

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "static" / "images" / "figma_export"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API Headers
headers = {
    "X-Figma-Token": FIGMA_TOKEN
}


def get_file_info():
    """获取 Figma 文件信息"""
    url = f"{BASE_URL}/files/{FILE_KEY}"
    print(f"正在获取文件信息: {url}")
    print("这可能需要一些时间...")
    
    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code != 200:
        print(f"❌ 获取文件信息失败: {response.status_code}")
        print(f"响应: {response.text}")
        return None
    
    print("正在解析 JSON...")
    data = response.json()
    print(f"✅ 文件名: {data['name']}")
    print(f"✅ 最后修改: {data['lastModified']}")
    
    # 保存文件结构
    print("正在保存文件结构...")
    with open(OUTPUT_DIR / "file_structure.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 文件结构已保存到: {OUTPUT_DIR / 'file_structure.json'}")
    
    return data


def find_exportable_nodes(document, parent_name=""):
    """递归查找所有可导出的节点"""
    nodes = []
    
    if not isinstance(document, dict):
        return nodes
    
    node_type = document.get("type", "")
    node_name = document.get("name", "")
    node_id = document.get("id", "")
    
    full_name = f"{parent_name}/{node_name}" if parent_name else node_name
    
    # 检查是否有导出设置
    export_settings = document.get("exportSettings", [])
    
    # 我们关心的节点类型
    interesting_types = [
        "COMPONENT",
        "INSTANCE",
        "FRAME",
        "GROUP",
        "VECTOR",
        "RECTANGLE",
        "ELLIPSE",
        "TEXT"
    ]
    
    if node_type in interesting_types:
        nodes.append({
            "id": node_id,
            "name": node_name,
            "full_name": full_name,
            "type": node_type,
            "has_export": len(export_settings) > 0
        })
    
    # 递归处理子节点
    children = document.get("children", [])
    for child in children:
        nodes.extend(find_exportable_nodes(child, full_name))
    
    return nodes


def export_images(node_ids, scale=2, format="png"):
    """批量导出图片"""
    if not node_ids:
        print("⚠️ 没有要导出的节点")
        return {}
    
    # Figma API 限制每次最多导出 100 个节点
    batch_size = 100
    all_images = {}
    
    for i in range(0, len(node_ids), batch_size):
        batch = node_ids[i:i+batch_size]
        ids_param = ",".join(batch)
        
        url = f"{BASE_URL}/images/{FILE_KEY}"
        params = {
            "ids": ids_param,
            "scale": scale,
            "format": format
        }
        
        print(f"正在导出第 {i//batch_size + 1} 批 ({len(batch)} 个节点)...")
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"❌ 导出失败: {response.status_code}")
            print(f"响应: {response.text}")
            continue
        
        data = response.json()
        images = data.get("images", {})
        all_images.update(images)
        
        print(f"✅ 成功获取 {len(images)} 个图片 URL")
    
    return all_images


def download_image(url, filepath):
    """下载单个图片"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"❌ 下载失败 ({response.status_code}): {filepath}")
            return False
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return False


def sanitize_filename(name):
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        name = name.replace(char, "_")
    
    # 移除前后空格
    name = name.strip()
    
    # 限制长度
    if len(name) > 200:
        name = name[:200]
    
    return name


def main():
    print("=" * 60)
    print("Figma 资源批量下载工具")
    print("=" * 60)
    
    # 1. 获取文件信息
    print("\n[1/4] 获取文件信息...")
    file_data = get_file_info()
    if not file_data:
        return
    
    # 2. 查找所有可导出的节点
    print("\n[2/4] 查找可导出节点...")
    document = file_data.get("document", {})
    nodes = find_exportable_nodes(document)
    
    print(f"✅ 找到 {len(nodes)} 个节点")
    
    # 保存节点列表
    with open(OUTPUT_DIR / "nodes_list.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 节点列表已保存到: {OUTPUT_DIR / 'nodes_list.json'}")
    
    # 3. 选择要导出的节点
    print("\n[3/4] 准备导出图片...")
    
    # 优先导出 COMPONENT 和 FRAME
    priority_nodes = [n for n in nodes if n["type"] in ["COMPONENT", "FRAME"]]
    
    # 限制数量（避免 API 限制）
    max_export = 10  # 先导出 10 个测试
    export_nodes = priority_nodes[:max_export]
    
    print(f"将导出前 {len(export_nodes)} 个节点（COMPONENT 和 FRAME 优先）")
    
    node_ids = [n["id"] for n in export_nodes]
    node_map = {n["id"]: n for n in export_nodes}
    
    # 4. 导出图片
    print("\n[4/4] 导出图片...")
    images = export_images(node_ids, scale=2, format="png")
    
    if not images:
        print("❌ 没有获取到图片 URL")
        return
    
    # 5. 下载图片
    print(f"\n开始下载 {len(images)} 张图片...")
    success_count = 0
    
    for node_id, image_url in images.items():
        node_info = node_map.get(node_id, {})
        node_name = node_info.get("name", node_id)
        
        # 清理文件名
        safe_name = sanitize_filename(node_name)
        filename = f"{safe_name}_{node_id}.png"
        filepath = OUTPUT_DIR / filename
        
        print(f"下载: {node_name} -> {filename}")
        
        if download_image(image_url, filepath):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！成功下载 {success_count}/{len(images)} 张图片")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
