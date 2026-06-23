# 📦 部署指南

> QueryMind 生产环境部署完整指南

---

## 📋 目录

- [部署架构](#部署架构)
- [环境要求](#环境要求)
- [部署方式](#部署方式)
- [配置优化](#配置优化)
- [监控维护](#监控维护)
- [故障恢复](#故障恢复)

---

## 部署架构

### 推荐架构

```
Internet
    │
    ▼
┌─────────────────┐
│   Load Balancer │  (Nginx/HAProxy)
│   SSL/TLS       │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
┌───▼───┐ ┌──▼───┐  ┌──▼───┐  ┌──▼───┐
│ Web 1 │ │Web 2 │  │Web 3 │  │Web N │  (Frontend)
└───┬───┘ └──┬───┘  └──┬───┘  └──┬───┘
    └────────┼─────────┼─────────┘
             │         │
        ┌────▼─────────▼────┐
        │   API Gateway     │
        │   (FastAPI)       │
        └────────┬──────────┘
                 │
    ┌────────────┼────────────────┐
    │            │                │
┌───▼─────┐ ┌───▼──────┐  ┌─────▼─────┐
│ App 1   │ │ App 2    │  │  App N    │  (Backend)
└────┬────┘ └────┬─────┘  └─────┬─────┘
     │           │               │
     └───────────┼───────────────┘
                 │
    ┌────────────┼───────────────────┐
    │            │           │        │
┌───▼────┐  ┌───▼────┐  ┌──▼───┐ ┌─▼─────┐
│Postgres│  │ChromaDB│  │Neo4j │ │ Redis │
└────────┘  └────────┘  └──────┘ └───────┘
```

---

## 环境要求

### 最低配置

**单机部署**：
- CPU: 4 核心
- 内存: 8 GB
- 硬盘: 50 GB SSD
- 网络: 100 Mbps

**生产环境**：
- CPU: 8 核心+
- 内存: 32 GB+
- 硬盘: 200 GB+ NVMe SSD
- 网络: 1 Gbps

### 软件要求

- **操作系统**: Ubuntu 22.04 LTS / CentOS 8+ / Debian 11+
- **Python**: 3.11+
- **Node.js**: 18+
- **数据库**: PostgreSQL 15+ / SQLite
- **容器**: Docker 24+ (可选)

---

## 部署方式

### 方式 1: Docker Compose（推荐）

#### 1. 克隆项目

```bash
git clone https://github.com/pocheang/querymind.git
cd querymind
```

#### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

**.env 配置**：
```bash
# 应用配置
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-strong-secret-key-here

# 数据库
DATABASE_URL=postgresql://user:password@db:5432/querymind

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# 前端
VITE_API_BASE_URL=https://api.yourdomain.com
```

#### 3. 启动服务

```bash
docker-compose up -d
```

#### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 访问健康检查
curl http://localhost:8000/health
```

---

### 方式 2: 手动部署

#### 后端部署

**1. 安装依赖**：
```bash
# 创建用户
sudo useradd -m -s /bin/bash querymind

# 切换用户
sudo su - querymind

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**2. 配置 Systemd**：

`/etc/systemd/system/querymind-api.service`:
```ini
[Unit]
Description=QueryMind API Server
After=network.target postgresql.service

[Service]
Type=notify
User=querymind
Group=querymind
WorkingDirectory=/home/querymind/querymind
Environment="PATH=/home/querymind/querymind/venv/bin"
ExecStart=/home/querymind/querymind/venv/bin/uvicorn app.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. 启动服务**：
```bash
sudo systemctl daemon-reload
sudo systemctl enable querymind-api
sudo systemctl start querymind-api
sudo systemctl status querymind-api
```

#### 前端部署

**1. 构建前端**：
```bash
cd frontend
npm install
npm run build
```

**2. 配置 Nginx**：

`/etc/nginx/sites-available/querymind`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 前端静态文件
    root /home/querymind/querymind/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript;
}
```

**3. 启用站点**：
```bash
sudo ln -s /etc/nginx/sites-available/querymind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### 方式 3: Kubernetes

#### 1. 创建 Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: querymind
```

#### 2. 配置 ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: querymind-config
  namespace: querymind
data:
  ENVIRONMENT: "production"
  LLM_PROVIDER: "openai"
  LLM_MODEL: "gpt-4"
```

#### 3. 配置 Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: querymind-secret
  namespace: querymind
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key"
  DATABASE_URL: "postgresql://..."
  OPENAI_API_KEY: "sk-..."
```

#### 4. 部署应用

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: querymind-api
  namespace: querymind
spec:
  replicas: 3
  selector:
    matchLabels:
      app: querymind-api
  template:
    metadata:
      labels:
        app: querymind-api
    spec:
      containers:
      - name: api
        image: querymind/api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: querymind-config
        - secretRef:
            name: querymind-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 5. 创建 Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: querymind-api-service
  namespace: querymind
spec:
  selector:
    app: querymind-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 6. 配置 Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: querymind-ingress
  namespace: querymind
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: querymind-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: querymind-api-service
            port:
              number: 80
```

#### 7. 应用配置

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

---

## 配置优化

### 数据库优化

**PostgreSQL 配置**：
```sql
-- 连接数
max_connections = 200

-- 内存
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 64MB

-- 写入优化
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### 应用优化

**Worker 数量**：
```bash
# 推荐公式: (CPU核心数 * 2) + 1
workers = (8 * 2) + 1 = 17
```

**Uvicorn 配置**：
```bash
uvicorn app.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 17 \
  --worker-class uvicorn.workers.UvicornWorker \
  --limit-concurrency 1000 \
  --backlog 2048 \
  --timeout-keep-alive 5
```

---

## 监控维护

### 日志管理

**Systemd 日志**：
```bash
# 查看日志
journalctl -u querymind-api -f

# 查看最近100行
journalctl -u querymind-api -n 100
```

### 性能监控

**Prometheus + Grafana**：
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'querymind'
    static_configs:
      - targets: ['localhost:8000']
```

### 健康检查

```bash
# 定期检查
*/5 * * * * curl -f http://localhost:8000/health || alert
```

---

## 故障恢复

### 备份策略

**数据库备份**：
```bash
# 每日备份
0 2 * * * pg_dump querymind | gzip > /backup/querymind-$(date +\%Y\%m\%d).sql.gz
```

**向量数据库备份**：
```bash
# 备份 ChromaDB
tar -czf chroma-backup-$(date +\%Y\%m\%d).tar.gz data/chroma_db/
```

### 恢复流程

**数据库恢复**：
```bash
gunzip < querymind-20260623.sql.gz | psql querymind
```

---

<div align="center">

**部署完成！ 🚀**

[返回主页](./README.md) · [配置指南](./docs/zh-CN/guides/configuration.md) · [故障排查](./docs/zh-CN/guides/troubleshooting.md)

</div>
