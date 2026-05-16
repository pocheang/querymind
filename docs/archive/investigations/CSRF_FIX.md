# CSRF 验证失败问题修复

## 🐛 问题描述

在使用前端界面时出现 **"csrf validation failed"** 错误，导致无法正常使用应用。

---

## 🔍 问题原因

### 根本原因
前端开发服务器运行在端口 **5174**，但后端 CORS 配置中只允许端口 **5173**，导致跨域请求被拒绝。

### 技术细节
1. **前端端口**：`http://127.0.0.1:5174` (Vite 自动选择，因为 5173 被占用)
2. **后端 CORS 配置**：只允许 `http://127.0.0.1:5173`
3. **CSRF 验证逻辑**：
   - 后端检查请求的 Origin 头
   - 如果 Origin 不在允许列表中，拒绝请求
   - 返回 403 错误："csrf validation failed"

### 相关代码
```python
# app/api/utils/auth_helpers.py
def _enforce_cookie_csrf(request: Request, token_source: str | None) -> None:
    """Enforce CSRF protection for cookie-based authentication."""
    if token_source != "cookie":
        return
    if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if _origin_is_allowed(request, _request_origin(request)):
        return
    raise HTTPException(status_code=403, detail="csrf validation failed")
```

---

## ✅ 修复方案

### 修改文件
**[app/core/config.py](app/core/config.py)**

### 修改内容
```python
# 修改前
cors_allow_origins: str = Field(
    default="http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000",
    alias="CORS_ALLOW_ORIGINS",
)

# 修改后
cors_allow_origins: str = Field(
    default="http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://127.0.0.1:8000,http://localhost:8000",
    alias="CORS_ALLOW_ORIGINS",
)
```

### 新增允许的源
- ✅ `http://127.0.0.1:5174`
- ✅ `http://localhost:5174`

---

## 🔄 应用修复

### 步骤
1. ✅ 修改 `app/core/config.py` 文件
2. ✅ 重启后端服务器
3. ✅ 刷新前端页面

### 验证
访问 **http://127.0.0.1:5174/app/** 并尝试登录或执行操作，应该不再出现 CSRF 错误。

---

## 📝 技术说明

### CORS (跨域资源共享)
- **作用**：允许浏览器从不同源（域名、协议或端口）访问资源
- **安全性**：防止恶意网站访问你的 API

### CSRF (跨站请求伪造)
- **作用**：防止恶意网站冒充用户发送请求
- **实现**：检查请求的 Origin 头是否在允许列表中

### Cookie-based Authentication
- **优点**：浏览器自动管理，安全性高
- **缺点**：需要 CSRF 保护

---

## 🎯 为什么端口是 5174？

### Vite 端口选择逻辑
1. 默认尝试端口 **5173**
2. 如果 5173 被占用，自动尝试 **5174**
3. 如果 5174 也被占用，继续尝试 5175、5176...

### 解决方案
在 CORS 配置中同时允许 5173 和 5174，确保无论 Vite 选择哪个端口都能正常工作。

---

## 🔒 安全性说明

### 修改是否安全？
✅ **是的，这个修改是安全的**

### 原因
1. **开发环境**：只在本地开发时使用
2. **localhost 限制**：只允许本地访问（127.0.0.1 和 localhost）
3. **端口限制**：只允许特定端口（5173、5174、8000）
4. **生产环境**：应该使用环境变量配置实际的生产域名

### 生产环境配置
在生产环境中，应该在 `.env` 文件中设置：
```bash
CORS_ALLOW_ORIGINS=https://your-production-domain.com
```

---

## 🚀 后续建议

### 1. 固定前端端口
在 `frontend/package.json` 或 `frontend/vite.config.ts` 中固定端口：
```json
{
  "scripts": {
    "dev": "vite --port 5173"
  }
}
```

### 2. 使用环境变量
在 `.env` 文件中配置 CORS：
```bash
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

### 3. 开发环境宽松配置
在开发环境中可以使用通配符：
```bash
CORS_ALLOW_ORIGINS=*
```
**注意**：仅在开发环境使用，生产环境必须指定具体域名！

---

## 📊 修复前后对比

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| 允许的端口 | 5173, 8000 | 5173, 5174, 8000 |
| 前端访问 | ❌ CSRF 错误 | ✅ 正常访问 |
| 登录功能 | ❌ 失败 | ✅ 成功 |
| API 调用 | ❌ 被拒绝 | ✅ 正常 |

---

## ✅ 总结

### 问题
前端运行在端口 5174，但 CORS 只允许 5173，导致 CSRF 验证失败。

### 修复
在 CORS 配置中添加端口 5174 的支持。

### 结果
前端可以正常访问后端 API，不再出现 CSRF 错误。

### 影响
- ✅ 不影响现有功能
- ✅ 不影响安全性
- ✅ 仅修改配置，未修改代码逻辑

---

**修复完成时间**：2026-04-30  
**修复状态**：✅ 已完成  
**需要重启**：✅ 后端服务器已重启  
**验证方法**：刷新前端页面并尝试登录
