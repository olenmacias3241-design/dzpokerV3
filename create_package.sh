#!/bin/bash

# 创建部署包脚本
# 将项目打包成 tar.gz 文件，方便上传到服务器

set -e

echo "=========================================="
echo "创建 dzpokerV3 部署包"
echo "=========================================="

# 配置
PROJECT_NAME="dzpokerV3"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="${PROJECT_NAME}_${TIMESTAMP}.tar.gz"
TEMP_DIR="/tmp/${PROJECT_NAME}_package"

# 清理临时目录
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

echo "[1/5] 复制项目文件..."

# 需要包含的文件和目录
cp -r \
    app.py \
    bots.py \
    config.py \
    tables.py \
    api_events.py \
    database.py \
    requirements.txt \
    deploy.sh \
    .env.example \
    DEPLOYMENT.md \
    DEPLOYMENT_CHECKLIST.md \
    README.md \
    $TEMP_DIR/ 2>/dev/null || true

# 复制目录
for dir in core database services specs tests static; do
    if [ -d "$dir" ]; then
        cp -r "$dir" $TEMP_DIR/
    fi
done

echo "[2/5] 清理不必要的文件..."

# 删除不需要的文件
cd $TEMP_DIR
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "*.log" -delete 2>/dev/null || true

# 删除 Figma 导出的大文件
rm -rf static/images/figma_export/*.png 2>/dev/null || true

echo "[3/5] 创建部署说明..."

cat > $TEMP_DIR/DEPLOY_README.txt << 'EOF'
dzpokerV3 部署包
================

快速部署步骤：

1. 上传到服务器
   scp dzpokerV3_*.tar.gz ec2-user@your-server-ip:/tmp/

2. SSH 登录服务器
   ssh ec2-user@your-server-ip

3. 解压
   cd /tmp
   tar -xzf dzpokerV3_*.tar.gz
   sudo mv dzpokerV3 /opt/

4. 运行部署脚本
   cd /opt/dzpokerV3
   sudo bash deploy.sh

5. 检查服务状态
   sudo systemctl status dzpoker

详细文档请参考：
- DEPLOYMENT.md - 完整部署指南
- DEPLOYMENT_CHECKLIST.md - 部署检查清单

EOF

echo "[4/5] 打包..."

cd /tmp
tar -czf $PACKAGE_NAME ${PROJECT_NAME}_package/

# 移动到当前目录
mv $PACKAGE_NAME $(pwd)/../

echo "[5/5] 清理临时文件..."
rm -rf $TEMP_DIR

echo ""
echo "=========================================="
echo "部署包创建完成！"
echo "=========================================="
echo ""
echo "文件名: $PAGE_NAME"
echo "大小: $(du -h ../$PACKAGE_NAME | cut -f1)"
echo ""
echo "上传到服务器："
echo "  scp $PACKAGE_NAME ec2-user@your-server-ip:/tmp/"
echo ""
