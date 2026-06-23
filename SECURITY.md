# 安全政策

> QueryMind 项目的安全漏洞披露和响应政策

---

## 🔒 支持的版本

我们为以下版本提供安全更新：

| 版本 | 支持状态 |
| --- | --- |
| 0.5.x | ✅ 支持 |
| 0.4.x | ✅ 支持（至 2026-12-31） |
| < 0.4.0 | ❌ 不支持 |

---

## 🐛 报告安全漏洞

### 请勿公开披露

如果你发现了安全漏洞，**请不要**通过公开的 GitHub Issues 报告。

### 私密报告流程

请通过以下方式报告安全问题：

1. **GitHub 私密报告**
   - 访问 [Security Advisories](https://github.com/pocheang/querymind/security/advisories)
   - 点击 "Report a vulnerability"
   - 填写详细信息

2. **邮件报告**（如果无法使用 GitHub）
   - 发送至：security@querymind.example.com
   - 邮件主题：`[SECURITY] 简短描述`

### 报告内容

请在报告中包含以下信息：

- **漏洞类型**：SQL 注入、XSS、CSRF、权限提升等
- **影响范围**：受影响的版本和组件
- **复现步骤**：详细的复现方法
- **影响评估**：可能的安全影响
- **建议修复**：如果有的话
- **概念验证**：PoC 代码或截图（可选）

**示例报告**：
```
漏洞类型: SQL 注入
影响范围: v0.5.0, 文档搜索功能
严重程度: 高

复现步骤:
1. 登录系统
2. 在搜索框输入: ' OR 1=1--
3. 观察返回所有文档

影响: 未授权访问其他用户的文档

建议修复: 使用参数化查询
```

---

## 🔐 安全响应流程

### 响应时间表

| 阶段 | 时间 |
|------|------|
| **初步确认** | 24 小时内 |
| **严重性评估** | 48 小时内 |
| **修复计划** | 72 小时内 |
| **补丁发布** | 根据严重性，见下表 |

### 严重性分级

| 级别 | 描述 | 修复时间 |
|------|------|----------|
| **严重** | 远程代码执行、数据泄露 | 24-48 小时 |
| **高** | 权限提升、身份验证绕过 | 1 周内 |
| **中** | XSS、CSRF、信息泄露 | 2 周内 |
| **低** | 配置问题、安全增强 | 下一个版本 |

### 响应流程

1. **确认**（24h）
   - 确认收到报告
   - 初步评估真实性

2. **评估**（48h）
   - 复现漏洞
   - 评估影响范围和严重性
   - 制定修复计划

3. **修复**（根据严重性）
   - 开发补丁
   - 内部测试
   - 代码审查

4. **发布**
   - 发布修复版本
   - 发布安全公告
   - 更新文档

5. **披露**（修复后 7-14 天）
   - 协调披露时间
   - 致谢报告者
   - 发布 CVE（如适用）

---

## 🛡️ 安全最佳实践

### 部署安全

**生产环境必须**：

1. **使用 HTTPS**
   ```nginx
   server {
       listen 443 ssl http2;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
   }
   ```

2. **强密钥配置**
   ```python
   # 使用强随机密钥
   SECRET_KEY = secrets.token_urlsafe(32)
   ```

3. **环境变量**
   ```bash
   # 不要硬编码密钥
   export OPENAI_API_KEY="your-key"
   export DATABASE_URL="postgresql://..."
   ```

4. **限制 CORS**
   ```python
   CORS_ORIGINS = [
       "https://yourdomain.com"
   ]
   ```

5. **启用速率限制**
   ```python
   RATE_LIMIT_PER_MINUTE = 60
   ```

### 数据库安全

**必须做**：
- ✅ 使用参数化查询（防止 SQL 注入）
- ✅ 加密敏感数据
- ✅ 定期备份
- ✅ 限制数据库访问权限

**不要做**：
- ❌ 硬编码数据库密码
- ❌ 使用默认凭据
- ❌ 暴露数据库端口到公网

### API 安全

**必须做**：
- ✅ 使用 JWT 认证
- ✅ 验证所有输入
- ✅ 实施速率限制
- ✅ 记录审计日志

**不要做**：
- ❌ 在 URL 中传递敏感信息
- ❌ 返回详细的错误信息
- ❌ 允许无限制的文件上传

### 前端安全

**必须做**：
- ✅ 防止 XSS（React 默认转义）
- ✅ 使用 HTTPS
- ✅ 实施 CSP 策略
- ✅ 验证用户输入

**CSP 配置示例**：
```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self'; 
               style-src 'self' 'unsafe-inline';">
```

---

## 🔍 安全审计

### 定期审计

我们定期进行以下安全审计：

- **代码审查** - 每个 PR 都需要审查
- **依赖扫描** - 使用 Dependabot
- **静态分析** - Bandit (Python), ESLint (JS)
- **动态测试** - 定期渗透测试

### 依赖管理

**自动化工具**：
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

### 安全扫描

**Python 依赖扫描**：
```bash
# 检查已知漏洞
pip-audit

# 安全检查
bandit -r app/
```

**JavaScript 依赖扫描**：
```bash
npm audit
npm audit fix
```

---

## 📋 已知安全问题

### 当前活跃问题

无

### 已修复问题

| CVE ID | 版本 | 严重性 | 描述 | 修复版本 |
|--------|------|--------|------|----------|
| - | - | - | 暂无 | - |

---

## 🏆 安全致谢

感谢以下安全研究人员的负责任披露：

| 研究员 | 发现的问题 | 日期 |
|--------|-----------|------|
| - | - | - |

如果你报告了安全问题并希望被列出，请在报告中说明。

---

## 📚 安全资源

### 相关文档

- [配置指南](./docs/zh-CN/guides/configuration.md#安全配置)
- [部署指南](./docs/zh-CN/guides/deployment.md)
- [API 文档](./docs/zh-CN/guides/api-guide.md)

### 外部资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [CVSS 评分系统](https://www.first.org/cvss/)

---

## 📞 联系方式

- **安全邮箱**: security@querymind.example.com
- **GitHub 安全**: [Security Advisories](https://github.com/pocheang/querymind/security/advisories)
- **紧急联系**: 对于严重漏洞，请优先使用 GitHub 私密报告

---

## 📜 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-23 | 1.0 | 初始版本 |

---

<div align="center">

**保护我们的用户是第一优先级** 🔒

感谢你帮助保持 QueryMind 的安全！

[返回主页](./README.md) · [报告安全问题](https://github.com/pocheang/querymind/security/advisories/new)

</div>
