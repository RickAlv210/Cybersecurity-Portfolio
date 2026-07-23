Google Cloud DLP (Sensitive Data Protection) Lab

A hands-on project using the Google Cloud Data Loss Prevention (DLP) API to detect sensitive PII in text and in cloud-stored files, including troubleshooting a real detection gap and simulating a production-style data-at-rest scanning pipeline.

Objective

Build a Python tool using the Cloud DLP API to detect sensitive PII (SSNs, emails, phone numbers, credit card numbers), understand how DLP's confidence scoring actually behaves in practice, and extend the project from a simple proof of concept into a realistic pipeline that scans data sitting in Cloud Storage rather than hardcoded text.

Tools Used
Google Cloud Sensitive Data Protection (DLP) API
Google Cloud Storage
Python (google-cloud-dlp, google-cloud-storage)
Google Cloud Shell
Part 1: Environment Setup

Enabled the Sensitive Data Protection (DLP) API within the existing cloud-security-lab project.

Show Image

Confirmed the API was active and ready to use.

Show Image

Opened Cloud Shell and confirmed the correct project context before writing any code.

Show Image

Installed the official Python client library for DLP.

Show Image

Part 2: Proof of Concept — Scanning Inline Text

Wrote a Python script (dlp_scan.py) that sends a sample block of text to the DLP API and checks for four PII types: email addresses, phone numbers, US Social Security Numbers, and credit card numbers.

Show Image

Ran the script against a sample record containing a fake name, email, phone number, SSN (123-45-6789), and credit card number.

Show Image

Unexpected result: three of the four info types were detected correctly (email, phone, credit card), but the SSN never appeared in the findings, even after lowering the confidence threshold to its most permissive setting.

Show Image

Part 3: Investigating the Detection Gap

Rather than assume a bug, I tested this systematically:

123-45-6789 — never detected, at any likelihood threshold. This is one of the most common placeholder SSNs used across tutorials, forms, and example data on the internet. DLP's model appears to deliberately filter well-known dummy values to reduce false positives from non-sensitive example content.
987-65-4321 — also never detected. This number falls in the 900–999 area range, which the Social Security Administration has never issued. DLP appears to validate structural plausibility, not just pattern-match.
452-88-1367 — a valid, non-placeholder, historically-issued number — was detected correctly at VERY_LIKELY.

Show Image

Key finding: Cloud DLP's PII detection is not simple regex matching. It incorporates real-world plausibility checks and appears to suppress widely-used placeholder values, meaning testing DLP tools with "obviously fake" sample data can silently produce false negatives that don't reflect how the tool behaves on real, unstructured data.

Part 4: Simulating a Real Data-at-Rest Pipeline

The proof of concept scanned a string hardcoded into the script — not representative of how DLP is used in practice. To simulate a more realistic scenario, I built a small pipeline where the scanned data actually lives in cloud storage rather than in the script itself.

Created a Cloud Storage bucket (cloud-security-lab-dlp-bucket210) to act as the data source.

Created a synthetic customer records file (fake_customer_data.csv) containing three fake customer rows with emails, phone numbers, SSNs, and credit card numbers — all fictional.

Show Image

Uploaded the file to the bucket and verified it landed correctly.

Show Image

Installed the Cloud Storage Python client library to allow the script to read files directly from the bucket.

Show Image

Rewrote the script (dlp_scan_bucket.py) to pull the CSV's contents directly from Cloud Storage and pass that content into the DLP API, rather than using a hardcoded string.

Ran the updated pipeline:

Show Image

All three fake customer records were scanned successfully, straight from cloud storage: 3 email addresses, 3 SSNs, and 3 credit card numbers were correctly identified, with the source explicitly labeled as gs://cloud-security-lab-dlp-bucket210/fake_customer_data.csv.

Additional finding: the SSNs in this run scored POSSIBLE rather than VERY_LIKELY, despite being the same number format used successfully earlier. The likely reason: the earlier test included the explicit phrase "Social Security Number:" directly next to the digits, giving DLP strong contextual confirmation. In the CSV, the number sits in a column with only a header label (ssn) and no adjacent descriptive text, so DLP relies on pattern-matching alone without that contextual boost — resulting in a lower confidence score for structurally identical data. This is a realistic consideration for anyone designing a DLP scanning strategy: column headers alone may not provide enough context for maximum-confidence detection.

Key Takeaways
DLP detection isn't naive pattern matching. It filters known placeholder values and validates structural plausibility (e.g., real vs. unissued SSN ranges), which means testing with "obviously fake" data can produce misleading negative results if the fake data happens to resemble common test values.
Confidence scores are context-dependent. Identical data formats scored differently depending on whether descriptive text sat near the value, a meaningful consideration when designing real scanning configurations.
Discovery and classification are only part of DLP. This project demonstrates identifying and classifying sensitive data; a full production deployment would pair this with an action layer (alerting, quarantining, or de-identifying flagged files) triggered automatically, for example via a Cloud Function firing on new file uploads.
Realistic architecture matters for a portfolio project. Moving from a hardcoded string to a Cloud Storage-backed scan meaningfully changes the story from "I called an API" to "I simulated how data-at-rest scanning actually works."
Skills Demonstrated

Google Cloud DLP API, Python API integration, Google Cloud Storage, systematic troubleshooting and root-cause analysis, understanding of PII detection confidence scoring, data governance concepts.
