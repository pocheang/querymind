# 🔒 全局模型覆盖功能说明

> 管理员可以强制所有用户使用统一的模型配置

---

## 📋 功能概述

当管理员启用「全局模型覆盖」后，系统将强制所有用户使用管理员配置的模型，用户的个人模型设置将被忽略。

---

## 🎯 优先级规则

### ✅ 已实现的优先级（v0.5.1+）

```
管理员全局设置（启用时） > 用户个人设置 > 环境变量默认值
```

**说明：**
1. **管理员全局设置启用时**：所有用户强制使用管理员配置的模型
2. **管理员全局设置禁用时**：用户可以使用自己的个人设置
3. **用户未配置时**：使用环境变量中的默认值

---

## 🔧 实现细节

### 后端逻辑 (`app/core/models.py`)

#### **修改前（旧逻辑）**
```python
def get_chat_model(temperature: float | None = None):
    settings = get_settings()
    # 用户设置优先于全局设置
    override = _request_chat_override() or _global_chat_override()
    if override:
        # 使用覆盖配置
        ...
```

**问题**：用户个人设置优先于管理员全局设置，管理员无法强制统一配置。

#### **修改后（新逻辑）**
```python
def get_chat_model(temperature: float | None = None):
    settings = get_settings()
    # 优先级：全局设置（启用时） > 用户设置 > 环境变量
    global_override = _global_chat_override()
    user_override = _request_chat_override()
    override = global_override or user_override
    if override:
        # 使用覆盖配置
        ...
```

**改进**：
- ✅ 全局设置优先检查
- ✅ 全局设置启用时，用户设置被忽略
- ✅ 全局设置禁用时，用户设置正常工作

### 覆盖函数说明

#### `_global_chat_override()` - 全局聊天模型覆盖
```python
def _global_chat_override() -> dict:
    raw = get_global_model_settings()
    # 检查是否启用
    if not bool(raw.get("enabled", False)):
        return {}  # 未启用，返回空字典
    
    # 返回全局配置
    return {
        "provider": "deepseek",
        "model": "deepseek-v4",
        "api_key": "...",
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.7,
        "max_tokens": 2048,
    }
```

#### `_global_reasoning_override()` - 全局推理模型覆盖
```python
def _global_reasoning_override() -> dict:
    raw = get_global_model_settings()
    if not bool(raw.get("enabled", False)):
        return {}
    
    # 使用 reasoning_model 或回退到 chat_model
    model = raw.get("reasoning_model") or raw.get("chat_model")
    return {
        "provider": "deepseek",
        "model": "deepseek-r1",  # 推理专用模型
        ...
    }
```

#### `_global_embedding_override()` - 全局嵌入模型覆盖
```python
def _global_embedding_override() -> dict:
    raw = get_global_model_settings()
    if not bool(raw.get("enabled", False)):
        return {}
    
    # Embedding 模型配置
    return {
        "provider": "openai",
        "model": "text-embedding-3-small",
        ...
    }
```

---

## 🎛️ 管理员操作指南

### 步骤 1: 访问管理后台

1. 以管理员身份登录系统
2. 点击导航栏的「管理」
3. 进入「全局模型配置」页面

### 步骤 2: 配置全局模型

#### **配置项说明**

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **启用全局覆盖** | 是否强制所有用户使用此配置 | ✅ 启用 |
| **Backend Type** | 模型提供商 | DeepSeek |
| **API Key** | 提供商 API 密钥 | `sk-...` |
| **Base URL** | API 端点地址 | `https://api.deepseek.com/v1` |
| **Chat Model** | 聊天对话模型 | `deepseek-v4` |
| **Reasoning Model** | 复杂推理模型 | `deepseek-r1` |
| **Embedding Model** | 文本嵌入模型 | `text-embedding-3-small` |
| **Temperature** | 生成温度 (0-2) | `0.7` |
| **Max Tokens** | 最大输出长度 | `2048` |

#### **推荐配置示例**

##### ⭐ 方案 1: DeepSeek V4（高性价比）
```
启用全局覆盖: ✅
Backend Type: deepseek
API Key: sk-your-deepseek-key
Base URL: https://api.deepseek.com/v1
Chat Model: deepseek-v4
Reasoning Model: deepseek-r1
Embedding Model: text-embedding-3-small
Temperature: 0.7
Max Tokens: 2048
```

**适用场景**：成本敏感、中文任务为主、高性价比需求

##### 🚀 方案 2: GPT-5.5（最强能力）
```
启用全局覆盖: ✅
Backend Type: openai
API Key: sk-your-openai-key
Base URL: https://api.openai.com/v1
Chat Model: gpt-5.5
Reasoning Model: gpt-5.5-thinking
Embedding Model: text-embedding-3-small
Temperature: 0.7
Max Tokens: 2048
```

**适用场景**：追求极致质量、复杂推理任务、预算充足

