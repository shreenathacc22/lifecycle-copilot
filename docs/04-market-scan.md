# 04. Market scan

Research date: 24-Oct-2026. Done with web search. Product claims link to the vendor's own docs where I could find them. Anything from a forum or a third party is marked as such.

Three kinds of statement are kept apart below:

- **Sourced**: says what a source says, with the link.
- **Interview**: from a real conversation. There are none yet, because `02-interview-notes.md` is still empty.
- **Hypothesis**: my guess. It needs checking before anyone relies on it.

## What I was looking for

What our process needs, and what I checked each option against:

1. Import a CMDB inventory export
2. Map version and edition to a lifecycle date (Win 11 Pro and Enterprise have different dates for the same build)
3. Reconcile this period against last period
4. Show the evidence behind each date
5. Review exceptions
6. Human overrides that stick
7. Export to Excel in our existing layout

## Options found

### 1. Native ServiceNow (SAM Pro / HAM Pro)

Sourced:
- SAM has a Content Library that supplies software lifecycle dates. When a publisher hasn't published dates, it supplies approximated ones, and a column marks each record as approximated or confirmed. Admins can add custom lifecycles or overwrite the content ones. [Product life cycles](https://www.servicenow.com/docs/r/pyt4lF0aAin_R6wVyV414Q/Xuefm5KFhtEUiFwotNmOAw)
- There's a Software Product Lifecycle report built by a scheduled job, and a Lifecycle management dashboard that shows upcoming EOL over the next 18 months. The dashboard needs the SAM Professional plugin. [Lifecycle management dashboard](https://www.servicenow.com/docs/bundle/zurich-it-asset-management/page/product/software-asset-management2/concept/lifecycle-management-dashboard.html)
- HAM normalization fills model metadata, including end-of-life dates, from the Content Library. [HAM Advanced release notes](https://www.servicenow.com/docs/r/C17ZqvSaMwUVpMBg8Nc5sg/zRqHtb5VYrw3du8bvThs5Q). The model management view tracks GA, End of Sale, End of Support and End of Life phases. [Model management view](https://www.servicenow.com/docs/r/it-asset-management/hardware-asset-management/model-management-view.html)
- Third party (community post, Dec 2025, one user, no replies): for some models the hardware content only supplies the GA phase, and Useful Life stays empty. [Hardware Content Services](https://servicenow.com/community/ham-forum/hardware-content-services/m-p/3445217)
- Third party (community answer): the hardware model lifecycle table is restricted by ACL to App Portfolio Management licensees. [Community thread](https://www.servicenow.com/community/itsm-forum/track-end-of-life-or-end-of-support-cisco-device/td-p/2790842)
- CMDB identity matching (IRE) uses identification rules checked in priority order, for example serial plus name, then name alone. [Identification rules](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/c_IdentificationRules.html)

Hypothesis:
- This is the biggest "it might already be solved" risk. If we already license SAM Pro or HAM Pro, part of the date lookup may already be in the platform and switched off or unused. **I need to check what we actually license before building the lookup part.**
- IRE matches CIs inside the CMDB. It doesn't compare this quarter's export with last quarter's TLM spreadsheet, and it doesn't carry forward our disposition calls. So the reconciliation and carry-forward part still seems to be ours to build.
- I found nothing showing a period-over-period Manage/Renew/Retire workbook in our 6-sheet layout.

### 2. Lifecycle data providers

**Flexera Technopedia**

Sourced:
- A catalog of hardware, software, SaaS and cloud products with EOL and EOS dates. Flexera says it can identify more than 5 million products. [Technopedia](https://www.flexera.com/enterprise/products/data-platform/technopedia/)
- It maps vendor policies onto standard stages: 3 for software, 4 for hardware. Dates are kept as published, and a blank date means research isn't done yet. Data comes through an API, a user console or a published database. [Technopedia Lifecycle Standards and Process](https://community.flexera.com/s/article/ka6PL000001RSSSYA4)
- Flexera's own page says most inventory tools don't show which apps are EOL/EOS, so this often ends up kept by hand in spreadsheets. [IT asset lifecycle](https://flexera.com/solutions/it-asset-lifecycle)

Not found: pricing. I won't guess.

**endoflife.date**

Sourced:
- A free, community-run site with lifecycle dates and an API. [endoflife.date](https://www.endoflife.date)
- Third party: covers Windows, Windows Server, Office, SQL Server and Surface. [oofhours.com](https://oofhours.com/?p=4231). The WinEOL PowerShell module uses the API for Windows products. [WinEOL](https://www.powershellgallery.com/packages/WinEOL/1.2.5/Content/Public%5CGet-WinEOL.ps1)

Not confirmed: the API doc pages didn't render for me, so I haven't checked the response fields, the data license, or whether it splits Windows dates by edition. Need to check by hand.

**Microsoft, as the primary source for EUC Windows**

Sourced:
- Windows 11 Enterprise, Education and IoT Enterprise get 36 months from release. Pro, Pro Education, Pro for Workstations and Home get 24 months. [Lifecycle FAQ, Windows](https://learn.microsoft.com/en-us/lifecycle/faq/windows)
- Release health lists the dates per version. For example, 26H2 (GA 2026-09-29) ends updates 2028-10-10 for Home/Pro and 2029-10-09 for Enterprise/Education. [Windows 11 release information](https://learn.microsoft.com/en-us/windows/release-health/windows11-release-information)

Hypothesis: for the v1 tower (EUC Windows), OS dates are basically a lookup table keyed on version plus edition from two Microsoft pages. That's a small, stable rule set. It probably doesn't need an LLM for most rows.

### 3. Discovery and inventory tools (Lansweeper)

Sourced:
- Lansweeper has Windows 10 and 11 EOL audit reports that flag devices as past EOL, near EOL, or supported, and it knows the 24 vs 36 month edition split. [Windows 11 EOL audit](https://www.lansweeper.com/resources/report/operating-system/windows-11-end-of-life-audit/)
- It says it tracks warranty, EOL and EOS for hardware assets. [Asset lifecycle management](https://www.lansweeper.com/solutions/use-cases/asset-lifecycle-management/)

Hypothesis: useful if we already run it, but it's a separate inventory, not our CMDB. Adding a second source of truth would create more matching work, not less.

### 4. Hardware ship date and warranty (asset EOL)

Sourced:
- Dell TechDirect has a warranty API. It takes service tags and returns ship date and warranty info. You need an approved API key. [1Password: Dell TechDirect](https://support.1password.com/saas-manager-dell-techdirect/)
- Third party: warranty entitlements can come back empty when Dell doesn't have the invoice, even though ship date is there. [Recast: Dell warranty status woes](https://www.recastsoftware.com/resources/dell-warranty-status-woes/)
- Lenovo: I only found the public lookup page, not a documented API. [Lenovo warranty lookup](https://support.lenovo.com/lc/en/warrantylookup)

Hypothesis: this is the most realistic answer to open question 3 in `product.md` (where asset EOL comes from when the CMDB has no ship date). It depends on which vendors make up our EUC fleet. It's v2 at the earliest.

### 5. The spreadsheet workaround (what I do today)

Sourced:
- Excel Power Query's fuzzy merge defaults to a 0.80 similarity threshold, and 1.00 means exact match. [Fuzzy merge](https://learn.microsoft.com/en-us/power-query/merge-queries-fuzzy-match)

Hypothesis: this is the trap rule I1 is there to avoid. A spreadsheet user reaching for fuzzy merge on hostnames would link replaced hardware to the old record. Exact merges in Power Query would handle the easy part of matching. They don't handle "hostname only when unique in both files and serials don't conflict" without hand-built helper columns, and that's where my two days go.

## Comparison

S = sourced, H = hypothesis, ? = not found.

| Need | ServiceNow SAM/HAM | Technopedia | endoflife.date | Lansweeper | Excel by hand |
|---|---|---|---|---|---|
| CMDB import | native (S) | via Flexera One (H) | no | own scan (S) | manual |
| Version + edition dates | software yes, approximated flagged (S) | yes (S) | ? edition split | Windows yes (S) | manual lookup |
| Period-over-period reconcile | no evidence found | no | no | no | manual |
| Evidence per value | approximated vs confirmed flag (S) | published date kept (S) | sources listed (H) | ? | Remarks by hand |
| Exception review | EOL workflow request (S) | ? | no | ? | by eye |
| Sticky human override | custom lifecycles (S) | ? | no | ? | yes, fragile |
| Excel in our 6-sheet layout | no | no | no | no | yes |
| Cost | ? we may already pay | ? | free | ? | my time |

## Where a small internal tool could help

Hypotheses, to test with the ITAM team:

1. **Reconciliation and carry-forward across periods.** None of these tools compare this export to last period's TLM sheet with our rules, keep disposition calls, and list the dropped rows. That's the part I re-code every refresh.
2. **Exceptions as output.** The Dropped and Data Quality tabs (duplicate serials, reused hostnames, positional copies) aren't something any of these produce for our sheet.
3. **The output leadership already reads.** Same columns, same layout, plus a reason on every filled value.

## Where an existing tool may already solve it

1. **OS lifecycle dates.** Microsoft publishes them, and SAM Pro, Technopedia, Lansweeper and endoflife.date all have them. Lifecycle Copilot should look them up from an approved table, not research them. The LLM researcher may barely be needed for EUC Windows.
2. **Hardware model dates.** If our HAM content is populated, use it before building anything. If it's only GA phase (per the forum post), it doesn't help.

## Research tasks still open

- [ ] Check which ServiceNow ITAM licenses we have (SAM Pro? HAM Pro? App Portfolio Mgmt?) and whether lifecycle content is turned on.
- [ ] Look at the endoflife.date API by hand: Windows edition split, fields, license.
- [ ] Find out whether we have Flexera or Lansweeper anywhere in the company.
- [ ] Get the EUC fleet split by manufacturer, to see if a Dell/HP/Lenovo warranty API would cover enough of it.
- [ ] Ask the ITAM team what they already use for dates (interview Q4 and Q5).
- [ ] No pricing found for anything here. Don't put prices in the Forge.
