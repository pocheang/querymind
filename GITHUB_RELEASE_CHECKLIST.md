# GitHub 发布准备清单 - v0.6.0

**准备日期：** 2026-06-28  
**目标版本：** v0.6.0  
**发布类型：** 公开发布  

---

## ✅ 已完成项

### 文档分类和整理
- [x] 完成56份文档分类（32公开，24私有）
- [x] 创建发布策略文档（GITHUB_PUBLICATION_STRATEGY.md）
- [x] 识别需要脱敏的内容
- [x] 制定安全审查指南

### 公开文档准备
- [x] 创建公开版README（README_PUBLIC.md）
- [x] 更新社区行为准则（CODE_OF_CONDUCT.md）
- [x] 简化贡献指南（CONTRIBUTING.md）
- [x] 更新安全政策（SECURITY.md）

### 版本文档更新
- [x] 更新所有版本号至v0.6.0
- [x] 创建完整发布说明（RELEASE_NOTES_v0.6.0.md）
- [x] 更新VERSION_HISTORY.md
- [x] 更新docs/releases/README.md

### Git管理
- [x] 创建v0.6.0标签
- [x] 提交40个commits
- [x] 文档全部同步

---

## 📋 发布前检查清单

### 必须完成（Critical）

#### 1. README处理
- [ ] **决策：使用README.md还是README_PUBLIC.md**
  - 选项A：替换现有README.md为public版本
  - 选项B：保持两个版本，发布时选择
  - 推荐：选项A，公开发布应该用简化版

- [ ] **README.md最终审查**
  - [ ] 移除所有内部任务编号（Task 1-20）
  - [ ] 移除精确的内部指标
  - [ ] 移除开发过程细节
  - [ ] 验证所有链接有效
  - [ ] 添加徽章（stars, forks, license）

#### 2. CHANGELOG脱敏
- [ ] **精简v0.6.0条目**
  - [ ] 移除"Task X"引用
  - [ ] 移除commit哈希
  - [ ] 保留用户相关变更
  - [ ] 简化技术细节

- [ ] **历史版本检查**
  - [ ] v0.5.0条目审查
  - [ ] v0.4.x条目审查
  - [ ] 移除敏感信息

#### 3. 配置文件审查
- [ ] **config/ 目录**
  - [ ] 确认敏感配置不在仓库中
  - [ ] 使用.env.example替代.env
  - [ ] 移除内部校准数据
  - [ ] 提供配置模板

#### 4. 代码审查
- [ ] **移除调试代码**
  - [ ] print/console.log语句
  - [ ] 临时测试代码
  - [ ] 注释掉的代码

- [ ] **移除硬编码信息**
  - [ ] API密钥
  - [ ] 内部URL
  - [ ] 数据库连接字符串

#### 5. 测试数据清理
- [ ] **tests/ 目录**
  - [ ] 移除tests/golden_dataset.json（内部）
  - [ ] 移除scripts/create_golden_dataset.py（内部）
  - [ ] 保留示例测试代码
  - [ ] 提供测试文档

#### 6. .gitignore检查
- [ ] **添加忽略规则**
  ```
  # 内部文档
  .superpowers/
  *_INTERNAL.md
  *_PRIVATE.md
  
  # 测试数据
  tests/golden_dataset.json
  
  # 配置
  config/router_calibration.json
  config/circuit_breaker.json
  config/retry_policy.json
  config/fact_verification.json
  
  # 项目管理
  DOCUMENTATION_INDEX.md
  DOCUMENTATION_CHECKLIST.md
  DELIVERY_CHECKLIST.md
  PROJECT_*.txt
  PROJECT_*.md
  DOCUMENTATION_UPDATE_SUMMARY.txt
  ```

---

### 重要项（Important）

#### 7. 文档链接检查
- [ ] README中的链接
- [ ] CHANGELOG中的链接
- [ ] docs/中的交叉引用
- [ ] 发布说明中的链接

#### 8. 许可证审查
- [ ] 确认LICENSE文件存在
- [ ] 验证第三方依赖许可证兼容性
- [ ] 添加NOTICE文件（如需要）

#### 9. 依赖项审查
- [ ] requirements.txt/environment.yml
- [ ] package.json
- [ ] 移除开发专用依赖（或标记为dev）
- [ ] 运行安全漏洞扫描

#### 10. 示例代码准备
- [ ] 创建examples/目录
- [ ] 添加基础使用示例
- [ ] 添加高级配置示例
- [ ] 添加自定义Agent示例

---

### 可选项（Optional）

#### 11. GitHub仓库设置
- [ ] 创建GitHub仓库
- [ ] 设置仓库描述
- [ ] 添加topics标签
- [ ] 配置GitHub Pages（文档站点）
- [ ] 设置Issue模板
- [ ] 设置PR模板

