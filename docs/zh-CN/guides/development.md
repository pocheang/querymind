# 💻 QueryMind 开发者指南

> 面向开发者的完整技术指南

---

## 📋 目录

- [开发环境搭建](#开发环境搭建)
- [项目结构](#项目结构)
- [开发工作流](#开发工作流)
- [API 开发](#api-开发)
- [前端开发](#前端开发)
- [测试指南](#测试指南)
- [代码规范](#代码规范)

---

## 开发环境搭建

### 前置要求

- Python 3.11+
- Node.js 16+
- Git
- VS Code（推荐）或其他 IDE

### 克隆项目

```bash
git clone https://github.com/pocheang/querymind.git
cd querymind
```

### 后端环境

```bash
# 创建虚拟环境
conda create -n rag-local python=3.11 -y
conda activate rag-local

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 初始化数据库
python scripts/init_database.py
```

### 前端环境

```bash
cd frontend
npm install
npm run dev
```

### IDE 配置

**VS Code 推荐插件**：
- Python
- Pylance
- ESLint
- Prettier
- GitLens

**VS Code 配置** (`.vscode/settings.json`)：
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

---

## 项目结构

```
querymind/
├── app/                    # 后端应用
│   ├── api/               # API 路由
│   │   ├── endpoints/     # 端点实现
│   │   └── main.py        # FastAPI 主应用
│   ├── core/              # 核心配置
│   │   ├── config.py      # 配置管理
│   │   └── security.py    # 安全认证
│   ├── db/                # 数据库
│   │   ├── models.py      # SQLAlchemy 模型
│   │   └── database.py    # 数据库连接
│   ├── schemas/           # Pydantic 模型
│   ├── services/          # 业务逻辑
│   │   ├── llm/          # LLM 服务
│   │   ├── retrieval/    # 检索服务
│   │   └── agents/       # Agent 实现
│   └── utils/             # 工具函数
│
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── pages/        # 页面组件
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── services/     # API 服务
│   │   ├── store/        # 状态管理
│   │   └── utils/        # 工具函数
│   ├── public/           # 静态资源
│   └── package.json      # 依赖配置
│
├── data/                  # 数据目录
│   ├── chroma_db/        # 向量数据库
│   └── querymind.db      # SQLite 数据库
│
├── scripts/              # 工具脚本
├── tests/                # 测试文件
├── docs/                 # 文档
└── requirements.txt      # Python 依赖
```

---

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发流程

```bash
# 启动后端（自动重载）
uvicorn app.api.main:app --reload

# 启动前端（热更新）
cd frontend && npm run dev
```

### 3. 代码检查

```bash
# Python 代码检查
pylint app/
black app/
isort app/

# JavaScript 代码检查
cd frontend
npm run lint
npm run format
```

### 4. 运行测试

```bash
# 后端测试
pytest tests/

# 前端测试
cd frontend
npm test
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request

在 GitHub 上创建 PR，描述：
- 功能说明
- 变更内容
- 测试结果
- 截图（如有 UI 变更）

---

## API 开发

### 创建新端点

**1. 定义 Schema** (`app/schemas/your_schema.py`):
```python
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    description: str

class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    
    class Config:
        from_attributes = True
```

**2. 创建端点** (`app/api/endpoints/items.py`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.your_schema import ItemCreate, ItemResponse

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """创建新项目"""
    # 实现逻辑
    return created_item

@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """获取项目详情"""
    # 实现逻辑
    return item
```

**3. 注册路由** (`app/api/main.py`):
```python
from app.api.endpoints import items

app.include_router(items.router, prefix="/api")
```

### 认证保护

```python
from app.core.security import get_current_user
from app.db.models import User

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    """需要认证的端点"""
    return {"user": current_user.username}
```

### 错误处理

```python
from fastapi import HTTPException, status

@router.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item
```

---

## 前端开发

### 创建新组件

**功能组件** (`src/components/ItemList.tsx`):
```typescript
import React, { useState, useEffect } from 'react';
import { getItems } from '@/services/api';

interface Item {
  id: number;
  name: string;
  description: string;
}

export const ItemList: React.FC = () => {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadItems();
  }, []);

  const loadItems = async () => {
    try {
      const data = await getItems();
      setItems(data);
    } catch (error) {
      console.error('Failed to load items:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {items.map(item => (
        <div key={item.id}>
          <h3>{item.name}</h3>
          <p>{item.description}</p>
        </div>
      ))}
    </div>
  );
};
```

### API 调用

**API 服务** (`src/services/api.ts`):
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
});

// 请求拦截器（添加 Token）
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器（处理错误）
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      // 重定向到登录页
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const getItems = () => api.get('/api/items');
export const createItem = (data: any) => api.post('/api/items', data);
```

### 状态管理

使用 Zustand：
```typescript
import create from 'zustand';

interface AppState {
  user: User | null;
  setUser: (user: User | null) => void;
  items: Item[];
  addItem: (item: Item) => void;
}

export const useStore = create<AppState>(set => ({
  user: null,
  setUser: user => set({ user }),
  items: [],
  addItem: item => set(state => ({ items: [...state.items, item] })),
}));
```

---

## 测试指南

### 后端测试

**单元测试** (`tests/test_api.py`):
```python
import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_create_item():
    response = client.post(
        "/api/items/",
        json={"name": "Test Item", "description": "Test"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"

def test_get_item():
    response = client.get("/api/items/1")
    assert response.status_code == 200
    assert "name" in response.json()
```

**运行测试**:
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 带覆盖率
pytest --cov=app tests/
```

### 前端测试

**组件测试** (`src/components/__tests__/ItemList.test.tsx`):
```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { ItemList } from '../ItemList';
import * as api from '@/services/api';

jest.mock('@/services/api');

describe('ItemList', () => {
  it('renders items', async () => {
    (api.getItems as jest.Mock).mockResolvedValue([
      { id: 1, name: 'Item 1', description: 'Desc 1' }
    ]);

    render(<ItemList />);

    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });
  });
});
```

---

## 代码规范

### Python 代码规范

遵循 PEP 8：
```python
# 导入顺序
import os
import sys

from fastapi import FastAPI
from sqlalchemy import create_engine

from app.core import config
from app.db import models

# 类定义
class MyClass:
    """类文档字符串"""
    
    def __init__(self, name: str):
        self.name = name
    
    def my_method(self) -> str:
        """方法文档字符串"""
        return f"Hello, {self.name}"

# 函数定义
def my_function(param: str, optional: int = 0) -> bool:
    """函数文档字符串
    
    Args:
        param: 参数说明
        optional: 可选参数
        
    Returns:
        返回值说明
    """
    return True
```

### TypeScript 代码规范

```typescript
// 接口定义
interface User {
  id: number;
  name: string;
  email: string;
}

// 函数定义
const fetchUser = async (id: number): Promise<User> => {
  const response = await api.get(`/users/${id}`);
  return response.data;
};

// 组件定义
export const UserProfile: React.FC<{ userId: number }> = ({ userId }) => {
  // 组件逻辑
  return <div>{/* JSX */}</div>;
};
```

### Git 提交规范

使用 Conventional Commits：
```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构代码
test: 添加测试
chore: 构建/工具变更
```

**示例**：
```bash
git commit -m "feat: add user authentication"
git commit -m "fix: resolve CORS issue"
git commit -m "docs: update API documentation"
```

---

## 🔗 相关资源

- [API 文档](http://localhost:8000/docs) - Swagger 接口文档
- [系统架构](../../guides/development/ARCHITECTURE.md) - 架构设计
- [贡献指南](../../../CONTRIBUTING.md) - 贡献流程

---

<div align="center">

**开始开发吧！ 💪**

[返回文档中心](../INDEX.md) · [GitHub 仓库](https://github.com/pocheang/querymind)

</div>
