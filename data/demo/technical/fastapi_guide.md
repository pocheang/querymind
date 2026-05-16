# FastAPI 快速入门指南

## 1. FastAPI 简介

FastAPI 是一个现代、快速（高性能）的 Web 框架，用于基于标准 Python 类型提示构建 API。

### 1.1 主要特性

- **快速**：性能与 NodeJS 和 Go 相当
- **快速编码**：开发速度提升约 200%-300%
- **更少的错误**：减少约 40% 的人为错误
- **直观**：强大的编辑器支持，自动补全
- **简单**：易于使用和学习
- **简短**：减少代码重复
- **健壮**：生产可用的代码，自动交互式文档
- **基于标准**：基于 API 的开放标准 OpenAPI 和 JSON Schema

### 1.2 安装

```bash
pip install fastapi
pip install "uvicorn[standard]"
```

## 2. 第一个 FastAPI 应用

### 2.1 Hello World

创建文件 `main.py`：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

### 2.2 运行应用

```bash
uvicorn main:app --reload
```

访问：
- API: http://127.0.0.1:8000
- 交互式文档: http://127.0.0.1:8000/docs
- 替代文档: http://127.0.0.1:8000/redoc

## 3. 路径参数

### 3.1 基本用法

```python
@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}
```

### 3.2 路径参数验证

```python
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(
    item_id: int = Path(..., title="The ID of the item", ge=1)
):
    return {"item_id": item_id}
```

### 3.3 枚举路径参数

```python
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    return {"model_name": model_name}
```

## 4. 查询参数

### 4.1 基本查询参数

```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

### 4.2 可选查询参数

```python
from typing import Optional

@app.get("/items/{item_id}")
def read_item(item_id: str, q: Optional[str] = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

### 4.3 查询参数验证

```python
from fastapi import Query

@app.get("/items/")
def read_items(
    q: Optional[str] = Query(
        None,
        min_length=3,
        max_length=50,
        regex="^fixedquery$"
    )
):
    return {"q": q}
```

## 5. 请求体

### 5.1 Pydantic 模型

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

### 5.2 嵌套模型

```python
from typing import List

class Image(BaseModel):
    url: str
    name: str

class Item(BaseModel):
    name: str
    images: Optional[List[Image]] = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

## 6. 响应模型

### 6.1 基本响应模型

```python
class ItemOut(BaseModel):
    name: str
    price: float

@app.post("/items/", response_model=ItemOut)
def create_item(item: Item):
    return item
```

### 6.2 响应状态码

```python
from fastapi import status

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item
```

## 7. 依赖注入

### 7.1 简单依赖

```python
from fastapi import Depends

def common_parameters(q: Optional[str] = None, skip: int = 0):
    return {"q": q, "skip": skip}

@app.get("/items/")
def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

### 7.2 类作为依赖

```python
class CommonQueryParams:
    def __init__(self, q: Optional[str] = None, skip: int = 0):
        self.q = q
        self.skip = skip

@app.get("/items/")
def read_items(commons: CommonQueryParams = Depends()):
    return commons
```

## 8. 数据库集成

### 8.1 SQLAlchemy 集成

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 8.2 使用数据库

```python
@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

## 9. 认证和安全

### 9.1 OAuth2 密码流

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

### 9.2 JWT Token

```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

## 10. 异步支持

### 10.1 异步路径操作

```python
@app.get("/async-items/")
async def read_items():
    results = await some_async_function()
    return results
```

### 10.2 异步数据库

```python
from databases import Database

database = Database("postgresql://user:password@localhost/dbname")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
```

## 11. 中间件

### 11.1 CORS 中间件

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 11.2 自定义中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 请求前处理
        response = await call_next(request)
        # 响应后处理
        return response

app.add_middleware(CustomMiddleware)
```

## 12. 测试

### 12.1 测试客户端

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
```

## 13. 部署

### 13.1 使用 Uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 13.2 使用 Gunicorn

```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### 13.3 Docker 部署

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**文档版本**：v1.0  
**最后更新**：2026年1月  
**官方文档**：https://fastapi.tiangolo.com
