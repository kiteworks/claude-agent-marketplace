# Compliance observations

How the User Account Reviewer report words its compliance mapping. Each row is
an observation about what the account review can show for the day it ran. It is
never a statement that a control is met, and never a certification or an audit
opinion. The report agent copies the first four columns, never adds a row and
never softens the "cannot show" column.

Every row carries `verified: false` until a person has checked the control title
and the citation against the primary text. Do not change a row to `true` without
that check, and do not drop the `verified` column. A title marked "needs
primary-source check" has not been compared with the primary text at all.

| Framework | Control | Title | This report observes | It cannot show | Source | verified |
| --- | --- | --- | --- | --- | --- | --- |
| SOX | ITGC user access review (needs primary-source check) | Periodic review of user access to in-scope systems | the tenant accounts, review candidates by type and the HR reconciliation as of the reference date, with a blank reviewer attestation page | that the Kiteworks tenant is in scope, that the review is performed at the required frequency, or that a reviewer completed it | <https://pcaobus.org/oversight/standards/auditing-standards/details/AS2201> | false |
| SOC 2 | CC6.2 | Registration and authorization of new users (paraphrase; needs primary-source check) | internal and external accounts, accounts never signed in, and accounts missing from the HR list | how access was requested or approved, or whether credentials were issued only after authorization | <https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services> | false |
| SOC 2 | CC6.3 | Authorization, modification and removal of access (paraphrase; needs primary-source check) | dormant, locked, suspended and mismatched accounts, and a proposal of changes for re-check | whether access is modified or removed on time, or whether the proposal was acted on | <https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services> | false |
| ISO 27001:2022 | A.5.18 | Access rights | account state, profile distribution and review candidates as of the reference date | the process for provisioning, review and removal of access rights, or the owner approvals | <https://www.iso.org/standard/82875.html> | false |
| NIST 800-53 | AC-2 | Account management | accounts by type, state and profile, and accounts with no matching HR row | account creation approvals, account monitoring outside this review, or the roles of account managers | <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final> | false |
| NIST 800-53 | AC-2(3) | Disable accounts | accounts inactive beyond the dormancy threshold and accounts that are locked or suspended | whether accounts were disabled within the organization-defined period | <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final> | false |
| CMMC | AC.L2-3.1.1 | Authorized access control | accounts, external accounts and admin-role accounts the connector returned | that every account belongs to an authorized user, process or device | <https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final> <https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2.pdf> | false |
| CMMC | PS.L2-3.9.2 | Personnel actions | accounts that remain active where the HR list shows the person as inactive | that HR actions are initiated or completed, or that the HR list is complete | <https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final> <https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2.pdf> | false |
| HIPAA | 164.308(a)(3)(ii)(C) | Termination procedures | accounts still active where the HR list shows the person as inactive | that termination procedures exist or are followed, or which accounts reach ePHI | <https://www.ecfr.gov/current/title-45/section-164.308> | false |
| PCI DSS v4.0.1 | 8.2.6 | Inactive user accounts are removed or disabled within 90 days | accounts inactive beyond the dormancy threshold used for this run | whether the threshold equals 90 days, which accounts are in the cardholder data environment, or whether accounts were removed | <https://www.pcisecuritystandards.org/document_library/> | false |
| DORA | Art. 9 (needs primary-source check) | Protection and prevention | account hygiene observations such as dormant, locked and external accounts | the ICT risk management framework, access policies, or whether the entity is in scope | <https://eur-lex.europa.eu/eli/reg/2022/2554/oj> | false |
