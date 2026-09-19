"""Unit tests for CVE and MITRE ATT&CK tools."""

import pytest

from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.request import RequestActor
from app.tools.cyber.cve_tools import (
    ATTACK_TOOL_DEFINITION,
    CVE_TOOL_DEFINITION,
    execute_cve_lookup,
    execute_mitre_attack_lookup,
)


@pytest.fixture
def actor() -> RequestActor:
    return RequestActor(user_id="sec_analyst", tenant_id="tenant_alpha", role="analyst")


@pytest.mark.asyncio
async def test_cve_lookup_standard_id(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="CVE-2021-44228"),),
    )
    result = await execute_cve_lookup(call, actor)
    assert result.status == "succeeded"
    assert "Log4Shell" in result.summary
    assert "CVSS 10.0" in result.summary


@pytest.mark.asyncio
async def test_cve_lookup_case_insensitive_and_whitespace(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="  cve-2014-0160  "),),
    )
    result = await execute_cve_lookup(call, actor)
    assert result.status == "succeeded"
    assert "Heartbleed" in result.summary


@pytest.mark.asyncio
async def test_cve_lookup_by_alias(actor: RequestActor) -> None:
    for alias in ["spring4shell", "xz", "moveit", "runc", "eternalblue", "struts2", "zerologon"]:
        call = ToolCall(
            tool_id=CVE_TOOL_DEFINITION.tool_id,
            arguments=(ToolArgument(name="cve_id", value=alias),),
        )
        result = await execute_cve_lookup(call, actor)
        assert result.status == "succeeded", f"Failed for alias: {alias}"
        assert result.summary != ""


@pytest.mark.asyncio
async def test_cve_lookup_chinese_alias(actor: RequestActor) -> None:
    for alias in ["心脏滴血", "永恒之蓝", "破壳", "核弹漏洞"]:
        call = ToolCall(
            tool_id=CVE_TOOL_DEFINITION.tool_id,
            arguments=(ToolArgument(name="cve_id", value=alias),),
        )
        result = await execute_cve_lookup(call, actor)
        assert result.status == "succeeded"
        assert result.summary != ""


@pytest.mark.asyncio
async def test_cve_lookup_argument_aliases(actor: RequestActor) -> None:
    call_dict = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="query", value="CVE-2024-3094"),),
    )
    result = await execute_cve_lookup(call_dict, actor)
    assert result.status == "succeeded"
    assert "XZ Utils" in result.summary


@pytest.mark.asyncio
async def test_cve_lookup_uncached_valid_format(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="CVE-2099-99999"),),
    )
    result = await execute_cve_lookup(call, actor)
    assert result.status == "succeeded"
    assert "CVE-2099-99999" in result.summary
    assert "subject to vendor advisory" in result.summary


@pytest.mark.asyncio
async def test_cve_lookup_invalid_format(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="invalid-token"),),
    )
    result = await execute_cve_lookup(call, actor)
    assert result.status == "failed"
    assert "Invalid CVE format" in result.summary


@pytest.mark.asyncio
async def test_mitre_attack_lookup_technique_id(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="technique_id", value="T1190"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)
    assert result.status == "succeeded"
    assert "Exploit Public-Facing Application" in result.summary
    assert "Initial Access" in result.summary


@pytest.mark.asyncio
async def test_mitre_attack_lookup_by_name(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="technique_id", value="Phishing"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)
    assert result.status == "succeeded"
    assert "T1566" in result.summary


@pytest.mark.asyncio
async def test_mitre_attack_lookup_chinese(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="technique_id", value="钓鱼邮件"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)
    assert result.status == "succeeded"
    assert "T1566" in result.summary


@pytest.mark.asyncio
async def test_mitre_attack_lookup_dict_arguments(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="name", value="Credential Dumping"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)
    assert result.status == "succeeded"
    assert "T1003" in result.summary


@pytest.mark.asyncio
async def test_mitre_attack_lookup_invalid(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="technique_id", value="xyz123"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)
    assert result.status == "failed"
    assert "Invalid MITRE ATT&CK technique" in result.summary
