Horizon HEDIS PoC — Requirements

**Version 3.12 · 10 September 2026**
Role: architecture / analysis pass. Requirements consolidated, de-duplicated, and current-state process steps converted to automation requirements.

## Contents

| § | Section |
| :---- | :---- |
| 1 | [**Document Overview**](#1-document-overview) |
| 2 | [**Common Platform**](#2-common-platform) |
| 2.1 | [ Intake & Document Handling](#21-intake-document-handling) |
| 2.2 | [ Analysis & Extraction](#22-analysis-extraction) |
| 2.3 | [ Evidence & Traceability](#23-evidence-traceability) |
| 2.4 | [ Document Quality & Validation](#24-document-quality-validation) |
| 2.5 | [ Human-in-the-Loop](#25-human-in-the-loop) |
| 2.6 | [ Output](#26-output) |
| 3 | [**Chart Chase / Hybrid HEDIS**](#3-chart-chase-hybrid-hedis) |
| 3.1 | [ Case Handling](#31-case-handling) |
| 3.2 | [ Abstraction](#32-abstraction) |
| 3.3 | [ Quality](#33-quality) |
| 3.4 | [ Reporting](#34-reporting) |
| 4 | [**Gap Closure / Non-Standard**](#4-gap-closure-non-standard) |
| 4.1 | [ Case Seeding](#41-case-seeding) |
| 4.2 | [ Validation](#42-validation) |
| 4.3 | [ Review & Extraction](#43-review-extraction) |
| 4.4 | [ Outcome](#44-outcome) |
| 4.5 | [ Quality](#45-quality) |
| 5 | [**Audit & Compliance**](#5-audit-compliance) |
| 6 | [**Prerequisites**](#6-prerequisites) |
| 6.1 | [ Reference materials in scope](#61-reference-materials-in-scope) |
| 6.2 | [ Reference coverage by measurement year](#62-reference-coverage-by-measurement-year) |
| 6.3 | [ Case data specification](#63-case-data-specification) |
| 7 | [**Out of Scope**](#7-out-of-scope) |
| 8 | [**Assumptions**](#8-assumptions) |
| 9 | [**Open Questions**](#9-open-questions) |
| 10 | [**Traceability**](#10-traceability) |
| 11 | [**Compliance resources**](#11-compliance-resources) |
| 12 | [**Carried inconsistencies — for the next pass**](#12-carried-inconsistencies-for-the-next-pass) |

## 1. Document Overview

**Structure note**

Most requirements are common to both workflows. Listing them under Chart Chase and again under Gap Closure would reintroduce the duplication this pass removes. So: **§2 Common Platform** holds everything shared, **§3** and **§4** hold only what is workflow-specific.

*Human-in-the-loop actions and PoC priority were removed from these tables — both are still under customer review, and most requirements need HITL in any case. The general HITL rule is 5.1: a reviewer confirms, modifies, rejects or comments on every AI finding before it counts.*

**Legend**

| Column | Values |
| ----- | :---- |
| **Depends on** | Reference artifacts (§6.1) and prerequisites (§6) this requirement needs. REF-06/07 and REF-08/09 denote the MY2025 and MY2026 versions of the same artifact. |
| **Source** | Trace to the customer document — section, page, and verbatim quote |
| **Coverage** | ✅ Available on the PenguinAI platform · ⚠️ Partial — needs adaptation, a data input, or a small build · 🆕 net-new |
| **Note** | Build status: what exists in the baseline HEDIS app today, and what is portable from Gwen / sister applications |

**Source column**

Every requirement is traced back to *Quality Mgmt Clinical Chart Review Scope v1.0.docx* (Horizon, "Clinical Chart Review, Abstraction, and Exclusion Identification — AI Use Case Scoping Document", DRAFT 15 Jun 2026). Each entry gives the page, the section, and a verbatim quote. All supporting passages are listed, not just the first one.

*Page numbers are the document's own, taken from its table of contents; where a section spans several pages the range is given and the named sub-heading (e.g. the functional requirement title) pins the exact location. Section 4.1 Functional Requirements contains ten named requirements across pp13–17 and is always cited by requirement name.*

*Where a requirement has no basis in the customer document — it was added by Penguin during the architecture pass — the Source cell says so explicitly and names the nearest supporting passage.*

*REF identifiers appearing inside a quoted passage are Horizon's own and are reproduced verbatim. Standalone pointers to the p26 reference table have been removed from this column; that mapping now lives in §6.1 and in the Depends on column.*

**Coverage summary**

| Coverage | Count | Share |
| :---- | ----: | ----: |
| ✅ Available | 49 | 73% |
| ⚠️ Partial | 18 | 27% |
| 🆕 New | 0 | 0% |
| **Total** | **67** | |

*Coverage and Note are carried from the PenguinAI platform-coverage analysis run against this version. No net-new items remain: every requirement is either available on the platform or a partial gated by the member roster (P7), the Horizon cheat sheets and precedence rules (P5/P8), or an open scope question (OQ-3, OQ-4, OQ-6).*

---

## 2. Common Platform

### 2.1 Intake & Document Handling

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| 1.1 | Manual chart upload | User uploads chart PDFs into the app. System does not collect from fax, mail, portal, MFT or shared drive. | ✅ Available | Upload endpoints + PDF text via pymupdf/pypdf. In the baseline today. | P1 | p5 §1.2 How AI Can Be Used: "Ingest clinical charts from multiple intake channels (fax, mail, portals, MFT) to generate a searchable, machine-readable layer for analysis" • pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Behavior: "Accept clinical charts from existing users (e.g., retrieved from inboxes, shared drives, or platforms)"; Acceptance: "Supports processing of PDFs and scanned documents once provided by users" • pp18–19 §A.1 In Scope: "Processing of clinical chart documents provided by users through existing intake channels (fax, scanned documents, portals, MFT, shared drives), including unstructured and variably formatted inputs" • pp19–20 §A.2 Out of Scope: "Provider outreach and chart chase execution" |
| 1.2 | Searchable text layer | OCR to standardised machine-readable text with page-level index. | ✅ Available | Real per-page tesseract OCR + page index in the baseline. Platform intake (IDI) adds richer OCR pipelines. | — | p5 §1.2 How AI Can Be Used: "…to generate a searchable, machine-readable layer for analysis" • pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Output: "Machine-readable text extracted from source documents (including OCR for scanned content)"; "Indexed references to source content (page-level mapping)"; Acceptance: "≥90% of documents produce usable, searchable text representations" • pp13–17 §4.1 FR "Handle Low-Quality and Complex Documents" — Acceptance: "≥95% of standard documents successfully processed to produce a usable, machine-readable representation (e.g., text extraction and indexing)" • pp18–19 §A.1 In Scope: "Conversion of clinical documents into standardized, searchable text to support consistent analysis across workflows" • p11 §3.2 Future State: "converting them into a standardized, searchable format to support consistent analysis" |
| 1.3 | Source immutability | Original PDF never altered, transformed or replaced. Remains system of record. | ✅ Available | Available on the platform — immutable source-of-record handling (content hashing, WORM/versioned storage) is a standard PenguinAI intake capability, portable here. Baseline today: originals saved un-overwritten but deletable. | — | p5 §1.2 How AI Can Be Used: "without altering, transforming, or replacing the original documents, which remain the system of record for audit and compliance purposes" • pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Behavior: "while preserving the original documents exactly as received, without alteration or transformation"; Output: "No modification or replacement of original documents; all outputs remain linked to the source record"; Acceptance: "Original documents remain unchanged and accessible as the system of record" |
| 1.4 | Document addressability | Every document retrievable by ID so any finding can be shown beside its source page. | ✅ Available | Retrievable by ID; findings carry page + char offsets. Gwen's Citations Panel (CIT) adds original-page addressing (see 3.3). | — | pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Output: "Indexed references to source content (page-level mapping)"; Acceptance: "All extracted data maintains traceability to the original document (page and location)" • pp18–19 §A.1 In Scope: "including citations to source locations within the chart (e.g., page number, excerpt) to support validation and auditability" |
| 1.5 | Document classification | Classify each document by clinical type; flag low-confidence classifications to exception queue. | ✅ Available | Available on the platform — AI clinical-document classification with a confidence-gated exception queue exists in PenguinAI intake (IDI); portable. Baseline today: type is extension-guessed. | — | pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Output: "Metadata (e.g., document type, member identifiers if available)" • pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Low-confidence results flagged for review" |

### 2.2 Analysis & Extraction

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | ----- | :---: | :---- | ----- | :---- |
| 2.1 | Measure-specific extraction | Extract data elements aligned to the member's assigned measures — vitals, labs, procedures, diagnoses, dates. | ✅ Available | specs.MEASURE_ELEMENTS (15 measures, typed) scoped to the assigned measure; persisted as AbstractionElement. In the baseline. | REF-06/07, REF-08/09, REF-12 · P3, P10 | p5 §1.2 How AI Can Be Used: "Analyze unstructured clinical documents to identify and highlight measure-specific data elements and potential exclusions with supporting evidence" • pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Behavior: "Identify and extract structured clinical data elements aligned to selected HEDIS measures, including all relevant data regardless of whether it meets compliance criteria"; Acceptance: "Extraction dynamically aligns to the selected measure (measure-specific logic applied)"; "Extracted data includes required contextual attributes: Dates (Date of Service and/or Reported Date as applicable); Place of Service (e.g., inpatient, outpatient, ED)" • pp18–19 §A.1 In Scope: "AI-driven extraction of measure-specific clinical data (e.g., vitals, procedures, diagnoses, lab values) aligned to HEDIS specifications" • p11 §3.2 Future State: "AI analyzes each chart to identify, extract, and reference measure-specific clinical data and potential exclusions using HEDIS specifications" |
| 2.2 | Member identity extraction | Extract member name and DOB from the chart for validation against roster. | ✅ Available | Available on the platform — chart→member identity extraction (name/DOB as cited findings) is a standard PenguinAI extraction capability. Baseline today: roster→chart confirmation only. | REF-12 · P7 | pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Output: "Metadata (e.g., document type, member identifiers if available)" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Acceptance: "Identifies missing or inconsistent patient identifiers" • pp22–24 §5.1 Data Sources — Member Context (QMRM / Gap Reports): "Must align with submitted chart; discrepancies can occur" |
| 2.3 | Provider entity & credential | Extract performing provider and credential where the measure requires it. | ✅ Available | Available on the platform — performing-provider + credential extraction is available in PenguinAI extraction; portable. Baseline today: optional free-text hints only. | REF-06/07, REF-12 · P3 | pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Output: "Supporting context (e.g., provider credentials where required)"; Acceptance: "Includes provider signature/credentials where required by measure" • pp8–10 §3.1 Current State: "This process is highly dependent on reviewer experience and judgment, particularly when interpreting documentation, validating provider context, and applying measure rules" |
| 2.4 | Targeted analysis mode | Analysis scoped to one measure or identified gap. | ✅ Available | Real mode param (targeted/broad) plumbed through analyzer + both routes. In the baseline. | — | p5 §1.2 How AI Can Be Used: "Support both targeted analysis (specific measure or gap) and broader scanning to identify additional clinical data and cross-measure opportunities" • pp13–17 §4.1 FR "Support Targeted and Broad Analysis Modes" — Behavior: "Control the scope of analysis by enabling users to focus on a specific measure or expand to identify additional findings across the full chart"; Acceptance: "Users can toggle between analysis modes"; "Outputs prioritize relevant findings based on mode" • pp18–19 §A.1 In Scope: "Support for targeted (measure-specific) and broad (multi-measure) analysis modes within the same chart" • p11 §3.2 Future State: "targeted analysis (aligned to a specific measure or identified gap)" |
| 2.5 | Broad analysis mode | Scan the same chart for clinical evidence relevant to other measures the member is flagged for. Surfaces **evidence**, not gaps — see X-12. Labelled secondary. | ✅ Available | broad_scan → CrossMeasureFinding (source vs found, proposed). In the baseline; platform GCI adds cross-measure opportunity surfacing. | REF-06/07 · P7 | p5 §1.2 How AI Can Be Used: "…and broader scanning to identify additional clinical data and cross-measure opportunities" • pp13–17 §4.1 FR "Support Targeted and Broad Analysis Modes" — Output: "Measure-specific and secondary findings clearly distinguished"; Acceptance: "Secondary findings clearly labeled" • pp18–19 §A.1 In Scope: "Identification of additional clinical data and cross-measure opportunities beyond the initially targeted measure" • p11 §3.2 Future State: "broader scanning to detect additional clinical data and cross-measure opportunities within the same chart, improving completeness of abstraction" |
| 2.6 | Exclusion identification | Surface candidate measure-specific and cross-measure exclusions (hospice, death) with evidence. Proposal only — never applied. | ✅ Available | Deterministic, evidence-anchored, proposal-only exclusion engine (3 universal + 9 measure rules) in the baseline. Platform adds cross-measure exclusions + death (eligibility-derived). | REF-02, REF-05, REF-08/09, REF-12 · P10 | p5 §1.2 How AI Can Be Used: "identify and highlight measure-specific data elements and potential exclusions with supporting evidence" • pp13–17 §4.1 FR "Identify and Surface Potential Exclusions" — Behavior: "Detect and present potential measure-specific and cross-measure exclusions based on clinical documentation and member context"; Output: "List of potential exclusions (REF 12) with supporting evidence and applicability to the targeted measure"; Acceptance: "Differentiates: Measure-specific exclusions; Global exclusions (e.g., hospice, death)" • pp18–19 §A.1 In Scope: "Identification of potential exclusions, including both measure-specific and cross-measure exclusions (e.g., hospice, death), with supporting evidence" • pp19–20 §A.2 Out of Scope: "final exclusion application" |
| 2.7 | Measure logic source | Analysis references Horizon cheat sheets and/or NCQA specs, with the applied version recorded per determination. | ⚠️ Partial | Partially available — references NCQA value sets; version-per-determination stamping is easy (overlaps A4). Horizon cheat sheets as the source depend on P5/P8/OQ-3. **Baseline currently carries MY2027 value sets; A-12 pins MY2025 and MY2026 — see §6.2.** | REF-03, REF-06/07, REF-08/09 · P8, P10 | pp8–10 §3.1 Current State: "Using HEDIS specifications and internally maintained "cheat sheets," reviewers navigate unstructured documents to locate required measure-specific data and evaluate exclusions" • pp22–24 §5.1 Data Sources — HEDIS Measure Specifications: "Measure definitions, abstraction rules, and exclusion criteria"; source: "NCQA HEDIS specifications and internal reference materials"; limitation: "Complex logic requires interpretation; not always directly mappable to chart text" • Version-per-determination stamping: no direct source — added by Penguin |
| 2.8 | Eligibility (roster-given; escalate) | Assigned measures taken as given from roster. not_eligible from the pipeline is routed to escalation, never applied as a determination. | ⚠️ Partial | Partially available — assigned measures taken as given; not_eligible→escalation routing needs the roster eligibility feed (P7). | P7 | pp22–24 §5.1 Data Sources — Member Context (QMRM / Gap Reports): "Member-level data including demographics, assigned measures, and gap status" • pp19–20 §A.2 Out of Scope: "Automated clinical or compliance decision-making, including determination of measure compliance, numerator status, or final exclusion application" • Escalation routing of not_eligible: no direct source — added by Penguin |
| 2.9 | Determination states | Per measure: evidence found · no evidence found · exclusion candidate · escalated. The vocabulary is deliberately evidentiary, not a compliance vocabulary — see X-11 and 2.11. Findings offered for validation, not applied determinations. Displayed as *evidence found* rather than as a compliance decision — see X-11. | ✅ Available | Available on the platform — per-measure determination states (compliant/gap/exclusion/escalated) are supported in Gwen (CCT); portable. Baseline today: only 'excluded' maps (compliance intentionally left to reviewer). | — | pp13–17 §4.1 FR "Support Reviewer Validation Workflow" — Acceptance: "Reviewers can confirm, modify, or reject: Data elements; Exclusions; Gap closure determinations"; "Validation required before downstream use" • pp19–20 §A.2 Out of Scope: "Automated clinical or compliance decision-making, including determination of measure compliance, numerator status, or final exclusion application" |
| 2.10 | Conflicting data detection | Where the same required data element has more than one candidate value in the chart, or across documents on the case, all candidates are surfaced with their citations, the conflict is flagged, and the item is routed to review. No automatic selection between competing values. | ⚠️ Partial | Partially available — evidence-anchored extraction, per-finding confidence scoring and the escalation queue all exist on the platform; competing-candidate detection for the same data element is assembled from those pieces rather than built from scratch. | REF-06/07, REF-12 · P3 | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Low-confidence results flagged for review" • pp19–20 §A.2 Out of Scope: "Resolution of ambiguous or complex clinical scenarios requiring nuanced human judgment or interpretation of intent" • Contradiction detection as distinct from ambiguity: no direct source — added by Penguin (see A-14) |
| 2.11 | Evidence-absent outcome | Where the assigned measure's required elements are not found, the case records **no evidence found** with a reason — not documented · documented but unreadable · wrong member or measure · candidate exclusion. The app never records non-compliance; absence of evidence is a finding, and what it means for the measure is Horizon's determination in QMRM (X-11, A-15). | ⚠️ Partial | Partially available — per-measure not_found status and the required_missing summary exist in the baseline; the named outcome with its reason taxonomy is the remaining piece. | REF-06/07, REF-12 · P3 | p10 §3.1 Current State process map — Chart Chase step 6: "Determine if Valid Data is Found (yes or no)"; "prescribe next step "Follow-up with Provider" or "Ready for Manual entry into QMRM"" • pp19–20 §A.2 Out of Scope: "Automated clinical or compliance decision-making, including determination of measure compliance, numerator status, or final exclusion application" • Reason taxonomy: no direct source — added by Penguin, on the hybrid conventions at S-1 |

*The NCQA specifications behind REF-03 and REF-06/07 are gated on OQ-3 (licence) and OQ-4 (scope).*

### 2.3 Evidence & Traceability

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| 3.1 | Citation per finding | Every element and exclusion carries page number and excerpt. | ✅ Available | Elements & exclusions carry page + char_start/end + evidence_text. In the baseline; Gwen CIT is the mature version. | — | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Each data element includes traceable citation (page number, excerpt)" • pp13–17 §4.1 FR "Identify and Surface Potential Exclusions" — Acceptance: "Exclusions include citations and supporting context" • pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Acceptance: "All outputs include traceable citations (page number, excerpt)" • pp18–19 §A.1 In Scope: "Generation of structured, evidence-based outputs with full traceability, including citations to source locations within the chart (e.g., page number, excerpt) to support validation and auditability" |
| 3.2 | Citation persistence | Citation stored with the determination, not regenerated on read. | ✅ Available | Persisted to DB columns at analysis time, read back unchanged. In the baseline. | — | pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Behavior: "Generate evidence-based outputs with full traceability to source documentation for all extracted data, exclusions, and recommendations" • pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Acceptance: "All extracted data maintains traceability to the original document (page and location)" • Store-at-determination rather than regenerate-on-read: no direct source — added by Penguin |
| 3.3 | Split-panel navigation | PDF with region overlays alongside findings; click either side to navigate to the other. | ✅ Available | Available on the platform — Gwen's Citations Panel (CIT) provides a true PDF split view with region overlays and click-either-side navigation. Baseline today: extracted-text panel with highlight spans. | — | p5 §1.2 How AI Can Be Used: "Reduce manual chart navigation by directing reviewers to relevant sections and extracted data within the document" • p11 §3.2 Future State: "enabling reviewers to quickly navigate to relevant sections of the chart instead of manually reviewing entire documents"; "Reviewers interact with AI-generated outputs through a human-in-the-loop validation workflow, where they confirm, modify, or reject findings, perform highlighting" • pp4–5 §1.1 Problem Definition: "Reviewers must navigate large, complex, and frequently unstructured charts—often spanning hundreds of pages" |
| 3.4 | Directed navigation | Reviewer taken to relevant chart sections rather than scrolling the full record. | ✅ Available | Available on the platform — directed, page-image navigation is part of Gwen's Citations Panel (CIT). Baseline today: text-level scroll-to-evidence. | — | p5 §1.2 How AI Can Be Used: "Reduce manual chart navigation by directing reviewers to relevant sections and extracted data within the document" • p11 §3.2 Future State: "Manual chart navigation is replaced with AI-guided evidence review" • pp8–10 §3.1 Current State: "Manual, labor-intensive review: Reviewers must navigate unstructured, highly variable clinical documents to locate relevant data" |

### 2.4 Document Quality & Validation

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| 4.1 | Multi-patient detection | Flag documents containing more than one member. | ⚠️ Partial | Partially available — document-segmentation / multi-identity detection exists in PenguinAI intake (IDI) and is portable; not yet wired into this workflow. | — | pp13–17 §4.1 FR "Detect Multi-Patient Documents" — Behavior: "Identify documents containing multiple members and flag for review"; Output: "Document-level flag with potential segmentation indicators"; Acceptance: "Detects indicators of multiple patients"; "Prevents misattribution of data" • pp18–19 §A.1 In Scope: "multiple members in one document"; "Detection and flagging of document limitations, including low-quality scans, handwritten content, and multi-patient documents" • pp22–24 §5.1 Data Sources — Clinical charts: "may include multi-patient documents" |
| 4.2 | Member / measure mismatch | Compare chart identity and content against the roster case. | ✅ Available | gap_validation checks name/DOB/provider/measure-alignment against the roster case. In the baseline. | P7 | p5 §1.2 How AI Can Be Used: "Improve gap closure efficiency by validating provider-submitted charts, including identifying mismatches, missing data, and incorrect formatting" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Behavior: "Assess submitted charts for correct member, measure alignment, completeness, and contextual validity required for gap closure"; Output: "Member or measure mismatches" • pp8–10 §3.1 Current State: "A defined naming convention is used to match submitted charts to specific members and measures; incorrect or inconsistent naming requires manual intervention"; "Reviewers validate the chart against pre-populated member and measure data" • p12 §3.3 Potential Risks: "Mismatch in gap closure workflows: Incorrect or inconsistent provider submissions (e.g., naming conventions) may lead to improper chart-to-gap matching" |
| 4.3 | Date of service issues | Flag missing, unclear or unreadable dates of service. | ✅ Available | Available on the platform — robust service-date parsing/validation is a standard PenguinAI intake check. Baseline today: coarse year-only heuristic. | — | pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Output: "Contextual gaps (e.g., incorrect place of service, missing dates)"; Acceptance: "Flags gaps in required documentation (e.g., missing date of service, missing encounter context)" • pp18–19 §A.1 In Scope: "unclear dates of service" |
| 4.4 | Missing required elements | Flag where the chart lacks elements the target measure requires. | ✅ Available | required flags on elements; not_found status + required_missing summary + validation blockers. In the baseline. | REF-06/07, REF-12 · P3 | pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Output: "Missing required clinical elements"; Acceptance: "Identifies incorrect or incomplete submissions" • p5 §1.2 How AI Can Be Used: "identifying mismatches, missing data, and incorrect formatting" • pp18–19 §A.1 In Scope: "including detection of mismatches, missing data, and naming/formatting issues" |
| 4.5 | Unreadable content | Flag poor scans and handwritten passages. State content could not be read — never infer a value. | ⚠️ Partial | Partially available — strong poor-scan handling (quality bands, OCR confidence, 'never infer'); handwriting-specific detection is a smaller add. | REF-12 | pp13–17 §4.1 FR "Handle Low-Quality and Complex Documents" — Behavior: "Process variable-quality charts and flag limitations"; Output: "Parsed content with identified gaps or unreadable sections (REF 12)"; Acceptance: "Low-quality or handwritten content flagged"; "No inferred or fabricated data" • pp18–19 §A.1 In Scope: "poor scan quality"; "Detection and flagging of document limitations, including low-quality scans, handwritten content, and multi-patient documents" • p12 §3.3 Potential Risks: "Variability in document quality: Poor scan quality, handwritten content, and inconsistent formats may limit AI accuracy and completeness" • pp4–5 §1.1 Problem Definition: "often spanning hundreds of pages, including scanned or handwritten content" • pp19–20 §A.2 Out of Scope: "Handling of all handwritten or low-quality content with full accuracy" |
| 4.6 | File naming issues | Inconsistent naming, missing member/measure identifiers in filename. | ✅ Available | Available on the platform — filename/identifier validation (member + measure) is available in PenguinAI intake. Baseline today: last-name check only. | — | pp18–19 §A.1 In Scope: "inconsistent file naming (missing member/measure identifiers)" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Acceptance: "Supports detection of formatting issues (e.g., multi-patient documents, inconsistent naming)" • pp8–10 §3.1 Current State: "incorrect or inconsistent naming requires manual intervention" • pp19–20 §A.2 Out of Scope: "Automated correction of provider submission issues, including fixing naming conventions or re-matching charts without human validation" |
| 4.7 | Case data sufficiency | Where the chart does not contain what the case's assigned measure requires, the case is flagged as unsupported and routed to review. No value is inferred, estimated, or substituted (A10). | ⚠️ Partial | Partially available — element-level not_found and required_missing exist in the baseline; the case-level unsupported disposition and its routing are the remaining piece. | REF-06/07, REF-12 · P3 | pp13–17 §4.1 FR "Handle Low-Quality and Complex Documents" — Acceptance: "No inferred or fabricated data" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Acceptance: "Identifies incorrect or incomplete submissions" • p10 §3.1 Current State process map — Chart Chase step 6: "Determine if Valid Data is Found (yes or no)" • Case-level unsupported disposition: no direct source — added by Penguin |

***Risk — the document-quality thresholds are not yet measurable.** Horizon's §4.1 acceptance criteria set ≥90% of documents producing usable, searchable text and ≥95% of "standard documents" successfully processed. "Standard" is not defined anywhere in the scoping document, and §A.2 separately excludes guaranteed interpretation of degraded or ambiguous inputs (X-15). Together these leave the denominator open: a measured rate can be argued up or down by reclassifying a chart as standard or degraded, which puts PoC acceptance on subjective ground. Neither threshold is carried as an acceptance criterion in this document for that reason.*

***Action.** Before either number is adopted as an acceptance criterion, run a calibration exercise on a representative sample of real charts spanning Horizon's actual quality range. Horizon abstractors and Penguin each classify every chart as usable, marginal or degraded; the boundary is agreed and written down; the thresholds are then restated against that agreed denominator. Owner and sample size to be set with the SME. Tracked as OQ-12.*

***4.1–4.5 are the agreed top five.** 4.6 is deferred — it is a Horizon submission-process fix, not an AI problem. Poor scan and handwriting appeared twice in the source document (validation bullet and document-limitations bullet); merged here into 4.5. 4.7 was added in 3.7.*

### 2.5 Human-in-the-Loop

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| 5.1 | Confirm / modify / reject / comment | Reviewer acts on every AI finding before it counts — confirming it, modifying the value, rejecting it, or attaching a free-text comment. Nothing validated until acted on. All four actions logged under A3. | ✅ Available | PATCH elements/exclusions (accept/modify/reject/confirm); ai_value never overwritten; completion gated. In the baseline. Free-text comment per finding is an additive field on the existing ReviewerAnnotation store. | — | p5 §1.2 How AI Can Be Used: "Enable human-in-the-loop validation, allowing reviewers to confirm, modify, or reject AI-identified findings before data entry" • pp13–17 §4.1 FR "Support Reviewer Validation Workflow" — Acceptance: "Reviewers can confirm, modify, or reject: Data elements; Exclusions; Gap closure determinations"; "Validation required before downstream use"; "All validation actions tracked (audit trail)" • pp18–19 §A.1 In Scope: "Human-in-the-loop validation workflow, allowing reviewers to accept, reject, or modify AI-generated outputs" • p11 §3.2 Future State: "Data extraction is automated, with reviewers focused on validation" • Free-text comment: no direct source — added by Penguin |
| 5.2 | Escalation surfacing | Low-confidence, ambiguous, contradictory and unreadable items raised for human attention, never silently resolved. | ✅ Available | Available on the platform — an active escalation queue routing low-confidence/ambiguous/unreadable items to humans is supported in Gwen (CCT). Baseline today: passive badges. Contradiction routing arrives with 2.10. | — | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Low-confidence results flagged for review" • pp13–17 §4.1 FR "Detect Multi-Patient Documents" — Acceptance: "Flags ambiguous cases for manual review" • pp13–17 §4.1 FR "Handle Low-Quality and Complex Documents" — Acceptance: "Low-quality or handwritten content flagged" • pp19–20 §A.2 Out of Scope: "Resolution of ambiguous or complex clinical scenarios requiring nuanced human judgment or interpretation of intent" • p12 §3.3 Potential Risks: "Over-reliance on AI outputs: Reviewers may place undue trust in AI-generated results" |

*Determination and gap identification boundaries moved to §7 (X-11, X-12), where they belong as scope statements rather than workflow requirements.*

### 2.6 Output

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| 6.1 | Structured findings record | Validated elements, exclusions and citations persisted to the case, reusable across both workflows. | ✅ Available | Elements/exclusions/annotations/cross-measure all case-scoped; DocumentRegistry indexes for reuse. In the baseline. | REF-12 | p5 §1.2 How AI Can Be Used: "Surface structured outputs (data elements, exclusions, citations) to support downstream abstraction workflows" • p11 §3.2 Future State: "Extracted insights are reusable across workflows, reducing redundant review" • p5 §2.1 Expected Value Creation: "reducing redundant effort through the reuse of extracted insights across workflows" • pp8–10 §3.1 Current State: "Redundant effort: Charts may be reviewed multiple times across workflows with limited reuse of previously identified information" |
| 6.2 | Export | Excel and PDF, formatted to support manual entry into QMRM / non-standard platform. | ✅ Available | Available on the platform — Excel/PDF export formatted for downstream manual entry is a standard PenguinAI output capability. Baseline today: export buttons not yet wired. | REF-12 | pp13–17 §4.1 FR "Export Outputs for Downstream Use" — Behavior: "Provide structured outputs (REF 12) for manual entry into abstraction systems"; Output: "Exportable summaries including data, exclusions, and citations"; Acceptance: "Outputs are complete and formatted consistently" • pp13–17 §4.1 FR "Support Reviewer Validation Workflow" — Output: "Validated dataset ready for manual entry into downstream systems" • pp18–19 §A.1 In Scope: "Export of validated structured outputs to support manual entry into existing abstraction systems (e.g., QMRM, non-standard platforms)" • Excel/PDF formats: Penguin constraint (Scoping doc, "[Issam] Limited to PDF format") |
| 6.3 | No system replacement | Outputs integrate into existing workflows. No write-back to any Horizon system. | ✅ Available | No external/QMRM write-back; submission gateway writes only to internal tables. In the baseline (design principle). | — | pp18–19 §A.1 In Scope: "Processing of unstructured clinical documents only, with structured outputs designed to integrate into current workflows without requiring system replacement" • pp19–20 §A.2 Out of Scope: "Direct write-back or integration with downstream systems (e.g., QMRM, non-standard platforms, reporting systems) for automated data entry or submission"; "Replacement of existing abstraction systems or workflows, including QMRM or other review platforms" |

---

## 3. Chart Chase / Hybrid HEDIS

**What this workflow is.** Horizon draws a sample of members and tells us, per member, which measures apply. We receive the chart. The app reads it, finds the data points each measure needs — a blood pressure reading, an HbA1c result, a date of service, a provider credential — and shows each one beside the page it came from. An abstractor validates the findings and enters them into QMRM.

**Where the boundary sits.** QMRM calculates the measure. The app does not. It answers *"did I find what the measure requires, and here is the evidence"* — never *"does this member meet the measure"* (X-11).

The hybrid method combines administrative compliance, already determined by Horizon from claims, with medical record review. This application performs the medical record review leg only: it reads charts to find what the administrative data could not supply. Hybrid abstraction rules are in scope. Claims and other structured sources (X-14), hybrid sampling (X-6) and hybrid rate calculation (X-7) are not.

Converted from the page 10 current-state flow. Steps 1–6 map to CC-1 through CC-6.

### 3.1 Case Handling

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | :---: | :---- |
| CC 1.1 | Roster import | Import member sample: member, DOB, provider, assigned measures, priority, admin gap status. | ✅ Available | Available on the platform — member-sample/roster import (member, DOB, provider, assigned measures, priority, admin gap status) is a core Gwen Chart Chase Tracker (CCT) capability. Baseline today: cases seeded only. | P7 | pp8–10 §3.1 Current State: "This process is initiated by random member samples by product and measure (sample size varies; REF-01) with reviewers requesting charts from providers for specific members and measures" • pp22–24 §5.1 Data Sources — Member Context (QMRM / Gap Reports): "Member-level data including demographics, assigned measures, and gap status"; source: "QMRM (Inovalon), gap reports" |
| CC 1.2 | Chart-to-member association | Uploaded charts attached to the roster case. Multiple charts per member supported. | ✅ Available | ChartDocument.case_id → case → member; multiple charts per case. In the baseline. | P7 | p10 §3.1 Current State process map — Chart Chase step 1: "Upload chart(s) per member" • pp8–10 §3.1 Current State: "reviewers requesting charts from providers for specific members and measures"; "Charts are not directly linked within QMRM and must be managed separately" |
| CC 1.3 | Chase board | Working view: member, provider, measures, priority, retrieval status, substantiation status. Search, filter, bulk action. | ✅ Available | Available on the platform — the full chase board (search, filter, bulk action, retrieval + substantiation columns) is Gwen's Chart Chase Tracker (CCT). Baseline today: board without retrieval/substantiation columns; search unwired. | — | pp8–10 §3.1 Current State: "Charts are assigned to reviewers via a centralized queue"; "charts are stored across decentralized locations, including individual inboxes and shared drives, with no centralized repository" • pp22–24 §5.1 Data Sources — Assignment / Queue Data: "Work allocation data assigning charts to reviewers" • Board columns, search, filter, bulk action: no direct source — added by Penguin |
| CC 1.5 | Substantiation status | pending · in review · complete. | ✅ Available | Available on the platform — substantiation status (pending/in review/complete) is tracked in Gwen CCT. Baseline today: approximated by case status/outcome. | — | p10 §3.1 Current State process map — Chart Chase step 6: "Determine if Valid Data is Found (yes or no)" • pp8–10 §3.1 Current State: "followed by a secondary quality review (over-read)" • State names pending/in review/complete: no direct source — added by Penguin |

*CC-1.1's quoted passage names REF-01. That reference documents Horizon's sample construction and is not a build input here — sampling is Horizon's (A-7) and out of scope (X-6). See §6.2.*

### 3.2 Abstraction

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| CC 2.1 | Cheat sheet application | Measure rules, exclusions and required fields applied from Horizon cheat sheets. Replaces manual lookup (current step 2). | ⚠️ Partial | Partially available — measure specs applied from internal NCQA-based specs; Horizon cheat sheets as the source depend on P5/P8/OQ-3. | REF-08/09 · P8, P10 | p10 §3.1 Current State process map — Chart Chase step 2: "Reference HEDIS Cheat Sheet — Measure Rules; Exclusions; Required Fields" • pp8–10 §3.1 Current State: "Using HEDIS specifications and internally maintained "cheat sheets," reviewers navigate unstructured documents to locate required measure-specific data and evaluate exclusions" |
| CC 2.2 | Required data identification | Member DOB, provider entity, measure specific values — per current step 4. | ✅ Available | Member DOB, provider fields, measure-specific required elements present and rendered. In the baseline. | REF-06/07, REF-12 · P3 | p10 §3.1 Current State process map — Chart Chase step 4: "Identify Required Data — Member DoB; Provider Entity; Measure-specific data (e.g. BP)" • pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Behavior: "Identify and extract structured clinical data elements aligned to selected HEDIS measures" • pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Acceptance: "Includes provider signature/credentials where required by measure" |
| CC 2.3 | Exclusion evaluation | Candidate exclusions surfaced with evidence. Interpretation and judgment remain human (current step 5 explicitly notes this). | ✅ Available | Candidate exclusions with evidence; human ruling via PATCH; judgment explicitly human. In the baseline. | REF-02, REF-05, REF-08/09, REF-12 · P10 | p10 §3.1 Current State process map — Chart Chase step 5: "Evaluate Exclusions — Apply HEDIS Criteria; Requires Judgment for interpretation" • pp8–10 §3.1 Current State: "This process is highly dependent on reviewer experience and judgment, particularly when interpreting documentation" • pp13–17 §4.1 FR "Identify and Surface Potential Exclusions" — Output: "List of potential exclusions (REF 12) with supporting evidence" |
| CC 2.4 | Valid-data determination | Per measure: is substantiating data present, yes or no. | ⚠️ Partial | Partially available — determined implicitly (required elements decided + outcome); an explicit stored per-measure yes/no flag is a small add. | REF-06/07 | p10 §3.1 Current State process map — Chart Chase step 6: "Determine if Valid Data is Found (yes or no)" |
| CC 2.5 | Disposition recommendation | Recommend next step — *Follow up with provider* or *Ready for manual entry into QMRM*. Recommendation only; QMRM entry is out of scope. | ⚠️ Partial | Partially available — produces return_to_provider / review_required / ready_for_review; the 'Ready for manual entry into QMRM' disposition is a small add. | — | p10 §3.1 Current State process map — Chart Chase step 6: "prescribe next step "Follow-up with Provider" or "Ready for Manual entry into QMRM"" • pp19–20 §A.2 Out of Scope: "Direct write-back or integration with downstream systems (e.g., QMRM, non-standard platforms, reporting systems) for automated data entry or submission" |

### 3.3 Quality

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| :---- | :---: | :---- | :---: | :---- | :---: | :---- |
| CC 3.1 | Over-read queue (configurable %) | Abstractions routed to a second reviewer; agreement/disagreement captured. | ⚠️ Partial | Partially available — manual over-read with agreement capture exists; configurable-% routing to a second reviewer is the remaining piece (OQ-6). | — | pp8–10 §3.1 Current State: "followed by a secondary quality review (over-read) to ensure accuracy and compliance with audit requirements"; "Strict audit requirements: Extensive QA (over-read) processes are required due to low tolerance for error" • pp4–5 §1.1 Problem Definition: "rigorous quality controls, including comprehensive overread practices" • Configurable % and application to Chart Chase: no direct source — added by Penguin on NCQA grounds; confirm with SME |

***Asymmetry flagged.** The source document specifies over-read for Gap Closure only. NCQA expects it on hybrid abstraction, which is this workflow. CC-3.1 added on that basis — confirm with SME.*

### 3.4 Reporting

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| CC 4.1 | Progress dashboard | Retrieval %, substantiation by measure, queue depth and ageing. | ⚠️ Partial | Partially available — queue depth, ageing, completion %, exclusion rate, throughput, outcomes-by-measure. Missing retrieval % and an explicit substantiation-by-measure rollup. | — | p7 §2.3 Metrics: "Average chart review time per chart"; "Charts processed per cycle"; "# of charts processed using AI-assisted review" • Retrieval % and substantiation-by-measure rollups: no direct source — added by Penguin |

---

## 4. Gap Closure / Non-Standard

**What this workflow is.** Horizon identifies care gaps from claims and sends monthly gap reports to providers. A provider responds by submitting documentation for a service already performed but not reflected in claims. By the time a chart reaches us, the gap is already known and arrives with the case — member, measure and gap status all supplied.

**Where the boundary sits.** The app does not find gaps (X-12). It answers one question: *does this chart contain valid data substantiating closure of the gap already identified?* That is the GC-4.1 / GC-4.2 split — nothing new found, or new data found. Whether the gap then closes is Horizon's call.

Converted from the page 10 current-state flow. Steps 1–8 map to GC-1 through GC-5.

### 4.1 Case Seeding

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| GC 1.1 | Case auto creation from roster | Chart upload creates a case pre-populated with member and measure **from the roster**, added to the work queue. | ✅ Available | Available on the platform — gap-driven, roster-pre-populated case creation is a standard PenguinAI workflow. Baseline today: auto-created on upload but member/measure from a manual form. | P7 | p10 §3.1 Current State process map — Gap Closure step 1: "Assign Task Loaded — Upload Chart; Automatically create a case with Pre-populated Member + Measure - add it to the work queue" • pp8–10 §3.1 Current State: "Reviewers validate the chart against pre-populated member and measure data" • pp22–24 §5.1 Data Sources — Member Context: "Member-level data including demographics, assigned measures, and gap status" |
| GC 1.2 | Work queue | Cases queued, prioritized, assignable. | ✅ Available | Queue list + filters + priority ordering; assignable (/assign, bulk allocation). In the baseline. | — | p10 §3.1 Current State process map — Gap Closure step 1: "add it to the work queue" • pp8–10 §3.1 Current State: "Charts are assigned to reviewers via a centralized queue" • pp22–24 §5.1 Data Sources — Assignment / Queue Data: "Work allocation data assigning charts to reviewers" |

***Design note.** Member and measure must come from the roster, not be derived from the chart — otherwise GC-2.1 has no independent value to validate against. This makes GC-1.1 a roster lookup, not an inference.*

### 4.2 Validation

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| :---- | :---- | :---- | :---: | :---- | :---: | :---- |
| GC 2.1 | Member match | Chart identity checked against the case member — name and DOB. | ✅ Available | gap_validation name + multi-format DOB check against the case member. In the baseline. | P7 | p10 §3.1 Current State process map — Gap Closure step 2: "Validate Chart — Member Match; DoB; Correct document" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Behavior: "Assess submitted charts for correct member, measure alignment, completeness, and contextual validity required for gap closure"; Acceptance: "Identifies missing or inconsistent patient identifiers" |
| GC 2.2 | Correct document check | Confirm the chart relates to the case measure and contains relevant content. | ✅ Available | measure_alignment + service_date + content + legibility checks. In the baseline. | REF-06/07 · P3 | p10 §3.1 Current State process map — Gap Closure step 2: "Correct document" • pp13–17 §4.1 FR "Validate Provider-Submitted Charts (Gap Closure)" — Output: "Member or measure mismatches"; Acceptance: "Identifies incorrect or incomplete submissions" • pp18–19 §A.1 In Scope: "documents containing unrelated content" |

### 4.3 Review & Extraction

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| :---- | :---- | :---- | :---: | :---- | ----- | :---- |
| GC 3.1 | Targeted highlighting | Relevant sections highlighted. Records are typically small and measure focused. | ✅ Available | AI evidence anchors + persisted ReviewerAnnotation highlights; rendered spans. In the baseline. | — | p10 §3.1 Current State process map — Gap Closure step 3: "Review Chart — Highlight relevant sections; Typically smaller, targeted records" • p11 §3.2 Future State: "where they confirm, modify, or reject findings, perform highlighting" • pp4–5 §1.1 Problem Definition: "While generally more targeted, this workflow introduces additional complexity related to data validation, member and provider matching, and submission readiness" |
| GC 3.2 | Measure-aligned extraction + rules | Extract data against the case measure and apply measure rules. | ⚠️ Partial | Partially available by design — extraction is measure-aligned; automated rule/compliance application is intentionally out of scope (6.3 / X-11). | REF-03, REF-06/07, REF-08/09 | p10 §3.1 Current State process map — Gap Closure step 4: "Extract Clinical Data — Measure-Aligned data; Apply HEDIS rules" • pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Behavior: "Identify and extract structured clinical data elements aligned to selected HEDIS measures" • pp19–20 §A.2 Out of Scope: "Automated clinical or compliance decision-making, including determination of measure compliance, numerator status, or final exclusion application" |

### 4.4 Outcome

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| ----- | :---- | :---- | :---: | :---- | ----- | :---- |
| GC 4.1 | No-new-data outcome | Where nothing new is found, record outcome: *previously compliant* or *no impact to gap*. | ✅ Available | Available on the platform — the specific gap-closure outcomes (previously compliant / no impact to gap) are supported in PenguinAI's gap workflow. Baseline today: only 'no_evidence' approximates them. | — | p10 §3.1 Current State process map — Gap Closure step 5: "If not new valid data - Mark Outcome — Previously compliant OR No Impact to gap" |
| GC 4.2 | New-data capture | Where new valid data is found, capture date of service and result values. | ✅ Available | Elements capture date + result values with evidence; reviewer edit/add supported. In the baseline. *(scope pending OQ-4)* | REF-12 | p10 §3.1 Current State process map — Gap Closure step 6: "If new valid data - Enter Data — Date of Service; Results" • pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Extracted data includes required contextual attributes: Dates (Date of Service and/or Reported Date as applicable)" |
| GC 4.3 | Code selection **[pending]** | Select ICD / CPT / LOINC codes representing the finding. | ⚠️ Partial | Partially available — a platform ICD/CPT/LOINC code extractor exists; needs tuning to customer-specific coding. Baseline today: no code selection (reference value sets present). Scope pending OQ-4 (and the 6.3 conflict). | REF-04 | p10 §3.1 Current State process map — Gap Closure step 6: "Select Codes" • pp8–10 §3.1 Current State: "including selection of appropriate codes and validation of compliance logic" • pp22–24 §5.1 Data Sources — Value Set Directory (Codes): "Clinical codes (ICD, CPT, LOINC) supporting measure compliance and exclusions"; limitation: "Requires contextual application within unstructured clinical notes" |
| GC 4.4 | Documentation only closure | Where the gap status supplied by Horizon shows an open gap but the chart documents the service, flag as closable on documentation. | ⚠️ Partial | Partially available — Gwen's Chart Audit (CAC) gap-vs-chart pattern is portable; driven by the admin gap status on the roster (P7). | P7 | pp8–10 §3.1 Current State: "Providers review identified gaps and submit documentation if services have already been completed but not reflected in claims" • p5 §2.1 Expected Value Creation: "In gap closure, improved validation of provider-submitted documentation enhances the ability to capture compliant services that are not reflected in claims" • pp19–20 §A.2 Out of Scope: "Processing of structured data sources outside of charts, including: Claims data" — the app therefore works from the admin gap status supplied on the roster (A-11), never from claims records. See X-14. |

***GC-4.2 and GC-4.3 are pending a scope decision.** Neither appears in the pages 4, 11 or 17 requirements — both come only from the current-state flow. Code selection is a distinct capability from extraction, carries its own audit exposure, and if in scope makes the app the abstraction record for this workflow, which conflicts with 6.3. **Do not estimate until resolved.***

### 4.5 Quality

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| :---- | ----- | :---- | :---: | :---- | ----- | :---- |
| GC 5.1 | Over-read queue | Completed cases placed in a dedicated over-read queue; reviewers work that queue. | ✅ Available | Available on the platform — a dedicated over-read queue exists (Gwen / abstractor module). Baseline today: surfaced via a status filter. | — | p10 §3.1 Current State process map — Gap Closure step 7: "Submit for Over-reads — Option in Gwen App - place case in a dedicated "Over-reads" queue; Reviewers doing Over-read work on this queue" |
| GC 5.2 | Quality review + audited corrections | Reviewer verifies accuracy and corrects errors. Corrections captured under A3. | ✅ Available | POST /qa (pass/correction + agreement detail), ai_value preserved for AI-vs-final, all logged to AuditLog. In the baseline. | P9 | p10 §3.1 Current State process map — Gap Closure step 8: "Quality Review — User Verifies Accuracy; Correct errors (e.g. mistyped values)" • pp8–10 §3.1 Current State: "all inputs are manually entered into the system and undergo quality review to ensure accuracy" |

---

## 5. Audit & Compliance

| # | Requirement | Description | Coverage | Note | Depends on | Source (customer scoping document) |
| :---- | ----- | :---- | :---: | :---- | ----- | :---- |
| A1 | Source immutability & retrievability | The original chart PDF is never altered, transformed, or replaced and remains the system of record, and every document is addressable by a stable ID so any finding can be shown next to the exact source page it came from, at any later point. | ✅ Available | In the baseline — originals stored without overwrite and addressable by stable ID; any finding renders beside its source page. Platform adds hardened WORM/versioned immutability. | — | p5 §1.2 How AI Can Be Used: "without altering, transforming, or replacing the original documents, which remain the system of record for audit and compliance purposes" • pp13–17 §4.1 FR "Ingest and Process Clinical Chart Documents for Analysis" — Output: "No modification or replacement of original documents; all outputs remain linked to the source record"; "Indexed references to source content (page-level mapping)"; Acceptance: "Original documents remain unchanged and accessible as the system of record"; "All extracted data maintains traceability to the original document (page and location)" |
| A2 | Citation persisted per finding | Every extracted element and exclusion carries its page number and verbatim excerpt, stored with the determination at the moment it is made rather than regenerated on read, so the citation can never drift from what the reviewer saw. | ✅ Available | In the baseline — page number + verbatim excerpt persisted with each element/exclusion at determination time, not regenerated on read. | P9 | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Each data element includes traceable citation (page number, excerpt)" • pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Acceptance: "All outputs include traceable citations (page number, excerpt)"; "Supports auditability and validation by reviewers" • pp18–19 §A.1 In Scope: "citations to source locations within the chart (e.g., page number, excerpt) to support validation and auditability" • Store-at-determination rather than regenerate-on-read: no direct source — added by Penguin |
| A3 | Actor & timestamp on every action | Every human action on a finding — who accepted, modified, rejected or commented on it and exactly when — is attributed to a named user and server-time-stamped; the spine of the audit trail. | ✅ Available | In the baseline — every reviewer action (accept/modify/reject) written to AuditLog with actor and server timestamp. Comment events join the same log with 5.1. | — | Customer meetings (not stated in the scoping document) • pp13–17 §4.1 FR "Support Reviewer Validation Workflow" — Acceptance: "All validation actions tracked (audit trail)" |
| A4 | Evidence trace & rules version | Each measure-specific data point carries a trace to its supporting evidence in the medical record, and the NCQA rules version applied (e.g. MY2025, MY2026) is recorded with it. | ⚠️ Partial | Evidence trace to source is in the baseline (per-element citations); recording the applied NCQA rules version per data point is a schema add. Partial — overlaps 2.7. **With two measurement years in scope (A-12), version stamping is load-bearing rather than optional.** | REF-06/07 | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Each data element includes traceable citation (page number, excerpt)" • pp22–24 §5.1 Data Sources — HEDIS Measure Specifications: "NCQA HEDIS specifications and internal reference materials" • Recording the applied rules version: no direct source — added by Penguin (overlaps 2.7) |
| A5 | Escalation logged | Every escalation is logged with the username and date-time. | ✅ Available | In the baseline — escalations captured (what/why/who/how) in the audit trail with username and date-time. | — | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Low-confidence results flagged for review" • pp13–17 §4.1 FR "Detect Multi-Patient Documents" — Acceptance: "Flags ambiguous cases for manual review" • Username and date-time capture: no direct source — added by Penguin |
| A6 | Human review & approval, logged | A human reviews and approves the results before they count, and the action is logged with username and date-time. | ✅ Available | In the baseline — no AI element/exclusion counts downstream until a reviewer acts; the validation gate is enforced and the action logged. | — | p5 §1.2 How AI Can Be Used: "Enable human-in-the-loop validation, allowing reviewers to confirm, modify, or reject AI-identified findings before data entry" • pp13–17 §4.1 FR "Support Reviewer Validation Workflow" — Acceptance: "Validation required before downstream use"; "All validation actions tracked (audit trail)" • pp18–19 §A.1 In Scope: "Human-in-the-loop validation workflow, allowing reviewers to accept, reject, or modify AI-generated outputs" |
| A7 | Per-finding confidence retained | The AI confidence score for each element and exclusion is recorded and low-confidence items are flagged, so an auditor can see which findings were high- versus low-certainty at abstraction time. | ✅ Available | In the baseline — per-finding AI confidence stored; low-confidence items flagged. | — | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Acceptance: "Low-confidence results flagged for review"; "[Note: extracted data is subject to confidence scoring, traceability to source evidence, and mandatory human validation, ensuring that final abstracted outputs meet audit and quality standards]" |
| A8 | Provider credential as evidence | Where a measure requires it, the performing provider's signature and credential are captured as part of the finding's evidence. | ⚠️ Partial | Partially available — provider credential extraction is on the platform; needs per-measure credential requirements and extraction tuning to capture signature/credential as evidence. | REF-06/07 | pp13–17 §4.1 FR "Provide Evidence-Based Outputs with Traceability" — Output: "Supporting context (e.g., provider credentials where required)"; Acceptance: "Includes provider signature/credentials where required by measure" |
| A9 | Non-compliant values retained | The record preserves all extracted clinical values regardless of whether they meet compliance criteria, including out-of-range and non-numerator-favorable results, so the trail reflects the full clinical picture. Competing candidate values surfaced under 2.10 are retained alongside the value the reviewer selects. | ✅ Available | In the baseline — all extracted values retained regardless of compliance, including out-of-range results. | — | pp13–17 §4.1 FR "Extract Measure-Specific Clinical Data" — Behavior: "including all relevant data regardless of whether it meets compliance criteria"; Acceptance: "All relevant clinical data elements are extracted, including non-compliant values (e.g., out-of-range results)" |
| A10 | No inferred/fabricated data | The system never infers, guesses, or fabricates a value, and unreadable content (poor scans, handwriting) is explicitly flagged as unread rather than filled in. Where the supplied data does not support the case's measure, the case is flagged as unsupported (4.7) rather than estimated. | ✅ Available | In the baseline — no inferred/fabricated values; unreadable content flagged as unread rather than filled in. | — | pp13–17 §4.1 FR "Handle Low-Quality and Complex Documents" — Acceptance: "No inferred or fabricated data"; "Low-quality or handwritten content flagged" • pp19–20 §A.2 Out of Scope: "Handling of all handwritten or low-quality content with full accuracy, including guaranteed interpretation of degraded or ambiguous inputs" • p12 §3.3 Potential Risks: "Inaccurate data extraction: Errors in extracting clinical values or dates could lead to incorrect abstraction and reporting outcomes" |
| A11 | User management logged | All user management activity — create user, assign role, disable user — is logged with the actor username, the action, and the date-time. | ✅ Available | Available on the platform — admin RBAC user management with audit logging is a standard PenguinAI capability, and the baseline already provides the audit spine (AuditLog: actor, action, timestamp + read/report API) and the User model (role + is_active disable flag). Baseline today: no user-management endpoints yet, so create/role/disable actions aren't emitted — wiring them to the existing audit-write is a small add. | — | Customer meetings (not stated in the scoping document) • p18 §4.2 Non-Functional Requirements: section left as "Click or tap here to enter text." — no Horizon NFRs were supplied |
| A12 | Multi-patient flag record | Documents flagged as containing more than one member or ambiguous identity are recorded and blocked from mis-attribution. | ⚠️ Partial | Partially available — multi-patient / multi-identity detection is portable from PenguinAI intake; the flag record + mis-attribution block is not yet wired into this workflow. | — | pp13–17 §4.1 FR "Detect Multi-Patient Documents" — Output: "Document-level flag with potential segmentation indicators"; Acceptance: "Detects indicators of multiple patients"; "Prevents misattribution of data" • pp18–19 §A.1 In Scope: "multiple members in one document" |

---

## 6. Prerequisites

| Ref | Item | Blocks | Status |
| :---: | :---- | ----- | ----- |
| P1 | Charts in PDF, uploaded manually to the app | 1.1 | Restated by A-1 |
| P2 | NCQA HEDIS specifications — REF-03, REF-06, REF-07 | 2.1, 2.7, GC-3.2 | **Blocked on OQ-3, OQ-4** |
| P3 | Specification interpretation and mapping to measures | 2.1, 2.3, 2.10, 4.4, 4.7, CC-2.2, GC-2.2 | — |
| P4 | Clinical codes — ICD, CPT, LOINC — REF-04 | GC-4.3 | Only if GC-4.3 in scope |
| P5 | Internally maintained cheat sheets — REF-08, REF-09 | 2.7, CC-2.1 | — |
| P6 | Exclusion definitions — REF-02, REF-05 | 2.6, CC-2.3 | Named in 3.7; previously unlinked |
| P7 | Member-level data — demographics, assigned measures, gap status. Field-level specification at §6.3 | 2.2, 2.5, 2.8, 4.2, CC-1.1, CC-1.2, GC-1.1, GC-2.1, GC-4.4 | **Highest dependency count** |
| P8 | Precedence rules: NCQA specs vs Horizon cheat sheets | 2.7, CC-2.1 | Moot if OQ-4 is no |
| P9 | Agreed audit requirements | §5 audit requirements, A2, GC-5.2 | Agreed — §5 |
| P10 | Documented list of Horizon's allowable adjustments affecting measure data | 2.1, 2.6, 2.7, CC-2.1, CC-2.3 | New in 3.7 — see A-13 |

### 6.1 Reference materials in scope

*Rows copied from the customer scoping document §7 Reference Materials. The "Maps to" column is Penguin's.*

| ID | Name | Description (customer's words) | Artifact | Maps to |
| :---- | :---- | :---- | :---- | :---- |
| REF-02 | Chart Abstractions, All Measures | Outlines the exclusions at a high level for each of the measures. | REF 02 AI Chart Abstraction Exclusions - All measures.xlsx | P6 · 2.6, CC-2.3 |
| REF-03 | HEDIS 2026 Technical Specifications | 2026 Measure Specifications | REF 03 HEDIS MY 2026 Volume 2 Technical Update 2026-03-31.docx | P2 · 2.7, GC-3.2 |
| REF-04 | Value Set Directory (VSD) | The Value Set Directory (VSD) includes value sets and single codes (referred to as direct reference codes) that are required for HEDIS reporting. | REF 04 HEDIS MY 2026 Volume 2 Value Set Directory 2026-03-31.xlsx | P4 · GC-4.3 |
| REF-05 | 2026 HEDIS Measure Exclusions | — | REF 05 MY26 HEDIS Measure Exclusions 2026.docx | P6 · 2.6, CC-2.3 |
| REF-06 | 2025 NCQA HEDIS Specifications | MY2025 represents the season just completed | REF 06 HEDIS MY2025 Technical Specifications - Hybrid Measures.pdf | P2 · 2.1, 2.7, A4 |
| REF-07 | 2026 NCQA HEDIS Specifications | MY2026 is the upcoming season. Please note that for the next season, we will be working with seven measures instead of eight, as we will no longer be collecting Lead Screening in Children (LSC) via Hybrid | REF 07 HEDIS MY2026 Technical Specifications - Hybrid Measures.pdf | P2 · 2.1, 2.7, A4, OQ-1 |
| REF-08 | 2025 Chart Chase Cheat Sheets | Internal Horizon training versions of HEDIS specifications | REF 08 HEDIS CHART CHASE MY2025 CHEAT SHEETS FINAL.pdf | P5, P10 · 2.7, CC-2.1 |
| REF-09 | 2026 Chart Chase Cheat Sheets | Internal Horizon training versions of HEDIS specifications | REF 09 HEDIS CHART CHASE MY2026 CHEAT SHEETS FINAL.pdf | P5, P10 · 2.7, CC-2.1 |
| REF-12 | Structured Data Elements | Listing of data elements, both Chart Chase & Gap Closure | REF 12 Structured Output Data Elements.docx | 2.6, 4.5, 6.1, 6.2, CC-2.3 · OQ-7 |

**Not required — no requirement depends on them.**

| ID | Name | Why not |
| :---- | :---- | :---- |
| REF-01 | Hybrid Measure Sample Sizes by Product & Measure | Sampling is Horizon's (A-7) and out of scope (X-6). Useful context for OQ-1 and OQ-2, not a build input |
| REF-10 | 2026 Chart Chase / Hybrid HEDIS Team Metrics | Feeds the value case. CC-4.1's source is p7 §2.3 Metrics |
| REF-11 | 2026 NCQA HEDIS Specifications – Glossary & Appendix | No requirement depends on it. Request later if P3 interpretation stalls on terminology |

### 6.2 Reference coverage by measurement year

| Rule set / artifact | MY2025 | MY2026 | Scope |
| :---- | :---- | :---- | :---- |
| Technical specs — hybrid measures | REF-06 | REF-07 | In — hybrid abstraction rules |
| Volume 2 Technical Update (full) | **missing** | REF-03 | In |
| Value Set Directory | **missing** | REF-04 | In — blocks P4, GC-4.3 |
| Measure exclusions | **missing** (REF-02 undated) | REF-05 | In — blocks P6, 2.6, CC-2.3 |
| Chart chase cheat sheets | REF-08 | REF-09 | In — Horizon's applied rules and adjustments (P5, P10) |
| Structured data elements | REF-12 (undated) | REF-12 | In — output shape |
| Hybrid sampling rules — MRSS, oversample, replacement | REF-01 — not required | REF-01 — not required | **Out — X-6, A-7** |
| Hybrid rate rules — admin + sample extrapolation | none supplied | none supplied | **Out — X-7.** No artifact needed |

*A-12 puts MY2025 and MY2026 in scope, but three MY2026 artifacts have no MY2025 counterpart. In order of consequence: Value Set Directory, measure exclusions, full Volume 2 Technical Update. Value sets are reissued annually — codes added each October, others retired — so MY2025 evidence validated against the MY2026 VSD can be wrong in both directions.*

*REF-02 carries no year. Confirm whether it covers both MY2025 and MY2026.*

*The baseline currently references NCQA MY2027 value sets (see 2.7). REF-06 and REF-07 agree with A-12; the platform note is the outlier and needs correcting before build.*

### 6.3 Case data specification

*One case is one member against one measure. This is the field-level specification behind P7, independent of file format. Penguin-proposed — no field list appears in the customer document, which describes Member Context only as "demographics, assigned measures, and gap status" (pp22–24 §5.1). Confirmation is pending OQ-9, OQ-10 and OQ-11.*

| Field | Description | Req. | Used by |
| :---- | :---- | :---- | :---- |
| **Member identity** | | | |
| Member ID | Horizon's member identifier. Case key, and the join between roster row and chart | Required | CC-1.1, CC-1.2, GC-1.1, 4.2 |
| Last name | Validates chart identity against the case | Required | 2.2, 4.2, GC-2.1 |
| First name | Validates chart identity against the case | Required | 2.2, 4.2, GC-2.1 |
| Date of birth | Validates chart identity against the case; multi-format parsing supported | Required | 2.2, 4.2, CC-2.2, GC-2.1 |
| Sex | Measure eligibility where the measure requires it | Preferred | 2.1, 2.8 |
| Product / line of business | Confirms the case falls inside A-2 | Preferred | 2.8 |
| **Measure assignment** | | | |
| Measure code | HEDIS abbreviation. Selects the required data elements and the targeted analysis scope | Required | 2.1, 2.4, 2.5, CC-2.2, GC-2.2, GC-3.2 |
| Measurement year | MY2025 or MY2026. Selects the rule and value-set version applied, and is stamped on each determination | Required | 2.7, A4 |
| Workflow | Chart Chase or Gap Closure. Routes the case to §3 or §4 | Required | CC-1.1, GC-1.1 |
| **Gap context** | | | |
| Gap or case ID | One row per member per gap, per A-11 | Required | GC-1.1, GC-4.1 |
| Gap status | Open, closed, or administratively compliant | Required | CC-1.1, GC-4.4 |
| Admin compliance date | Where administratively compliant, the date. Supports documentation-only closure | Preferred | GC-4.4 |
| **Provider** | | | |
| Provider name | Provider validation and per-measure credential checks | Required | 2.3, 4.2, CC-2.2 |
| Provider NPI | Unambiguous provider matching where names collide | Preferred | 2.3, 4.2 |
| **Workflow and linkage** | | | |
| Priority | Queue ordering on the chase board | Preferred | CC-1.1, CC-1.3, GC-1.2 |
| Chart file name or linking key | Ties each uploaded PDF to its case. Horizon's current state relies on a file naming convention; an explicit key removes that dependency | Required | CC-1.2, 4.6, GC-1.1 |

*Required means the requirement cannot be met without it. Preferred means there is a workable fallback — member matching can fall back to name plus date of birth, provider matching to name alone — at a cost in precision that should be agreed rather than discovered.*

---

## 7. Out of Scope

| # | Item |
| ----- | :---- |
| X-1 | Collecting documents from intake channels |
| X-2 | Generating HEDIS reports |
| X-3 | Handling members who switch product line mid-year |
| X-4 | Determining member eligibility |
| X-5 | Writing back to QMRM or a non-standard platform; entering data manually into QMRM |
| X-6 | Drawing the medical record sample — sampling, oversample, MRSS, and replacement logic. *No direct source — added by Penguin; not among the customer's §A.2 exclusions* |
| X-7 | Producing a reportable or certified hybrid rate. *The hybrid method combines claims-based (administrative) compliance with chart-review results from the sample to produce the reportable measure rate. That rate must come from NCQA-certified software and be signed off by a licensed auditor; the app supplies evidence into that process, it does not produce the rate* |
| X-8 | Contacting providers — chasing charts and sending alerts and reminders |
| X-9 | Calculating inter-rater reliability statistics |
| X-10 | Generating abstractor qualification records |
| X-11 | **Computing HEDIS measures.** The app extracts and evidences the data points QMRM uses to calculate compliance. It does not determine measure compliance, numerator status, or final exclusion application. |
| X-12 | **Identifying care gaps.** Gaps are derived from claims by Horizon and arrive with the case. The app determines whether a submitted chart substantiates closure of an already identified gap. |
| X-13 | Integrating with any Horizon system. All inputs arrive as file uploads. No inbound or outbound interface to QMRM, EMRs, HIEs, claims systems, or reporting systems. |
| X-14 | **Processing structured data sources outside the chart** — claims data, laboratory feeds, and registry or supplemental data sources. Administrative compliance is determined by Horizon before a case reaches the app; what remains is chart evidence. |
| X-15 | **Guaranteeing interpretation of degraded or ambiguous content.** Poor scans and handwritten passages are detected and flagged (4.5), and no value is ever inferred (A10) — but full-accuracy reading of degraded inputs is not guaranteed. |
---

## 8. Assumptions

| # | Assumption | Mirrors |
| :---- | :---- | :---- |
| A-1 | Horizon uploads all chart documents directly into the PoC application as PDF files. The format of structured inputs is pending OQ-9 and OQ-11 | — |
| A-2 | Medicare only — one line of business, which determines the applicable measure set | X-3 |
| A-3 | Member eligibility already determined by Horizon | X-4 |
| A-4 | Roster is authoritative for member and assigned measures | — |
| A-5 | Synthetic or de-identified data only | — |
| A-6 | Horizon retrieves charts from its intake channels — fax, mail, portals, MFT, shared drives | X-1 |
| A-7 | Horizon draws the medical record sample and supplies it as the roster | X-6 |
| A-8 | QMRM is the system of record for measure computation and reporting. Abstractors manually enter validated output; QMRM produces the reportable rates | X-2, X-5, X-7, X-11 |
| A-9 | Horizon performs provider outreach and chart chase | X-8 |
| A-10 | Horizon's existing QA program covers abstractor qualification and inter-rater reliability | X-9, X-10 |
| A-11 | Care gaps are identified by Horizon and provided to the application by file upload, one record per member per gap | X-12 |
| A-12 | Measurement years 2025 and 2026 only. The solution uses the version of the rules provided by Horizon as PDF or DOCX | — |
| A-13 | All adjustments Horizon applies that affect measure data are documented and provided | P10 |
| A-14 | Where measure data is contradictory or ambiguous, the app surfaces it for human review. It does not adjudicate between competing values | 2.10 |
| A-15 | Under the NCQA hybrid method a sampled member with no substantiating evidence is reported as non-compliant and remains in the denominator. That determination is Horizon's, applied in QMRM; the app records only whether evidence was found (S-1, S-2) | 2.11, X-11 |

---

## 9. Open Questions

| # | Question | Blocks |
| :---- | :---- | :---- |
| OQ-1 | REF-07 notes the hybrid set drops from eight measures to seven for MY2026. Which are the seven, and which of them apply to Medicare? Penguin will assess the feasibility of a subset for the PoC | 2.1, 2.7, CC-1.1 |
| OQ-2 | Number of members in scope | Volume, A-1 feasibility |
| OQ-3 | Does the NCQA licence permit loading specifications into an AI app | P2, P8, 2.7 |
| OQ-4 | Are GC-4.2 and GC-4.3 in scope | GC-4.2, GC-4.3, P4 |
| OQ-5 | Answer-key sourcing for validation. *Measurement year and specification version are settled by A-12* | 2.7 |
| OQ-6 | Over-read design — same for both workflows | CC-3.1, GC-5.1 |
| OQ-7 | Excel export target shape | 6.2 |
| OQ-8 | Is MY2025 in scope for abstraction, or reference only? Decides whether the missing MY2025 artifacts in §6.2 are blockers | 2.7, A4, §6.2 |
| OQ-9 | **Member Context report — content and format.** §5.1 describes it as structured system data from QMRM and gap reports, available as report extracts. Which fields will the extract carry, and can it be supplied as CSV or Excel? | CC-1.1, P7, A-4 |
| OQ-10 | **Location of the assigned measure and gap.** For each member case, which artifact carries them — columns on the roster extract, a separate gap report, or the chart PDF itself? | GC-1.1, GC-2.1, A-11, X-12, 2.8 |
| OQ-11 | **Upload set and sequence.** What is the full list of files Horizon uploads per batch, in what formats, in what order, and are any merged — several members in one PDF, or member context folded into another file? | 1.1, 4.1, A-1, A12, CC-1.2 |
| OQ-12 | **Document quality thresholds.** Do the §4.1 criteria — ≥90% usable searchable text, ≥95% of standard documents processed — apply to the PoC? How is "standard" defined, and what is the denominator? X-15 excludes guaranteed interpretation of degraded content, so the thresholds can only be measured over charts of agreed legibility. Requires the calibration exercise in §2.4 | 1.2, 4.5, 4.7, X-15 |
| OQ-13 | **No-evidence reason codes.** Should the reasons recorded under 2.11 align to Horizon's existing chase dispositions, and what are those dispositions today? | 2.11, CC-2.5 |

***OQ-2 and A-1 interact.** Manual upload caps a live demonstration at a handful of charts, which limits how convincingly the queue and prioritisation requirements can be shown.*

***OQ-10 carries a design consequence.** If the assigned measure and gap arrive inside the chart PDF, the design note under GC-1.1 fails: member and measure must come from the roster rather than be derived from the chart, or GC-2.1 has no independent value to validate against and the gap-closure match check collapses.*

***OQ-11 interacts with 4.1 and A12.** Merged uploads — several members in one PDF — are exactly what multi-patient detection exists to catch. Knowing in advance whether Horizon merges determines how much that path matters.*

***OQ-1 is unanswered by anything supplied.** No document in our possession names the seven measures. REF-01 column I (sample sizes by product and measure) would answer it and inform OQ-2. Candidate measures should not be assumed until then.*

---

## 10. Traceability

| Source in the customer document | Requirement IDs |
| :---- | :---- |
| pp4–5 · §1.1 Problem Definition | 3.3, 4.5, CC-3.1 |
| p5 · §1.2 How AI Can Be Used | 1.1–1.3, 2.1, 2.4–2.6, 3.3–3.4, 4.2, 4.4, 5.1, 6.1, A1, A6 |
| p5 · §2.1 Expected Value Creation | 6.1, GC-4.4 |
| p7 · §2.3 Metrics | CC-4.1 |
| pp8–10 · §3.1 Current State (prose) | 1.1, 2.3, 2.7, 4.2, 4.6, 6.1, CC-1.1–CC-1.3, CC-1.5, CC-2.1, CC-2.3, CC-3.1, GC-1.1–GC-1.2, GC-4.3–GC-4.4, GC-5.2, A4 |
| p10 · §3.1 Current State process map — Chart Chase | CC-1.2, CC-1.5, CC-2.1–CC-2.5, 4.7 |
| p10 · §3.1 Current State process map — Gap Closure | GC-1.1–GC-1.2, GC-2.1–GC-2.2, GC-3.1–GC-3.2, GC-4.1–GC-4.3, GC-5.1–GC-5.2 |
| p11 · §3.2 Future State | 1.2, 2.1, 2.4–2.5, 3.3–3.4, 5.1, 6.1, GC-3.1 |
| p12 · §3.3 Potential Risks | 4.2, 4.5, 5.2, A10, A11 |
| pp13–17 · §4.1 Functional Requirements | 1.1–1.5, 2.1–2.4, 2.6, 2.9–2.10, 3.1–3.2, 4.1–4.7, 5.1–5.2, 6.2, CC-2.2–CC-2.3, GC-2.1–GC-2.2, GC-3.2, GC-4.2, A1–A3, A5–A10, A12 |
| p18 · §4.2 Non-Functional Requirements (empty in the document) | A11 |
| pp18–19 · §A.1 In Scope | 1.1–1.2, 1.4, 2.1, 2.4–2.6, 3.1, 4.1, 4.3–4.6, 5.1, 6.2–6.3, GC-2.2, A2, A6, A12 |
| pp19–20 · §A.2 Out of Scope | 1.1, 2.6, 2.8–2.10, 4.5–4.6, 5.2, 6.3, CC-2.5, GC-3.2, GC-4.4, A10, X-14 |
| pp22–24 · §5.1 Data Sources, Inputs, and Quality | 2.2, 2.7–2.8, CC-1.1, CC-1.3, GC-1.1, GC-1.2, GC-4.3, A4, A11, P1–P7 |
| p26 · §7 Reference Materials | Mapped in full at §6.1 and §6.2, and carried per requirement in the Depends on column. Standalone pointers removed from the Source column in 3.7 |
| Penguin-added — flagged in the Source cell as having no direct basis in the customer document | **Whole requirement added:** 2.10 (conflicting data detection), 4.7 (case data sufficiency), CC-1.3 (chase board), CC-1.5 (substantiation states), CC-3.1 (over-read on Chart Chase), CC-4.1 (progress dashboard), A3 (actor + timestamp), A5 (escalation logging), A11 (user management logging). **Whole section added:** §6.3 (case data specification). **Whole exclusion added:** X-6 (sampling), X-13 (integration boundary). X-14 is sourced to §A.2 verbatim. **Specific aspect added, rest is sourced:** 2.7 (version-per-determination), 2.8 (not_eligible escalation), 3.2 and A2 (citation persisted at determination rather than regenerated), 5.1 (free-text comment), 6.2 (Excel/PDF export shape), A4 (rules-version recording). **Sourced to customer meetings rather than the scoping document:** A3, A11. |

---

## 11. Compliance resources

*External references consulted when adding items that have no basis in the customer scoping document. These are secondary sources. Authoritative texts are the NCQA technical specifications (REF-03, REF-06, REF-07) and the Value Set Directory (REF-04), which Horizon supplies. Where a Penguin-added item rests on one of these, it cites the S-number.*

| # | Source | Publisher | Relied on for |
| :---- | :---- | :---- | :---- |
| S-1 | HEDIS FAQ Directory — ncqa.org/hedis/faq | NCQA | Hybrid method conventions; treatment of a sampled member with no supporting documentation (A-15, 2.11) |
| S-2 | HEDIS Measures and Technical Resources — ncqa.org/hedis/measures | NCQA | Measure structure and reporting method; certification of measure calculation (A-15, X-7, X-11) |
| S-3 | HEDIS MY 2026: What's New, What's Changed, What's Retired — ncqa.org/blog | NCQA | Measurement-year framing and MY2026 measure changes (A-12, OQ-1) |
| S-4 | NCQA's Proposed Timeline for Retiring and Replacing HEDIS Hybrid Measures — ncqa.org/blog | NCQA | Direction of travel for hybrid measures; context for the sampling and rate boundaries (X-6, X-7) |
| S-5 | Changes to HEDIS reporting, hybrid measures, and year-round MRR review — bluecrossnc.com | Blue Cross NC | Corroborating payer-side account of hybrid chart-review practice (X-6, X-8) |

*Each of these was consulted, not quoted. None is a substitute for the NCQA specifications, and no requirement in this document is traced to an S-number alone — every S-reference sits beside a customer-document citation or an explicit Penguin-added flag.*

---

## 12. Carried inconsistencies — for the next pass

These were identified during the 3.7 edit and are not yet resolved.

| # | Item |
| :---- | :---- |
| 1 | The baseline references NCQA MY2027 value sets while A-12 pins MY2025 and MY2026 (2.7, §6.2) |
| 2 | Three MY2026 reference artifacts have no MY2025 counterpart — see §6.2 and OQ-8 |
| 3 | REF-02 carries no measurement year |
| 4 | X-6 is Penguin-added and is not among the customer's stated exclusions |
| 5 | CC-1.4 (retrieval status) is absent while CC-1.5 still follows CC-1.3. Either add the retrieval-status requirement or renumber the series |
| 6 | The MRSS expansion used by Horizon is not defined in NCQA's public specifications — confirm their usage |
| 7 | SSO / identity integration is not addressed anywhere. X-13 excludes system interfaces; whether that includes authentication is unstated |
| 8 | Penguin's internal Gaps in Care measure catalog maps LSC to "Lung Cancer Screening"; HEDIS LSC is Lead Screening in Children (per REF-07). Fix wherever that catalog feeds the baseline |
| 9 | Requirement 1.1 says the system does not collect from fax, mail, portal, MFT or shared drive, which restates X-1. Acceptable duplication, but confirm it is intentional |
| 10 | §A.2 also lists exclusions that §7 does not carry: gap report generation and distribution, case assignment and workflow routing, document standardization or restructuring, guaranteed complete data capture, real-time or near-real-time integration, predictive or prescriptive analytics, and use beyond Quality Management scope. Decide which belong in §7 |
| 11 | Document-quality thresholds are unmeasurable until "standard document" is defined. Raised as a risk with a calibration action in §2.4 and tracked as OQ-12. Open until the calibration is scheduled and the denominator agreed |
