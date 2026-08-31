# AWS IAM Security Lab — Least Privilege, Roles, and Access Auditing

A self-directed AWS IAM lab simulating a small-organization access management environment — built from scratch to demonstrate least-privilege policy design, IAM roles vs. long-lived credentials, access key lifecycle management, automated exposure detection, and audit log validation.

## Overview

| | |
|---|---|
| **Platform** | AWS (fresh account, IAM + S3 + Access Analyzer + CloudTrail) |
| **Region** | us-east-1 (N. Virginia) |
| **Scenario** | Simulated small org with 3 departments (Developers, Finance, Admins) |
| **Cost** | $0 — IAM, Access Analyzer, and CloudTrail management events are free tier / free services |

## What I Actually Did

### 1. Hardened the Root Account
Before touching anything else, I enabled MFA on the root account using a virtual authenticator app. Root has unrestricted access to the entire account, so leaving it unprotected is one of the highest-risk misconfigurations in any AWS environment. After this step, root was not used again except for account-level administration.

**Screenshot:** `screenshots/01-iam-dashboard-before-mfa.png.png` — IAM Dashboard showing the "Add MFA for root user" security recommendation before remediation
**Screenshot:** `screenshots/02-root-mfa-enabled.png.png` — Security Credentials page confirming the virtual MFA device is active

### 2. Modeled a Small-Org Access Structure
I created three IAM groups representing departments — **Developers**, **Finance**, and **Admins** — and three corresponding IAM users (`alice-dev`, `bob-finance`, `carlos-admin`). Each group started with a broad AWS-managed policy (`ReadOnlyAccess` or `AdministratorAccess`) as a deliberate "before" baseline, reflecting how access is often granted in practice: broadly, for convenience, without a specific least-privilege review.

**Screenshot:** `screenshots/03-groups-created-baseline-policies.png.png` — All three groups with initial broad policies attached
**Screenshot:** `screenshots/04-users-created-and-grouped.png.png` — All three users created and assigned to their groups

### 3. Redesigned Developer Access Using Least Privilege
`ReadOnlyAccess` grants read access to nearly every AWS service in the account — far more than a developer working with a single S3 bucket actually needs. I wrote a custom JSON policy scoped to exactly one bucket:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowListOwnBucket",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::iam-lab-developer-bucket-ricardo"
        },
        {
            "Sid": "AllowObjectActionsInOwnBucket",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::iam-lab-developer-bucket-ricardo/*"
        }
    ]
}
```

`ListBucket` is scoped to the bucket itself, while object-level actions (`GetObject`, `PutObject`, `DeleteObject`) are scoped separately to objects inside it — no wildcard resources anywhere in the policy. I then removed `ReadOnlyAccess` from the Developer group entirely and attached this custom policy in its place, so the "after" state reflects a real reduction in access, not an addition on top of the broad policy.

**Screenshot:** `screenshots/05-developer-group-least-privilege-applied.png.png` — Developer group showing only the custom scoped policy, with `ReadOnlyAccess` removed

### 4. Built an IAM Role for Cross-Service Access
To demonstrate roles vs. users, I created an `EC2-S3-ReadWrite-Role` that an EC2 instance can assume via `sts:AssumeRole`, rather than embedding a long-lived access key in an application. The trust policy restricts who can assume the role to the EC2 service only:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

This role reuses the same least-privilege S3 policy from Step 3, showing that a single well-scoped policy document can secure both a person and a service.

**Screenshot:** `screenshots/06-ec2-role-trust-policy.png.png` — Trust relationship confirming only `ec2.amazonaws.com` can assume this role

### 5. Practiced Access Key Lifecycle Management
I issued a CLI access key to `carlos-admin`, then treated it as an audit finding: an active key with zero usage is exactly the kind of stale credential a real access review should catch. I deactivated it, then deleted it, walking through the full lifecycle a real credential audit would follow.

**Screenshot:** `screenshots/07-access-key-active-unused.png.png` — Newly issued key showing "Last used: None"
**Screenshot:** `screenshots/08-access-key-deleted.png.png` — Confirmation of zero active access keys after cleanup

### 6. Detected and Remediated a Real Public Exposure
I enabled IAM Access Analyzer and confirmed a clean baseline scan. Then, to generate a genuine (not simulated) finding, I deliberately misconfigured the S3 bucket's policy to allow public read access (`"Principal": "*"`) and temporarily disabled Block Public Access at the bucket level.

Access Analyzer caught it automatically, flagging the bucket as publicly accessible with `s3:GetObject` read access. I remediated by removing the public bucket policy and re-enabling Block Public Access, then confirmed via re-scan that the finding resolved.

**Screenshot:** `screenshots/09-access-analyzer-public-finding.png.png` — Access Analyzer flagging the bucket as publicly accessible
**Screenshot:** `screenshots/10-access-analyzer-finding-resolved.png.png` — Finding detail confirming Status: Resolved after remediation

### 7. Validated Every Change via CloudTrail
To confirm the entire exercise was auditable — not just something that happened in a screenshot — I filtered CloudTrail's event history for `PutBucketPolicy` events. All five bucket policy changes made during this lab (including the misconfiguration and its removal) appear as separate, timestamped events tied to the root identity, each traceable to the exact second it occurred.

**Screenshot:** `screenshots/11-cloudtrail-putbucketpolicy-events.png.png` — CloudTrail event history showing all `PutBucketPolicy` calls with timestamps

## Key Concepts Demonstrated

- **Least privilege policy design** — writing scoped custom JSON policies instead of relying on broad AWS-managed policies
- **IAM roles vs. IAM users** — using `sts:AssumeRole` and temporary credentials instead of long-lived access keys for service-to-service access
- **Access key lifecycle management** — issuing, auditing, deactivating, and deleting credentials
- **Automated misconfiguration detection** — using IAM Access Analyzer to catch unintended public/cross-account exposure
- **Audit logging and validation** — using CloudTrail to independently verify that remediation actions actually took effect

## Why This Matters

Misconfigured IAM — overly broad permissions, exposed S3 buckets, unused long-lived credentials — is one of the most common root causes of real cloud security incidents. This lab was built around a consistent narrative: identify a risk, understand *why* it's a risk, fix it with a scoped and defensible solution, then verify the fix worked using AWS's own tooling rather than assuming it did.

---

*This lab was independently designed and executed in a personal AWS account. All screenshots reflect real console output from the actions described above.*
