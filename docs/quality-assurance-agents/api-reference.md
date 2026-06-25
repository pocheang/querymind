# API 使用指南

## 概述

Quality Assurance Agents 系统提供增强的查询 API，集成了完整的质量验证和上下文跟踪功能。

## API 端点

### 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证**: 根据系统配置
- **Content-Type**: `application/json`

### 端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/enhanced/query` | POST | 增强查询（含质量验证） |
| `/enhanced/health` | GET | 健康检查 |
| `/enhanced/config` | GET | 配置信息 |

---

## POST /enhanced/query

### 请求

#### 请求体

```json
{
  "query": "string (必需)",
  "session_id": "string (可选)",
  "user_id": "string (可选)",
  "agent_class_hint": "string (可选)",
  "enable_quality_validation": "boolean (可选，默认 true)",
  "enable_context_tracking": "boolean (可选，默认 true)",
  "max_retries": "integer (可选，默认 2)"
}
```

#### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 用户查询内容 |
| `session_id` | string | ❌ | 自动生成 | 会话 ID，用于多轮对话 |
| `user_id` | string | ❌ | "anonymous" | 用户 ID |
| `agent_class_hint` | string | ❌ | null | Agent 类型提示 (general/cybersecurity/...) |
| `enable_quality_validation` | boolean | ❌ | true | 是否启用质量验证 |
| `enable_context_tracking` | boolean | ❌ | true | 是否启用上下文跟踪 |
| `max_retries` | integer | ❌ | 2 | 最大重试次数 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/v1/enhanced/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "张三和李四有什么关系？",
    "session_id": "session_123",
    "enable_quality_validation": true,
    "enable_context_tracking": true
  }'
```

### 响应

#### 成功响应 (200 OK)

```json
{
  "answer": "根据文档，张三是李四的项目经理。他们在同一个开发团队中工作。",
  "citations": [
    {
      "doc_id": "doc_001",
      "title": "团队组织结构",
      "score": 0.92,
      "snippet": "张三担任项目经理，管理包括李四在内的开发团队..."
    },
    {
      "doc_id": "doc_002",
      "title": "项目分工",
      "score": 0.88,
      "snippet": "李四作为开发工程师，向项目经理张三汇报..."
    }
  ],
  "quality_report": {
    "overall_confidence": 0.87,
    "quality_level": "high",
    "quality_label": "高质量",
    "user_prompt": null,
    "breakdown": {
      "route_decision": {
        "score": 0.92,
        "status": "✓ 通过"
      },
      "retrieval": {
        "score": 0.85,
        "status": "✓ 良好"
      },
      "answer_factuality": {
        "score": 0.88,
        "status": "✓ 可信"
      },
      "citations": {
        "score": 0.90,
        "status": "✓ 完整"
      }
    },
    "issues": [],
    "suggestions": [],
    "execution_stats": {
      "total_time_ms": 2350,
      "validation_overhead_ms": 178,
      "retry_count": 0,
      "route_retry": 0,
      "answer_retry": 0
    }
  },
  "metadata": {
    "route": "graph",
    "skill": "compare_entities",
    "agent_class": "general",
    "model": "gpt-4",
    "timestamp": "2026-06-25T10:30:00Z"
  },
  "session_id": "session_123"
}
```

#### 响应字段说明

##### 根级别字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 生成的答案 |
| `citations` | array | 引用来源列表 |
| `quality_report` | object | 质量评估报告 |
| `metadata` | object | 元数据信息 |
| `session_id` | string | 会话 ID |

##### quality_report 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `overall_confidence` | float | 综合置信度 (0.0-1.0) |
| `quality_level` | string | 质量等级: "high" / "medium" / "low" / "very_low" |
| `quality_label` | string | 质量标签 (中文) |
| `user_prompt` | string / null | 用户提示信息（低质量时显示） |
| `breakdown` | object | 各组件评分详情 |
| `issues` | array | 问题列表 |
| `suggestions` | array | 改进建议 |
| `execution_stats` | object | 执行统计 |

##### breakdown 详情

| 组件 | score | status |
|------|-------|--------|
| `route_decision` | 路由决策置信度 | ✓/⚠ 状态 |
| `retrieval` | 检索质量分数 | ✓/⚠ 状态 |
| `answer_factuality` | 答案事实性分数 | ✓/⚠ 状态 |
| `citations` | 引用完整性分数 | ✓/⚠ 状态 |

#### 错误响应

##### 400 Bad Request

```json
{
  "detail": "Query is required and must not be empty"
}
```

##### 500 Internal Server Error

```json
{
  "detail": "Internal server error: [error message]"
}
```

---

## GET /enhanced/health

### 请求

```bash
curl -X GET "http://localhost:8000/api/v1/enhanced/health"
```

### 响应

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "quality_validation": {
    "enabled": true,
    "agents": ["route_validator", "retrieval_quality", "answer_validator", "quality_orchestrator", "context_tracker"]
  },
  "nli_model": {
    "loaded": true,
    "name": "cross-encoder/nli-MiniLM2-L6-H768"
  }
}
```

