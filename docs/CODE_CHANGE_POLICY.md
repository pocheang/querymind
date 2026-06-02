# 代码变更管理规范

**版本**: v1.0  
**生效日期**: 2026-06-02  
**维护者**: pocheang  

---

## 🎯 目的

确保每次代码修改都有完整的文档记录，包括：
- ✅ 修改前的计划文档
- ✅ 修改过程的时间戳
- ✅ 修改后的总结文档

---

## 📋 强制要求

### ⚠️ 核心原则

**没有计划文档 = 不允许修改代码**

每个代码变更必须遵循以下流程：

```
1. 创建计划文档 (BEFORE)
   ↓
2. 评审并批准计划
   ↓
3. 执行代码修改
   ↓
4. 创建总结文档 (AFTER)
   ↓
5. 归档到历史记录
```

---

## 📁 文档结构

### 目录组织

```
.claude/
├── plans/                           # 修改前的计划文档
│   ├── YYYY-MM-DD-HHmm-{feature}.md
│   └── YYYY-MM-DD-HHmm-{bugfix}.md
│
└── completed/                       # 修改后的总结文档
    ├── YYYY-MM-DD-HHmm-{feature}-summary.md
    └── YYYY-MM-DD-HHmm-{bugfix}-summary.md

docs/
└── changes/                         # 变更历史（公开）
    └── YYYY-MM/
        └── DD-{change-id}.md
```

---

## 📝 文档模板

### 1. 修改前计划文档模板

**文件名格式**: `.claude/plans/YYYY-MM-DD-HHmm-{描述}.md`

**示例**: `.claude/plans/2026-06-02-1430-add-user-auth.md`

```markdown
# 代码修改计划

**变更ID**: CHANGE-2026-06-02-001  
**创建时间**: 2026-06-02 14:30:00  
**创建人**: pocheang  
**类型**: feature | bugfix | refactor | performance | security  
**优先级**: P0 (紧急) | P1 (高) | P2 (中) | P3 (低)  
**预计工作量**: 2小时  

---

## 📋 变更概述

### 问题描述
[清晰描述要解决的问题或要实现的功能]

### 影响范围
- 影响的文件数量: 
- 影响的功能模块: 
- 是否影响API: 是/否
- 是否需要数据库迁移: 是/否
- 是否向后兼容: 是/否

---

## 🎯 变更目标

### 主要目标
1. [目标1]
2. [目标2]

### 成功标准
- [ ] 标准1
- [ ] 标准2
- [ ] 所有测试通过
- [ ] 文档已更新

---

## 🔍 现状分析

### 当前代码状态
[描述当前代码的状态，包括问题点]

```python
# 当前代码示例
def old_function():
    pass
```

### 问题根因
[分析问题的根本原因]

---

## 💡 解决方案

### 方案设计
[详细描述解决方案]

### 技术选型
- 选择的技术/库: 
- 选择理由: 

### 实施步骤
1. [ ] 步骤1
2. [ ] 步骤2
3. [ ] 步骤3

### 代码变更计划

#### 文件: `path/to/file1.py`
**变更类型**: 修改 | 新增 | 删除

**计划修改**:
```python
# 新代码
def new_function():
    pass
```

**影响**: [说明这个修改的影响]

---

## 🧪 测试计划

### 单元测试
- [ ] 测试用例1
- [ ] 测试用例2

### 集成测试
- [ ] 集成测试场景

### 回归测试
- [ ] 现有功能验证

---

## 🚨 风险评估

### 潜在风险
| 风险 | 可能性 | 影响 | 缓解措施 |
|------|-------|------|---------|
| 风险1 | 高/中/低 | 高/中/低 | [缓解措施] |

### 回滚方案
[如果出现问题，如何回滚]

---

## 📅 时间规划

- **计划开始时间**: YYYY-MM-DD HH:mm
- **预计完成时间**: YYYY-MM-DD HH:mm
- **实际开始时间**: [待填写]
- **实际完成时间**: [待填写]

---

## ✅ 审批

- [ ] 技术负责人审批: __________ (签名/日期)
- [ ] 代码审查人: __________ (签名/日期)

---

**状态**: 待审批 | 已批准 | 进行中 | 已完成 | 已取消
```

