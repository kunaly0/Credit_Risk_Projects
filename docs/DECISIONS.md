# Decision Log — Credit Risk Portfolio

Append-only record of non-obvious decisions, with rationale and date.

**Conventions**
- Never edit a past entry. To change a decision, write a new entry marked
  `SUPERSEDES D-0XX`.
- Every entry records: what was decided, what alternatives were considered,
  why this option won, and what would trigger a revisit.
- Mistakes, incidents, and control failures are logged here too. A decision
  log with no errors in it is not a decision log.

---

### D-001 | 2026-08-20 | Vintage selection: 2005, 2006, 2007, 2008, 2012, 2017

**Context:** Freddie Mac Single Family Loan Performance covers 1999–present.
Full history is not required; regime coverage is.

**Decision:** Six vintages, selected to span four distinct credit regimes —
bubble-era underwriting (2005–2007), crisis (2008), post-crisis tightening
(2012), benign (2017).

**Alternatives considered:**
- *All available years* — large ETL and query cost, no additional regime
  information, materially slower iteration.
- *Adding 2009–2011* — near-duplicates of 2008 and 2012 in underwriting
  regime. New rows, no new story.
- *Pre-2005 vintages* — genuinely a fifth regime, but the dataset appears to
  include 15- and 20-year fixed-rate product only from 1 Jan 2005 onward.
  Comparing a 2002 cohort to a 2012 cohort would confound product-mix change
  with credit risk. **Unverified — confirm in the User Guide before revisiting.**

**Rationale:** Regime coverage over raw volume. More data is not more signal.

**Revisit if:** OOT validation shows insufficient recent data, or User Guide
disproves the pre-2005 product-mix concern.

---

### D-002 | 2026-08-21 | Develop on sample, validate on standard

**Decision:** Use Freddie Mac sample files for all development and iteration;
run the finished pipeline against the standard files for final validation.

**Measured basis:** Sample ≈ 300 MB compressed across six vintages; standard
≈ 8.2 GB. Ratio ≈ 27×.

**Rationale:** S11 (WoE binning) will run hundreds of iterations. Iteration
speed is the binding constraint during development, not data volume.

**OPEN ITEM — must close in S01:** The sampling methodology is not yet
verified. Unknown whether the sample is a simple random draw per vintage,
what the sampling rate is, and whether the default rate is preserved.
A sample whose selection mechanism cannot be described cannot be defended.

**Revisit if:** Sample proves non-representative on default rate or key
covariate distributions.

---

### D-003 | 2026-08-21 | Provenance controls on the raw data layer

**Decision:** SHA-256 checksum recorded for every source archive at
acquisition. Raw layer immutable — archives are never modified, extracted in
place, or deleted. All extraction and transformation occurs in a separate
working layer.

