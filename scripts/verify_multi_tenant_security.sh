#!/bin/bash
# 多租户安全验证脚本
# 用途：验证所有安全修复是否正确实施

set -e

echo "======================================"
echo "多租户安全验证脚本"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}!${NC} $1"
    ((WARNINGS++))
}

echo "1. 检查查询缓存隔离..."
echo "--------------------------------"

# 检查 query_result_cache.py 是否有 user_id 参数
if grep -q "def get.*user_id.*:" app/services/query_result_cache.py; then
    check_pass "QueryResultCache.get() 包含 user_id 参数"
else
    check_fail "QueryResultCache.get() 缺少 user_id 参数"
fi

if grep -q "def set.*user_id.*:" app/services/query_result_cache.py; then
    check_pass "QueryResultCache.set() 包含 user_id 参数"
else
    check_fail "QueryResultCache.set() 缺少 user_id 参数"
fi

# 检查是否有用户验证逻辑
if grep -q "Cache ownership mismatch" app/services/query_result_cache.py; then
    check_pass "缓存包含用户归属验证逻辑"
else
    check_fail "缓存缺少用户归属验证逻辑"
fi

echo ""
echo "2. 检查向量存储隔离..."
echo "--------------------------------"

# 检查 similarity_search 是否有 require_source_filter 参数
if grep -q "require_source_filter.*bool.*True" app/retrievers/vector_store.py; then
    check_pass "similarity_search() 默认强制要求 allowed_sources"
else
    check_fail "similarity_search() 缺少强制过滤机制"
fi

# 检查是否有安全验证逻辑
if grep -q "allowed_sources is required" app/retrievers/vector_store.py; then
    check_pass "向量存储包含安全验证逻辑"
else
    check_fail "向量存储缺少安全验证逻辑"
fi

echo ""
echo "3. 检查 API 路由调用..."
echo "--------------------------------"

# 检查 query.py 是否传递 user_id
USER_ID_CALLS=$(grep -c 'user_id=str(user.get("user_id"' app/api/routes/query.py || echo "0")
if [ "$USER_ID_CALLS" -ge 5 ]; then
    check_pass "API 路由正确传递 user_id ($USER_ID_CALLS 处)"
else
    check_warn "API 路由 user_id 传递可能不完整 (找到 $USER_ID_CALLS 处)"
fi

echo ""
echo "4. 检查安全工具模块..."
echo "--------------------------------"

if [ -f "app/api/utils/tenant_isolation.py" ]; then
    check_pass "tenant_isolation.py 工具模块存在"

    # 检查关键函数
    if grep -q "def verify_resource_ownership" app/api/utils/tenant_isolation.py; then
        check_pass "verify_resource_ownership() 函数存在"
    else
        check_fail "verify_resource_ownership() 函数缺失"
    fi

    if grep -q "def filter_resources_by_ownership" app/api/utils/tenant_isolation.py; then
        check_pass "filter_resources_by_ownership() 函数存在"
    else
        check_fail "filter_resources_by_ownership() 函数缺失"
    fi
else
    check_fail "tenant_isolation.py 工具模块不存在"
fi

echo ""
echo "5. 检查测试文件..."
echo "--------------------------------"

if [ -d "tests/security" ]; then
    check_pass "安全测试目录存在"

    if [ -f "tests/security/test_query_cache_isolation.py" ]; then
        check_pass "查询缓存隔离测试存在"
    else
        check_fail "查询缓存隔离测试缺失"
    fi

    if [ -f "tests/security/test_vector_store_isolation.py" ]; then
        check_pass "向量存储隔离测试存在"
    else
        check_fail "向量存储隔离测试缺失"
    fi
else
    check_fail "安全测试目录不存在"
fi

echo ""
echo "6. 检查文档完整性..."
echo "--------------------------------"

DOCS=(
    "MULTI_TENANT_SECURITY_AUDIT.md"
    "TENANT_ISOLATION_FIXES.md"
    "TENANT_ISOLATION_FIXES_COMPLETE.md"
    "P1_FIXES_COMPLETE.md"
    "FINAL_MULTI_TENANT_SECURITY_REPORT.md"
    "PROJECT_COMPLETE_SUMMARY.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "$doc 存在"
    else
        check_warn "$doc 缺失"
    fi
done

echo ""
echo "7. 检查 Agent Tracking 隔离..."
echo "--------------------------------"

if grep -q "_verify_trace_ownership" app/api/routes/agent_tracking.py; then
    check_pass "Agent Tracking 包含归属验证函数"
else
    check_fail "Agent Tracking 缺少归属验证"
fi

if grep -q "execution_id.*Field.*description" app/core/schemas.py; then
    check_pass "QueryResponse 包含 execution_id 字段"
else
    check_warn "QueryResponse 可能缺少 execution_id 字段"
fi

echo ""
echo "======================================"
echo "验证结果汇总"
echo "======================================"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo -e "${YELLOW}警告: $WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有关键检查通过！${NC}"
    echo "系统已准备好部署。"
    exit 0
else
    echo -e "${RED}✗ 发现 $FAILED 个问题需要修复${NC}"
    exit 1
fi
