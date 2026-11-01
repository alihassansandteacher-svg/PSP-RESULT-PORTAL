# Project audit and verification — 29 October 2026

## Scope and priorities

Inspected the application, seven CSV files, template, JavaScript, stylesheet, dependency list, editor settings, and archive structure before implementation. The archive contained a machine-specific Windows `.venv` and thousands of installed dependency/cache files; these are reproducible environment files and are excluded from the deliverable. All application data files are retained byte-for-byte.

Priorities were: (1) reliable and safe record lookup, (2) preserving records and subject/PDF consistency, (3) responsive and accessible redesign, (4) deployable configuration and regression checks.

## Findings and implemented changes

| Finding | Resolution |
| --- | --- |
| Search depended on implicit global `event`, including Enter-key calls | Explicit form submit listener and controlled loading state |
| CSV values interpolated into `innerHTML` | Text-only DOM rendering; PDF text escaped before paragraph parsing |
| Zero marks evaluated as falsy and shown as absent | Zero, absent (`A`), and unprovided marks handled separately |
| Lookup/PDF used repeated normalization code and inconsistent state | Shared backend lookup; frontend PDF requests use the displayed record |
| Unknown/empty classes hardcoded as ready | API-backed class availability and publication labels |
| Relative CSV paths failed outside project directory | Paths anchored to application directory; configurable private data directory |
| Ambiguous identifiers silently selected first record | HTTP 409 on duplicate matches; no guessed student identity |
| Public stats returned full class student directory | Endpoint disabled by default; optional aggregates only |
| Missing ReportLab fallback still called undefined classes | PDF dependency explicitly required; removed misleading fallback |
| Repeated browser PDF libraries, never-ending polling and external imagery | One server PDF implementation; local assets and system fonts |
| Fixed-width layout and obstructive onboarding overlay | Single-page responsive search with persistent class selection |
| Missing labels, image alternatives, keyboard focus and feedback | Semantic form, skip link, focus styles, live status, table headings, native disclosure |
| Popup print flow and contradictory hidden ancestors | Same-page print stylesheet; no popup dependency |
| Debug server enabled by default; obsolete environment bundled | Debug off, Gunicorn/Procfile, clean requirements and Git ignores |
| Cacheable personal result responses and no content restrictions | No-store API/PDF responses, CSP, frame denial, no-sniff, no-referrer and noindex |
| Core PDF fonts rendered inconsistently in QA | Embedded DejaVu fonts with their license; rendered sample visually checked |

Flask remains appropriate for this small CSV-backed service. Pandas was removed in favor of Python's CSV module, eliminating NumPy/Pandas installation overhead. Subject definitions are shared by the JSON result and PDF paths. School/team identity, session, search modes, marks, grades, downloads, and printing are retained. Unavailable external portraits are replaced with designed initials; no stock staff identities are fabricated.

## Source data requiring school correction

There are 281 supplied student rows. Of these, 21 have blank or nonnumeric GR identifiers and are excluded from lookup. The original rows remain in the CSV files.

| File | CSV row numbers (header is row 1) | Issue |
| --- | --- | --- |
| `class_7.csv` | 15, 16, 17, 33, 34, 58, 77 | GR is `A` |
| `class_8.csv` | 14, 33, 50, 65 | GR is `A` |
| `class_8.csv` | 49, 60 | Duplicate numeric GR `1032`; both lookups blocked pending correction |
| `class_9.csv` | 13, 14, 29, 30, 42, 60, 61 | Blank GR |
| `class_10.csv` | 36, 37 | Blank GR |
| `class_11.csv` | 45 | Nonnumeric GR |
| `class_6.csv`, `class_12.csv` | No student rows | Results not published in supplied data |

Totals, percentages and grades remain authoritative CSV values. Subject maxima, grading thresholds and examination policy were not supplied, so recalculating academic results would be unjustified.

## Verified results

- Runtime requirements installed successfully on Python 3.12.
- Nine backend regression tests passed: home/assets, normalization, zero/absent marks, invalid/missing/duplicate records, cross-class search, publication flags, stats privacy/empty averages, security headers, and PDF response generation.
- Full supplied numeric-GR dataset checked: 258 successful result responses and 258 successful PDF generations; two ambiguous records returned HTTP 409 as expected.
- All seven delivered CSVs compared byte-for-byte with the original ZIP and matched.
- JavaScript syntax (`node --check`) and Python compilation passed.
- Two-worker Gunicorn started successfully; real HTTP checks passed for health, home, CSS and class metadata.
- Firefox browser regression suite passed: Enter-key submit, class-specific/all-class lookup, escaped malicious markup, zero/absent rendering, PDF download filename, print invocation, print visibility, duplicate/missing results and network error recovery. No JavaScript runtime errors were observed.
- No horizontal page overflow at widths 320, 390, 768 and 1440 pixels, both before and after displaying a result.
- Desktop and mobile screenshots and a synthetic A4 PDF were visually inspected. PDF uses embedded fonts and readable table rows.

The hosted execution environment required `MOZ_DISABLE_CONTENT_SANDBOX=1 MOZ_DISABLE_RDD_SANDBOX=1` for Firefox automation. This was a test-environment setting, not a web application setting. Chromium's browser download failed in the environment, so Chromium, Safari, physical devices and actual printer dialogs were not verified. Print invocation and CSS visibility were verified without completing an OS print dialog.

## Remaining deployment boundaries

No live host or domain was configured or deployed. HTTPS, hosting-edge authentication/request limits, persistent private file storage and actual school register corrections require school/hosting configuration. This portal still uses GR knowledge for lookup; it does not implement student passwords, roles, SSO or authorization. Student CSVs are included in the private deliverable but Git-ignored to prevent accidental public source publication. The new safeguards do not make a GR identifier a secure authentication credential.

Data changes require worker restart. The UI uses the existing 2025–26 session, not an invented multi-year dataset. The portal has no admin editing interface because none existed and no staff authentication or editing requirements were provided. This is a source-code delivery, not a claim of a completed security penetration test, dependency advisory audit, load test or cross-browser certification.
