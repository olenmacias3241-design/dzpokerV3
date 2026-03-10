#!/bin/bash

# dzpokerV3 自动部署脚本
# 适用于 Amazon Linux 2/2023

set -e  # 遇到错误立即退出

echo "=========================================="
echo "dzpokerV3 自动部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="/opt/dzpokerV3"
SERVICE_NAME="dzpoker"
DB_NAME="dzpoker"
DB_USER="dzpoker"
PORT=5002

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}[1/10] 更新系统...${NC}"
yum update -y

echo -e "${GREEN}[2/10] 安装基础依赖...${NC}"
yum install -y python3 python3-pip git mysql-server nginx

echo -e "${GREEN}[3/10] 启动 MySQL...${NC}"
systemctl start mysqld
systemctl enable mysqld

echo -e "${GREEN}[4/10] 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo -e "${GREEN}[5/10] 安装 Python 依赖...${NC}"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
else
    echo -e "${YELLOW}警告: requirements.txt 不存在，跳过依赖安装${NC}"
fi

echo -e "${GREEN}[6/10] 配置数据库...${NC}"
read -p "请输入 MySQL root 密码（如果是首次安装，直接回车）: " MYSQL_ROOT_PASSWORD
read -p "请输入 dzpoker 数据库密码: " DB_PASSWORD

# 创建数据库和用户
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}[7/10] 创建环境配置文件...${NC}"
cat > $PROJECT_DIR/.env <<EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME

# 服务器配置
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
PORT=$PORT

# 游戏配置
PLAYER_ACTION_TIMEOUT=15
PLAYER_ACTION_TIMEOUT_MIN=10
PLAYER_ACTION_TIMEOUT_MAX=30
EOF

echo -e "${GREEN}[8/10] 初始化数据库...${NC}"
if [ -f "database/migrations/create_hand_actions.py" ]; then
    python3 -m database.migrations.create_hand_actions
else
    echo -e "${YELLOW}警告: 数据库迁移脚本不存在，跳过${NC}"
fi

echo -e "${GREEN}[9/10] 创建 systemd 服务...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=dzpokerV3 Game Server
After=network.target mysql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$PROJECT_DIR
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 $PROJECT_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
systemctl daemon-reload

# 启动服务
systemctl start $SERVICE_NAME
systemctl enable $SERVICE_NAME

echo -e "${GREEN}[10/10] 配置防火墙...${NC}"
# 尝试使用 firewalld
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=$PORT/tcp
    firewall-cmd --reload
else
    # 使用 iptables
    iptables -A INPUT -p tcp --dport $PORT -j ACCEPT
    service iptables save 2>/dev/null || true
fi

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务状态:"
systemctl status $SERVICE_NAME --no-pager
echo ""
echo "访问地址: http://$(curl -s ifconfig.me):$PORT"
echo ""
echo "常用命令:"
echo "  查看日志: sudo journalctl -u $SERVICE_NAME -f"
echo "  重启服务: sudo systemctl restart $SERVICE_NAME"
echo "  停止服务: sudo systemctl stop $SERVICE_NAME"
echo ""
echo "配置文件位置: $PROJECT_DIR/.env"
echo ""
