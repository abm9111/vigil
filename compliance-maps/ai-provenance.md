# VIGIL Compliance Map: AI Transparency & Artifact Integrity

**Standards:** EU AI Act (Reg. 2024/1689) Art. 50 · NIST SSDF (SP 800-218) PS & PW practices
**Purpose:** Map the Data Egress & Provenance cluster (`VIGIL-EGRESS`) and correlation patterns
8–10 to obligations that the SOC2/ISO maps do not cover.

## Why a separate map

SOC2 and ISO 27001 are built around protecting a system from an attacker. Neither has a control
that says *"label content a machine wrote"* or *"prove the artifact you shipped is the artifact
you built."* Those obligations now exist in law and in federal software-supply-chain guidance,
and they are precisely what `TRUST_LAUNDERING` and `INTEGRITY_THEATER` detect.

## EU AI Act — transparency obligations

Applies when the audited system generates or manipulates content that reaches a person. Art. 50
transparency duties apply from **2 August 2026**.

| Article | Who it binds | Obligation (verified wording) | VIGIL Clusters |
|---------|--------------|-------------------------------|----------------|
| Art. 50(1) | **Providers** | AI systems intended to interact directly with natural persons must inform them they are interacting with an AI system, unless obvious | EGRESS, AIML |
| Art. 50(2) | **Providers** | Providers of AI systems *generating synthetic audio, image, video or text* must mark outputs in a machine-readable format, detectable as artificially generated | AIML |
| Art. 50(4) ¶1 | **Deployers** | Image/audio/video constituting a **deep fake** must be disclosed as artificially generated | AIML |
| Art. 50(4) ¶2 | **Deployers** | Text **published to inform the public on matters of public interest** must be disclosed as AI-generated — *unless* it underwent human review / editorial control with a named person holding editorial responsibility | COMP |

### Scope warning — read before mapping a finding to Art. 50

An earlier version of this file mapped Art. 50(4) to "prose fields shipped to a third party."
**That was wrong**, and it is worth keeping the correction visible:

- Art. 50(4) ¶1 is the **deep-fake** provision — image, audio, video. Not data exports.
- Art. 50(4) ¶2 covers text **published to inform the public on matters of public interest**.
  A B2B partner data bundle is not that, and the human-editorial-review carve-out excludes much
  of what remains.
- Art. 50(2) binds the **provider of the AI system**, not an organisation that uses a model's
  output inside its own dataset. Using an LLM to enrich a table does not make you a provider.

So for the common `TRUST_LAUNDERING` case — model-written columns in a partner export — **the
EU AI Act most likely does not apply at all.** The finding is still real; the obligation is
contractual, ISO 27001 A.5.34, or plain honesty, not Art. 50.

**Correlation link:** pattern 8 `TRUST_LAUNDERING` overlaps Art. 50 only where the content is
public-facing or the audited party *is* the AI provider. Say which, or cite nothing.

**Judgement:** a caveat buried in a data dictionary the recipient never opens does not satisfy
"disclose." Check the README, the first screen, the column header — wherever the reader lands.
That is good practice regardless of whether Art. 50 binds; do not dress good practice as law.

## NIST SSDF (SP 800-218) — integrity of what ships

| Practice | Obligation | VIGIL Clusters | Check |
|----------|-----------|----------------|-------|
| PS.1 | Protect all forms of code from unauthorized access **and tampering** | SEC, EGRESS | Source datasets and exports are gitignored or access-controlled |
| PS.2 | Provide a mechanism for verifying software release integrity | EGRESS, INFRA | Checksum/signature exists **and can actually fail** — not self-certifying, over a reproducible build, reference value carried out-of-band |
| PS.3 | Archive and protect each release | EGRESS, INFRA | A failed rebuild cannot destroy the last known-good artifact |
| PW.4 | Reuse existing, well-secured software | CODE | Duplicated provenance constants drift — single-source them |

**Correlation link:** pattern 10 `INTEGRITY_THEATER` is a PS.2 failure. A manifest that ships
inside the archive it certifies satisfies the letter ("a mechanism exists") and fails the intent
("verifying"). Pattern 9 `DESTRUCTIVE_BEFORE_VALIDATE` is a PS.3 failure.

## Verification status

Every citation in this file was checked against primary sources on **2026-07-30**:

| Claim | Status |
|---|---|
| EU AI Act = Regulation (EU) 2024/1689 | **verified** |
| Art. 50 transparency duties apply from 2 Aug 2026 | **verified** |
| Art. 50(1)/(2)/(4) wording and who they bind | **verified** — and one mapping corrected, see above |
| NIST SSDF = SP 800-218 (v1.1) | **verified** |
| PS.1 / PS.2 / PS.3 / PW.4 titles | **verified** |
| ISO 27001:2022 A.5.34 "Privacy and protection of PII" | **verified** |
| ISO 27001:2022 A.8.13 "Information backup" | **verified** |
| SOC 2 A1.2 environmental protections / backup / recovery | **verified** |
| SOC 2 Availability is optional beyond the Common Criteria | **verified** |
| EU AI Act extraterritorial reach | **not verified** — stated below as context, do not rely on it |
| OMB M-22-18 / M-23-16 as the self-attestation memoranda | **not verified** — treat as a pointer, not a citation |

Anything marked *not verified* must not be used to tell someone they have an obligation.
Re-check before relying on any of this: application dates move, and SSDF has a 800-218A
companion for generative AI that this map does not yet cover.

## Gap reporting

When `--compliance ai-provenance` is passed, report unmapped obligations as gaps, and state
plainly which are **legal** duties versus **guidance**:

- EU AI Act Art. 50 — binding regulation, applies to providers and deployers placing systems on
  the EU market. Extraterritorial: an artifact reaching EU users is in scope regardless of where
  it was built.
- NIST SSDF — guidance, but contractually binding for US federal software suppliers via
  OMB M-22-18 / M-23-16 self-attestation.

Do not assert applicability. VIGIL cannot know the audited project's market or contracts —
report the obligation and the evidence, and let the reader decide whether it binds them.
