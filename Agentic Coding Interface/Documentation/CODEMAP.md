# Code map

## Architecture overview

The terminal entry point gathers file/header/section settings and delegates to a UI-independent application service. Shared parsing produces a Dataset snapshot. Four pure section modules return structured dictionaries containing counts, original values, locations and typed numerical findings. Text formatters consume those results; export is explicit and separate. The same service can support a future visual interface without parsing report text. An optional Streamlit visual interface now runs on a loopback-only local server; terminal usage stays independent of visual dependencies.

Terminal -> application -> section analysis -> structured results -> text formatter -> safe export. Terminal navigation and prompts live in terminal_input/terminal_sections; analysis never imports these or text_reports. Processing still loads the CSV into memory and preserves source bytes. Interactive exports get numbered alternatives; explicit --sections runs refuse existing files.

## Repository structure

```text
CSV Profiler.py
visual_app.py
Start Visual Profiler.cmd
requirements-visual.txt
.streamlit/config.toml
.gitignore
README.md
Visual/
  __init__.py
  app.py
  configuration.py
  results.py
  session.py
Examples/
  demo_leads.csv
Profiling/
  __init__.py
  application.py
  csv_input.py
  profiling_common.py
  structure.py
  completeness.py
  uniqueness.py
  distribution.py
  text_reports.py
  terminal_input.py
  terminal_sections.py
Tests/
  __init__.py
  test_profiler.py
  test_uniqueness.py
  test_distribution.py
  test_terminal_input.py
  test_application.py
  test_visual.py
Input Data/
  ... input CSV files
  Outputs/
    ... generated text reports
Agentic Coding Interface/
  AGENTS.md
  Documentation/
    CODEMAP.md
    PROGRESS.md
```

Input CSVs may be elsewhere. Default reports go to project-relative Input Data/Outputs; --output overrides the destination. README provides usage; Agentic Coding Interface contains project instructions and continuity records.

## File index

