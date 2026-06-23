#!/bin/bash
# P1权限区分测试脚本 - Viewer vs Analyst

echo "=========================================="
echo "  P1: Viewer vs Analyst 权限测试"
echo "=========================================="
echo ""

# 获取tokens
echo "=== 获取测试Tokens ==="

# 使用已有的admin_test (admin角色)
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"AdminTest@123"}' | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

# 注册并登录Analyst用户
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst_test","password":"AnalystTest@123"}' > /dev/null

# 提升为analyst角色
python << 'EOF'
import sqlite3
conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()
cursor.execute("UPDATE users SET role='analyst' WHERE username='analyst_test'")
conn.commit()
conn.close()
print("Analyst role updated")
EOF

ANALYST_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst_test","password":"AnalystTest@123"}' | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

# 使用已有的user_test1 (viewer角色)
VIEWER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user_test1","password":"UserTest@123"}' | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

echo "Admin Token: ${ADMIN_TOKEN:0:30}..."
echo "Analyst Token: ${ANALYST_TOKEN:0:30}..."
echo "Viewer Token: ${VIEWER_TOKEN:0:30}..."
echo ""

# 测试统计
TOTAL=0
PASSED=0
FAILED=0

run_test() {
    local name="$1"
    local expected="$2"
    local actual="$3"

    TOTAL=$((TOTAL + 1))
    if [ "$actual" = "$expected" ]; then
        echo "  ✓ PASS: $name"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ FAIL: $name (expected $expected, got $actual)"
        FAILED=$((FAILED + 1))
    fi
}

# ============================================
# 测试1: 会话管理权限
# ============================================
echo "=== 测试1: 会话管理 ==="

# Viewer只能读和创建
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $VIEWER_TOKEN")
run_test "Viewer创建会话" "200" "$STATUS"

# 获取viewer的会话ID
VIEWER_SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $VIEWER_TOKEN" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# Viewer不能删除会话（应该403）
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "http://localhost:8000/sessions/$VIEWER_SESSION" \
  -H "Authorization: Bearer $VIEWER_TOKEN")
run_test "Viewer删除会话（应拒绝）" "403" "$STATUS"

# Analyst可以删除会话
ANALYST_SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $ANALYST_TOKEN" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "http://localhost:8000/sessions/$ANALYST_SESSION" \
  -H "Authorization: Bearer $ANALYST_TOKEN")
run_test "Analyst删除会话" "200" "$STATUS"

# ============================================
# 测试2: 消息管理权限
# ============================================
echo ""
echo "=== 测试2: 消息管理 ==="

# 创建测试会话和消息
VIEWER_SESSION2=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $VIEWER_TOKEN" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# 发送查询创建消息
curl -s -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"test\",\"session_id\":\"$VIEWER_SESSION2\"}" > /dev/null

sleep 1

# 获取消息ID
MESSAGE_ID=$(curl -s "http://localhost:8000/sessions/$VIEWER_SESSION2" \
  -H "Authorization: Bearer $VIEWER_TOKEN" | grep -o '"message_id":"[^"]*"' | head -1 | cut -d'"' -f4)

# Viewer不能编辑消息
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X PATCH "http://localhost:8000/sessions/$VIEWER_SESSION2/messages/$MESSAGE_ID" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"edited"}')
run_test "Viewer编辑消息（应拒绝）" "403" "$STATUS"

# Viewer不能删除消息
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "http://localhost:8000/sessions/$VIEWER_SESSION2/messages/$MESSAGE_ID" \
  -H "Authorization: Bearer $VIEWER_TOKEN")
run_test "Viewer删除消息（应拒绝）" "403" "$STATUS"

# Analyst可以编辑和删除消息
ANALYST_SESSION2=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $ANALYST_TOKEN" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

curl -s -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"test\",\"session_id\":\"$ANALYST_SESSION2\"}" > /dev/null

sleep 1

ANALYST_MSG=$(curl -s "http://localhost:8000/sessions/$ANALYST_SESSION2" \
  -H "Authorization: Bearer $ANALYST_TOKEN" | grep -o '"message_id":"[^"]*"' | head -1 | cut -d'"' -f4)

STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X PATCH "http://localhost:8000/sessions/$ANALYST_SESSION2/messages/$ANALYST_MSG" \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"edited"}')
run_test "Analyst编辑消息" "200" "$STATUS"

# ============================================
# 测试3: Prompt模板权限
# ============================================
echo ""
echo "=== 测试3: Prompt模板管理 ==="

# Viewer不能创建prompt
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/prompts \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"test","content":"test prompt"}')
run_test "Viewer创建Prompt（应拒绝）" "403" "$STATUS"

# Viewer可以查看prompts
STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8000/prompts \
  -H "Authorization: Bearer $VIEWER_TOKEN")
run_test "Viewer查看Prompts" "200" "$STATUS"

# Analyst可以创建prompt
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/prompts \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"test","content":"test prompt"}')
run_test "Analyst创建Prompt" "200" "$STATUS"

# 获取analyst创建的prompt ID
PROMPT_ID=$(curl -s -X POST http://localhost:8000/prompts \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"test2","content":"test prompt"}' | grep -o '"prompt_id":"[^"]*"' | cut -d'"' -f4)

# Viewer不能删除prompt
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "http://localhost:8000/prompts/$PROMPT_ID" \
  -H "Authorization: Bearer $VIEWER_TOKEN")
run_test "Viewer删除Prompt（应拒绝）" "403" "$STATUS"

# Analyst可以删除prompt
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "http://localhost:8000/prompts/$PROMPT_ID" \
  -H "Authorization: Bearer $ANALYST_TOKEN")
run_test "Analyst删除Prompt" "200" "$STATUS"

# ============================================
# 测试4: 核心功能（两者都可以）
# ============================================
echo ""
echo "=== 测试4: 核心查询功能（两者都可以） ==="

# Viewer可以查询
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"你好"}')
run_test "Viewer执行查询" "200" "$STATUS"

# Analyst可以查询
STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"你好"}')
run_test "Analyst执行查询" "200" "$STATUS"

# ============================================
# 最终报告
# ============================================
echo ""
echo "=========================================="
echo "  P1测试结果"
echo "=========================================="
echo "总测试数: $TOTAL"
echo "✓ 通过: $PASSED"
echo "✗ 失败: $FAILED"
echo "通过率: $(( PASSED * 100 / TOTAL ))%"
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "🎉 所有P1测试通过！Viewer和Analyst权限已正确区分。"
    exit 0
else
    echo ""
    echo "⚠️  有测试失败，请检查上面的输出"
    exit 1
fi
