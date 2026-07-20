# Google Cloud Threat Detection & Remediation Lab

A hands-on GCP security project covering environment deployment, simulated adversary activity, log-based investigation, and vulnerability remediation using Security Command Center.

## Objective

Deploy a cloud VM, simulate post-compromise attacker behavior, investigate what visibility Cloud Logging actually provides, then use Security Command Center to discover and remediate real misconfigurations — moving beyond detection into hands-on fix and risk-acceptance decisions.

## Tools Used

- Google Cloud Compute Engine
- Google Cloud IAM & Admin
- Google Cloud Ops Agent
- Cloud Audit Logs / Logs Explorer
- Security Command Center (SCC)
- VPC Firewall Rules
- Identity-Aware Proxy (IAP)

---

## Part 1: Environment Setup

Created a new GCP project (`cloud-security-lab`) and deployed a Compute Engine VM (`security-lab-vm`) in `us-central1-a`.

![VM created](./screenshots/VM%20created.png)

Reviewed IAM permissions for the project to confirm ownership and role assignments before proceeding.

![IAM Admin](./screenshots/IAM%20and%20Admin.png)

Checked the VM's Cloud API access scopes. This became relevant later: the VM was provisioned with **default access scopes**, not the specific logging/monitoring scopes needed for full observability.

![Access scopes](./screenshots/access%20scopes.png)

## Part 2: Logging Agent Configuration

Installed the Google Cloud Ops Agent to forward VM logs to Cloud Logging. On first status check, the agent reported two permission failures:

```
[API Check] Result: FAIL, Error code: MonApiPermissionErr
[API Check] Result: FAIL, Error code: LogApiPermissionErr
```

This confirmed the service account was missing the required logging/monitoring scopes noted in Part 1.

![Agent check](./screenshots/agent%20check.png)

After adjusting the environment and restarting the agent, the logging service (`google-cloud-ops-agent-fluent-bit`) came up active and running.

![Agent status](./screenshots/agent%20status.png)

Verified the agent's merged configuration to confirm it was correctly set up to collect both `syslog` and `authlog` sources.

![Agent config updated](./screenshots/agent%20updated%20.png)

## Part 3: Simulated Adversary Activity

To test detection visibility, I simulated common post-compromise attacker behavior directly on the VM:

- Viewed `/etc/shadow` (credential access attempt)
- Ran `whoami`, `id`, `netstat -tulpn` (situational awareness / discovery)
- Created a new user: `sudo useradd backdoor-user` (persistence)
- Staged suspicious shell scripts (`malicious_payload.sh`, `suspicious_file.sh`)

![Simulated commands](./screenshots/sus%20commands.png)

## Part 4: Detection & Investigation

Reviewed the project's Audit Log configuration, confirming Admin Read, Data Read, and Data Write logging was enabled across 50 services.

![Audit log config](./screenshots/top%20of%20iam%20page%20.png)

Queried Logs Explorer broadly across the project and found 78 results, including IAM policy changes, service account activity, and API calls tied to my own actions during setup.

![Broad log query](./screenshots/log%20into%20detail%20.png)

**Key finding:** Cloud Audit Logs (control-plane visibility — who did what to the infrastructure) worked reliably and captured meaningful events. However, OS-level log forwarding (the actual attacker commands run inside the VM) never reached Cloud Logging, despite the logs existing locally on the VM. Root cause: the VM's service account access scopes were fixed at creation time and could not be changed without stopping and editing the instance — a real troubleshooting scenario, not a configuration mistake.

This is a genuine enterprise lesson: **logging pipelines need to be designed before deployment**, since some settings can't be patched live afterward.

---

## Part 5: Vulnerability Discovery (Security Command Center)

Used Security Command Center's Findings page to check for misconfigurations on the environment. It surfaced **4 High-severity findings**:

| Category | Severity |
|---|---|
| Open RDP port | High |
| Open SSH port | High |
| Non org IAM member | High |
| Public IP address | High |

![SCC findings baseline](./screenshots/Security%20Center.png)

## Part 6: Remediation

### Fix 1 — Open RDP port

