# 部署前检查清单

## 📋 部署前准备

### 1. 服务器准备
- [ ] Amazon Linux 2/2023 实例已创建
- [ ] 安全组已配置（开放端口 5002, 80, 443, 22）
- [ ] SSH 密钥已配置
- [ ] 服务器内存 >= 2GB
- [ ] 磁盘空间 >= 10GB

### 2. 域名和 DNS（可选）
- [ ] 域名已购买
- [ ] DNS A 记录已指向服务器 IP
- [ ] SSL 证书已准备（Let's Encrypt 或其他）

### 3. 数据库准备
- [ ] MySQL 8.0+ 已安装
- [ ] 数据库用户和密码已准备
- [ ] 数据库名称已确定

### 4. 代码准备
- [ ] 所有代码已提交到 Git
- [ ] `.env.example` 已创建
- [ ] `requirements.txt` 已更新
- [ ] 测试已通过

---

## 🚀 部署步骤

### 方式1: 自动部署（推荐）

```bash
# 1. 上传项目到服务器
scp -r dzpokerV3 ec2-user@your-server-ip:/tmp/

# 2. SSH 登录服务器
ssh ec2-user@your-server-ip

# 3. 移动项目到 /opt
sudo mv /tmp/dzpokerV3 /opt/

# 4. 运行部署脚本
cd /opt/dzpokerV3
sudo bash deploy.sh
```

### 方式2: 手动部署

参考 `DEPLOYMENT.md` 文档。

---

## ✅ 部署后检查

### 1. 服务状态
```bash
sudo systemctl status dzpoker
```

### 2. 日志检查
```bash
sudo journalctl -u dzpoker -f
```

### 3. API 测试
```bash
# 测试大厅 API
curl http://localhost:5002/api/lobby/tables

# 测试登录 API
curl -X POST http://localhost:5002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

### 4. WebSocket 测试
使用浏览器访问：`http://your-server-ip:5002`

### 5. 数据库连接
```bash
mysql -u dzpoker -p dzpoker
SHOW TABLES;
```

---

## 🔧 常见问题排查

### 服务无法启动
```bash
# 查看详细日志
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

# 测试数据库连接
mysql -u dzpoker -p -h localhost dzpoker

# 检查 .env 文件
cat /opt/dzpokerV3/.env
```

### 防火墙问题
```bash
# 检查防火墙状态
sudo firewall-cmd --list-all

# 或
sudo iptables -L -n
```

---

## 📊 监控和维护

### 日志位置
- 应用日志: `sudo journalctl -u dzpoker`
- Nginx 日志: `/var/log/nginx/`
- MySQL 日志: `/var/log/mysqld.log`

### 性能监控
```bash
# CPU 和内存
top
htop

# 磁盘使用
df -h

# 网络连接
netstat -tulpn | grep 5002
```

### 定期维护
- [ ] 每周检查日志
- [ ] 每月备份数据库
- [ ] 每月更新系统和依赖
- [ ] 监控磁盘空间
- [ ] 监控内存使用

---

## 🔐 安全加固

### 1. 修改默认端口
编辑 `.env` 文件，修改 `PORT` 值。

### 2. 配置 HTTPS
使用 Let's Encrypt:
```bash
sudo yum install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

### 3. 限制数据库访问
```sql
-- 只允许本地连接
REVOKE ALL PRIVILEGES ON *.* FROM 'dzpoker'@'%';
GRANT ALL PRIVILEGES ON dzpoker.* TO 'dzpoker'@'localhost';
FLUSH PRIVILEGES;
```

### 4. 配置防火墙
```bash
# 只开放必要端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### 5. 定期更新
```bash
# 系统更新
sudo yum update -y

# Python 依赖更新
cd /opt/dzpokerV3
sudo pip3 install -r requirements.txt --upgrade
```

---

## 📞 紧急联系

如遇到严重问题，请联系：
- 开发团队: [联系方式]
- 运维团队: [联系方式]

---

## 📝 部署记录

| 日期 | 版本 | 操作人 | 备注 |
|------|------|--------|------|
| 2026-03-10 | v1.0 | 胖子 | 初始部署 |
|  |  |  |  |
