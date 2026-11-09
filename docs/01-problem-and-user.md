# 01. Problem and user

## The problem

I spend about two days per technology tower updating our lifecycle report. I take the latest ServiceNow export and match it by hand against the previous spreadsheet. Then I look up end-of-life and end-of-support dates on vendor websites one at a time, and decide which assets to manage, renew or retire. Duplicate serial numbers and reused hostnames need extra checks every time.

Three of our nine towers have never been done because there isn't enough time. I'm the only person who can run the full process today, so when I'm out, the reporting stops.

Still to validate: the two-day figure is my estimate, not a measured number. The tower counts also need checking, because the earlier document review found totals that don't agree.

## Who is involved

| Role | Person | Why they care | Status |
|---|---|---|---|
| Primary operator / design partner | ITAM team (TechOps). Owns the EOL/EOS reference sheet and pulls the tower extracts. | Every refresh goes through the ITAM team by hand. Network, storage and database never got done. | Confirmed for Sun 25-Oct, 10:10 AM PT. |
| Backup operator | CMDB extract owner. Sends the CMDB extracts. | Same workflow, upstream side. | Use only if the ITAM team can't do it. |
| Sponsor / report consumer | Infrastructure leadership | Gaps in the report make it hard to spot unsupported tech and plan upgrades before something breaks. | Doesn't do the refresh. Don't treat as the operator. |

The operator has to be someone other than me. If the tool only works when I run it, it hasn't fixed the "only one person can do this" problem.

## The job

Given a raw CMDB export and last period's TLM sheet, produce a finished lifecycle workbook for one tower. Every row needs EOL/EOS dates, a Manage/Renew/Retire call, and the reason behind each filled-in value.
