# 📡 QueryMind API 开发指南

> 后端 API 开发完整指南

---

## 📋 目录

- [API 概览](#api-概览)
- [认证授权](#认证授权)
- [核心 API](#核心-api)
- [错误处理](#错误处理)
- [速率限制](#速率限制)
- [API 示例](#api-示例)

---

## API 概览

### 基础信息

- **Base URL**: `http://localhost:8000`
- **API 前缀**: `/api`
- **文档地址**: `http://localhost:8000/docs` (Swagger)
- **格式**: JSON
- **认证**: JWT Bearer Token

### API 版本

当前版本: **v1**

### 响应格式

**成功响应**：
```json
{
  "data": {...},
  "message": "Success",
  "code": 200
}
```

**错误响应**：
```json
{
  "detail": "Error message",
  "code": 400
}
```

---

## 认证授权

### 注册用户

**端点**: `POST /api/auth/register`

**请求体**：
```json
{
  "username": "johndoe",
  "password": "securepassword123",
  "role": "analyst"
}
```

**响应**：
```json
{
  "id": 1,
  "username": "johndoe",
  "role": "analyst",
  "created_at": "2024-06-23T10:00:00"
}
```

### 用户登录

**端点**: `POST /api/auth/login`

**请求体**：
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 使用 Token

所有需要认证的请求都需要在请求头中添加：

```http
Authorization: Bearer <access_token>
```

**示例**：
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "http://localhost:8000/api/documents",
    headers=headers
)
```

---

## 核心 API

### 文档管理

#### 上传文档

**端点**: `POST /api/documents/upload`

**请求**：
- Content-Type: `multipart/form-data`
- 文件字段: `file`

**示例**：
```python
files = {"file": open("document.pdf", "rb")}
response = requests.post(
    "http://localhost:8000/api/documents/upload",
    files=files,
    headers={"Authorization": f"Bearer {token}"}
)
```

**响应**：
```json
{
  "id": "doc_123",
  "filename": "document.pdf",
  "size": 1048576,
  "status": "processing",
  "uploaded_at": "2024-06-23T10:00:00"
}
```

#### 获取文档列表

**端点**: `GET /api/documents`

**查询参数**：
- `page`: 页码（默认 1）
- `limit`: 每页数量（默认 20）
- `status`: 过滤状态（processing/completed/failed）

**响应**：
```json
{
  "total": 50,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "doc_123",
      "filename": "document.pdf",
      "size": 1048576,
      "status": "completed",
      "uploaded_at": "2024-06-23T10:00:00"
    }
  ]
}
```

#### 删除文档

**端点**: `DELETE /api/documents/{document_id}`

**响应**：
```json
{
  "message": "Document deleted successfully"
}
```

---

### 查询对话

#### 发送查询

**端点**: `POST /api/chat/query`

**请求体**：
```json
{
  "query": "什么是机器学习？",
  "session_id": "session_abc123",
  "use_graph": false,
  "use_web_search": false
}
```

**响应**：
```json
{
  "answer": "机器学习是人工智能的一个分支...",
  "sources": [
    {
      "document": "ML_Basics.pdf",
      "page": 3,
      "content": "机器学习是...",
      "score": 0.92
    }
  ],
  "agent_trace": {
    "router": "vector_rag",
    "execution_time": 2.5
  }
}
```

#### 流式查询

**端点**: `POST /api/chat/query-stream`

**请求体**：同上

**响应**：Server-Sent Events (SSE)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat/query-stream",
    json={"query": "什么是机器学习？"},
    headers={"Authorization": f"Bearer {token}"},
    stream=True
)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8'))
        print(data)
```

#### 获取对话历史

**端点**: `GET /api/chat/sessions/{session_id}/messages`

**响应**：
```json
{
  "session_id": "session_abc123",
  "messages": [
    {
      "role": "user",
      "content": "什么是机器学习？",
      "timestamp": "2024-06-23T10:00:00"
    },
    {
      "role": "assistant",
      "content": "机器学习是...",
      "timestamp": "2024-06-23T10:00:05"
    }
  ]
}
```

---

### 知识图谱

#### 查询实体

**端点**: `GET /api/graph/entities`

**查询参数**：
- `search`: 搜索关键词
- `limit`: 返回数量

**响应**：
```json
{
  "entities": [
    {
      "id": "entity_1",
      "label": "机器学习",
      "type": "concept",
      "properties": {
        "description": "AI的一个分支"
      }
    }
  ]
}
```

#### 查询关系

**端点**: `GET /api/graph/relationships`

**查询参数**：
- `entity_id`: 实体 ID
- `depth`: 关系深度（默认 1）

**响应**：
```json
{
  "nodes": [
    {
      "id": "entity_1",
      "label": "机器学习"
    },
    {
      "id": "entity_2",
      "label": "深度学习"
    }
  ],
  "edges": [
    {
      "source": "entity_1",
      "target": "entity_2",
      "type": "includes"
    }
  ]
}
```

---

### 代理追踪

#### 获取执行追踪

**端点**: `GET /api/agents/trace/{query_id}`

**响应**：
```json
{
  "query_id": "query_xyz",
  "steps": [
    {
      "agent": "RouterAgent",
      "action": "route_query",
      "input": "什么是机器学习？",
      "output": "vector_rag",
      "duration": 0.5
    },
    {
      "agent": "VectorRAGAgent",
      "action": "retrieve",
      "input": "什么是机器学习？",
      "output": ["doc1", "doc2"],
      "duration": 1.2
    }
  ]
}
```

---

### 用户管理（仅管理员）

#### 获取用户列表

**端点**: `GET /api/admin/users`

**权限**: 需要 `admin` 角色

**查询参数**：
- `page`: 页码
- `limit`: 每页数量
- `role`: 过滤角色

**响应**：
```json
{
  "total": 100,
  "users": [
    {
      "id": 1,
      "username": "johndoe",
      "role": "analyst",
      "created_at": "2024-06-23T10:00:00",
      "last_login": "2024-06-23T15:30:00"
    }
  ]
}
```

#### 更新用户角色

**端点**: `PATCH /api/admin/users/{user_id}/role`

**请求体**：
```json
{
  "role": "viewer"
}
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 未找到 |
| 422 | 验证错误 |
| 500 | 服务器错误 |

### 错误响应格式

```json
{
  "detail": "具体错误信息",
  "code": "ERROR_CODE",
  "errors": [
    {
      "field": "password",
      "message": "密码至少6位"
    }
  ]
}
```

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| `INVALID_TOKEN` | Token 无效或过期 | 重新登录获取新 Token |
| `PERMISSION_DENIED` | 权限不足 | 检查用户角色 |
| `FILE_TOO_LARGE` | 文件过大 | 减小文件大小或分割 |
| `DOCUMENT_NOT_FOUND` | 文档不存在 | 检查文档 ID |
| `RATE_LIMIT_EXCEEDED` | 超过速率限制 | 稍后重试 |

---

## 速率限制

### 限制规则

| 用户类型 | 限制 |
|----------|------|
| **匿名用户** | 10 请求/分钟 |
| **注册用户** | 60 请求/分钟 |
| **管理员** | 无限制 |

### 响应头

请求响应会包含速率限制信息：

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1687512000
```

### 超限响应

```json
{
  "detail": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

---

## API 示例

### Python 客户端

```python
import requests
from typing import Optional

class QueryMindClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def login(self, username: str, password: str):
        """用户登录"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data
    
    def _headers(self):
        """获取请求头"""
        if not self.token:
            raise ValueError("Not authenticated")
        return {"Authorization": f"Bearer {self.token}"}
    
    def upload_document(self, file_path: str):
        """上传文档"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{self.base_url}/api/documents/upload",
                files=files,
                headers=self._headers()
            )
        response.raise_for_status()
        return response.json()
    
    def query(self, question: str, session_id: Optional[str] = None):
        """发送查询"""
        data = {"query": question}
        if session_id:
            data["session_id"] = session_id
        
        response = requests.post(
            f"{self.base_url}/api/chat/query",
            json=data,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_documents(self, page: int = 1, limit: int = 20):
        """获取文档列表"""
        response = requests.get(
            f"{self.base_url}/api/documents",
            params={"page": page, "limit": limit},
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

# 使用示例
client = QueryMindClient()

# 登录
client.login("admin", "password")

# 上传文档
result = client.upload_document("document.pdf")
print(f"Document uploaded: {result['id']}")

# 查询
answer = client.query("什么是机器学习？")
print(f"Answer: {answer['answer']}")
```

### JavaScript/TypeScript 客户端

```typescript
class QueryMindClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async login(username: string, password: string) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) throw new Error('Login failed');
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  private headers() {
    if (!this.token) throw new Error('Not authenticated');
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  async query(question: string, sessionId?: string) {
    const response = await fetch(`${this.baseUrl}/api/chat/query`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({
        query: question,
        session_id: sessionId
      })
    });
    
    if (!response.ok) throw new Error('Query failed');
    return response.json();
  }

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseUrl}/api/documents/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData
    });
    
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  }
}

// 使用示例
const client = new QueryMindClient();

await client.login('admin', 'password');
const answer = await client.query('什么是机器学习？');
console.log('Answer:', answer.answer);
```

### cURL 示例

```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 上传文档
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"

# 查询
curl -X POST http://localhost:8000/api/chat/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是机器学习？"}'

# 获取文档列表
curl -X GET "http://localhost:8000/api/documents?page=1&limit=20" \
  -H "Authorization: Bearer <token>"
```

---

## 🔗 相关资源

- [在线 API 文档](http://localhost:8000/docs) - Swagger UI
- [配置指南](./configuration.md) - API 配置
- [开发者指南](./development.md) - 后端开发

---

<div align="center">

**开始使用 QueryMind API！ 🚀**

[返回文档中心](../INDEX.md) · [GitHub 仓库](https://github.com/pocheang/querymind)

</div>
