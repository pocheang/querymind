# 贡献指南

> 感谢你对 QueryMind 项目的关注！我们欢迎所有形式的贡献。

---

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [报告问题](#报告问题)

---

## 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们作为贡献者和维护者承诺：无论年龄、体型、残疾、种族、性别认同和表达、经验水平、教育程度、社会经济地位、国籍、外貌、种族、宗教或性取向如何，参与我们的项目和社区的每个人都不会受到骚扰。

### 我们的标准

**积极行为包括**：
- ✅ 使用友好和包容的语言
- ✅ 尊重不同的观点和经验
- ✅ 优雅地接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表示同情

**不可接受的行为包括**：
- ❌ 使用性化的语言或图像
- ❌ 挑衅、侮辱或贬损性评论
- ❌ 人身或政治攻击
- ❌ 公开或私下骚扰
- ❌ 未经明确许可发布他人的私人信息

---

## 如何贡献

### 贡献方式

你可以通过以下方式为 QueryMind 做出贡献：

1. **🐛 报告 Bug** - 发现问题并提交 Issue
2. **💡 提出新功能** - 分享你的想法和建议
3. **📝 改进文档** - 完善或翻译文档
4. **💻 提交代码** - 修复 Bug 或实现新功能
5. **🧪 编写测试** - 提高代码覆盖率
6. **🎨 UI/UX 改进** - 优化用户界面和体验
7. **🌍 翻译** - 添加多语言支持

---

## 开发流程

### 1. Fork 项目

```bash
# 访问 GitHub 页面并点击 "Fork" 按钮
# 然后克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/querymind.git
cd querymind
```

### 2. 设置开发环境

**后端环境**：
```bash
# 创建虚拟环境
conda create -n rag-local python=3.11 -y
conda activate rag-local

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

**前端环境**：
```bash
cd frontend
npm install
```

### 3. 添加上游仓库

```bash
git remote add upstream https://github.com/pocheang/querymind.git
```

### 4. 创建功能分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

**分支命名规范**：
- `feature/功能名称` - 新功能
- `fix/问题描述` - Bug 修复
- `docs/文档主题` - 文档改进
- `refactor/重构范围` - 代码重构
- `test/测试内容` - 测试相关

### 5. 开发和测试

```bash
# 后端开发
uvicorn app.api.main:app --reload

# 前端开发
cd frontend && npm run dev

# 运行测试
pytest tests/
npm test  # 前端测试
```

### 6. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
```

### 7. 推送到你的 Fork

```bash
git push origin feature/your-feature-name
```

### 8. 创建 Pull Request

访问 GitHub 并创建 Pull Request。

---

## 代码规范

### Python 代码规范

遵循 **PEP 8** 和 **Black** 格式化：

```python
# 好的示例
def calculate_similarity(query: str, documents: List[str]) -> List[float]:
    """计算查询与文档的相似度
    
    Args:
        query: 查询字符串
        documents: 文档列表
        
    Returns:
        相似度分数列表
    """
    scores = []
    for doc in documents:
        score = compute_score(query, doc)
        scores.append(score)
    return scores
```

**代码检查工具**：
```bash
# 格式化代码
black app/

# 排序 imports
isort app/

# 类型检查
mypy app/

# 代码检查
pylint app/
```

### TypeScript/React 代码规范

遵循 **ESLint** 和 **Prettier**：

```typescript
// 好的示例
interface User {
  id: number;
  username: string;
  role: 'viewer' | 'analyst';
}

export const UserProfile: React.FC<{ userId: number }> = ({ userId }) => {
  const [user, setUser] = useState<User | null>(null);
  
  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);
  
  if (!user) return <Loading />;
  
  return (
    <div className="user-profile">
      <h2>{user.username}</h2>
      <Badge role={user.role} />
    </div>
  );
};
```

**代码检查**：
```bash
cd frontend

# 格式化
npm run format

# 检查
npm run lint

# 类型检查
npm run type-check
```

---

## 提交规范

我们使用 **Conventional Commits** 规范：

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add user authentication` |
| `fix` | Bug 修复 | `fix: resolve CORS issue` |
| `docs` | 文档更新 | `docs: update API documentation` |
| `style` | 代码格式 | `style: format with black` |
| `refactor` | 重构 | `refactor: simplify query logic` |
| `test` | 测试 | `test: add unit tests for auth` |
| `chore` | 构建/工具 | `chore: update dependencies` |
| `perf` | 性能优化 | `perf: optimize vector search` |

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**示例**：
```bash
feat(auth): add JWT token refresh mechanism

- Implement refresh token endpoint
- Add token expiration handling
- Update frontend to use refresh tokens

Closes #123
```

### 提交消息规则

1. **标题行**（必需）
   - 使用祈使句（"add" 不是 "added"）
   - 不超过 72 个字符
   - 首字母小写
   - 结尾不加句号

2. **正文**（可选）
   - 解释"为什么"而不是"是什么"
   - 详细描述变更内容
   - 空行分隔标题和正文

3. **页脚**（可选）
   - 引用相关 Issue：`Closes #123`
   - 标记破坏性变更：`BREAKING CHANGE: ...`

---

## Pull Request 流程

### PR 检查清单

在提交 PR 之前，请确认：

- [ ] 代码遵循项目的代码规范
- [ ] 已添加必要的测试
- [ ] 所有测试都通过
- [ ] 已更新相关文档
- [ ] 提交消息遵循 Conventional Commits
- [ ] 没有合并冲突
- [ ] PR 描述清晰完整

### PR 描述模板

```markdown
## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 重构
- [ ] 性能优化

## 变更说明
简要描述此 PR 的目的和实现方式。

## 相关 Issue
Closes #issue_number

## 测试
描述你如何测试了这些变更。

## 截图（如适用）
添加截图以展示 UI 变更。

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已添加测试
- [ ] 所有测试通过
- [ ] 已更新文档
```

### PR 审查流程

1. **提交 PR** - 填写完整的 PR 描述
2. **自动检查** - CI/CD 自动运行测试
3. **代码审查** - 维护者审查代码
4. **反馈修改** - 根据反馈修改代码
5. **批准合并** - 审查通过后合并

### PR 合并要求

- ✅ 至少 1 个维护者批准
- ✅ 所有 CI 检查通过
- ✅ 没有未解决的讨论
- ✅ 代码符合项目标准
- ✅ 文档已更新

---

## 报告问题

### Bug 报告

使用 [Bug Report 模板](https://github.com/pocheang/querymind/issues/new?template=bug_report.md)

**包含以下信息**：
1. **描述** - 清楚简洁地描述 Bug
2. **复现步骤** - 详细的复现步骤
3. **期望行为** - 应该发生什么
4. **实际行为** - 实际发生了什么
5. **环境** - 操作系统、Python 版本、浏览器等
6. **截图** - 如果适用
7. **日志** - 相关的错误日志

**示例**：
```markdown
## Bug 描述
用户登录后无法上传 PDF 文件

## 复现步骤
1. 登录系统
2. 进入文档管理页面
3. 点击"上传文档"
4. 选择 PDF 文件
5. 点击"确认上传"

## 期望行为
文件应该成功上传并显示处理进度

## 实际行为
显示错误消息："文件上传失败"

## 环境
- OS: Windows 10
- Python: 3.11.5
- Browser: Chrome 120
- QueryMind: v0.5.0

## 错误日志
```
ERROR: Failed to upload file: Permission denied
```
```

### 功能请求

使用 [Feature Request 模板](https://github.com/pocheang/querymind/issues/new?template=feature_request.md)

**包含以下信息**：
1. **功能描述** - 你想要什么功能
2. **使用场景** - 为什么需要这个功能
3. **解决方案** - 你期望的实现方式
4. **替代方案** - 其他可能的解决方案
5. **额外信息** - 其他相关信息

---

## 开发提示

### 有用的命令

**后端开发**：
```bash
# 运行开发服务器
uvicorn app.api.main:app --reload --port 8000

# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest --cov=app tests/

# 代码检查
black app/ && isort app/ && pylint app/
```

**前端开发**：
```bash
# 开发服务器
npm run dev

# 构建
npm run build

# 测试
npm test

# 代码检查
npm run lint && npm run type-check
```

**数据库**：
```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head
```

### 调试技巧

**后端调试**：
```python
# 添加调试日志
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Query: {query}")
```

**前端调试**：
```typescript
// 使用 React DevTools
console.log('Debug:', { user, permissions });
```

---

## 资源链接

- 📖 [完整文档](./docs/zh-CN/README.md)
- 🏗️ [系统架构](./docs/zh-CN/guides/architecture.md)
- 💻 [开发者指南](./docs/zh-CN/guides/development.md)
- 📡 [API 文档](./docs/zh-CN/guides/api-guide.md)
- 🐛 [故障排查](./docs/zh-CN/guides/troubleshooting.md)

---

## 联系我们

- 📋 **Issues**: [GitHub Issues](https://github.com/pocheang/querymind/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/pocheang/querymind/discussions)
- 📧 **Email**: 项目维护者邮箱

---

## 许可证

通过贡献代码，你同意你的贡献将在 [MIT License](./LICENSE) 下授权。

---

<div align="center">

**感谢你的贡献！ 🎉**

[返回主页](./README.md) · [查看文档](./docs/zh-CN/README.md)

</div>