---

## GET /enhanced/config

### 请求

```bash
curl -X GET "http://localhost:8000/api/v1/enhanced/config"
```

### 响应

```json
{
  "quality_validation": {
    "enabled": true,
    "thresholds": {
      "route_high_confidence": 0.85,
      "answer_fast_path": 0.80,
      "hallucination_high_risk": 0.30
    }
  },
  "context_tracking": {
    "enabled": true,
    "max_history_turns": 10,
    "ttl_seconds": 3600
  },
  "retry_strategy": {
    "max_route_retries": 1,
    "max_answer_retries": 1,
    "max_total_time_ms": 10000
  }
}
```

---

## 完整使用示例

### Python 示例

```python
import requests
import json

class QueryMindClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def query(self, query_text, **kwargs):
        """发送增强查询"""
        url = f"{self.base_url}/api/v1/enhanced/query"
        
        payload = {
            "query": query_text,
            "session_id": self.session_id,
            **kwargs
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # 保存 session_id 用于后续对话
        self.session_id = result.get("session_id")
        
        return result
    
    def print_result(self, result):
        """格式化打印结果"""
        print(f"\n{'='*60}")
        print(f"答案: {result['answer']}")
        print(f"\n质量评分: {result['quality_report']['overall_confidence']:.2f}")
        print(f"质量等级: {result['quality_report']['quality_label']}")
        
        if result['quality_report']['user_prompt']:
            print(f"⚠️ {result['quality_report']['user_prompt']}")
        
        print(f"\n执行时间: {result['quality_report']['execution_stats']['total_time_ms']}ms")
        print(f"验证开销: {result['quality_report']['execution_stats']['validation_overhead_ms']}ms")
        
        if result['citations']:
            print(f"\n引用来源 ({len(result['citations'])} 个):")
            for i, citation in enumerate(result['citations'][:3], 1):
                print(f"  {i}. {citation['title']} (相关性: {citation['score']:.2f})")
        
        print(f"{'='*60}\n")

# 使用示例
client = QueryMindClient()

# 第一个查询
result1 = client.query("什么是机器学习？")
client.print_result(result1)

# 跟进查询 (使用相同 session_id)
result2 = client.query("它有哪些应用场景？")
client.print_result(result2)

# 禁用质量验证的快速查询
result3 = client.query(
    "快速查询测试",
    enable_quality_validation=False
)
client.print_result(result3)
```

### JavaScript/Node.js 示例