- [visual_app.py](#visual_apppy): Visual entry point.
- [Visual/__init__.py](#visual__init__py): Optional visual-interface package marker.
- [Visual/app.py](#visualapppy): Local browser workflow and session orchestration.
- [Visual/configuration.py](#visualconfigurationpy): Clickable controls translated into existing backend selection contracts.
- [Visual/session.py](#visualsessionpy): Framework-independent file identity and result-validity helpers.
- [Visual/results.py](#visualresultspy): Visual presentation of structured results without recalculation.
- [Tests/test_visual.py](#teststest_visualpy): Optional visual workflow and session tests.
- [requirements-visual.txt](#requirements-visualtxt): Optional visual dependency definition.
- [Start Visual Profiler.cmd](#start-visual-profilercmd): Windows repeat-launch shortcut.
- [.streamlit/config.toml](#streamlitconfigtoml): Local server, uploader and theme configuration.
- [.gitignore](#gitignore): Exclude local environments, input files and generated artifacts from new commits.
- [Examples/demo_leads.csv](#examplesdemo_leadscsv): Public-safe synthetic demonstration fixture.

- [CSV Profiler.py](#csv-profilerpy): Terminal entry point: arguments, file/header guidance, menu and optional configuration.
- [Profiling/__init__.py](#profiling__init__py): Empty package marker.
- [Profiling/application.py](#profilingapplicationpy): UI-independent application coordination shared by current terminal and future interfaces.
- [Profiling/csv_input.py](#profilingcsv_inputpy): Shared CSV decoding and parsing, independent of interfaces.
- [Profiling/profiling_common.py](#profilingprofiling_commonpy): Shared placeholder policy and report value quoting.
- [Profiling/structure.py](#profilingstructurepy): Section 1 structured data analysis.
- [Profiling/completeness.py](#profilingcompletenesspy): Section 2 structured counters and field-count mismatches.
- [Profiling/uniqueness.py](#profilinguniquenesspy): Section 3 structured duplicate groups and fuzzy candidates.
- [Profiling/distribution.py](#profilingdistributionpy): Section 4 structured numerical analysis and group definitions.
- [Profiling/text_reports.py](#profilingtext_reportspy): Plain-text presentation of structured findings, separate from calculations.
- [Profiling/terminal_input.py](#profilingterminal_inputpy): Terminal-only input parsing and navigation.
- [Profiling/terminal_sections.py](#profilingterminal_sectionspy): Terminal-specific configuration for Sections 3 and 4.
- [Tests/__init__.py](#tests__init__py): Empty unittest package marker.
- [Tests/test_profiler.py](#teststest_profilerpy): Fifteen checks for structure, completeness, loading and terminal/export behavior.
- [Tests/test_uniqueness.py](#teststest_uniquenesspy): Eight Section 3 functional and terminal tests.
- [Tests/test_distribution.py](#teststest_distributionpy): Nine Section 4 numerical and selection tests.
- [Tests/test_terminal_input.py](#teststest_terminal_inputpy): Four shared input/navigation integration checks.
- [Tests/test_application.py](#teststest_applicationpy): Six backend/API and architectural boundary checks.

## CSV Profiler.py

**Role:** Terminal entry point: arguments, file/header guidance, menu and optional configuration.

### `main`

- **Contract / responsibilities / dependencies / behavior:** CLI arguments produce exit status 0, 1 or 130. Uses application.dataset_from_bytes/run_analysis/format_text/save_report and terminal configuration modules. Reads the selected CSV; catches navigation and expected errors. Main supplies report locations and numbering policy. Explicit --sections exits once; interactive runs return to menu. No section calculations remain here.
- **Related tests:** Terminal, CLI, path-retry, navigation, section-isolation and export tests across all suites.

## Profiling/__init__.py

**Role:** Empty package marker.

### `Package boundary`

- **Contract / responsibilities / dependencies / behavior:** Enables regular imports of Profiling modules; no executable behavior.
- **Related tests:** Import/discovery exercised by all suites.

## Profiling/application.py

**Role:** UI-independent application coordination shared by current terminal and future interfaces.

### `Dataset, load_dataset, dataset_from_bytes, run_analysis, format_text, save_report`

- **Contract / responsibilities / dependencies / behavior:** Dataset stores source path/size, detected encoding/delimiter, numbered records and detection notes. load_dataset reads a path; dataset_from_bytes decodes/parses provided bytes. run_analysis receives Dataset, header choice, selected integer sections, placeholder configuration and optional uniqueness/distribution selections; returns a section-number-keyed dictionary of structured findings. Rejects empty/unknown sections. Missing optional selections run whole-row matching only and skip distribution. format_text passes existing results to formatters without recalculation. save_report writes text exclusively, rejects source-path output, and optionally tries numbered alternatives. File/decoding/analysis errors propagate to callers; no prompts or printing.
- **Related tests:** Tests/test_application.py plus existing terminal regressions.

## Profiling/csv_input.py

**Role:** Shared CSV decoding and parsing, independent of interfaces.

### `decode_csv, parse_csv`

- **Contract / responsibilities / dependencies / behavior:** Bytes and optional encoding produce text, encoding and caveats. Text and optional delimiter produce (record number, first physical line, last physical line, original field list) records plus delimiter and notes. Uses codecs, csv and StringIO; called by application and tests. Detects BOMs, common BOM-less UTF-16 patterns, UTF-8 and Windows-1252 fallback. Sniffer failure defaults to comma with caveat. Decoding errors propagate; strict quoting errors become ValueError. No prompts or file writes.
- **Related tests:** StructureTests encoding/delimiter/multiline/malformed cases.

## Profiling/profiling_common.py

**Role:** Shared placeholder policy and report value quoting.

### `DEFAULT_PLACEHOLDERS, placeholder_markers, quoted`

- **Contract / responsibilities / dependencies / behavior:** Custom markers and standard-list toggle produce trimmed casefolded marker set; blank marker definitions are ignored. quoted returns ASCII-safe JSON text. Application and structure use marker policy; terminal/reports use quoting. No input mutation or I/O.
- **Related tests:** Structure and application placeholder tests.

## Profiling/structure.py

**Role:** Section 1 structured data analysis.

### `value_type, analyze_structure`

- **Contract / responsibilities / dependencies / behavior:** A field produces Boolean/Numeric/ISO date/ISO datetime/Text/Empty-whitespace classification. Dataset metadata, records, header decision, notes and placeholder settings produce dictionaries containing dimensions, first record, duplicate-header positions and per-column type counts, eligible values, frequencies, distinct_count and cardinality. First record defines width. Leading-zero numeric strings classify Numeric without mutation. Duplicate headers casefold but preserve whitespace. Distinct values compare original text; incomplete values are excluded. Application invokes this module; no text report or terminal dependency.
- **Related tests:** StructureTests plus ApplicationTests structured-result and architecture checks.

## Profiling/completeness.py

**Role:** Section 2 structured counters and field-count mismatches.

### `analyze_completeness`

- **Contract / responsibilities / dependencies / behavior:** Source label, records, header flag, markers and notes produce data_row_count, expected width, names, per-column existing-cell counters, dataset totals, affected-row counters and mismatch dictionaries with record/line locations and actual/expected/missing/extra counts. Headers excluded. Blank rows contain no fields or only whitespace/empty cells. Counts extra cells but never assigns absent fields to guessed column positions. Application calls it; no mutation, formatting or I/O.
- **Related tests:** CompletenessTests manually computed counters, separate categories, compact reports, structural locations; ApplicationTests.

## Profiling/uniqueness.py

**Role:** Section 3 structured duplicate groups and fuzzy candidates.

### `normalize, similarity, analyze_uniqueness`

- **Contract / responsibilities / dependencies / behavior:** Source label, records, header flag, markers and optional zero-based identifier/composite/grouping columns, methods, threshold and limit produce original whole-row groups, independent identifier exact/fuzzy findings and optional composite results. Validates columns/methods, threshold 0-100, nonnegative budget and at least two composite columns. Exact rows preserve all original cells. Identifier/key normalization strips/casefolds; incomplete identifiers/keys excluded. Fuzzy normalization collapses whitespace; equivalences stay separate. Groups constrain fuzzy comparisons only; incomplete group values excluded. Scores average forward/reverse SequenceMatcher. Entire scan skips if distinct pair budget exceeds limit; exact/equivalence findings remain. Original values and record numbers remain structured. No prompts/report formatting.
- **Related tests:** UniquenessTests exact/fuzzy/composite/group/safeguard cases; ApplicationTests.

## Profiling/distribution.py

**Role:** Section 4 structured numerical analysis and group definitions.

### `OPTIONS, GROUPS, quantile, analyze_values, analyze_distribution`

- **Contract / responsibilities / dependencies / behavior:** GROUPS maps five user-facing groups to statistic names. analyze_distribution receives selected zero-based columns/options, validates them, excludes incomplete observations, records invalid originals/record numbers and requires >=95% numeric non-incomplete values. Returns per-column applicability, counts, invalid values, selected statistics and optional arithmetic error. analyze_values uses a local 50-significant-digit Decimal context and returns numeric values, structured quartiles/modes/skewness/kurtosis/outlier candidates/histogram bins; unavailable sample variance uses None and unavailable moments carry a reason. Quantiles interpolate (n-1)*fraction. Sample moments require sufficient nonconstant data. Histogram floor(sqrt(n)) bins capped at 20, final upper edge inclusive; equal-height runs collapse for peak counting, n<30 flagged unstable, extrema frequencies retained. Decimal errors reported per column. No UI/report dependencies or data mutation.
- **Related tests:** DistributionTests known moments, precision, gates, outliers, bins and grouped selection; ApplicationTests typed numerical results.

## Profiling/text_reports.py

**Role:** Plain-text presentation of structured findings, separate from calculations.

### `format_structure, format_completeness, format_uniqueness, format_statistics, format_distribution; render_* adapters`

- **Contract / responsibilities / dependencies / behavior:** format_* receive result dictionaries and return existing text layouts (format_statistics returns lines). Completeness prints only empty/placeholder column categories and row-level structural findings. Distribution groups use matching headings. Numeric formatting retains Decimal precision. formatters never run analysis; render_* convenience adapters explicitly call one analyzer then its formatter, and statistics_text adapts analyze_values for numerical regression tests. Imports JSON/quoting and group definitions; application and report tests use it. No terminal interaction or file writes.
- **Related tests:** All prior report checks; ApplicationTests confirms formatting does not recalculate; four pre/post representative reports compared exactly during refactor.

## Profiling/terminal_input.py

**Role:** Terminal-only input parsing and navigation.

### `answer, parse_selection, select, BackToMenu, QuitSession`

- **Contract / responsibilities / dependencies / behavior:** Comma-separated 1-based selections become sorted unique zero-based indices. Allows spaces around commas, optional all and cardinality/range rules. parse_selection raises ValueError; select explains format and retries. answer raises navigation exceptions for back/q. Called by main and terminal_sections; no analysis dependencies.
- **Related tests:** TerminalInputTests syntax/navigation/recovery/CLI consistency.

## Profiling/terminal_sections.py

**Role:** Terminal-specific configuration for Sections 3 and 4.

### `prompt_options, prompt_distribution`

- **Contract / responsibilities / dependencies / behavior:** Records and header flag produce uniqueness option dictionary or column-to-statistic mapping. Prompts display labels/examples/descriptions. Identifier methods are numbered exact/fuzzy/both, grouping is optional single column, composite requires two distinct columns. Distribution selects columns then groups independently per column; groups expand into complete statistic sets. Blank skips, back/q propagate. Uses terminal_input, JSON and distribution.GROUPS; called only by terminal main. Analysis modules do not import this file.
- **Related tests:** Uniqueness/distribution prompt tests and TerminalInputTests.

## Tests/__init__.py

**Role:** Empty unittest package marker.

### `Discovery`

- **Contract / responsibilities / dependencies / behavior:** Allows recursive unittest discovery from project root; no executable behavior.
- **Related tests:** python -m unittest -v.

## Tests/test_profiler.py

**Role:** Fifteen checks for structure, completeness, loading and terminal/export behavior.

### `StructureTests, CompletenessTests`

- **Contract / responsibilities / dependencies / behavior:** Uses direct analyzer utilities and text_report adapters; loads root entry script via importlib for integration. Temporary fixtures are removed; tests source protection, numbered reports and project-relative output location.
- **Related tests:** This is the Sections 1-2/regression suite.

## Tests/test_uniqueness.py

**Role:** Eight Section 3 functional and terminal tests.

### `UniquenessTests`

- **Contract / responsibilities / dependencies / behavior:** Uses structured matching utilities, text-report adapters, terminal configuration and loaded main. Tests comparisons, grouping, pair safeguards, defaults/CLI overrides and source preservation; temporary fixtures cleaned up.
- **Related tests:** This is the Section 3 suite.

## Tests/test_distribution.py

**Role:** Nine Section 4 numerical and selection tests.

### `DistributionTests`

- **Contract / responsibilities / dependencies / behavior:** Uses statistics_text/report adapters to retain numerical/output regressions and terminal_sections for group selection. Known values, Decimal precision, small/constant samples, invalid observations, outlier rules, histograms and group isolation are exercised. Temporary fixtures cleaned up.
- **Related tests:** This is the Section 4 suite.

## Tests/test_terminal_input.py

**Role:** Four shared input/navigation integration checks.

### `TerminalInputTests`

- **Contract / responsibilities / dependencies / behavior:** Verifies selection syntax, specific validation, back/q behavior, interactive file retry and normalized CLI section selection using mocks and temporary files.
- **Related tests:** This is the shared terminal suite.

## Tests/test_application.py

**Role:** Six backend/API and architectural boundary checks.

### `ApplicationTests`

- **Contract / responsibilities / dependencies / behavior:** Invokes the shared application without input/print, verifies typed findings and unchanged datasets, optional-selection defaults, structured numerical edge cases, formatting without recalculation, export safety and forbidden interface dependencies in analysis modules. Temporary fixtures cleaned up.
- **Related tests:** This is the backend integration suite; all suites total 42 tests.

<!--
## Agent documentation rules

These rules govern how this file is populated and maintained. **Do not treat this section as a codebase activity log.**

### File-by-file documentation

- Give **each indexed file one H2 section**, titled with its exact relative path (for example, `## \`src/lib/leads/service.ts\``).
- Start each file section with its **Role**: why the file exists and what responsibility it owns. Briefly identify its key connections to other files when useful.
- Within each file, use **H3 headings for meaningful chunks of code**: functions, components, classes, or cohesive responsibility groups. Use H4 only when genuinely needed to explain a subsection.
- For each meaningful chunk, document:
  - **Use case / responsibility:** What it accomplishes and why it exists.
  - **Dependencies:** The modules, services, data, or external systems it relies on, where relevant.
  - **Used by:** The callers, components, routes, or workflows that rely on it, where identifiable.
  - **Related tests:** Relevant test file(s) and the behavior they cover; say *Not found* if none exist rather than inventing tests.
  - **Behavior / side effects:** Important steps, state changes, database/network actions, or non-obvious logic when useful for understanding.
- For **functions and methods**, additionally document their **contract**:
  - **Purpose:** What the function promises to do.
  - **Inputs:** Parameters, significant data requirements, and assumptions.
  - **Outputs:** Return values, types, or observable results, including asynchronous results if applicable.
  - **Errors:** Relevant thrown/rejected errors, validation failures, or failure outcomes. Distinguish explicit handling from errors that may propagate.
- Keep explanations focused on **meaningful logical sections**, not every line or trivial helper. Avoid copying code verbatim, duplicating obvious names, or describing implementation details that are easily read in the source. For a very small file, one concise chunk may be enough.

### Selective, automatic maintenance

- **When writing or changing code, evaluate the documentation in the same change.** Update affected CODEMAP sections immediately when a change alters the architecture, repository layout, file responsibilities, meaningful logic, contracts, dependencies, usage, or tests.
- **Make targeted edits.** Revise only affected file/chunk sections and the corresponding sections of this documentation when necessary. Do **not** regenerate or rewrite the entire CODEMAP for routine changes.
- **Do not document insignificant edits** such as formatting, simple renaming of local variables, or small internal refactors that do not change the documented meaning or behavior.
- When a file or documented chunk is **created, deleted, renamed, or moved**, update its index entry, heading, links, and relevant dependencies/callers. Remove stale descriptions. 
- **Verify against the actual source and tests.** Never invent files, functions, callers, behavior, or test coverage. Do not claim a test passed unless it was run. Verify Markdown heading links/anchors after edits.
- Keep descriptions **accurate, concise, and useful to someone unfamiliar with the codebase**. This document explains the current implementation; it is **not** a changelog, task diary, or exhaustive line-by-line commentary.

### Example format (illustrative only)

Replace the placeholders with facts verified from the real codebase. Do not keep example sections for files that do not exist.

```md
## `src/lib/leads/service.ts`

**Role:** Applies lead-creation rules independently of HTTP and database code.

### `createLead(input)`
- **Use case / responsibility:** Validate and create a lead.
- **Dependencies:** `repository.ts` for data lookup and persistence.
- **Used by:** `src/app/api/leads/route.ts`.
- **Related tests:** `tests/lead-service.test.ts` (validation and duplicates).
- **Behavior / side effects:** Normalizes email and saves a record.
- **Contract:**
  - **Purpose:** Create a valid, nonduplicate lead.
  - **Inputs:** `input` with required lead details.
  - **Outputs:** Saved lead record.
  - **Errors:** Invalid input or duplicate email.
```
-->

## visual_app.py

**Role:** Visual entry point.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Imports Visual.app.main and runs it under Streamlit; start with python -m streamlit run visual_app.py. No calculations.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Visual/__init__.py

**Role:** Optional visual-interface package marker.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** No executable behavior. Visual dependencies are not imported by the backend or terminal entry point.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Visual/app.py

**Role:** Local browser workflow and session orchestration.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** main builds upload/review/configure/run/results stages. Real Streamlit uploader supplies bytes to application.dataset_from_bytes. A fingerprint of file contents/name and parser overrides controls parsed-data reuse; changed files clear configuration/results. Header confirmation and Continue gate analysis controls. Changing parsing settings clears incompatible column selections. Only the Run button calls application.run_analysis; format_text supplies report downloads. Result signatures include parsing/header/request settings; outdated results/downloads are hidden. Expected parsing and analysis errors are shown inline. No source edits or report writes occur. Streamlit and shared application APIs are dependencies. Uses Visual configuration/session/results; visual_app calls main.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Visual/configuration.py

**Role:** Clickable controls translated into existing backend selection contracts.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** column_labels provides indexed labels even for duplicate/empty headers. configure takes Dataset/header choice and returns backend keyword arguments plus validation errors. Sections start unselected; optional identifiers/methods/grouping/composite keys and per-column distribution GROUPS are explicit. Advanced settings expose standard/custom placeholders and fuzzy defaults. Single-column composite keys and missing identifier methods disable Run. No analysis occurs. Depends on Streamlit, group definitions, marker constants.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Visual/session.py

**Role:** Framework-independent file identity and result-validity helpers.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** file_identity hashes filename and contents; fingerprint canonicalizes configuration to a SHA-256 signature. reset_file_state clears file-dependent parse/config/result keys when identity changes, retaining uploader state. results_current checks signature plus stored result presence. Uses hashlib/json; app calls helpers. No file/network I/O.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Visual/results.py

**Role:** Visual presentation of structured results without recalculation.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** show_results dispatches result tabs to section renderers. table limits display to 50 findings per page and shows every result on selectable pages. Structure displays counts/types/frequencies; completeness keeps empties/placeholders separate and structural findings at row level; uniqueness distinguishes exact/equivalence/fuzzy/composite results and skipped budgets. Distribution renders selected groups, unavailable statistics and invalid-value locations. Histogram uses returned bin boundaries/counts with Altair; chart coordinates are approximate floats and nonfinite chart values are skipped. Decimal displays shorten long numbers while text download keeps full precision. Uses Streamlit, optional transitive pandas/Altair, and group definitions; no backend calls.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Tests/test_visual.py

**Role:** Optional visual workflow and session tests.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** One framework-independent session test and four Streamlit AppTest workflows use the real file uploader. Tests cover no automatic analysis, backend/report parity across all sections, opt-in uniqueness/distribution, numeric applicability, composite validation, stale results, file replacement, parser changes and malformed uploads. Streamlit workflows skip when the optional dependency is absent; terminal tests remain runnable. No browser driver or external service required.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## requirements-visual.txt

**Role:** Optional visual dependency definition.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Pins Streamlit 1.67.0, the verified version. Terminal usage requires no visual dependency installation. pip resolves Streamlit transitive dependencies in a project virtual environment.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Start Visual Profiler.cmd

**Role:** Windows repeat-launch shortcut.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Changes to the project directory, checks for .venv Python and starts Streamlit with loopback binding and telemetry disabled. Missing setup or startup failure leaves a readable terminal message. No automatic installs.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## .streamlit/config.toml

**Role:** Local server, uploader and theme configuration.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Binds server to 127.0.0.1, disables usage telemetry, sets 50 MB uploader limit and light/teal theme. Launcher supplies explicit loopback/telemetry flags as well. Processing remains in memory.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## .gitignore

**Role:** Exclude local environments, input files and generated artifacts from new commits.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Ignores .venv, caches, secrets, logs, normal Input Data CSVs/Outputs and root CSVs; does not remove already tracked files. Examples/demo_leads.csv remains eligible for publication.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

## Examples/demo_leads.csv

**Role:** Public-safe synthetic demonstration fixture.

### Responsibility and contract

- **Behavior / dependencies / used by / side effects:** Contains invented example.test identities, missing values, a duplicated row and numerical salary data/outliers. No real lead data; users can load it through either interface.
- **Related tests:** Tests/test_visual.py and full terminal/backend regressions; launcher startup and initial upload screen also inspected locally.

Verification: 47 tests in the visual environment, including four real-upload Streamlit workflows; terminal-only discovery skips four optional workflows when Streamlit is absent. Windows verified; macOS/Linux setup commands are documented but untested.