#### 12. CI/CD配置
- [ ] 设置GitHub Actions
  - [ ] 测试工作流
  - [ ] Linting工作流
  - [ ] 文档构建工作流
- [ ] 配置代码覆盖率报告
- [ ] 设置自动发布流程

#### 13. 社区建设
- [ ] 创建Discussions分类
- [ ] 准备欢迎消息
- [ ] 设置Wiki（如需要）
- [ ] 创建项目网站

#### 14. 营销材料
- [ ] 创建项目Logo
- [ ] 准备截图/GIF演示
- [ ] 撰写发布公告
- [ ] 准备社交媒体内容

---

## 🔍 安全审查检查项

### 敏感信息扫描
- [ ] API密钥和Token
- [ ] 数据库凭证
- [ ] 内部服务器地址
- [ ] 员工信息
- [ ] 客户数据

### 代码安全
- [ ] SQL注入防护
- [ ] XSS防护
- [ ] CSRF防护
- [ ] 依赖漏洞扫描

### 数据保护
- [ ] 移除测试数据中的真实数据
- [ ] 移除日志中的敏感信息
- [ ] 移除截图中的敏感信息

---

## 📦 发布包准备

### 创建发布分支
```bash
git checkout -b release/v0.6.0
```

### 清理不需要的文件
```bash
# 移除内部文档
rm -rf .superpowers/

# 移除内部配置
rm config/router_calibration.json
rm config/circuit_breaker.json
rm config/retry_policy.json
rm config/fact_verification.json

# 移除内部测试数据
rm tests/golden_dataset.json
rm scripts/create_golden_dataset.py
rm scripts/ab_comparison.py
rm scripts/load_test.py

# 移除项目管理文档
rm DOCUMENTATION_INDEX.md
rm DOCUMENTATION_CHECKLIST.md
rm DELIVERY_CHECKLIST.md
rm FINAL_PROJECT_SUMMARY.txt
rm PROJECT_COMPLETE.txt
rm DOCUMENTATION_UPDATE_SUMMARY.txt

# 移除内部报告
rm docs/ab_comparison_report.md
rm docs/performance_regression_report.md
rm docs/2026-06-27-agent-quality-optimization-plan.md
rm docs/2026-06-27-agent-quality-optimization-design.md
rm docs/DEPLOYMENT_GUIDE_v0.6.0.md  # 或创建脱敏版本
```

### 替换README
```bash
mv README.md README_INTERNAL.md
mv README_PUBLIC.md README.md
```

### 最终检查
```bash
# 扫描敏感信息
git grep -i "password"
git grep -i "secret"
git grep -i "token"
git grep -i "key"

# 检查文件大小
find . -type f -size +1M

# 验证测试
pytest tests/

# 验证构建
docker build -t querymind:v0.6.0 .
```

---

## 🚀 发布步骤

### 1. 最终提交
```bash
git add .
git commit -m "chore: prepare for v0.6.0 public release"
git push origin release/v0.6.0
```

### 2. 创建GitHub Release
- 标题：v0.6.0 - Agent Quality Optimization
- 描述：使用RELEASE_NOTES_v0.6.0.md内容（精简版）
- 附件：无（代码通过GitHub自动打包）

### 3. 发布公告
- [ ] 在GitHub Discussions发布公告
- [ ] 在社交媒体分享
- [ ] 通知相关社区

### 4. 监控和响应
- [ ] 监控Issues和Discussions
- [ ] 及时响应问题
- [ ] 收集反馈

---

## ⚠️ 风险提示

### 不可逆操作
一旦公开发布，以下操作不可逆：
- 删除已发布的代码
- 移除已公开的文档
- 撤回已分发的信息

### 建议
1. 在公开前进行内部审查
2. 先在私有仓库测试
3. 准备FAQ应对常见问题
4. 准备回滚计划（如需要）

---

## 📞 审批流程

### 需要审批
- [ ] 技术负责人审批
- [ ] 法务审批（如需要）
- [ ] 安全团队审批
- [ ] 产品负责人审批

### 审批检查点
1. 代码质量符合开源标准
2. 无敏感信息泄露
3. 许可证合规
4. 文档完整准确
5. 安全漏洞已修复

---

## ✅ 最终确认

发布前最后确认：

- [ ] 所有critical项已完成
- [ ] 安全审查已通过
- [ ] 测试全部通过
- [ ] 文档审查完成
- [ ] 相关人员已批准
- [ ] 回滚计划已准备

**签字确认：**

技术负责人：________________ 日期：______

安全负责人：________________ 日期：______

---

**清单版本：** 1.0  
**创建日期：** 2026-06-28  
**状态：** 待执行  
**预计发布日期：** TBD
