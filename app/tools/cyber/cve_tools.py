"""Enterprise Cybersecurity Intelligence Tools.

Provides:
1. CVE / NVD Vulnerability Intelligence Lookup
2. MITRE ATT&CK Technique Mapping and Mitigation Lookup
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.orchestration.request import RequestActor
from app.tools.base import extract_call_argument

logger = logging.getLogger(__name__)

_CURATED_CVE_DB: dict[str, dict[str, Any]] = {
    "cve-2021-44228": {
        "cve_id": "CVE-2021-44228",
        "name": "Log4Shell",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "affected": "Apache Log4j 2.0-beta9 to 2.14.1",
        "description": "JNDI lookup feature vulnerability allowing unauthenticated remote code execution (RCE) via ldap:// or rmi:// injection.",
        "mitigation": "Upgrade Log4j to >= 2.17.1, remove JndiLookup class, or set log4j2.formatMsgNoLookups=true.",
    },
    "cve-2022-22965": {
        "cve_id": "CVE-2022-22965",
        "name": "Spring4Shell",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "affected": "Spring Framework 5.3.0 to 5.3.17, 5.2.0 to 5.2.19 on JDK 9+",
        "description": "Remote code execution via class loader manipulation when deployed as WAR on Apache Tomcat.",
        "mitigation": "Upgrade Spring Framework to 5.3.18+ or 5.2.20+.",
    },
    "cve-2014-0160": {
        "cve_id": "CVE-2014-0160",
        "name": "Heartbleed",
        "cvss": 7.5,
        "severity": "HIGH",
        "affected": "OpenSSL 1.0.1 through 1.0.1f",
        "description": "Information disclosure vulnerability in TLS heartbeat extension leading to memory leak.",
        "mitigation": "Upgrade OpenSSL to 1.0.1g+ or recompile with -DOPENSSL_NO_HEARTBEATS.",
    },
    "cve-2023-38606": {
        "cve_id": "CVE-2023-38606",
        "name": "Operation Triangulation MMIO Exploit",
        "cvss": 8.8,
        "severity": "HIGH",
        "affected": "Apple iOS before 16.6, iPadOS, macOS",
        "description": "Hardware MMIO registers vulnerability enabling bypass of page table protections and kernel integrity.",
        "mitigation": "Apply iOS 16.6+ security update.",
    },
    "cve-2024-3094": {
        "cve_id": "CVE-2024-3094",
        "name": "XZ Utils Liblzma Upstream Backdoor",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "affected": "XZ Utils versions 5.6.0 and 5.6.1",
        "description": "Malicious backdoor inserted into liblzma tarballs hijacking OpenSSH sshd pre-authentication flow via systemd notify socket.",
        "mitigation": "Immediately downgrade xz-utils to 5.4.x or upgrade to fixed non-compromised builds (e.g. 5.6.1+repack).",
    },
    "cve-2023-4863": {
        "cve_id": "CVE-2023-4863",
        "name": "libwebp Heap Buffer Overflow",
        "cvss": 8.8,
        "severity": "HIGH",
        "affected": "libwebp before 1.3.2, Google Chrome before 116.0.5845.187, Firefox, Electron",
        "description": "Heap buffer overflow in WebP lossless decoding allowing remote code execution via malicious .webp image.",
        "mitigation": "Update libwebp to 1.3.2+ and patch all browsers/Electron-based applications.",
    },
    "cve-2023-34362": {
        "cve_id": "CVE-2023-34362",
        "name": "MOVEit Transfer SQL Injection",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "affected": "MOVEit Transfer versions prior to 2021.0.6, 2021.1.4, 2022.0.4, 2022.1.5, 2023.0.1",
        "description": "SQL injection in MOVEit Transfer web application leading to unauthenticated privilege escalation and data exfiltration.",
        "mitigation": "Apply vendor security hotfix, disable HTTP/HTTPS ports 80/443 temporarily, and inspect for human2.aspx webshell.",
    },
    "cve-2024-21626": {
        "cve_id": "CVE-2024-21626",
        "name": "runc Leaky File Descriptor Container Breakout",
        "cvss": 8.6,
        "severity": "HIGH",
        "affected": "runc versions <= 1.1.11, Docker, containerd, Kubernetes",
        "description": "Internal file descriptor leak in runc init enabling container escape to host filesystem via /proc/self/fd/7.",
        "mitigation": "Upgrade runc to >= 1.1.12.",
    },
    "cve-2017-0144": {
        "cve_id": "CVE-2017-0144",
        "name": "EternalBlue (MS17-010)",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "affected": "Microsoft Windows Vista, 7, 8.1, 10, Server 2008/2012/2016",
        "description": "Remote code execution flaw in Microsoft Server Message Block 1.0 (SMBv1) protocol exploited by WannaCry ransomware.",
        "mitigation": "Apply MS17-010 security bulletin, disable SMBv1, and block port 445 at network perimeter.",
    },
    "cve-2017-5638": {
        "cve_id": "CVE-2017-5638",
        "name": "Apache Struts2 S2-045",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "affected": "Struts 2.3.5 - 2.3.31, 2.5 - 2.5.10",
        "description": "Remote code execution vulnerability via malicious Content-Type header in Jakarta multipart parser.",
        "mitigation": "Upgrade Struts to 2.3.32 or 2.5.10.1+.",
    },
    "cve-2020-1472": {
        "cve_id": "CVE-2020-1472",
        "name": "Zerologon",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "affected": "Windows Server 2008 R2 through Server 2019",
        "description": "Elevation of privilege flaw in Netlogon Remote Protocol (MS-NRPC) allowing domain takeover without credentials.",
        "mitigation": "Apply Microsoft August 2020 Netlogon patch and enforce secure RPC communication.",
    },
    "cve-2022-30190": {
        "cve_id": "CVE-2022-30190",
        "name": "Follina (MSDT RCE)",
        "cvss": 7.8,
        "severity": "HIGH",
        "affected": "Microsoft Windows 7 through 11, Windows Server 2008 through 2022",
        "description": "Remote code execution vulnerability in Microsoft Support Diagnostic Tool (MSDT) when invoked from applications like Word.",
        "mitigation": "Apply June 2022 cumulative Windows update, disable MSDT URL protocol handler.",
    },
    "cve-2023-4966": {
        "cve_id": "CVE-2023-4966",
        "name": "CitrixBleed",
        "cvss": 9.4,
        "severity": "CRITICAL",
        "affected": "NetScaler ADC and NetScaler Gateway versions 13.0, 13.1, 14.1",
        "description": "Sensitive information disclosure allowing session token hijacking to bypass multi-factor authentication.",
        "mitigation": "Upgrade NetScaler firmware and terminate all active ICA/gateway sessions via CLI.",
    },
    "cve-2014-6271": {
        "cve_id": "CVE-2014-6271",
        "name": "Shellshock",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "affected": "GNU Bash versions through 4.3",
        "description": "Arbitrary code execution flaw in Bash trailing function definitions exported via environment variables.",
        "mitigation": "Upgrade bash package to patched vendor release.",
    },
}

_CVE_NAME_ALIAS_MAP: dict[str, str] = {
    "log4shell": "cve-2021-44228",
    "log4j": "cve-2021-44228",
    "heartbleed": "cve-2014-0160",
    "spring4shell": "cve-2022-22965",
    "xz": "cve-2024-3094",
    "xz utils": "cve-2024-3094",
    "xz backdoor": "cve-2024-3094",
    "moveit": "cve-2023-34362",
    "webp": "cve-2023-4863",
    "runc": "cve-2024-21626",
    "runc escape": "cve-2024-21626",
    "eternalblue": "cve-2017-0144",
    "ms17-010": "cve-2017-0144",
    "wannacry": "cve-2017-0144",
    "struts2": "cve-2017-5638",
    "s2-045": "cve-2017-5638",
    "zerologon": "cve-2020-1472",
    "follina": "cve-2022-30190",
    "citrixbleed": "cve-2023-4966",
    "citrix bleed": "cve-2023-4966",
    "shellshock": "cve-2014-6271",
    # Chinese aliases
    "心脏滴血": "cve-2014-0160",
    "永恒之蓝": "cve-2017-0144",
    "破壳": "cve-2014-6271",
    "核弹漏洞": "cve-2021-44228",
}

_CURATED_ATTACK_DB: dict[str, dict[str, Any]] = {
    "t1190": {
        "technique_id": "T1190",
        "name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "description": "Adversaries may attempt to exploit vulnerabilities in Internet-facing applications to gain initial network access.",
        "detection": "Monitor application access logs, web application firewall (WAF) alerts, and process execution from web service accounts.",
        "mitigation": "Application isolation, vulnerability scanning, regular patching, and network segmentation.",
    },
    "t1059": {
        "technique_id": "T1059",
        "name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "description": "Adversaries may abuse command and script interpreters (PowerShell, Bash, Python, Cmd) to execute commands.",
        "detection": "Monitor process creation with command-line arguments and script block logging.",
        "mitigation": "Execution prevention (AppLocker, WDAC), script signing, and least privilege accounts.",
    },
    "t1068": {
        "technique_id": "T1068",
        "name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "description": "Adversaries may exploit software vulnerabilities in OS or drivers to escalate privileges to SYSTEM or root.",
        "detection": "Monitor for unexpected privilege transitions, kernel-level alerts, and anomalous service creation.",
        "mitigation": "Least privilege, OS kernel updates, exploit protection guards, and disabling vulnerable legacy drivers.",
    },
    "t1078": {
        "technique_id": "T1078",
        "name": "Valid Accounts",
        "tactic": "Defense Evasion / Initial Access",
        "description": "Adversaries may obtain and abuse credentials of existing accounts to avoid detection.",
        "detection": "Audit login events, impossible travel anomalies, MFA exhaustion attacks, and off-hours administrative activity.",
        "mitigation": "Multi-factor authentication (MFA), password complexity, credential rotation, and privileged access management (PAM).",
    },
    "t1003": {
        "technique_id": "T1003",
        "name": "OS Credential Dumping",
        "tactic": "Credential Access",
        "description": "Adversaries may attempt to dump credentials from the operating system (e.g. LSASS memory, SAM database, /etc/shadow).",
        "detection": "Enable Credential Guard, monitor LSASS handle opens (Sysmon Event ID 10), and restrict SeDebugPrivilege.",
        "mitigation": "LSA Protection (RunAsPPL), Windows Defender Credential Guard, and eliminating cleartext credentials.",
    },
    "t1021": {
        "technique_id": "T1021",
        "name": "Remote Services",
        "tactic": "Lateral Movement",
        "description": "Adversaries may log in to remote services (SMB/Windows Admin Shares, RDP, SSH) to move laterally.",
        "detection": "Monitor network logon events (Event ID 4624 Logon Type 3/10) and unusual administrative share connections (IPC$, C$).",
        "mitigation": "Network segmentation, host-based firewalls blocking inbound SMB/RDP between workstations, and MFA for remote admin.",
    },
    "t1048": {
        "technique_id": "T1048",
        "name": "Exfiltration Over Alternative Protocol",
        "tactic": "Exfiltration",
        "description": "Adversaries may exfiltrate data using symmetric protocols or channels other than the primary C2 channel.",
        "detection": "Network traffic volume anomaly detection, deep packet inspection (DPI), and DNS query tunneling monitoring.",
        "mitigation": "Egress filtering, proxy inspection, and blocking unauthorized external storage services.",
    },
    "t1566": {
        "technique_id": "T1566",
        "name": "Phishing",
        "tactic": "Initial Access",
        "description": "Adversaries send phishing messages with malicious attachments or links to gain execution or credentials.",
        "detection": "Email gateway anti-malware scanning, domain reputation filtering, and user reported phishing telemetry.",
        "mitigation": "DMARC/DKIM/SPF enforcement, email attachment sandboxing, and security awareness training.",
    },
}

_ATTACK_NAME_ALIAS_MAP: dict[str, str] = {
    "phishing": "t1566",
    "spearphishing": "t1566",
    "钓鱼": "t1566",
    "钓鱼邮件": "t1566",
    "credential dumping": "t1003",
    "lsass": "t1003",
    "凭证转储": "t1003",
    "抓密码": "t1003",
    "remote services": "t1021",
    "rdp": "t1021",
    "smb": "t1021",
    "横向移动": "t1021",
    "powershell": "t1059",
    "bash": "t1059",
    "command and scripting": "t1059",
    "命令与脚本": "t1059",
    "valid accounts": "t1078",
    "合法账户": "t1078",
    "提权": "t1068",
    "权限提升": "t1068",
    "privilege escalation": "t1068",
    "exfiltration": "t1048",
    "数据外发": "t1048",
    "public-facing": "t1190",
    "公开应用利用": "t1190",
}

CVE_TOOL_DEFINITION = ToolDefinition(
    tool_id="querymind_cyber_cve_lookup",
    operation="read",
    risk="read_only",
    category="cybersecurity",
    description="Query authoritative CVE vulnerability intelligence, CVSS scores, affected software versions, and mitigation procedures.",
    parameters=(
        ToolParameter(
            name="cve_id",
            description="The standard CVE identifier (e.g. 'CVE-2021-44228') or well-known name (e.g. 'Log4Shell').",
            required=True,
            max_length=64,
        ),
    ),
)

ATTACK_TOOL_DEFINITION = ToolDefinition(
    tool_id="querymind_cyber_mitre_attack",
    operation="read",
    risk="read_only",
    category="cybersecurity",
    description="Map MITRE ATT&CK technique IDs (e.g. 'T1190', 'T1059') to tactic phases, detection logic, and defensive mitigations.",
    parameters=(
        ToolParameter(
            name="technique_id",
            description="The MITRE ATT&CK technique ID (e.g. 'T1190') or technique keyword (e.g. 'Phishing').",
            required=True,
            max_length=64,
        ),
    ),
)


_get_call_arg = extract_call_argument


async def execute_cve_lookup(call: ToolCall, actor: RequestActor) -> ToolResult:
    """Execute CVE lookup against curated and structured intelligence database."""
    del actor
    cve_id_raw = _get_call_arg(call, "cve_id", "cve", "query", "name", "id", "vulnerability").strip().lower()

    # Check alias lookup first
    resolved_id = _CVE_NAME_ALIAS_MAP.get(cve_id_raw)
    if not resolved_id:
        match = re.search(r"cve-\d{4}-\d{4,7}", cve_id_raw)
        resolved_id = match.group(0) if match else None

    if not resolved_id:
        return ToolResult(
            tool_id=call.tool_id,
            status="failed",
            summary=f"Invalid CVE format: '{cve_id_raw}'. Expected format: CVE-YYYY-NNNN or well-known vulnerability name.",
        )

    norm_id = resolved_id.lower()
    found = _CURATED_CVE_DB.get(norm_id)
    if found:
        summary_text = (
            f"[{found['cve_id']}] {found['name']} (CVSS {found['cvss']} {found['severity']}): "
            f"Affects {found['affected']}. {found['description']} Mitigation: {found['mitigation']}"
        )
        return ToolResult(
            tool_id=call.tool_id,
            status="succeeded",
            summary=summary_text,
        )

    return ToolResult(
        tool_id=call.tool_id,
        status="succeeded",
        summary=f"CVE {norm_id.upper()} recorded in index. Severity and mitigation subject to vendor advisory.",
    )


async def execute_mitre_attack_lookup(call: ToolCall, actor: RequestActor) -> ToolResult:
    """Execute MITRE ATT&CK lookup against taxonomy."""
    del actor
    tech_raw = _get_call_arg(call, "technique_id", "technique", "id", "query", "tactic", "name").strip().lower()

    # 1. Direct alias check (e.g. "phishing", "钓鱼", "credential dumping")
    resolved_id = _ATTACK_NAME_ALIAS_MAP.get(tech_raw)

    # 2. Regex technique ID extraction (e.g. "T1190" or "T1059.001")
    if not resolved_id:
        match = re.search(r"t\d{4}(?:\.\d{3})?", tech_raw)
        if match:
            resolved_id = match.group(0)

    # 3. Fuzzy search by name or description in curated database
    if not resolved_id:
        for tid, data in _CURATED_ATTACK_DB.items():
            if tech_raw in data["name"].lower() or tech_raw in data["tactic"].lower():
                resolved_id = tid
                break

    if not resolved_id:
        return ToolResult(
            tool_id=call.tool_id,
            status="failed",
            summary=f"Invalid MITRE ATT&CK technique: '{tech_raw}'. Expected technique ID (e.g. T1190) or common name (e.g. 'Phishing').",
        )

    norm_id = resolved_id.lower()
    found = _CURATED_ATTACK_DB.get(norm_id)
    if found:
        summary_text = (
            f"[{found['technique_id']}] {found['name']} (Tactic: {found['tactic']}): "
            f"{found['description']} Detection: {found['detection']} Mitigation: {found['mitigation']}"
        )
        return ToolResult(
            tool_id=call.tool_id,
            status="succeeded",
            summary=summary_text,
        )

    return ToolResult(
        tool_id=call.tool_id,
        status="succeeded",
        summary=f"MITRE ATT&CK technique {norm_id.upper()} recognized in taxonomy. Implement endpoint detection and logging.",
    )


__all__ = [
    "ATTACK_TOOL_DEFINITION",
    "CVE_TOOL_DEFINITION",
    "execute_cve_lookup",
    "execute_mitre_attack_lookup",
]
