"""
多租户隔离安全测试

测试用户数据隔离和越权访问防护。
"""

import pytest
from fastapi import HTTPException

from app.services.query_result_cache import QueryResultCache


class TestQueryCacheIsolation:
    """测试查询缓存的用户隔离"""

    def test_cache_returns_none_for_different_user(self):
        """测试用户无法访问其他用户的缓存数据"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 用户A保存缓存
        cache.set(key="test_key", value={"answer": "sensitive data", "user_id": "user_A"}, user_id="user_A")

        # 用户B尝试访问相同的缓存键
        result = cache.get(key="test_key", user_id="user_B")

        # 应该返回 None（被过滤）
        assert result is None

    def test_cache_returns_data_for_same_user(self):
        """测试用户可以访问自己的缓存数据"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 用户A保存缓存
        test_data = {"answer": "my data", "user_id": "user_A"}
        cache.set(key="test_key", value=test_data, user_id="user_A")

        # 用户A访问自己的缓存
        result = cache.get(key="test_key", user_id="user_A")

        # 应该返回数据
        assert result is not None
        assert result["answer"] == "my data"
        assert result["user_id"] == "user_A"

    def test_cache_set_always_includes_user_id(self):
        """测试保存缓存时总是包含用户ID"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 保存时提供 user_id
        cache.set(key="test_key", value={"answer": "test"}, user_id="user_A")

        # 不验证用户ID的情况下获取（用于测试）
        result = cache.get(key="test_key", user_id=None)

        # 缓存数据应该包含 user_id
        assert result is not None
        assert result["user_id"] == "user_A"

    def test_session_cache_isolation(self):
        """测试会话级缓存的用户隔离"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 用户A在会话中保存缓存
        cache.set(key="test_key", value={"answer": "session data"}, session_id="session_123", user_id="user_A")

        # 用户B尝试通过相同会话ID访问
        result = cache.get(key="test_key", session_id="session_123", user_id="user_B")

        # 应该被过滤
        assert result is None

    def test_cache_without_user_id_verification(self):
        """测试不提供 user_id 时的行为（向后兼容）"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 保存缓存时不提供 user_id（旧代码兼容性）
        cache.set(key="test_key", value={"answer": "legacy data"})

        # 获取时不验证 user_id
        result = cache.get(key="test_key")

        # 应该返回数据（向后兼容）
        assert result is not None
        assert result["answer"] == "legacy data"

    def test_cache_key_collision_between_users(self):
        """测试不同用户之间的缓存键碰撞"""
        cache = QueryResultCache(backend="memory", ttl_seconds=300, max_items=100, session_ttl_seconds=600)

        # 用户A和用户B使用相同的缓存键（但查询内容可能不同）
        cache.set(key="common_key", value={"answer": "user A answer", "user_id": "user_A"}, user_id="user_A")

        cache.set(key="common_key", value={"answer": "user B answer", "user_id": "user_B"}, user_id="user_B")

        # 用户A应该只能看到自己的数据
        result_a = cache.get(key="common_key", user_id="user_A")
        # 注意：由于使用相同的 key，后者会覆盖前者
        # 但验证机制会阻止用户A看到用户B的数据
        if result_a is not None:
            assert result_a["user_id"] == "user_A"

        # 用户B应该只能看到自己的数据
        result_b = cache.get(key="common_key", user_id="user_B")
        assert result_b is not None
        assert result_b["user_id"] == "user_B"
        assert result_b["answer"] == "user B answer"


class TestTenantIsolationHelpers:
    """测试租户隔离辅助函数"""

    def test_verify_resource_ownership_success(self):
        """测试资源所有权验证通过"""
        from app.api.utils.tenant_isolation import verify_resource_ownership

        resource = {"owner_user_id": "user_A", "data": "test"}
        user = {"user_id": "user_A", "role": "user"}

        # 应该不抛出异常
        verify_resource_ownership(resource, user, "document")

    def test_verify_resource_ownership_failure(self):
        """测试资源所有权验证失败"""
        from app.api.utils.tenant_isolation import verify_resource_ownership

        resource = {"owner_user_id": "user_A", "data": "test"}
        user = {"user_id": "user_B", "role": "user"}

        # 应该抛出 403 异常
        with pytest.raises(HTTPException) as exc:
            verify_resource_ownership(resource, user, "document")

        assert exc.value.status_code == 403

    def test_verify_resource_ownership_admin_bypass(self):
        """测试管理员可以访问所有资源"""
        from app.api.utils.tenant_isolation import verify_resource_ownership

        resource = {"owner_user_id": "user_A", "data": "test"}
        admin = {"user_id": "admin_user", "role": "admin"}

        # 管理员应该可以访问
        verify_resource_ownership(resource, admin, "document")

    def test_verify_resource_ownership_public_resource(self):
        """测试公共资源的访问"""
        from app.api.utils.tenant_isolation import verify_resource_ownership

        resource = {"owner_user_id": "user_A", "visibility": "public", "data": "test"}
        user = {"user_id": "user_B", "role": "user"}

        # 公共资源应该可以访问
        verify_resource_ownership(resource, user, "document", allow_public=True)

    def test_filter_resources_by_ownership(self):
        """测试资源列表过滤"""
        from app.api.utils.tenant_isolation import filter_resources_by_ownership

        resources = [
            {"owner_user_id": "user_A", "name": "doc1"},
            {"owner_user_id": "user_B", "name": "doc2"},
            {"owner_user_id": "user_A", "visibility": "public", "name": "doc3"},
            {"owner_user_id": "user_C", "visibility": "public", "name": "doc4"},
        ]

        user = {"user_id": "user_A", "role": "user"}

        filtered = filter_resources_by_ownership(resources, user)

        # 应该只包含用户A的资源和公共资源
        assert len(filtered) == 3
        names = [r["name"] for r in filtered]
        assert "doc1" in names
        assert "doc3" in names
        assert "doc4" in names
        assert "doc2" not in names

    def test_filter_resources_admin_sees_all(self):
        """测试管理员可以看到所有资源"""
        from app.api.utils.tenant_isolation import filter_resources_by_ownership

        resources = [
            {"owner_user_id": "user_A", "name": "doc1"},
            {"owner_user_id": "user_B", "name": "doc2"},
        ]

        admin = {"user_id": "admin", "role": "admin"}

        filtered = filter_resources_by_ownership(resources, admin)

        # 管理员应该看到所有资源
        assert len(filtered) == 2

    def test_validate_cache_ownership(self):
        """测试缓存归属验证"""
        from app.api.utils.tenant_isolation import validate_cache_ownership

        cached_data = {"user_id": "user_A", "answer": "test"}
        user = {"user_id": "user_A", "role": "user"}

        # 应该返回数据
        result = validate_cache_ownership(cached_data, user)
        assert result is not None
        assert result["answer"] == "test"

    def test_validate_cache_ownership_mismatch(self):
        """测试缓存归属不匹配"""
        from app.api.utils.tenant_isolation import validate_cache_ownership

        cached_data = {"user_id": "user_A", "answer": "test"}
        user = {"user_id": "user_B", "role": "user"}

        # 应该返回 None
        result = validate_cache_ownership(cached_data, user)
        assert result is None


class TestCacheKeyGeneration:
    """测试缓存键生成的安全性"""

    def test_cache_key_includes_user_id(self):
        """测试缓存键包含用户ID"""
        cache_key_1 = QueryResultCache.build_key(
            user_id="user_A",
            session_id="session_123",
            question="test question",
            use_web_fallback=False,
            use_reasoning=False,
            retrieval_strategy="baseline",
            agent_class_hint="general",
        )

        cache_key_2 = QueryResultCache.build_key(
            user_id="user_B",
            session_id="session_123",
            question="test question",
            use_web_fallback=False,
            use_reasoning=False,
            retrieval_strategy="baseline",
            agent_class_hint="general",
        )

        # 不同用户的缓存键应该不同
        assert cache_key_1 != cache_key_2

    def test_cache_key_same_for_same_params(self):
        """测试相同参数生成相同的缓存键"""
        params = {
            "user_id": "user_A",
            "session_id": "session_123",
            "question": "test question",
            "use_web_fallback": False,
            "use_reasoning": False,
            "retrieval_strategy": "baseline",
            "agent_class_hint": "general",
        }

        cache_key_1 = QueryResultCache.build_key(**params)
        cache_key_2 = QueryResultCache.build_key(**params)

        # 相同参数应该生成相同的键
        assert cache_key_1 == cache_key_2