##### 📚 方案 3: Claude Opus 4.8（长上下文）
```
启用全局覆盖: ✅
Backend Type: anthropic
API Key: sk-ant-your-key
Base URL: https://api.anthropic.com
Chat Model: claude-opus-4-8
Reasoning Model: claude-opus-4-8
Embedding Model: (留空，使用 OpenAI)
Temperature: 0.7
Max Tokens: 2048
```

**适用场景**：长文档分析、代码审查、企业级应用

##### 🖥️ 方案 4: Ollama 本地部署
```
启用全局覆盖: ✅
Backend Type: ollama
API Key: (留空)
Base URL: http://localhost:11434
Chat Model: qwen3:14b
Reasoning Model: deepseek-r1:32b
Embedding Model: nomic-embed-text
Temperature: 0.7
Max Tokens: 2048
```

**适用场景**：私有化部署、数据安全敏感、无需外网

### 步骤 3: 测试连接

1. 配置完成后，点击「连接测试」按钮
2. 系统会验证：
   - API Key 是否有效
   - Base URL 是否可达
   - 模型是否存在
   - 网络延迟
3. 测试成功后显示：
   ```
   ✅ 连接成功
   Provider: deepseek
   Model: deepseek-v4
   Latency: 245ms
   Preview: 你好！我是...
   ```

### 步骤 4: 保存并启用

1. 点击「保存配置」按钮
2. 确保「启用全局模型覆盖」已勾选 ✅
3. 配置立即生效，所有用户的下一次查询将使用新配置

---

## 👥 用户体验

### 当全局覆盖启用时

#### **用户个人设置界面**

用户仍然可以看到自己的 API 设置页面，但会显示提示信息：

```
ℹ️ 提示：管理员已启用全局模型配置
当前系统使用管理员配置的模型：deepseek-v4
您的个人设置将被忽略，直到管理员禁用全局配置。
```

**注意**：用户仍然可以保存自己的个人设置，但这些设置不会生效，直到管理员禁用全局覆盖。

#### **查询行为**

```python
# 用户 A 的个人设置：gpt-4o
# 用户 B 的个人设置：claude-sonnet-4-6
# 管理员全局设置：deepseek-v4 (已启用)

# 结果：两个用户都使用 deepseek-v4
用户 A 查询 → 使用 deepseek-v4 ✅
用户 B 查询 → 使用 deepseek-v4 ✅
```

### 当全局覆盖禁用时

```python
# 管理员全局设置：(已禁用)
# 用户 A 的个人设置：gpt-4o
# 用户 B 的个人设置：claude-sonnet-4-6

# 结果：用户各自使用自己的设置
用户 A 查询 → 使用 gpt-4o ✅
用户 B 查询 → 使用 claude-sonnet-4-6 ✅
```

---

## 🔍 监控与验证

### 查看当前生效的模型

#### 方法 1: 管理后台查看

访问 `/admin` → 全局模型配置 → 查看当前状态卡片：

```
┌─────────────────────────────┐
│ 全局覆盖: 已启用            │
│ Backend: deepseek           │
│ Chat Model: deepseek-v4     │
│ Embedding Model: text-...   │
└─────────────────────────────┘
```

#### 方法 2: 用户查询时查看

在查询结果的「代理执行追踪」中，可以看到使用的模型：

```
🤖 Router Agent
   Model: deepseek-v4
   Provider: deepseek
   Temperature: 0.7
   Latency: 1.2s
```

#### 方法 3: 日志文件

后端日志会记录模型选择过程：

```log
[INFO] Model override: global_enabled=True, provider=deepseek, model=deepseek-v4
[INFO] User john requested query, using global model: deepseek-v4
```

---

## 🛡️ 安全特性

### 1. API Key 加密存储

管理员配置的 API Key 会加密存储在数据库中：

```python
# 存储时加密
encrypted_key = encrypt(api_key, encryption_key)

# 使用时解密
api_key = decrypt(encrypted_key, encryption_key)
```

### 2. API Key 不回显

前端显示时，API Key 会被掩码：

```
保存的 API Key: sk-****************************xyz
```

### 3. 权限控制

- ✅ 只有管理员可以查看和修改全局模型配置
- ✅ 普通用户只能查看自己的个人设置
- ✅ 访客无法查看任何模型配置

### 4. 安全边界

管理员配置的安全提示：

```
🔒 安全边界
• API Key 不会回显 - 加密存储在服务器
• 私网 URL 被拦截 - 防止 SSRF 攻击
• 个人设置隔离 - 用户无法访问全局配置
```

---

## 📊 使用场景

### 场景 1: 统一企业标准

**需求**：公司要求所有部门使用统一的 AI 模型供应商（如 DeepSeek）以控制成本。

