# IAM Access Management — Simulated Helpdesk Tickets

A companion lab to the [AWS IAM Security Lab](https://github.com/RickAlv210/Cybersecurity-Portfolio/tree/main/aws-iam-lab), focused on day-to-day, ticket-driven IAM operations rather than architecture design. Reuses the same AWS environment: 3 IAM groups (Developers, Finance, Admins) and 3 users (alice-dev, bob-finance, carlos-admin), plus one new user created as part of this lab (diana-dev).

**Goal:** Demonstrate the kind of recurring, ticket-based access management work a Tier 1 SOC analyst or IT helpdesk analyst actually handles — onboarding, temporary access, offboarding, investigation, and periodic audits — as a companion to the architecture-focused IAM lab.

**Tools used:** AWS IAM, AWS Lambda, Amazon EventBridge Scheduler, AWS CloudTrail, IAM Credential Reports

---

## Ticket 1 — New Hire Onboarding

**Request:** New developer joins the team and needs the same access as an existing developer (alice-dev).

**Actions taken:**
- Reviewed alice-dev's group membership to identify the target role (Developer group)
- Created new IAM user `diana-dev`, no console access (IAM-only, consistent with existing lab users)
- Added `diana-dev` to the **Developer** group during creation rather than attaching policies individually
- Verified via the Developer group's Permissions tab that its single managed policy (`S3-Developer-Bucket-Access`) now showed 2 attached entities (alice-dev, diana-dev), confirming identical effective permissions with zero manual policy work
- Validated the action in CloudTrail — confirmed `CreateUser` and `AddUserToGroup` events for diana-dev, timestamped and correctly attributed

![Developer group showing 2 attached entities after adding diana-dev](Developer_permissions.png)
*The Developer group's policy now shows 2 attached entities (alice-dev, diana-dev) — identical access granted through group membership alone.*

**Takeaway:** Group-based access assignment means onboarding into an existing role is a single step (add to group) instead of re-deriving and reattaching a custom policy — the reason the original lab built the policy at the group level rather than per-user.

---

## Ticket 2 — Temporary Access Request (with Automated Expiration)

**Request:** A finance team member (bob-finance) needs temporary, read-only access to the developer S3 bucket for a one-time audit task.

**Actions taken:**
- Reviewed bob-finance's baseline access (ReadOnlyAccess via the Finance group)
- Granted a scoped inline policy (`TEMP-bob-finance-audit-readonly-2026-09-04`) — read-only, limited to `s3:GetObject` / `s3:ListBucket` on a single bucket, no wildcard resources
- **IAM users have no native policy expiration**, so built automation to enforce it:
  - A Lambda function (`revoke-temp-access-bob-finance`) that calls `iam:DeleteUserPolicy` to remove the temp policy
  - A dedicated, least-privilege execution role for the Lambda, scoped to exactly one action against exactly one resource (bob-finance's ARN)
  - A one-time **EventBridge Scheduler** rule set to invoke the Lambda automatically at a fixed expiration time
- Tested the Lambda manually first, confirmed successful revocation, then re-granted the policy and let the scheduled trigger fire on its own
- Validated the full chain in CloudTrail: manual grant → manual test revoke → re-grant → scheduled auto-revoke, each event correctly attributed to the acting identity (root, the Lambda's assumed role, and finally the scheduler-triggered Lambda invocation)

![EventBridge Scheduler configured for a one-time trigger](event_bridge_schedule_made.png)
*One-time EventBridge schedule set to invoke the revoke Lambda automatically at a fixed expiration time.*

![CloudTrail event showing the schedule fired and DeleteUserPolicy ran automatically](deleteuserpolicy_detected.png)
*The schedule fired on time with zero manual intervention — CloudTrail confirms the DeleteUserPolicy call.*

![CloudTrail JSON confirming the deletion was performed by the Lambda's assumed role](deleted_user_policy_in_detail.png)
*userIdentity shows "AssumedRole" tied to the Lambda's execution role — proof the revocation was automated, not manually clicked.*

**Takeaway:** IAM users don't support time-based policy expiration natively — "temporary access" is a process problem, not a checkbox. Event-driven automation with tightly scoped execution permissions at every layer (the temp policy, the Lambda role, the scheduler) is one legitimate way to solve it without relying on a human remembering to revoke access later.

---

## Ticket 3 — Offboarding

**Request:** carlos-admin has left the company. Access must be revoked immediately and the action documented for audit purposes.

**Actions taken:**
- Reviewed baseline access — confirmed carlos-admin had full `AdministratorAccess` via the Admins group, no console login, and no active access keys (already clean from prior credential lifecycle work in the original lab)
- Removed carlos-admin from the **Admins** group, immediately revoking all inherited permissions
- Verified via the Permissions tab — 0 active policies remaining
- Validated via CloudTrail that the `RemoveUserFromGroup` event was logged with the correct user, group, and timestamp

![CloudTrail event confirming carlos-admin was removed from the Admins group](user_removed_from_group_event_history.png)
*RemoveUserFromGroup event showing carlos-admin removed from Admins, fully revoking his inherited AdministratorAccess.*

**Takeaway:** Group-based access removal offboards a user in a single action instead of requiring individual policy detachment — the same design principle from Ticket 1, applied symmetrically in reverse. A real offboarding ticket would also check for MFA devices, SSH keys, and any resource-level permissions granted outside group membership (e.g., a bucket policy naming the user directly) — not applicable here, but worth flagging as a next step.

---

## Ticket 4 — Suspicious Activity / Access Review

**Request:** Security team flags potential unusual activity tied to alice-dev. Review her access and recent activity before escalating or restricting anything.

**Investigation steps:**
- Reviewed current permissions — confirmed standard Developer-tier access only, nothing elevated or unexpected
- Reviewed IAM Access Advisor (Last Accessed) — both IAM and S3 showed **no activity in the tracking period**
- Reviewed Security Credentials — no console sign-ins ever recorded, no access keys, no API keys, console access enabled but **no MFA device assigned**

**Finding:** No evidence supports the suspicious activity alert — the account shows no usage of any kind. **Disposition: not substantiated.**

**Secondary finding surfaced during review:** alice-dev has console access enabled but has never signed in and has no MFA configured. Recommended either enforcing MFA before next use or disabling unused console access entirely.

**Takeaway:** Investigative work isn't just "find the smoking gun" — producing a documented, evidence-based conclusion is the deliverable even when the answer is "nothing happened." The MFA gap found along the way was flagged for the next audit even though it wasn't the subject of the original alert.

---

## Ticket 5 — Quarterly Access Audit

**Request:** Periodic review of all IAM users for stale credentials, excessive permissions, or dormant accounts.

**Method:** Generated an IAM Credential Report — a single CSV covering console access, password usage, MFA status, and access key status for every user in the account.

**Findings:**

| User | Console Access | MFA | Password Last Used | Access Keys | Finding |
|---|---|---|---|---|---|
| alice-dev | Enabled | None | Never | None active | Console access enabled, unused, no MFA |
| bob-finance | Enabled | None | Never | None active | Console access enabled, unused, no MFA |
| carlos-admin | Disabled | None | N/A | None active | Fully offboarded (Ticket 3) — clean |
| diana-dev | Disabled | None | N/A | None active | IAM-only by design (Ticket 1) — clean |

**Key finding:** A consistent pattern across two active accounts — console passwords enabled but never used, with no MFA configured on either. Not visible from any single user's ticket in isolation; only surfaced by reviewing all accounts together.

**Recommendation:** Disable console password access for alice-dev and bob-finance, since neither has ever used it and both only require the programmatic/CLI-style access already demonstrated in their respective tickets. If console access is genuinely needed going forward, enforce MFA before further use.

**Takeaway:** Most access-related security incidents don't start with a dramatic breach — they start with old, forgotten, over-permissioned accounts nobody cleaned up. Periodic audits are the unglamorous work that catches this before it becomes a real incident.

---

## Skills Demonstrated

- IAM user/group lifecycle management (onboarding, offboarding, temporary access)
- Least-privilege policy design (scoped inline policies, single-action/single-resource execution roles)
- Python scripting for security automation (Lambda)
- Event-driven automation (EventBridge Scheduler)
- CloudTrail-based verification and audit trail construction
- Access review and investigative documentation
- Credential/access auditing at the account level
