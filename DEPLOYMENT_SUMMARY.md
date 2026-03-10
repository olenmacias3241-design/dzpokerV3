# dzpokerV3 部署文件总结

## 📦 已创建的部署文件

### 1. 核心部署文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `DEPLOYMENT.md` | 完整部署指南 | 详细的部署步骤和配置说明 |
| `DEPLOYMENT_CHECKLIST.md` | 部署检查清单 | 部署前后的检查项目 |
| `deploy.sh` | 自动部署脚本 | 一键自动部署到 Amazon Linux |
| `create_package.sh` | 打包脚本 | 创建部署包 tar.gz |

### 2. 配置文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `.env.example` | 环境变量示例 | 生产环境配置模板 |
| `config_production.py` | 生产环境配置 | Python 配置类 |
| `.gitignore` | Git 忽略文件 | 排除敏感文件和临时文件 |

### 3. 已有文件

| 文件名 | 说明 |
|--------|------|
| `requirements.txt` | Python 依赖 |
| `app.py` | 主应用文件 |
| `README.md` | 项目说明 |

---

## 🚀 快速部署流程

### 方式1: 使用部署脚本（推荐）

```bash
# 1. 创建部署包
cd /Users/taoyin/.openclaw/workspace/dzpokerV3
bash create_package.sh

# 2. 上传到服务器
scp dzpokerV3_*.tar.gz ec2-user@your-server-ip:/tmp/

# 3. SSH 登录服务器
ssh ec2-user@your-server-ip

# 4. 解压并部署
cd /tmp
tar -xzf dzpokerV3_*.tar.gz
sudo mv dzpokerV3 /opt/
cd /opt/dzpokerV3
sudo bash deploy.sh

# 5. 检查服务
sudo systemctl status dzpoker
```

### 方式2: 手动部署

参考 `DEPLOYMENT.md` 文档中的详细步骤。

---

## 📋 部署前准备

### 服务器要求
- **操作系统**: Amazon Linux 2 或 Amazon Linux 2023
- **Python**: 3.9+
- **MySQL**: 8.0+
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 10GB

### 需要准备的信息
- [ ] 服务器 IP 地址
- [ ] SSH 密钥
- [ ] 数据库密码
- [ ] 域名（可选）
- [ ] SSL 证书（可选）

---

## 🔧 部署后配置

### 1. 环境变量

复制并编辑 `.env` 文件：

```bash
cd /opt/dzpokerV3
sudo cp .env.example .env
sudo nano .env
```

必须修改的配置：
- `DB_PASSWORD` - 数据库密码
- `SECRET_KEY` - 应用密钥（使用 `openssl rand -hex 32` 生成）

### 2. 服务管理

```bash
# 启动服务
sudo systemctl start dzpoker

# 停止服务
sudo systemctl stop dzpoker

# 重启服务
sudo systemctl restart dzpoker

# 查看状态
sudo systemctl status dzpoker

# 查看日志
sudo journalctl -u dzpoker -f
```

### 3. Nginx 反向代理（可选）

如果需要使用域名和 HTTPS，配置 Nginx：

```bash
sudo yum install nginx -y
sudo nano /etc/nginx/conf.d/dzpoker.conf
```

参考 `DEPLOYMENT.md` 中的 Nginx 配置。

---

## ✅ 验证部署

### 1. 检查服务状态

```bash
sudo systemctl status dzpoker
```

应该显示 `active (running)`。

### 2. 测试 API

```bash
# 测试大厅 API
curl http://localhost:5002/api/lobby/tables

# 应该返回 JSON 数据
```

### 3. 测试 WebSocket

使用浏览器访问：`http://your-server-ip:5002`

### 4. 检查数据库

```bash
mysql -u dzpoker -p dzpoker
SHOW TABLES;
```

应该看到所有表已创建。

---

## 🔐 安全建议

1. **修改默认端口**（可选）
2. **配置 HTTPS**（强烈推荐）
3. **限制数据库访问**（只允许本地）
4. **配置防火墙**（只开放必要端口）
5. **定期备份数据库**
6. **使用强密码**
7. **定期更新系统**

---

## 📊 监控和维护

### 日志位置
- 应用日志: `sudo journalctl -u dzpoker`
- Nginx 日志: `/var/log/nginx/`
- MySQL 日志: `/var/log/mysqld.log`

### 常用命令

```bash
# 查看实时日志
sudo journalctl -u dzpoker -f

# 查看最近 100 行日志
sudo journalctl -u dzpoker -n 100

# 查看今天的日志
sudo journalctl -u dzpoker --since today

# 重启服务
sudo systemctl restart dzpoker

# 更新代码
cd /opt/dzpokerV3
sudo git pull
sudo systemctl restart dzpoker
```

---

## 🆘 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u dzpoker -n 100 --no-pager

# 检查端口占用
sudo lsof -i :5002

# 检查权限
ls -la /opt/dzpokerV3
```

### 数据库连接失败

```bash
# 检查 MySQL 状态
sudo systemctl status mysqld

# 测试连接
mysql -u dzpoker -p -h localhost dzpoker

# 检查配置
cat /opt/dzpokerV3/.env
```

### 防火墙问题

```bash
# 检查防火墙规则
sudo firewall-cmd --list-all

# 或
sudo iptables -L -n
```

---

## 📞 支持

如有问题，请参考：
1. `DEPLOYMENT.md` - 完整部署指南
2. `DEPLOYMENT_CHECKLIST.md` - 检查清单
3. 联系开发团队

---

## 📝 部署记录

| 日期 | 版本 | 操作 | 备注 |
|------|------|------|------|
| 2026-03-10 | v1.0 | 创建部署文件 | 初始版本 |

---

**准备完成！现在可以开始部署了。** 🚀