**方案**：
1. 管理员配置全局 DeepSeek V4
2. 启用全局覆盖
3. 所有用户自动使用 DeepSeek，个人设置失效

### 场景 2: 临时切换模型

**需求**：OpenAI API 故障，需要临时切换到备用供应商。

**方案**：
1. 管理员快速配置全局 Claude Opus 4.8
2. 启用全局覆盖
3. 所有用户立即切换到 Claude，无需通知每个用户修改设置

### 场景 3: 成本控制实验

**需求**：测试使用更便宜的模型是否满足业务需求。

**方案**：
1. 周一：启用全局 DeepSeek V4（低成本）
2. 监控一周的用户满意度和答案质量
3. 周五：如果效果不佳，切换回 GPT-5.5

### 场景 4: 新模型灰度发布

**需求**：测试新发布的 GPT-5.5 模型表现。

**方案**：
1. 初期：保持全局覆盖禁用，仅内部测试用户配置 GPT-5.5
2. 中期：启用全局覆盖，强制 10% 用户使用 GPT-5.5
3. 稳定后：全量发布，所有用户使用 GPT-5.5

### 场景 5: 本地化部署

**需求**：政府或金融客户要求数据不出境，必须使用本地 Ollama。

**方案**：
1. 部署 Ollama 服务器（内网）
2. 管理员配置全局 Ollama + Qwen3:14b
3. 启用全局覆盖，强制所有数据本地处理

---

## 🔄 切换流程

### 启用全局覆盖

```
步骤 1: 配置全局模型设置
↓
步骤 2: 点击「连接测试」验证
↓
步骤 3: 勾选「启用全局模型覆盖」✅
↓
步骤 4: 点击「保存配置」
↓
✅ 完成：所有用户立即使用全局配置
```

### 禁用全局覆盖

```
步骤 1: 访问管理后台
↓
步骤 2: 取消勾选「启用全局模型覆盖」❌
↓
步骤 3: 点击「保存配置」
↓
✅ 完成：用户恢复使用个人设置
```

---

## 🧪 测试验证

### 测试脚本

```python
# test_global_override.py

import requests

BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "your-admin-token"
USER_TOKEN = "your-user-token"

# 1. 启用全局覆盖
def test_enable_global_override():
    response = requests.post(
        f"{BASE_URL}/admin/model-settings",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={
            "enabled": True,
            "provider": "deepseek",
            "api_key": "sk-...",
            "base_url": "https://api.deepseek.com/v1",
            "chat_model": "deepseek-v4",
            "reasoning_model": "deepseek-r1",
            "embedding_model": "text-embedding-3-small",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
    )
    assert response.json()["ok"] == True
    print("✅ 全局覆盖已启用")

# 2. 用户查询（应使用全局模型）
def test_user_query_with_override():
    response = requests.post(
        f"{BASE_URL}/api/query",
        headers={"Authorization": f"Bearer {USER_TOKEN}"},
        json={"question": "测试问题", "session_id": "test"}
    )
    # 检查响应中使用的模型
    assert "deepseek-v4" in str(response.json())
    print("✅ 用户查询使用了全局模型")

# 3. 禁用全局覆盖
def test_disable_global_override():
    response = requests.post(
        f"{BASE_URL}/admin/model-settings",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"enabled": False}
    )
    assert response.json()["ok"] == True
    print("✅ 全局覆盖已禁用")

if __name__ == "__main__":
    test_enable_global_override()
    test_user_query_with_override()
    test_disable_global_override()
    print("\n🎉 所有测试通过！")
```

---

## 📝 更新日志

### v0.5.1 (2026-06-23)

**新增功能：**
- ✅ 管理员全局模型覆盖优先级调整
- ✅ 全局设置启用时强制所有用户使用统一模型
- ✅ 支持独立配置聊天模型、推理模型、嵌入模型

**修改文件：**
- `app/core/models.py` - 调整模型选择优先级逻辑
  - `get_chat_model()` - 全局设置优先
  - `get_reasoning_model()` - 全局设置优先
  - `get_embedding_model()` - 保持原有逻辑（仅全局）

**影响：**
- ✅ 向后兼容，不影响现有配置
- ✅ 全局覆盖禁用时，行为与之前完全一致
- ✅ 全局覆盖启用时，管理员配置优先生效

---

## 🔗 相关文档

- [模型配置升级报告](./MODEL_CONFIG_UPGRADE_2026.md) - 2026 最新模型支持
- [MODELS.md](./MODELS.md) - 所有支持的模型列表
- [配置指南](./docs/zh-CN/guides/configuration.md) - 详细配置说明
- [管理员手册](./docs/zh-CN/guides/admin-manual.md) - 管理员操作指南

---

<div align="center">

**🎯 现在管理员可以统一控制所有用户的模型配置了！**

[返回主页](./README.md) · [模型升级报告](./MODEL_CONFIG_UPGRADE_2026.md)

</div>