The VM is Linux-only, so RDP (port 3389) was never in use. The `default-allow-rdp` firewall rule was open to `0.0.0.0/0` with no legitimate purpose.

**Before:**

![RDP rule before delete](./screenshots/RDP%20before%20delete.png)

**Action:** Deleted the `default-allow-rdp` rule entirely.

**After:**

![RDP rule after delete](./screenshots/RDP%20after%20deleting.png)

### Fix 2 — Open SSH port

The `default-allow-ssh` rule allowed SSH (port 22) from anywhere on the internet (`0.0.0.0/0`). Rather than simply deleting it (which would have blocked all access), I replaced it with a rule scoped only to Google's fixed IAP range (`35.235.240.0/20`), which is the IP range Google's Identity-Aware Proxy uses to tunnel SSH sessions through the console.

**Creating the replacement rule:**

![Creating IAP-only SSH rule](./screenshots/Firewall%20rule%20being%20created.png)

**New rule confirmed:**

![New SSH rule created](./screenshots/Rule%20showed%20on%20list.%20.png)

**Old open rule removed, final list:**

![Old SSH rule deleted](./screenshots/firewall%20list%20with%20deleted%20SSH.png)

**Verification — SSH access still works, now exclusively through IAP:**

![SSH still works after rule swap](./screenshots/opening%20Vm%20after%20rule%20change.png)

The terminal login confirms the session originated from `35.235.245.129`, an address inside Google's documented IAP range — proof the connection is tunneling through IAP rather than a direct open port.

### Fix 3 — Public IP address

The VM had an external IP attached, increasing its internet-facing attack surface unnecessarily. Removed the external IP entirely, relying on IAP tunneling for all future access.

**External IP set to None:**

![External IP removed](./screenshots/external%20none.png)

**Verification — SSH access still works with zero public IP:**

![SSH still works with no external IP](./screenshots/VM%20after%20external.png)

### Accepted Risk — Non org IAM member

This finding flags that the project's IAM principal isn't part of a Cloud Identity/Google Workspace organization. Since this is a personal, free-tier lab environment with no organizational hierarchy attached, there is no org to "join," and building one solely to satisfy this finding wouldn't reflect a real environment.

**Decision:** Accepted as a documented risk rather than remediated. In an enterprise context, this same finding would represent a genuine access control gap warranting investigation — the distinction here is recognizing when a finding reflects environment design versus an actual security gap.

## Part 7: Verification

Re-ran the Findings query after remediation. Active High-severity findings dropped from 4 to 1, with only the accepted-risk item (Non org IAM member) remaining.

![Findings resolved](./screenshots/Almost%20all%20findings%20solved.png)

---

## MITRE ATT&CK Mapping

| Technique | ID | Where it applied |
|---|---|---|
| Account Discovery | T1087 | `whoami`, `id` |
| System Network Configuration Discovery | T1016 | `netstat -tulpn` |
| Create Account | T1136 | `useradd backdoor-user` |
| Unsecured Credentials | T1552 | `/etc/shadow` access |
| External Remote Services | T1133 | Open SSH/RDP exposure, remediated via IAP |

## Key Takeaways

- **Control-plane vs. data-plane visibility matters.** Cloud Audit Logs capture infrastructure-level changes reliably; OS-level activity requires correctly-scoped service accounts configured at VM creation time.
- **Not every finding should be "fixed."** Recognizing when a finding reflects environment context (like a personal lab with no org) versus a genuine security gap is itself a security skill.
- **IAP is a stronger default than open SSH/RDP rules.** Removing public exposure while preserving operational access is a realistic, in-demand remediation pattern.
- **Some misconfigurations can't be patched live.** VM access scopes are fixed at creation, reinforcing the importance of designing logging and access architecture before deployment, not after.

## Skills Demonstrated

Cloud security fundamentals, GCP IAM, VPC firewall configuration, Identity-Aware Proxy, Cloud Logging/Audit Logs, Security Command Center, vulnerability remediation, risk acceptance documentation, MITRE ATT&CK mapping, cloud troubleshooting.