```javascript
const axios = require('axios');

class QueryMindClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.sessionId = null;
  }

  async query(queryText, options = {}) {
    const url = `${this.baseURL}/api/v1/enhanced/query`;
    
    const payload = {
      query: queryText,
      session_id: this.sessionId,
      ...options
    };

    try {
      const response = await axios.post(url, payload);
      this.sessionId = response.data.session_id;
      return response.data;
    } catch (error) {
      console.error('Query failed:', error.response?.data || error.message);
      throw error;
    }
  }

  printResult(result) {
    console.log('\n' + '='.repeat(60));
    console.log(`答案: ${result.answer}`);
    console.log(`\n质量评分: ${result.quality_report.overall_confidence.toFixed(2)}`);
    console.log(`质量等级: ${result.quality_report.quality_label}`);
    
    if (result.quality_report.user_prompt) {
      console.log(`⚠️ ${result.quality_report.user_prompt}`);
    }
    
    console.log(`\n执行时间: ${result.quality_report.execution_stats.total_time_ms}ms`);
    console.log(`验证开销: ${result.quality_report.execution_stats.validation_overhead_ms}ms`);
    
    if (result.citations && result.citations.length > 0) {
      console.log(`\n引用来源 (${result.citations.length} 个):`);
      result.citations.slice(0, 3).forEach((citation, i) => {
        console.log(`  ${i+1}. ${citation.title} (相关性: ${citation.score.toFixed(2)})`);
      });
    }
    
    console.log('='.repeat(60) + '\n');
  }
}

// 使用示例
(async () => {
  const client = new QueryMindClient();

  // 第一个查询
  const result1 = await client.query('什么是机器学习？');
  client.printResult(result1);

  // 跟进查询
  const result2 = await client.query('它有哪些应用场景？');
  client.printResult(result2);
})();
```

### cURL 完整示例

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

# 健康检查
echo "=== Health Check ==="
curl -s "$BASE_URL/enhanced/health" | jq '.'

# 查询
echo -e "\n=== Query ==="
curl -s -X POST "$BASE_URL/enhanced/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "张三和李四有什么关系？",
    "enable_quality_validation": true,
    "enable_context_tracking": true
  }' | jq '{
    answer: .answer,
    confidence: .quality_report.overall_confidence,
    quality: .quality_report.quality_label,
    time_ms: .quality_report.execution_stats.total_time_ms,
    citations: .citations | length
  }'
```

---

## 质量等级说明

| 等级 | confidence | 标签 | 用户提示 |
|------|-----------|------|---------|
| `high` | ≥0.85 | 高质量 | null (无需提示) |
| `medium` | 0.70-0.85 | 中等质量 | "答案质量中等，建议结合其他来源验证" |
| `low` | 0.50-0.70 | 低质量 | "答案质量较低，请谨慎参考，建议人工核实" |
| `very_low` | <0.50 | 极低质量 | "⚠️ 答案可能不准确，强烈建议人工审核" |

---

## 最佳实践

### 1. 多轮对话

保持 `session_id` 一致以获得更好的上下文理解：

```python
# ✅ 好的做法
client.query("张三是谁？")
client.query("他的职位是什么？")  # 自动解析"他"指张三

# ❌ 不好的做法
client.query("张三是谁？")
# 不保存 session_id，重新创建 client
new_client.query("他的职位是什么？")  # 无法理解"他"是谁
```

### 2. 处理低质量答案

```python
result = client.query("复杂查询")

if result['quality_report']['quality_level'] in ['low', 'very_low']:
    # 提醒用户
    print(f"⚠️ {result['quality_report']['user_prompt']}")
    
    # 查看具体问题
    for issue in result['quality_report']['issues']:
        print(f"- {issue['message']}")
    
    # 考虑人工审核或重新查询
```

### 3. 性能优化

对于不需要高质量保证的场景，可以禁用质量验证：

```python
# 快速查询（牺牲质量换取速度）
result = client.query(
    "简单查询",
    enable_quality_validation=False
)
```

### 4. 错误处理

```python
try:
    result = client.query("查询内容")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("请求参数错误")
    elif e.response.status_code == 500:
        print("服务器错误，请稍后重试")
    else:
        print(f"未知错误: {e}")
```

---

## 相关文档

- [系统架构](./README.md)
- [配置指南](./configuration.md)
- [性能优化](./performance.md)
