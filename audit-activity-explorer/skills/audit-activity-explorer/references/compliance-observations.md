# Compliance observations

How the Activity Explorer report words its compliance mapping. Each row is an
observation about what the Kiteworks audit log can show for the period. It is
never a statement that a control is met, and never a certification or an audit
opinion. The report agent copies the first four columns, never adds a row and
never softens the "cannot show" column.

Every row carries `verified: false` until a person has checked the control title
and the citation against the primary text. Do not change a row to `true` without
that check, and do not drop the `verified` column.

| Framework | Control | Title | This report observes | It cannot show | Source | verified |
| --- | --- | --- | --- | --- | --- | --- |
| HIPAA | 164.312(b) | Audit controls | event counts by category and outcome over the period, as recorded by the connector | which events involve ePHI, or that the log is examined by the covered entity | <https://www.ecfr.gov/current/title-45/section-164.312> | false |
| SOC 2 | CC7.2 | System monitoring | volume spikes, failure bursts, bulk downloads and outside-hours activity flagged by explicit rules | how the organisation responds to a flag, or whether monitoring is continuous | <https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services> | false |
| ISO 27001 | A.8.15 | Logging | that the audit log records events with a time, an event name, an outcome and an account | log protection, retention or clock synchronisation | <https://www.iso.org/standard/82875.html> | false |
| ISO 27001 | A.8.16 | Monitoring activities | rule-based anomaly observations over the period | that anyone reviews the observations, or what baseline applies | <https://www.iso.org/standard/82875.html> | false |
| NIST 800-53 | AU-2 | Event logging | which event categories appear in the log and which event names were not recognised | whether the right event types are enabled in the tenant | <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final> | false |
| NIST 800-53 | AU-6 | Audit record review, analysis, and reporting | an aggregated review with anomaly rules and a previous-period comparison | that a periodic human review took place or what followed from it | <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final> | false |
| NIST 800-53 | AU-12 | Audit record generation | that the audit log records events with a time, an event name, an outcome and an account | which components generate records, or whether any events are missing | <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final> | false |
| CMMC | AU.L2-3.3.1 | System Auditing | that records exist for the period and how far back the oldest returned row reaches | retention policy, or records older than the oldest row returned | <https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final> | false |
| CMMC | AU.L2-3.3.2 | User Accountability | that rows carry an account identifier, in the person view and object history only | that every action maps to one real person, or shared account use | <https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final> | false |
| CMMC | AU.L2-3.3.5 | Audit Correlation | events grouped by category, day and rule flag in one report | correlation with sources outside the Kiteworks audit log | <https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final> | false |
| PCI DSS v4.0.1 | 10.4 | Audit logs are reviewed to identify anomalies or suspicious activity | rule-based anomaly observations over the period | whether the review frequency or scope matches the standard, or which systems hold cardholder data | <https://www.pcisecuritystandards.org/document_library/> | false |
| DORA | Art. 10 | Detection | unusual volume, failure and timing patterns in the audit log | detection of incidents outside Kiteworks, or any ICT incident classification | <https://eur-lex.europa.eu/eli/reg/2022/2554/oj> | false |
| NIS2 | Art. 21(2) | Cybersecurity risk-management measures | that activity monitoring data exists and can be summarised | whether the measures are adequate or proportionate for the entity | <https://eur-lex.europa.eu/eli/dir/2022/2555/oj> | false |
| FedRAMP | AU-6 | Audit record review, analysis, and reporting | an aggregated review with anomaly rules and a previous-period comparison | that a periodic human review took place, or the authorisation status of any system | <https://www.fedramp.gov/documents/> | false |
| NIST CSF 2.0 | DE.CM | Continuous monitoring | activity patterns for the period, read at one point in time | that monitoring is continuous or covers the whole environment | <https://www.nist.gov/cyberframework> | false |
| EU AI Act | Art. 12 | Record-keeping | events by clients identified as AI agents (client Kiteworks MCP), always shown, also when there are none | whether a system is a high-risk AI system, or the logging capability of that system itself | <https://eur-lex.europa.eu/eli/reg/2024/1689/oj> | false |
| ISO 42001 | A.6.2.8 | AI system recording of event logs (needs primary-source check) | actions by AI agents against Kiteworks as recorded in the audit log | the AI management system, its roles or its impact assessments | <https://www.iso.org/standard/81230.html> | false |
| NIST AI RMF | MEASURE | Measurement of AI risks | the number and kind of actions by AI agents and their failure rate | model quality, bias or risk evaluation | <https://www.nist.gov/itl/ai-risk-management-framework> | false |

The last three rows (EU AI Act, ISO 42001, NIST AI RMF) belong to the AI-client
section of the report and are shown with it.