---

### 2. 修改后总结文档模板

**文件名格式**: `.claude/completed/YYYY-MM-DD-HHmm-{描述}-summary.md`

**示例**: `.claude/completed/2026-06-02-1630-add-user-auth-summary.md`

```markdown
# 代码修改总结

**变更ID**: CHANGE-2026-06-02-001  
**完成时间**: 2026-06-02 16:30:00  
**实施人**: pocheang  
**关联计划**: [链接到计划文档]  

---

## 📊 执行概况

### 时间记录
- **计划开始时间**: 2026-06-02 14:30:00
- **实际开始时间**: 2026-06-02 14:45:00
- **计划完成时间**: 2026-06-02 16:30:00
- **实际完成时间**: 2026-06-02 16:25:00
- **总耗时**: 1小时40分钟
- **与计划偏差**: -5分钟 (提前)

### 执行状态
- [x] 按计划完成
- [ ] 部分完成
- [ ] 需要后续工作

---

## ✅ 完成内容

### 实际修改的文件
1. `app/services/auth.py` (+120行, -50行)
2. `tests/test_auth.py` (+80行, 新增)
3. `docs/AUTH_GUIDE.md` (+100行, 新增)

### Git提交记录
```
commit abc123: feat(auth): add user authentication system
- Add JWT token generation
- Add password hashing
- Add login/logout endpoints
```

### 实际代码变更

#### 文件: `app/services/auth.py`
```python
# 实际实施的代码
class AuthService:
    def authenticate(self, username, password):
        # 实现细节
        pass
```

**与计划差异**: [说明与原计划的差异及原因]

---

## 🧪 测试结果

### 单元测试
```
✅ 15/15 tests passed
- test_jwt_generation: PASS
- test_password_hashing: PASS
- test_login_endpoint: PASS
```

### 集成测试
```
✅ 5/5 integration tests passed
```

### 性能测试
- 响应时间: 120ms (目标<150ms) ✅
- 吞吐量: 1000 req/s ✅

---

## 📈 实际影响

### 性能影响
| 指标 | 修改前 | 修改后 | 变化 |
|------|-------|-------|------|
| 响应时间 | 200ms | 120ms | ⬇️ 40% |
| 内存使用 | 100MB | 105MB | ⬆️ 5% |

### 功能影响
- ✅ 新增用户认证功能
- ✅ 所有现有功能正常
- ✅ API向后兼容

---

## 🐛 遇到的问题

### 问题1: JWT库兼容性
**发现时间**: 2026-06-02 15:20  
**问题描述**: PyJWT 3.0版本API变更  
**解决方案**: 升级到PyJWT 3.1并更新代码  
**耗时**: 15分钟  

### 问题2: [如有其他问题]
...

---

## 📝 与计划的偏差

### 计划外的修改
1. **修改内容**: 额外添加了密码强度检查
   **原因**: 安全团队建议
   **影响**: +30分钟开发时间

### 未完成的内容
- [ ] 社交登录集成 (延期到v0.5.0)
  **原因**: 依赖第三方API尚未就绪

---

## 💡 经验教训

### 做得好的地方
1. 提前准备了测试数据
2. 代码复用了现有的加密模块

### 需要改进的地方
1. 应该更早发现JWT库版本问题
2. 测试覆盖率可以更高

### 建议
[对未来类似工作的建议]

---

## 📚 相关文档

- 计划文档: `.claude/plans/2026-06-02-1430-add-user-auth.md`
- API文档: `docs/api/AUTH_API.md`
- 用户指南: `docs/AUTH_GUIDE.md`
- PR链接: https://github.com/user/repo/pull/123

---

## ✅ 验收清单

- [x] 所有测试通过
- [x] 代码审查完成
- [x] 文档已更新
- [x] 部署到staging环境
- [x] 产品经理验收
- [x] 归档文档

---

**状态**: ✅ 已完成  
**归档日期**: 2026-06-02 16:30:00  
**归档人**: pocheang
```

