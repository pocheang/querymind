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
async def test_a_cve_outside_the_curated_set_is_reported_as_a_miss(actor: RequestActor) -> None:
    """A miss is a miss, and this test used to assert the opposite.

    Its previous form pinned `status == "succeeded"` and the words "subject to
    vendor advisory" for CVE-2099-99999 -- so a CVE that does not exist came
    back CONFIRMED, with a success status nothing downstream could distinguish
    from a real hit, out of a tool whose description promised authoritative
    intelligence. In a compliance application that is not a thin answer, it is a
    fabricated one, and the test was locking it in.

    What has to hold instead: the status says the lookup failed, the summary
    says which set it is absent from, and it explicitly does NOT claim the CVE
    is unknown or harmless -- 14 curated entries is not the NVD.
    """

    call = ToolCall(
        tool_id=CVE_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="cve_id", value="CVE-2099-99999"),),
    )
    result = await execute_cve_lookup(call, actor)

    assert result.status == "failed"
    assert "CVE-2099-99999" in result.summary
    assert "curated offline" in result.summary
    # The exact wording that used to be here, asserted absent: a reader must not
    # be told a severity judgement was made when none was.
    assert "subject to vendor advisory" not in result.summary


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


@pytest.mark.asyncio
async def test_an_attack_technique_outside_the_curated_subset_is_reported_as_a_miss(actor: RequestActor) -> None:
    """Same rule as the CVE lookup: T9999 used to come back "recognized in
    taxonomy" with generic detection advice attached, for any id matching the
    shape."""

    call = ToolCall(
        tool_id=ATTACK_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="technique_id", value="T9999"),),
    )
    result = await execute_mitre_attack_lookup(call, actor)

    assert result.status == "failed"
    assert "T9999" in result.summary
    assert "curated offline" in result.summary
    assert "recognized in taxonomy" not in result.summary


@pytest.mark.parametrize(
    "definition",
    [CVE_TOOL_DEFINITION, ATTACK_TOOL_DEFINITION],
    ids=["cve", "attack"],
)
def test_the_description_the_model_reads_says_the_source_is_a_curated_offline_set(definition) -> None:
    """The description is the only thing the tool selector sees, so it is where
    the honesty has to live.

    The CVE tool's said it queried "authoritative CVE vulnerability
    intelligence" while holding a hand-maintained table of a dozen entries and
    no live feed. A model shown that will offer the answer with the confidence
    the word "authoritative" buys it.
    """

    text = definition.description.lower()

    assert "curated" in text
    assert "offline" in text
    assert "authoritative" not in text
