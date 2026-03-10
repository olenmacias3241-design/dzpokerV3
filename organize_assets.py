#!/usr/bin/env python3
"""
整理和分类 Figma 导出的图片
"""

import os
import shutil
from pathlib import Path

# 源目录和目标目录
SOURCE_DIR = Path(__file__).parent / "static" / "images" / "figma_export"
TARGET_DIR = Path(__file__).parent / "static" / "images" / "assets"

# 创建目标目录结构
CATEGORIES = {
    "pages": TARGET_DIR / "pages",           # 完整页面
    "icons": TARGET_DIR / "icons",           # 图标
    "buttons": TARGET_DIR / "buttons",       # 按钮
    "cards": TARGET_DIR / "cards",           # 扑克牌
    "chips": TARGET_DIR / "chips",           # 筹码
    "ui": TARGET_DIR / "ui",                 # UI 元素
    "backgrounds": TARGET_DIR / "backgrounds", # 背景
}

# 创建所有目录
for category_dir in CATEGORIES.values():
    category_dir.mkdir(parents=True, exist_ok=True)

# 分类规则（根据文件名关键词）
CLASSIFICATION_RULES = {
    "pages": ["德州扑克大厅", "挑战中心", "新闻", "牌友"],
    "icons": ["tuijian", "paiyou", "qingqiu", "jinqi", "serach", "xinwen", "jiangli"],
    "buttons": ["Target", "right_green", "friends_none"],
    "cards": ["poker"],
    "chips": ["coin", "tiket"],
    "ui": ["Layer_1", "Lock", "Frame"],
}


def classify_file(filename):
    """根据文件名判断分类"""
    for category, keywords in CLASSIFICATION_RULES.items():
        for keyword in keywords:
            if keyword in filename:
                return category
    return "ui"  # 默认分类


def sanitize_filename(filename):
    """清理文件名"""
    # 移除 ID 后缀
    name = filename.replace(".png", "")
    
    # 如果包含中文，保留中文
    if any('\u4e00' <= c <= '\u9fff' for c in name):
        # 移除 ID 部分（如 _52:40）
        parts = name.split("_")
        if len(parts) > 1 and ":" in parts[-1]:
            name = "_".join(parts[:-1])
    
    return name + ".png"


def organize_files():
    """整理文件"""
    print("=" * 60)
    print("整理 Figma 导出的图片")
    print("=" * 60)
    
    if not SOURCE_DIR.exists():
        print(f"❌ 源目录不存在: {SOURCE_DIR}")
        return
    
    files = list(SOURCE_DIR.glob("*.png"))
    print(f"\n找到 {len(files)} 个文件")
    
    stats = {category: 0 for category in CATEGORIES.keys()}
    
    for file_path in files:
        filename = file_path.name
        category = classify_file(filename)
        new_filename = sanitize_filename(filename)
        
        target_path = CATEGORIES[category] / new_filename
        
        # 复制文件
        shutil.copy2(file_path, target_path)
        stats[category] += 1
        
        print(f"[{category:12}] {filename:40} -> {new_filename}")
    
    print("\n" + "=" * 60)
    print("整理完成！")
    print("=" * 60)
    
    for category, count in stats.items():
        if count > 0:
            print(f"{category:12}: {count:3} 个文件 -> {CATEGORIES[category]}")
    
    print("\n总计: {} 个文件".format(sum(stats.values())))


if __name__ == "__main__":
    organize_files()
