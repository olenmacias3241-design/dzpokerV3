# dzpokerV3 部署指南

## 环境要求

- **操作系统**: Amazon Linux 2 或 Amazon Linux 2023
- **Python**: 3.9+
- **数据库**: MySQL 8.0+
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 10GB

---

## 快速部署

### 1. 安装依赖

```bash
# 更新系统
sudo yum update -y

# 安装 Python 3.9+
sudo yum install python3 python3-pip -y

# 安装 MySQL
sudo yum install mysql-server -y
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 安装 Git
sudo yum install git -y
```

### 2. 克隆项目

```bash
cd /opt
sudo git clone <your-repo-url> dzpokerV3
cd dzpokerV3
```

### 3. 安装 Python 依赖

```bash
sudo pip3 install -r requirements.txt
```

### 4. 配置数据库

```bash
# 登录 MySQL
sudo mysql -u root -p

# 创建数据库和用户
CREATE DATABASE dzpoker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dzpoker'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON dzpoker.* TO 'dzpoker'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. 配置环境变量

复制示例并编辑（项目根目录）：

```bash
cp .env.example .env
nano .env
```

`.env.example` 位于项目根目录，变量与 `config.py` 一致。必填示例：

```env
# 应用
SECRET_KEY=your_secret_key_here_use_openssl_rand_hex_32
FLASK_DEBUG=0

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=dzpoker
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=dzpoker
MYSQL_CHARSET=utf8mb4

# 游戏（可选，有默认值）
PLAYER_ACTION_TIMEOUT=15
PLAYER_ACTION_TIMEOUT_MIN=10
PLAYER_ACTION_TIMEOUT_MAX=30
```

说明：本仓库使用 `MYSQL_*` 变量名（见 `config.py`），若从旧文档看到 `DB_*` 请以 `.env.example` 为准。

### 6. 初始化数据库

```bash
cd /opt/dzpokerV3
python3 -m database.migrations.create_hand_actions
```

### 7. 启动服务

#### 方式1: 直接运行（测试用）

```bash
python3 app.py
```

#### 方式2: 使用 systemd（生产环境推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/dzpoker.service
```

添加以下内容：

```ini
[Unit]
Description=dzpokerV3 Game Server
After=network.target mysql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/dzpokerV3
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /opt/dzpokerV3/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start dzpoker
sudo systemctl enable dzpoker
sudo systemctl status dzpoker
```

### 8. 配置防火墙

```bash
# 开放端口 5002
sudo firewall-cmd --permanent --add-port=5002/tcp
sudo firewall-cmd --reload

# 或者使用 iptables
sudo iptables -A INPUT -p tcp --dport 5002 -j ACCEPT
sudo service iptables save
```

### 9. 配置 Nginx 反向代理（可选）

```bash
sudo yum install nginx -y

sudo nano /etc/nginx/conf.d/dzpoker.conf
```

添加以下内容：

```nginx
upstream dzpoker {
    server 127.0.0.1:5002;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://dzpoker;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://dzpoker/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

启动 Nginx：

```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## 前后端分离部署

当**前端静态资源**（大厅、牌桌页等）与**后端 API/WebSocket** 部署在不同域名或机器时，按以下方式配置。

- **架构说明**：见 [ARCHITECTURE.md](./ARCHITECTURE.md)（服务端单一数据源、客户端只监控当前桌、数据流）。
- **服务端**：按本文「快速部署」部署后端即可；CORS 当前允许任意来源（`*`），生产可按需收紧。
- **环境变量**：服务端使用项目根目录 [.env.example](./.env.example) 复制为 `.env` 配置（见上文「配置环境变量」）。

### 客户端配置

前端需在**加载任何业务脚本之前**指定 API 与 WebSocket 地址，否则请求会走同源。

在入口 HTML（如 `index.html`、`lobby.html` 或模板中的 `<head>`）中，在引用 `config.js` 之前加入：

```html
<script>
  window.DZPOKER_API_BASE = "https://api.example.com";   // 后端 API 根地址，无末尾斜杠
  window.DZPOKER_WS_URL   = "https://api.example.com";   // Socket.IO 连此地址
</script>
<script src="/static/config.js"></script>
```

- 同源部署时可不设置上述两个变量（或设为 `""`），则使用当前页面的 origin。
- 分离部署时把 `https://api.example.com` 换成实际后端地址（如 `http://IP:5001`）。

### 流程简述

1. **后端**：在一台服务器上按本文完成「快速部署」，保证 `/api/*` 与 `/socket.io` 可访问。
2. **前端**：将 `templates/` 渲染后的静态资源放到 CDN 或另一域名；在该站点页面中设置 `DZPOKER_API_BASE` 与 `DZPOKER_WS_URL` 指向后端地址。
3. **验证**：浏览器打开前端入口 → 登录 → 大厅 → 创建/加入桌 → 牌桌页，确认请求发往后端且 WebSocket 正常推送。

---

## 验证部署

### 1. 检查服务状态

```bash
sudo systemctl status dzpoker
```

### 2. 查看日志

```bash
sudo journalctl -u dzpoker -f
```

### 3. 测试 API

```bash
curl http://localhost:5002/api/lobby/tables
```

---

## 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
sudo lsof -i :5002

# 杀死进程
sudo kill -9 <PID>
```

### 2. 数据库连接失败

- 检查 MySQL 是否运行：`sudo systemctl status mysqld`
- 检查 `.env` 文件中的数据库配置
- 检查防火墙规则

### 3. 权限问题

```bash
# 修改项目目录权限
sudo chown -R ec2-user:ec2-user /opt/dzpokerV3
sudo chmod -R 755 /opt/dzpokerV3
```

---

## 监控和维护

### 查看日志

```bash
# 实时日志
sudo journalctl -u dzpoker -f

# 最近 100 行
sudo journalctl -u dzpoker -n 100

# 今天的日志
sudo journalctl -u dzpoker --since today
```

### 重启服务

```bash
sudo systemctl restart dzpoker
```

### 更新代码

```bash
cd /opt/dzpokerV3
sudo git pull
sudo systemctl restart dzpoker
```

---

## 性能优化

### 1. 使用 Gunicorn（推荐）

安装：

```bash
sudo pip3 install gunicorn eventlet
```

修改 systemd 服务文件：

```ini
ExecStart=/usr/local/bin/gunicorn --worker-class eventlet -w 4 --bind 0.0.0.0:5002 app:app
```

### 2. 数据库优化

```sql
-- 添加索引
ALTER TABLE hand_actions ADD INDEX idx_hand_id (hand_id);
ALTER TABLE hand_participants ADD INDEX idx_hand_id (hand_id);
ALTER TABLE game_hands ADD INDEX idx_table_id (table_id);
```

### 3. Redis 缓存（可选）

```bash
sudo yum install redis -y
sudo systemctl start redis
sudo systemctl enable redis
```

---

## 安全建议

1. **修改默认端口**
2. **使用 HTTPS**（配置 SSL 证书）
3. **限制数据库访问**（只允许本地连接）
4. **定期备份数据库**
5. **使用强密码**
6. **启用防火墙**
7. **定期更新系统和依赖**

---

## 备份和恢复

### 备份数据库

```bash
mysqldump -u dzpoker -p dzpoker > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
mysql -u dzpoker -p dzpoker < backup_20260310.sql
```

---

## 联系支持

如有问题，请联系开发团队。