**Implementation:**
- `D:\Datasets\Raw\<source>\` — archives as received, plus
  `docs\provenance\` holding the checksum CSV
- `D:\Datasets\Working\<source>\` — extracted files
- Checksum CSVs also committed to `docs/provenance/` in the repo, so they are
  timestamped and tamper-evident under version control

**Provenance quality differs by source:**
- *Freddie Mac* — vendor-published, institutional distribution channel,
  official User Guide and file layout obtained. Strong provenance.
- *LendingClub* — obtained via Kaggle mirror, not from the originator
  (LendingClub ceased publishing this data). Source URL: **[FILL IN]**
  Downloaded 2026-08-21. Archive was named `archive (1).zip` by the browser
  and renamed to `lendingclub_accepted_rejected_2007_2018.zip`; hash verified
  unchanged after rename. **Third-party provenance — any accompanying data
  dictionary is community-maintained and must be validated against the actual
  data in S01, not trusted.**

**Rationale:** A hash proves a file has not changed since acquisition. It does
not prove what was acquired. Provenance requires source *and* integrity.

---

### D-004 | 2026-08-21 | RISK (OPEN): Power BI Service refresh against non-Azure PostgreSQL

**Issue:** Community and vendor evidence indicates Power BI Service requires
an on-premises data gateway to run a scheduled refresh against PostgreSQL,
regardless of whether the database is cloud-hosted. Power BI classifies
sources by whether a first-party cloud connector exists, not by physical
location. Neon is therefore treated as a generic PostgreSQL endpoint.
Personal-mode gateway is additionally reported not to work with PostgreSQL
validation, implying the full standard gateway is required.

**Impact:** Threatens the mandatory Project 1 live-artifact requirement —
a Power BI dashboard published to Service, connected to the Project 0
PostgreSQL database, on a scheduled monthly refresh.

**Status:** OPEN. To be tested empirically on S00 Day 3 rather than accepted
from documentation.

**Fallback ladder, preferred order:**
- **A.** Azure Database for PostgreSQL — inside the Microsoft ecosystem,
  likely gateway-free. Cost: card required, free tier time-limited.
- **B.** Standard on-premises gateway on local machine, pointed at Neon.
  Cost: refresh only runs when the laptop is on.
- **C.** Monitoring script writes an aggregate extract to OneDrive/SharePoint;
  Power BI refreshes from that. Cost: deviates from the "not flat files"
  requirement — would need explicit documentation as a deviation.
- **D.** Streamlit becomes the live dashboard; Power BI remains Desktop-only
  with screenshots. Cost: loses the Power BI Service artifact entirely.

---

### D-005 | 2026-08-21 | INCIDENT: FRED API key exposed

**What happened:** FRED API key pasted into a chat window during setup.

**Severity assessment:** Low. The key is read-only, grants access only to
public economic time series available without an account, carries no billing
relationship, and reaches no other system. Realistic worst case is rate-limit
consumption.

**Action taken:** Regeneration attempted; no regeneration option located in
the FRED account interface. Exposure accepted and monitored.

**Control change:** No credential of any kind — key, token, password, or
connection string — is pasted anywhere outside `.env`. This applies
especially to the Neon connection string created on Day 2, which contains
username, password, host and database in a single line.

**Note for future reference:** In a professional environment the correct
response to credential exposure is to report it, not to self-assess severity.
The person who exposed a credential is the worst-placed person to judge how
serious it was.

---

### D-006 | 2026-08-21 | CONTROL FAILURE: pre-commit hooks never operational

**Found:** `pre-commit` and `detect-secrets` were installed as Python packages
and recorded in the environment notes as configured. In fact
`.pre-commit-config.yaml` did not exist and the git hook had never been
installed. Every commit made to this repository prior to today ran with
**no secret scanning whatsoever.**

**How it surfaced:** A commit produced no hook output. Silence was noticed and
investigated rather than assumed to mean "passed."

**Root cause:** Package installation mistaken for control implementation.
Three distinct steps were required — install the package, write the config,
install the git hook — and only the first was done.

**Impact:** Low in practice. A baseline scan confirmed no credentials had been
committed. Would have been severe had `.env` been created before detection —
`.env` containing the Neon connection string is scheduled for Day 2.

**Remediation:** Config written covering trailing-whitespace, end-of-file,
YAML/TOML validation, merge-conflict detection, private-key detection,
large-file blocking (5 MB ceiling), black, ruff, and detect-secrets with a
reviewed baseline. Hook installed and verified by forced run across all files.

**Secondary issue during remediation:** The baseline file was initially
unreadable because PowerShell 5.1's `>` redirect writes UTF-16 while
`detect-secrets` expects UTF-8 JSON. Regenerated via `cmd /c` to bypass
PowerShell's re-encoding. **Carry into S03:** text encoding must be an
explicit parameter in the ETL loader, not an inherited default. The Freddie
Mac files are Windows-encoded pipe-delimited text and will fail silently on
mismatch — typically as a BOM fused to the first column name, producing
zero-row joins against SQL that is otherwise correct.

**Lesson:** Verify that controls *operate*. Do not infer operation from
installation. A control believed to be working but not working is more
dangerous than no control, because it removes vigilance without providing
protection.

### D-007 | 2026-08-22 | FAILED: Microsoft 365 Business Basic trial — tenant unusable

**Objective:** Obtain a `.onmicrosoft.com` work account. Power BI Service does
not accept personal accounts (Gmail/Outlook.com), so a work identity was
required to satisfy the Project 1 live-artifact requirement.

**What was attempted:** Microsoft 365 Business Basic one-month trial,
India region, signed up with Panchkula address and personal PAN.

**Obstacles encountered, in order:**

1. **GSTIN/PAN requirement.** Field read "Tax ID or PAN registration number";
   personal PAN was accepted. Not a blocker in this instance, but Microsoft
   support threads (Feb 2026) indicate GSTIN is now mandatory for India-region
   Business-level tenants including trials, and that PAN alone was sufficient
   only until recently. Route is fragile.
2. **Billing terms materially worse than assumed.** Trial converts to a
   **12-month subscription billed annually at ~$84 (~₹7,300) in a single
   charge**, not a monthly rollover. Original plan assumed one month of
   exposure if cancellation was missed.
3. **Payment declined** — insufficient balance at RBI e-mandate registration.
   No charge was made.
4. **Region defaulted to United States** on the payment page with no option to
   change, despite an Indian address entered at signup. Tenant country is
   permanent and determines currency, tax treatment and available offers.
5. **Tenant provisioned but inaccessible.** Microsoft Fabric free signup
   reported success and issued `KunalYadav@kunalriskanalytics.onmicrosoft.com`.
   Sign-in to `app.powerbi.com` entered an infinite redirect loop. Power BI
   Desktop returned an error and, separately, **"access to the tenant is
   denied."** Persisted after one hour, across incognito sessions and direct
   URL entry, ruling out propagation delay and session conflict.

**Assessment:** Half-provisioned tenant, likely region-mismatched (Indian
address, US-defaulted billing, no active subscription). Further sign-in
attempts discontinued — a documented case exists of this configuration being
suspended by Microsoft's fraud systems.

**Outcome:** No work identity obtained. No money spent. Route closed.

**Alternatives considered and rejected:**
- *Custom domain + Power BI self-service signup* (~₹900/yr) — routes into the
  same Microsoft signup machinery that produced a broken tenant; unproven,
  and not worth purchasing on an unverified assumption.
- *Microsoft support escalation* — free but slow; India phone support reported
  as non-functional in the same threads.
- *Non-India region signup* — **rejected on integrity grounds.** Requires
  declaring a false country of residence. Not acceptable for a portfolio
  supporting applications to regulated financial services roles.

**Recoverable:** Yes. On joining an employer, a work account exists on day one
and an existing `.pbix` can be published to Service in an afternoon. Deferred,
not abandoned.

---

### D-008 | 2026-08-22 | Streamlit adopted as primary live artifact
**SUPERSEDES the Power BI Service component of D-004**

**Decision:** The mandatory Project 1 live-artifact requirement will be met by
a publicly deployed Streamlit application reading from cloud PostgreSQL
(Neon), rather than a Power BI report published to Power BI Service.

**Trigger:** D-007. No work identity obtainable as an individual in India.

**Consequential effect — D-004 is closed by this decision.** The open risk
that Power BI Service requires an on-premises data gateway for scheduled
refresh against non-Azure PostgreSQL no longer applies. Streamlit connects to
Postgres directly via a Python driver: no gateway, no first-party connector
dependency, no scheduled-refresh restrictions. Two open infrastructure risks
are resolved by one change, on a stack fully under my control.

**What is retained:**
- **Power BI Desktop** (free, no account) for all dashboard development —
  fact/dimension modelling, relationships, DAX measures, executive KPI design,
  drill-through pages. The full skill set is exercised; only publishing is lost.
- **Automated monthly PSI/CSI monitoring** (S18) is unaffected — it was always
  a scheduled Python script writing to a Postgres monitoring table. Streamlit
  reads that table instead of Power BI Service.

**What is lost:** A Power BI Service artifact, which is instantly recognisable
to some recruiters and occasionally named explicitly in job specifications.

**What is gained:** A deployed application with a FastAPI service behind it —
arguably a stronger signal for Model Risk Manager roles than a configured BI
tool, since it demonstrates shipping a service rather than operating a product.

**Deviation from original instructions, acknowledged:** The stretch-goal cut
order (CI → Docker → Streamlit → FastAPI, Power BI Service never cut) assumed
Power BI Service was achievable. It is not, for reasons outside my control.
Streamlit moves from optional stretch goal to primary live artifact. Same
technology, different role in the architecture.

**Interview position:** Report built in Power BI Desktop; live monitoring layer
deployed as a public Streamlit app calling a FastAPI service, reading cloud
Postgres, because Power BI Service required an organisational tenant not
available to an individual in this jurisdiction.

**Revisit if:** A work identity becomes available (employment, or a verified
alternative signup route). Power BI Service publishing then becomes an
afternoon's work on an existing `.pbix`.

---

### D-009 | 2026-08-22 | S00 plan revision — Day 3 repurposed

**Change:** Day 3 was "Power BI Desktop → Neon → publish to Service →
configure scheduled refresh." It is now a **Streamlit deployment smoke test**:
deploy a trivial public Streamlit app reading one table from Neon.

**Rationale unchanged:** Prove the live-artifact deployment path works before
building anything on top of it. Different technology, identical discipline.

**Day 1 status:** Closed with a negative result. Not abandoned — the negative
result is the deliverable, and it was obtained in August with three months of
runway rather than in November against a deadline. This is what S00 exists for.

**Unaffected:** Day 2 (Neon, `.env`, detect-secrets verification) and Day 5
(`COPY` load timing) proceed as planned. FastAPI and Streamlit remain S23–S24
(November); Docker and CI remain December overflow. Nothing to install today.

### D-010 | 2026-08-22 | Environment audit — documented packages not installed
**Found:** `python-dotenv`, `seaborn`, `optbinning`, `imbalanced-learn`,
`jupyterlab`, `ipykernel` recorded as installed but absent. Third instance
this week of documentation describing intent rather than verified state
(see D-006).
**Remediation:** Installed; `requirements.txt` regenerated from `pip freeze`
so the manifest reflects actual environment with pinned versions.
**Lesson:** Verify state, don't trust records of intent.

### D-011 | 2026-08-23 | Measured: Neon write throughput ~1,335 rows/sec
**Measurement:** 10,000-row COPY to Neon completed in 7.49s. Includes
probable cold-start (free-tier auto-suspend). Local Postgres expected
50–200k rows/sec.
**Implication:** Bulk loading Freddie Mac to Neon is not viable — tens of
millions of rows would take hours. Confirms the two-database architecture:
local Postgres as development warehouse, Neon as serving layer holding only
scored outputs, monitoring tables and dashboard aggregates.
**Revisit if:** Serving-layer tables exceed ~500k rows.