---

## 🔄 工作流程

### Step 1: 创建计划文档 (必须)

```bash
# 1. 创建计划文档
cd .claude/plans
cp ../templates/change-plan-template.md YYYY-MM-DD-HHmm-description.md

# 2. 填写计划内容
# 编辑文档，填写所有必填字段

# 3. 提交计划文档
git add .claude/plans/YYYY-MM-DD-HHmm-description.md
git commit -m "plan: add change plan for [description]"
git push origin main
```

**⚠️ 检查点**: 计划文档必须经过审批才能开始编码

### Step 2: 实施代码变更

```bash
# 1. 创建功能分支
git checkout -b feature/YYYY-MM-DD-description

# 2. 记录开始时间
echo "实际开始时间: $(date)" >> .claude/plans/YYYY-MM-DD-HHmm-description.md

# 3. 进行代码修改
# [编写代码...]

# 4. 运行测试
pytest tests/

# 5. 提交代码
git add .
git commit -m "feat: [description] (ref: CHANGE-YYYY-MM-DD-XXX)"
```

### Step 3: 创建总结文档 (必须)

```bash
# 1. 记录完成时间
echo "实际完成时间: $(date)" >> .claude/plans/YYYY-MM-DD-HHmm-description.md

# 2. 创建总结文档
cd .claude/completed
cp ../templates/change-summary-template.md YYYY-MM-DD-HHmm-description-summary.md

# 3. 填写总结内容
# 编辑文档，记录实际情况

# 4. 提交总结文档
git add .claude/completed/YYYY-MM-DD-HHmm-description-summary.md
git commit -m "docs: add change summary for [description]"
```

**⚠️ 检查点**: 没有总结文档 = PR不能合并

### Step 4: 代码审查与合并

```bash
# 1. 创建PR，链接到计划和总结文档
gh pr create --title "feat: [description]" --body "
计划文档: .claude/plans/YYYY-MM-DD-HHmm-description.md
总结文档: .claude/completed/YYYY-MM-DD-HHmm-description-summary.md
变更ID: CHANGE-YYYY-MM-DD-XXX
"

# 2. 代码审查通过后合并
gh pr merge --squash
```

---

## 📊 文档检查清单

### 修改前 (计划文档)
- [ ] 文件命名符合规范 (`YYYY-MM-DD-HHmm-description.md`)
- [ ] 包含变更ID
- [ ] 包含创建时间
- [ ] 问题描述清晰
- [ ] 解决方案明确
- [ ] 风险已评估
- [ ] 测试计划完整
- [ ] 已获得审批

### 修改后 (总结文档)
- [ ] 文件命名符合规范 (`YYYY-MM-DD-HHmm-description-summary.md`)
- [ ] 关联到计划文档
- [ ] 记录实际时间
- [ ] Git提交记录
- [ ] 测试结果
- [ ] 性能数据
- [ ] 遇到的问题
- [ ] 经验教训
- [ ] 验收清单

---

## 🚨 违规处理

### 违规情况
1. 没有计划文档就修改代码
2. 没有总结文档就合并PR
3. 文档格式不符合规范
4. 缺少必填字段

### 处理措施
1. PR自动拒绝
2. 必须补充文档才能继续
3. 记录到违规日志

---

## 📈 效果追踪

### 每月统计
- 代码变更次数
- 平均计划质量
- 计划vs实际偏差
- 文档完整度

### 季度回顾
- 优秀实践案例
- 改进建议
- 流程优化

---

## 🔗 相关文档

- [计划文档模板](../templates/change-plan-template.md)
- [总结文档模板](../templates/change-summary-template.md)
- [变更ID生成规则](./CHANGE_ID_RULES.md)

---

**最后更新**: 2026-06-02  
**版本**: v1.0
