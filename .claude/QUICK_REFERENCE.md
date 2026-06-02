# 代码变更管理 - 快速参考指南

**最后更新**: 2026-06-02  
**适用范围**: 所有代码修改  

---

## 🚨 核心原则

### ⚠️ 绝对规则

```
没有计划文档 = 不允许修改代码
没有总结文档 = PR不能合并
```

---

## 📋 快速检查清单

### 开始编码前
- [ ] 已创建计划文档 (`.claude/plans/YYYY-MM-DD-HHmm-description.md`)
- [ ] 已填写完整计划内容
- [ ] 已记录计划开始时间
- [ ] 已获得审批（如需要）
- [ ] 已创建功能分支

### 编码完成后
- [ ] 已记录实际完成时间
- [ ] 已创建总结文档 (`.claude/completed/YYYY-MM-DD-HHmm-description-summary.md`)
- [ ] 已运行所有测试
- [ ] 已提交代码并推送
- [ ] 已创建PR并关联文档
- [ ] 已通过代码审查

---

## 🔄 标准流程（5步）

```
┌─────────────────────────────────────────────────────┐
│ Step 1: 创建计划文档 (BEFORE)                       │
│   文件: .claude/plans/YYYY-MM-DD-HHmm-{desc}.md    │
│   内容: 问题、方案、风险、测试计划                   │
│   ⏱️  时间: 记录"计划开始时间"                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: 审批计划 (可选但推荐)                       │
│   提交: git commit -m "plan: [description]"         │
│   审批: 技术负责人/团队评审                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: 实施代码修改                                │
│   分支: git checkout -b feature/YYYY-MM-DD-{desc}  │
│   编码: 按计划实施修改                              │
│   测试: pytest tests/                               │
│   提交: git commit -m "feat: [description]"         │
│   ⏱️  时间: 记录"实际开始/完成时间"                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Step 4: 创建总结文档 (AFTER)                        │
│   文件: .claude/completed/YYYY-MM-DD-HHmm-summary.md│
│   内容: 时间、测试、问题、经验、偏差分析            │
│   提交: git commit -m "docs: add summary"           │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Step 5: 代码审查与合并                              │
│   PR: 关联计划和总结文档                            │
│   审查: 代码+文档双重检查                           │
│   合并: gh pr merge --squash                        │
└─────────────────────────────────────────────────────┘
```

---

## 📁 文件命名规范

### 计划文档
```
.claude/plans/YYYY-MM-DD-HHmm-description.md

示例:
.claude/plans/2026-06-02-1430-fix-memory-leak.md
.claude/plans/2026-06-02-1530-add-cache-layer.md
```

### 总结文档
```
.claude/completed/YYYY-MM-DD-HHmm-description-summary.md

示例:
.claude/completed/2026-06-02-1630-fix-memory-leak-summary.md
.claude/completed/2026-06-02-1730-add-cache-layer-summary.md
```

### 变更ID
```
CHANGE-YYYY-MM-DD-XXX

示例:
CHANGE-2026-06-02-001
CHANGE-2026-06-02-002
```

---

## 📝 必填字段速查

### 计划文档必填
- [x] 变更ID
- [x] 创建时间 (YYYY-MM-DD HH:mm:ss)
- [x] 创建人
- [x] 类型 (feature/bugfix/refactor/performance/security)
- [x] 优先级 (P0/P1/P2/P3)
- [x] 问题描述
- [x] 解决方案
- [x] 风险评估
- [x] 测试计划
- [x] 计划开始时间

### 总结文档必填
- [x] 变更ID
- [x] 完成时间 (YYYY-MM-DD HH:mm:ss)
- [x] 实施人
- [x] 关联计划文档
- [x] 实际开始时间
- [x] 实际完成时间
- [x] 总耗时
- [x] 修改的文件列表
- [x] Git提交记录
- [x] 测试结果
- [x] 遇到的问题
- [x] 经验教训

---

## 🎯 常见场景

### 场景1: 紧急Bug修复 (P0)
```bash
# 1. 快速创建计划 (5分钟)
cp .claude/templates/change-plan-template.md \
   .claude/plans/2026-06-02-1500-urgent-fix.md
# 填写关键信息：问题、方案、风险

# 2. 立即实施
git checkout -b hotfix/urgent-fix
# 修改代码...
pytest tests/
git commit -m "fix(urgent): [description]"

# 3. 创建总结 (5分钟)
cp .claude/templates/change-summary-template.md \
   .claude/completed/2026-06-02-1530-urgent-fix-summary.md
# 填写关键信息：时间、测试、影响

# 4. 快速审查合并
gh pr create --title "hotfix: [description]"
```

### 场景2: 新功能开发 (P1-P2)
```bash
# 1. 详细计划 (30-60分钟)
cp .claude/templates/change-plan-template.md \
   .claude/plans/2026-06-02-1000-new-feature.md
# 填写完整计划：分析、设计、测试、风险

# 2. 计划评审
git add .claude/plans/2026-06-02-1000-new-feature.md
git commit -m "plan: add plan for new feature"
# 等待团队评审...

# 3. 实施开发
git checkout -b feature/new-feature
# 开发...测试...
git commit -m "feat: implement new feature"

# 4. 完整总结 (20-30分钟)
cp .claude/templates/change-summary-template.md \
   .claude/completed/2026-06-02-1600-new-feature-summary.md
# 详细记录：时间、测试、问题、经验

# 5. 正式审查
gh pr create --title "feat: new feature"
```

### 场景3: 性能优化 (P2)
```bash
# 1. 基准测试 + 计划
# 先测试现状，记录性能数据
python benchmark.py > baseline.txt

cp .claude/templates/change-plan-template.md \
   .claude/plans/2026-06-02-1400-performance-opt.md
# 计划中包含：baseline数据、目标、方案

# 2. 实施优化
git checkout -b perf/optimization
# 优化代码...

# 3. 对比测试
python benchmark.py > optimized.txt
diff baseline.txt optimized.txt

# 4. 总结包含性能对比
# 在总结文档中详细记录性能提升数据
```

---

## 💡 最佳实践

### ✅ 推荐做法
1. **计划先行**: 编码前先思考，避免返工
2. **小步迭代**: 将大任务拆分为小的变更
3. **及时记录**: 遇到问题立即记录，不要事后回忆
4. **时间真实**: 记录真实的时间，帮助改进估算
5. **经验分享**: 总结文档是团队知识库

### ❌ 避免做法
1. **先写代码再补文档**: 容易遗漏关键信息
2. **复制粘贴模板不改**: 失去文档的价值
3. **时间造假**: 影响团队的估算能力
4. **只记录成功不记录问题**: 失去学习机会
5. **文档太简单**: 几个月后自己都看不懂

---

## 🔗 完整文档

- **详细政策**: [docs/CODE_CHANGE_POLICY.md](../docs/CODE_CHANGE_POLICY.md)
- **计划模板**: [.claude/templates/change-plan-template.md](./templates/change-plan-template.md)
- **总结模板**: [.claude/templates/change-summary-template.md](./templates/change-summary-template.md)

---

## 📞 支持

如有疑问，联系：
- 技术负责人: pocheang
- 文档维护: Claude & pocheang

---

**记住**: 好的文档 = 未来的你感谢现在的你 💡
