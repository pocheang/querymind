"""Enterprise Cybersecurity Intelligence Tools.

Provides:
1. CVE / NVD Vulnerability Intelligence Lookup
2. MITRE ATT&CK Technique Mapping and Mitigation Lookup
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.orchestration.request import RequestActor
from app.tools.base import extract_call_argument

logger = logging.getLogger(__name__)

# Every score here is NVD's own (`nvd@nist.gov`) CVSS v3.1 base score, checked
# against the NVD API on the date each entry carries. This tool answers
# `succeeded` and the model cites it as authoritative, so a wrong number becomes
# a wrong answer. Four were: CVE-2023-38606 read 8.8 HIGH where NVD has 5.5
# MEDIUM, EternalBlue 9.8 CRITICAL for 8.8 HIGH, Struts2 S2-045 10.0 for 9.8,
# and CitrixBleed carried Citrix's own 9.4 where NVD has 7.5 -- the table mixed
# sources without saying which. A score changed later must name its source and
# date the same way.
#
# The same holds for the other two fields a reader acts on. `affected` is
# generated from NVD's CPE configurations for each entry's primary products;
# four read narrower than NVD (Spring4Shell, Struts2, CitrixBleed,
# CVE-2023-38606), which tells someone on an affected version they are safe.
# `mitigation` says what the official advisory it names says: Log4Shell's
# offered `log4j2.formatMsgNoLookups=true`, which Apache's advisory for this CVE
# does not list, and XZ's pointed at a "5.6.1+repack" build tukaani.org never
# mentions.
# The date every NVD-derived field below was checked, and the two sources they
# name -- one definition each, so a refresh changes one line rather than 28.
_NVD_CHECKED = "2026-09-23"
_NVD_CVSS_SOURCE = "NVD (nvd@nist.gov), CVSS v3.1"
_NVD_CPE_SOURCE = f"NVD CPE configurations, primary products, {_NVD_CHECKED}"
_CURATED_CVE_DB: dict[str, dict[str, Any]] = {
    "cve-2021-44228": {
        "cve_id": "CVE-2021-44228",
        "name": "Log4Shell",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Apache Log4j 2.0.1 to before 2.3.1, 2.4.0 to before 2.12.2, 2.13.0 to before 2.15.0, 2.0, 2.0-beta9, 2.0-rc1, 2.0-rc2",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "JNDI lookup feature vulnerability allowing unauthenticated remote code execution (RCE) via ldap:// or rmi:// injection.",
        "mitigation": "Upgrade log4j-core to 2.15.0 or later (Java 8 and later), 2.12.2 (Java 7) or 2.3.1 (Java 6). Apache's advisory gives upgrading as the mitigation and lists no configuration-only workaround.",
        "mitigation_source": "https://logging.apache.org/log4j/2.x/security.html, checked 2026-09-23",
    },
    "cve-2022-22965": {
        "cve_id": "CVE-2022-22965",
        "name": "Spring4Shell",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Spring Framework before 5.2.20, 5.3.0 to before 5.3.18",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Remote code execution via class loader manipulation when deployed as WAR on Apache Tomcat.",
        "mitigation": "Upgrade Spring Framework to 5.3.18 or later, or 5.2.20 or later.",
        "mitigation_source": "https://spring.io/security/cve-2022-22965, checked 2026-09-23",
    },
    "cve-2014-0160": {
        "cve_id": "CVE-2014-0160",
        "name": "Heartbleed",
        "cvss": 7.5,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "OpenSSL 1.0.1 to before 1.0.1g",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Information disclosure vulnerability in TLS heartbeat extension leading to memory leak.",
        "mitigation": "Upgrade OpenSSL to 1.0.1g; if that is not immediately possible, recompile with -DOPENSSL_NO_HEARTBEATS.",
        "mitigation_source": "https://www.openssl.org/news/secadv/20140407.txt, checked 2026-09-23",
    },
    "cve-2023-38606": {
        "cve_id": "CVE-2023-38606",
        "name": "Operation Triangulation MMIO Exploit",
        "cvss": 5.5,
        "severity": "MEDIUM",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "iPadOS before 15.7.8, 16.0 to before 16.6; iOS before 15.7.8, 16.0 to before 16.6; macOS 11.0 to before 11.7.9, 12.0.0 to before 12.6.8, 13.0 to before 13.5; tvOS before 16.6; watchOS before 9.6",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Hardware MMIO registers vulnerability enabling bypass of page table protections and kernel integrity.",
        "mitigation": "Update to iOS/iPadOS 16.6 or 15.7.8, macOS 13.5, 12.6.8 or 11.7.9, tvOS 16.6, or watchOS 9.6.",
        "mitigation_source": "https://support.apple.com/en-us/HT213841 and NVD's fixed versions, checked 2026-09-23",
    },
    "cve-2024-3094": {
        "cve_id": "CVE-2024-3094",
        "name": "XZ Utils Liblzma Upstream Backdoor",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "XZ Utils 5.6.0, 5.6.1",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Malicious backdoor inserted into liblzma tarballs hijacking OpenSSH sshd pre-authentication flow via systemd notify socket.",
        "mitigation": "Replace XZ Utils 5.6.0 and 5.6.1, whose release tarballs contain the backdoor: downgrade to a release before 5.6.0, or upgrade to 5.6.2 or later, the upstream cleanup release.",
        "mitigation_source": "https://tukaani.org/xz-backdoor/, checked 2026-09-23",
    },
    "cve-2023-4863": {
        "cve_id": "CVE-2023-4863",
        "name": "libwebp Heap Buffer Overflow",
        "cvss": 8.8,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Google Chrome before 116.0.5845.187; Firefox before 102.15.1, before 117.0.1, 115.1.0 to before 115.2.1; Thunderbird before 102.15.1, 115.0 to before 115.2.2; libwebp before 1.3.2",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Heap buffer overflow in WebP lossless decoding allowing remote code execution via malicious .webp image.",
        "mitigation": "Update libwebp to 1.3.2 or later, and every application that bundles it; NVD lists Chrome 116.0.5845.187, Firefox 117.0.1 / ESR 115.2.1 / 102.15.1 and Thunderbird 115.2.2 / 102.15.1 as fixed.",
        "mitigation_source": "https://github.com/webmproject/libwebp/releases/tag/v1.3.2 and NVD's fixed versions, checked 2026-09-23",
    },
    "cve-2023-34362": {
        "cve_id": "CVE-2023-34362",
        "name": "MOVEit Transfer SQL Injection",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "MOVEit Cloud before 14.0.5.45, 14.1.0.0 to before 14.1.6.97, 15.0.0.0 to before 15.0.2.39; MOVEit Transfer before 2021.0.7, 2021.1.0 to before 2021.1.5, 2022.0.0 to before 2022.0.5, 2022.1.0 to before 2022.1.6, 2023.0.0 to before 2023.0.2",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "SQL injection in MOVEit Transfer web application leading to unauthenticated privilege escalation and data exfiltration.",
        "mitigation": "Deny HTTP and HTTPS traffic (ports 80 and 443) to MOVEit Transfer until the patch is applied; follow Progress's review-delete-reset steps (delete human2.aspx and any human2-prefixed files, .cmdline scripts and unauthorized user accounts); then apply Progress's fixed release.",
        "mitigation_source": "https://community.progress.com/s/article/MOVEit-Transfer-Critical-Vulnerability-31May2023, checked 2026-09-23",
    },
    "cve-2024-21626": {
        "cve_id": "CVE-2024-21626",
        "name": "runc Leaky File Descriptor Container Breakout",
        "cvss": 8.6,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "runc before 1.1.12",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Internal file descriptor leak in runc init enabling container escape to host filesystem via /proc/self/fd/7.",
        "mitigation": "Upgrade runc to 1.1.12 or later.",
        "mitigation_source": "https://github.com/opencontainers/runc/security/advisories/GHSA-xr7r-f8xq-vfvv, checked 2026-09-23",
    },
    "cve-2017-0144": {
        "cve_id": "CVE-2017-0144",
        "name": "EternalBlue (MS17-010)",
        "cvss": 8.8,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "SMBv1 on Windows 10 1507, Windows 10 1511, Windows 10 1607, Windows 7 SP1, Windows 8.1, Windows RT 8.1, Windows Server 2008 SP2, Windows Server 2008 R2 SP1, Windows Server 2012, Windows Server 2012 R2, Windows Server 2016, Windows Vista SP2",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Remote code execution flaw in Microsoft Server Message Block 1.0 (SMBv1) protocol exploited by WannaCry ransomware.",
        "mitigation": "Install security update MS17-010. Microsoft's workaround is disabling SMBv1 (KB 2696547).",
        "mitigation_source": "https://learn.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-010, checked 2026-09-23",
    },
    "cve-2017-5638": {
        "cve_id": "CVE-2017-5638",
        "name": "Apache Struts2 S2-045",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Apache Struts 2.2.3 to before 2.3.32, 2.5.0 to before 2.5.10.1",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Remote code execution vulnerability via malicious Content-Type header in Jakarta multipart parser.",
        "mitigation": "Upgrade Apache Struts to 2.3.32 or 2.5.10.1, or switch to a different multipart parser than the Jakarta-based one.",
        "mitigation_source": "https://cwiki.apache.org/confluence/display/WW/S2-045, checked 2026-09-23",
    },
    "cve-2020-1472": {
        "cve_id": "CVE-2020-1472",
        "name": "Zerologon",
        "cvss": 10.0,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Windows Server 1903; Windows Server 1909; Windows Server 2004; Windows Server 2008 R2 SP1; Windows Server 2012, R2; Windows Server 2016; Windows Server 2019; Windows Server 20H2",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Elevation of privilege flaw in Netlogon Remote Protocol (MS-NRPC) allowing domain takeover without credentials.",
        "mitigation": "Install the August 11, 2020 or later Windows updates on every domain controller, then enable enforcement mode (FullSecureChannelProtection); updates from February 9, 2021 enforce it.",
        "mitigation_source": "https://support.microsoft.com/en-us/topic/how-to-manage-the-changes-in-netlogon-secure-channel-connections-associated-with-cve-2020-1472-f7e8cc17-0309-1d6a-304e-5ba73cd1a11e, checked 2026-09-23",
    },
    "cve-2022-30190": {
        "cve_id": "CVE-2022-30190",
        "name": "Follina (MSDT RCE)",
        "cvss": 7.8,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "Windows 10 1507 before 10.0.10240.19325; Windows 10 1607 before 10.0.14393.5192; Windows 10 1809 before 10.0.17763.3046; Windows 10 20H2 before 10.0.19042.1766; Windows 10 21H1 before 10.0.19043.1766; Windows 10 21H2 before 10.0.19044.1766; Windows 11 21H2 before 10.0.22000.739; Windows 7 SP1; Windows 8.1; Windows RT 8.1; Windows Server 2008 R2 SP1; Windows Server 2012, R2; Windows Server 2016 before 10.0.14393.5192; Windows Server 2019 before 10.0.17763.3046; Windows Server 2022 before 10.0.20348.770; Windows Server 20H2 before 10.0.19042.1766",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Remote code execution vulnerability in Microsoft Support Diagnostic Tool (MSDT) when invoked from applications like Word.",
        "mitigation": "Install the June 2022 cumulative Windows updates.",
        "mitigation_source": "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2022-30190, checked 2026-09-23",
    },
    "cve-2023-4966": {
        "cve_id": "CVE-2023-4966",
        "name": "CitrixBleed",
        "cvss": 7.5,
        "severity": "HIGH",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "NetScaler ADC 12.1 to before 12.1-55.300, 13.0 to before 13.0-92.19, 13.1 to before 13.1-37.164, 13.1 to before 13.1-49.15, 14.1 to before 14.1-8.50; NetScaler Gateway 13.0 to before 13.0-92.19, 13.1 to before 13.1-49.15, 14.1 to before 14.1-8.50",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Sensitive information disclosure allowing session token hijacking to bypass multi-factor authentication.",
        "mitigation": "Install the fixed NetScaler ADC / Gateway builds, then kill active and persistent sessions: kill icaconnection -all, kill rdp connection -all, kill pcoipConnection -all, kill aaa session -all, clear lb persistentSessions.",
        "mitigation_source": "https://www.netscaler.com/blog/news/cve-2023-4966-critical-security-update-now-available-for-netscaler-adc-and-netscaler-gateway/, checked 2026-09-23",
    },
    "cve-2014-6271": {
        "cve_id": "CVE-2014-6271",
        "name": "Shellshock",
        "cvss": 9.8,
        "severity": "CRITICAL",
        "cvss_source": _NVD_CVSS_SOURCE,
        "cvss_as_of": _NVD_CHECKED,
        "affected": "GNU Bash through 4.3",
        "affected_source": _NVD_CPE_SOURCE,
        "description": "Arbitrary code execution flaw in Bash trailing function definitions exported via environment variables.",
        "mitigation": "Upgrade bash to your operating system vendor's patched release.",
        "mitigation_source": "https://access.redhat.com/security/cve/cve-2014-6271, checked 2026-09-23",
    },
}

# A nickname that names exactly one vulnerability. Product names are NOT here:
# "log4j" used to resolve to Log4Shell and "runc" to CVE-2024-21626, answering
# `succeeded` with one CVE as though it were the product's only one -- Log4j
# alone has CVE-2021-45046, CVE-2021-45105 and CVE-2021-44832 beside it. Those
# names live in `_PRODUCT_NAMES` and answer with what the set holds instead.
_CVE_NAME_ALIAS_MAP: dict[str, str] = {
    "log4shell": "cve-2021-44228",
    "heartbleed": "cve-2014-0160",
    "spring4shell": "cve-2022-22965",
    "xz backdoor": "cve-2024-3094",
    "eternalblue": "cve-2017-0144",
    "wannacry": "cve-2017-0144",
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

# A product or bulletin covering more than one CVE, mapped to the ones the
# curated set holds for it. `ms17-010` is a bulletin of six (CVE-2017-0143
# through -0148); "runc escape" also describes CVE-2019-5736.
_PRODUCT_NAMES: dict[str, tuple[str, ...]] = {
    "log4j": ("cve-2021-44228",),
    "xz": ("cve-2024-3094",),
    "xz utils": ("cve-2024-3094",),
    "moveit": ("cve-2023-34362",),
    "webp": ("cve-2023-4863",),
    "libwebp": ("cve-2023-4863",),
    "runc": ("cve-2024-21626",),
    "runc escape": ("cve-2024-21626",),
    "ms17-010": ("cve-2017-0144",),
    "struts2": ("cve-2017-5638",),
    "openssl": ("cve-2014-0160",),
    "bash": ("cve-2014-6271",),
}

# `(?!\d)`: `\d{4,7}` alone took the first seven digits of a longer run, so
# "CVE-2021-442281234" was looked up as CVE-2021-4422812.
_CVE_ID_RE = re.compile(r"cve-\d{4}-\d{4,7}(?!\d)")

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
    description=(
        "Look up a CVE in QueryMind's CURATED OFFLINE vulnerability set "
        "(a small hand-maintained table, not a live NVD feed). Returns CVSS score, affected "
        "versions and mitigation for the entries it holds, and reports 'not in the set' for "
        "everything else -- absence here is NOT evidence that a CVE is unknown or harmless."
    ),
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
    description=(
        "Map a MITRE ATT&CK technique ID to tactic phase, detection logic and mitigations, from "
        "QueryMind's CURATED OFFLINE subset of the matrix (not the full published taxonomy). "
        "Reports 'not in the subset' for techniques it does not hold."
    ),
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


def _product_result(tool_id: str, product: str) -> ToolResult:
    """A product name resolves to no single CVE, so the lookup does not pick one.

    `failed` because no one vulnerability was identified; the summary says what
    the curated set does hold, so the model can ask for that id rather than
    presenting it as the product's only CVE.
    """

    held = ", ".join(f"{_CURATED_CVE_DB[k]['cve_id']} ({_CURATED_CVE_DB[k]['name']})" for k in _PRODUCT_NAMES[product])
    return ToolResult(
        tool_id=tool_id,
        status="failed",
        summary=(
            f"'{product}' names a product or bulletin, not one vulnerability. QueryMind's curated offline set "
            f"holds {held} for it; that is not a complete list of its CVEs. Look up a specific CVE id."
        ),
    )


async def execute_cve_lookup(call: ToolCall, actor: RequestActor) -> ToolResult:
    """Execute CVE lookup against curated and structured intelligence database."""
    await asyncio.sleep(0)
    del actor
    cve_id_raw = _get_call_arg(call, "cve_id", "cve", "query", "name", "id", "vulnerability").strip().lower()

    # Check alias lookup first
    resolved_id = _CVE_NAME_ALIAS_MAP.get(cve_id_raw)
    if not resolved_id and cve_id_raw in _PRODUCT_NAMES:
        return _product_result(call.tool_id, cve_id_raw)
    if not resolved_id:
        match = _CVE_ID_RE.search(cve_id_raw)
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
            f"[{found['cve_id']}] {found['name']} (CVSS {found['cvss']} {found['severity']}, "
            f"{found['cvss_source']}, as of {found['cvss_as_of']}): "
            f"Affects {found['affected']} ({found['affected_source']}). "
            f"{found['description']} Mitigation ({found['mitigation_source']}): {found['mitigation']}"
        )
        return ToolResult(
            tool_id=call.tool_id,
            status="succeeded",
            summary=summary_text,
        )

    # A miss is a miss. This used to answer `succeeded` with "recorded in index"
    # for ANY well-formed identifier, so CVE-9999-9999 came back confirmed and
    # nothing downstream could tell a real hit from a fabricated one -- in a tool
    # whose own description promised authoritative intelligence. Reporting a
    # vulnerability that does not exist is worse than having no tool at all.
    return ToolResult(
        tool_id=call.tool_id,
        status="failed",
        summary=(
            f"{norm_id.upper()} is not in QueryMind's curated offline CVE set "
            f"({len(_CURATED_CVE_DB)} entries). No severity, affected-version or mitigation data is "
            "available here, and this says nothing about whether the CVE exists or how severe it is -- "
            "consult NVD or the vendor advisory."
        ),
    )


# Resolution is exact, never fuzzy. The previous step 3 accepted a technique if
# the INPUT was a substring of its name or tactic, and returned the first hit:
# "a", "on" and "" all resolved to T1190 as `succeeded`, and "initial access" --
# a tactic three curated techniques share -- resolved to whichever came first.
_TECHNIQUE_ID_RE = re.compile(r"(?<![a-z0-9])t\d{4}(?:\.\d{3})?(?!\d)")


def _attack_invalid(tool_id: str, tech_raw: str) -> ToolResult:
    return ToolResult(
        tool_id=tool_id,
        status="failed",
        summary=(
            f"Invalid MITRE ATT&CK technique: '{tech_raw}'. Expected a technique ID (e.g. T1190), "
            "a technique name (e.g. 'Phishing') or a tactic name (e.g. 'Initial Access')."
        ),
    )


def _technique_by_name(tech_raw: str) -> str | None:
    """The technique whose name is exactly this, ignoring case."""

    return next((tid for tid, data in _CURATED_ATTACK_DB.items() if data["name"].lower() == tech_raw), None)


def _techniques_in_tactic(tech_raw: str) -> list[dict[str, Any]]:
    """Every curated technique filed under a tactic named exactly this.

    A technique may carry more than one tactic ("Defense Evasion / Initial Access").
    """

    return [
        data
        for data in _CURATED_ATTACK_DB.values()
        if tech_raw in (part.strip().lower() for part in data["tactic"].split("/"))
    ]


def _tactic_result(tool_id: str, tactic: str, members: list[dict[str, Any]]) -> ToolResult:
    """A tactic is a phase with several techniques, so every curated one is named."""

    listed = "; ".join(f"[{m['technique_id']}] {m['name']}" for m in members)
    return ToolResult(
        tool_id=tool_id,
        status="succeeded",
        summary=(
            f"Tactic '{tactic}' in QueryMind's curated offline ATT&CK subset (not the full matrix): {listed}. "
            "Look up a technique id for its detection and mitigation."
        ),
    )


def _with_parent_fallback(technique_id: str) -> tuple[str, str]:
    """A sub-technique the subset lacks falls back to its parent, and says so."""

    parent = technique_id.split(".", 1)[0]
    if technique_id not in _CURATED_ATTACK_DB and parent != technique_id and parent in _CURATED_ATTACK_DB:
        note = f"{technique_id.upper()} is not in the curated subset; showing its parent technique. "
        return parent, note
    return technique_id, ""


async def execute_mitre_attack_lookup(call: ToolCall, actor: RequestActor) -> ToolResult:
    """Execute MITRE ATT&CK lookup against taxonomy."""
    await asyncio.sleep(0)
    del actor
    tech_raw = _get_call_arg(call, "technique_id", "technique", "id", "query", "tactic", "name").strip().lower()
    if not tech_raw:
        return _attack_invalid(call.tool_id, tech_raw)

    tactic_members = _techniques_in_tactic(tech_raw)
    if tactic_members:
        return _tactic_result(call.tool_id, tech_raw, tactic_members)

    resolved_id = _ATTACK_NAME_ALIAS_MAP.get(tech_raw) or _technique_by_name(tech_raw)
    note = ""
    if not resolved_id:
        match = _TECHNIQUE_ID_RE.search(tech_raw)
        if match is None:
            return _attack_invalid(call.tool_id, tech_raw)
        resolved_id, note = _with_parent_fallback(match.group(0))

    norm_id = resolved_id.lower()
    found = _CURATED_ATTACK_DB.get(norm_id)
    if found:
        summary_text = (
            f"{note}[{found['technique_id']}] {found['name']} (Tactic: {found['tactic']}): "
            f"{found['description']} Detection: {found['detection']} Mitigation: {found['mitigation']}"
        )
        return ToolResult(
            tool_id=call.tool_id,
            status="succeeded",
            summary=summary_text,
        )

    # Same rule as the CVE lookup above: an unknown technique id was being
    # confirmed as "recognized in taxonomy" with generic advice attached.
    return ToolResult(
        tool_id=call.tool_id,
        status="failed",
        summary=(
            f"{norm_id.upper()} is not in QueryMind's curated offline ATT&CK subset "
            f"({len(_CURATED_ATTACK_DB)} techniques). No tactic, detection or mitigation data is "
            "available here -- consult attack.mitre.org."
        ),
    )


__all__ = [
    "ATTACK_TOOL_DEFINITION",
    "CVE_TOOL_DEFINITION",
    "execute_cve_lookup",
    "execute_mitre_attack_lookup",
]
