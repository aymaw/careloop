# Scope and evidence

CareLoop coordinates fictional referrals through an operational state machine. An agent proposes an eligible provider; a reviewer approves the exact version; closure requires a matching local completion receipt.

Source, synthetic fixtures, tests, installed commands, and demo artifacts are the
evidence. JSON and HTML examples record completed runs; they are not a hosted
service. Provider tests use mocked responses and do not establish the quality of
any specific running model.

## Limits

This is an administrative simulation, not medical software. It performs no
diagnosis, triage, treatment selection, EHR integration, messaging, or real patient
matching. It has no authentication, tenant isolation, calendar integration, or
automatic capacity replenishment. Capacity is a fixed fictional booking allocation.
Receipt lookup verifies a local synthetic record, not an external provider's work.
Reviewer and owner fields are local labels.

No production scale, vendor connectivity, clinical safety, business outcomes,
or model superiority is claimed. CI configuration and locally passing checks
are separate from a verified remote CI run.
