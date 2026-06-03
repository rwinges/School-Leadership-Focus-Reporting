# SCHOOL LEADERSHIP FOCUS REPORTING
*This document is entirely human-written without the assistance of AI.*

# Project Overview

This is a solution prototype for an actual data collection and reporting scenario at a large Colorado school district. The prototype is built for a fictitous entity - "Clear River Public Schools (CRPS)."

This project is meant to demonstrate competency in the following areas implemented through the Microsoft 365 stack and IBM Db2 cloud. For more details see the ***Skills Demonstrated*** section and don't hesitate to contact the developer - Ryan Winges at [ryan.winges@gmail.com](mailto:ryan.winges@gmail.com).
  - Data modeling, ETL, and analysis
  - Process modernization and automation
  - Business analysis and requirements gathering
  - API configuration
  - Communication to non-technical and technical audiences

# Business Scenario

## Background

All the schools in CRPS are divided into 10 articuluation areas. All the school principals in an articulation area report to a district-level, "Principal Supervisor." The 10 district-level supervisors, their manager, and two executive assistants comprise the School Leadership Team.

Historically the Principal Supervisors have tended to spend as much or more of their time providing *operational* and other support to their schools as they have providing *instructional* support. The district has determined that transitioning the role of the Principal Supervisor to primarily an "instructional leader" role will improve student outcomes. The district has launched an initiative to shift a significant part of the operational support burden to other teams so supervisors can prioritize instructional leadership efforts in their schools.

To track progress on this initiative, the School Leadership team has implemented a system for the Principal Supervisors to report their working hours by major focus category on a weekly basis. Every week, each supervisor reviews their prior week's report with the team manager in their one-on-one meeting. The team manager regularly reports team-level statistics to the superintendent and board of directors.

## Current Business Process

Currently the Principal Supervisorss submit their weekly hours totals to the team manager via a Microsoft Form (the district runs Microsoft 365 Business) at the end of each week. At the beginning of each week, the team's executive assistants (EAs) manually review the prior week's submissions. The EAs manually send reminder messages to Principal Supervisorss with missing submissions. They also manually generate a summary bar chart for each submission inside the form's response spreadsheet, take a screenshot of the chart and email it to the supervisor. Principal Supervisorss are restricted to receiving reporting on their own submission data only.

The EAs use the same manual process for ad hoc reporting requests from Principal Supervisorss and for regular and ad hoc reporting requests from the team manager.

## Current Technical Implementation Details

### Submission via Microsoft Form  

  - **Data Security.** The form and associated response spreadsheet live on the SharePoint site associated with the team's main Microsoft Group (associated with their main Teams team, etc.). While the Principal Supervisorss are generally not highly technical users and probably wouldn't ever stumble upon the response sheet, they all technically have access to it and could view their colleagues' data if they found the sheet.

  - **Data Integrity.** The Microsoft Form does not restrict a supervisor's submissions to un-submitted weeks and there are sometimes duplicate submissions that the EAs must check for and resolve to ensure accurate reporting.

### Reporting via Microsoft Excel, Screenshots, and Email  

  - **Static, Asynchronous Reporting.** The visuals used for reporting are generated as Pivot Charts inside the form's response spreadsheet. The Principal Supervisorss could technically generate their own summary reporting on demand relatively easily using slicers however that would give them access to the whole team's data and they should only have access to their own. Therefore, the EAs generate weekly charts for each supervisor and email screenshots of the charts to the supervisorss. Reporting is only available to the extent that the EAs are available to manually generate and distribute it.

  - **Manual Reminder Notifications.** No automated notification solution is in place to remind Principal Supervisorss to submit data for missing weeks. The EAs must manually review the submission data and send reminder notifications.

  - **Business Analysis Gap.** Currently the Principal Supervisorss do not submit their leave (time-off) data as part of their weekly submissions because they successfully argued that doing so is a significant administrative burden. All district employees record their leave-taken in a separate time and attendance system but the EAs do not have access to that system to pull leave data and incorporate it into their reporting. This undermines (arguably negates) the analytical value of all reporting because unidentified leave-taken incorrectly presents as underperformance.

# Solution Overview

This prototyped solution is a low-maintenance, highly automated, data-secure, no-extra-cost integration of Microsoft SharePoint and Microsoft Power Platform solutions.

The following two documents are simulated client-facing documentation. Some specific data values - such as literal security group IDs - have been modified from the actual working prototype values to simulated values that match the ficitious entity. Otherwise, these documents accurately describe the prototype configuration.  
  - [CRPS_Focus Reporting_System Overview.docx](https://github.com/rwinges/School-Leadership-Focus-Reporting/blob/8d77629bf35f40c79990989976256e56717a79e5/Client-facing%20Documents/CRPS_FocusReporting_SystemOverview.docx)
  - [CRPS_Focus Reporting_Technical Reference.docx](https://github.com/rwinges/School-Leadership-Focus-Reporting/blob/8d77629bf35f40c79990989976256e56717a79e5/Client-facing%20Documents/CRPS_FocusReporting_TechnicalReference.docx)

The sub-sections that follow give an overview of the solution from a project/prototype development perspective.

## Submission and Data Storage

Replacing the Microsoft Form, Principal Supervisorss submit their weekly data through an easy to use Power Apps application. The app's submission screen allows them to choose from a drop-down list of un-submitted weeks (no duplicate submissions). The app is interfaced to the district's time and attendance system and automatically pulls the user's leave data for the selected week and displays it for informational purposes.

Instead of storing submission data to a spreadsheet, the app writes submission data to a SharePoint list configured with permissions that allow all supervisorss to write data to the list and only allow them to retrieve/view their own data. If supervisorss navigate directly to the SharePoint list, they will only be able to view their own data.

## Reporting

Replacing emailed screenshots of manually-generated Excel charts, Principal Supervisorss have real-time access to a Power BI report embedded in the same app that they use to submit their data (one-stop shopping). The Power BI report pulls data from the submissions SharePoint list and the district's time and attendance system so that leave data is properly integrated into the analytics. In this prototype, the time and attendance system is simulated using an IBM Db2 cloud database accessed through a Microsoft on-premises data gateway. The report's data model is configured for automatic daily refreshes.

The Power BI report has expanded analytics representing two different valid methods of measuring the same key performance indicator (KPI): the propotion of total working hours spent on instructional leadership efforts. It gives supervisorss a year-to-day (YTD) weekly distribution of hours by category, YTD cumulative KPI trend with a highlighted target range, and year-over-year (YoY) YTD cumulative KPI trend.

The Power BI report is configured with "row level security" (RLS) that restricts supervisorss to their own data but enables the team manager and EAs to view all data. The RLS is based on security group membership, not on individual role assignment; this enables the EAs to maintain access permissions without ever touching a Power BI workspace.

## Notifications

Reminder notifications for missing submissions are automatically sent to supervisorss by a Power Automate Flow that runs daily (weekdays). The Flow runs at 12:00 PM on Mondays to allow supervisorss Monday morning to submit their hourly summary for the previous week. It runs at 8:00 AM on Tuesdays through Fridays.

## Maintenance

### User Permissions Maintenance

As the team staffing evolves, the EAs maintain the two security groups - one for team members and one for managers and EAs - by submitting an IT helpdesk ticket.

### Data maintenance

The only required data mainetnance task is an annual update of a SharePoint list that contains every reporting period date (the Saturday of the reporting week) and associated metadata (e.g. the school year it belongs to). The EAs perform this task.

If necessary, EAs can modify submission data directly on the SharePoint list e.g. to correct submission errors.

# Documentation

## [GitHub Repository](https://github.com/rwinges/School-Leadership-Focus-Reporting) Contents

 - **README.md** (this file)
 - [**Client-facing Documents**](https://github.com/rwinges/School-Leadership-Focus-Reporting/tree/8d77629bf35f40c79990989976256e56717a79e5/Client-facing%20Documents) (folder) - Business spec and technical spec documents
 - [**Data Seeting**](https://github.com/rwinges/School-Leadership-Focus-Reporting/tree/8d77629bf35f40c79990989976256e56717a79e5/Data%20Seeding) (folder) - Python scripts for generating seeded data
 - [**Power BI GIFs**](https://github.com/rwinges/School-Leadership-Focus-Reporting/tree/8d77629bf35f40c79990989976256e56717a79e5/Power%20BI%20GIFs) (folder) - GIF images displaying previews of report pages

## Video Walkthroughs

  - [Solution Overview (09:24)](https://vimeo.com/1197869734)
  - [Front-end Walkthrough (10:28)](https://vimeo.com/1197870568)
  - [Architecture Overview (06:55)](https://vimeo.com/1197871727)
  - [Data Model & Row-level Security (RLS) (04:38)](https://vimeo.com/1197871780)
  - [DAX Measures (04:02)](https://vimeo.com/1197871863)
  - [Power BI Reports Back-end (19:02)](https://vimeo.com/1197873386)

# Development Approach

## Development Methodology

Throughout the development process I had access to key individuals involved in the actual business scenario. I was able to inspect actual as-is technical artifacts and iteratively gather requirements and deliver the solution in increments following a basic agile development pattern.

## Development Environment

The prototype was developed in a sandbox Microsoft 365 Business enviornment personally maintained by the developer. Multiple user licenses are maintained to endable security testing (RLS, etc.). The IBM Db2 cloud environment used is also personally maintained by the developer for sandbox purposes.

## Use of AI

Claude (Anthropic) was leveraged as a development partner in the following ways:

  - **Chasing down technical details.** LLMs can search technical documentation and read lengthy error logs more quickly than humans.

  - **Synthetic data generation.** I wrote spec documents for Claude describing business logic constraints, target analytical patterns, and recommended logical sequence for data seeding scripts (time and attendance data and historical submission data). I also instructed Claude to use certain specific Python packages (e.g. Pandas) when writing the scripts. The time and attendance data only took two script iterations while the historical submissions data was more complex and required six iterations.

  - **Code generation.** I used Claude to write inital versions of some DAX measures in Power BI, some Power Fx property logic in Power Apps, and most Workflow Definition Language expressions in Power Automate. I reviewed all generated code and optimized where possible.

  - **Document drafting.** Throughought the development process, I instructed Claude to add various decisions to a running decision log to be included in the final documentation. I also used it to draft inital versions of the client-facing documents and an AI-prompt-optimized version of the data seeding spec document for the historical submissions script which took six iterations to get right.

Claude was not used for the following:

  - **Business scenario selection or business logic.** I chose the business scenario and defined and validated all business logic.

  - **Architecture decisions.** I designed the solution architecture and used Claude to provide technical details that would help me make certain detailed architectural/configuration decisions e.g. whether to run the SharePoint connector for the Power BI model through the on-premises data gateway even though it wasn't necessary from a security standpoint.

  - **Validation and testing.** I validated all business logic at every step. Claude ran its own set of tests internally on the data seeding scripts it generated then I ran my own suite of tests which dictated whether a script re-write was necessary. I perfomed all UX testing. For the DAX KPI measures, I developed a full validation (not spot-checking) dataset in Excel which enabled Claude to quickly identify logic errors in its DAX code.

  - **UX Design.** I made all UX design decisions.

  - **Writing this README file.** The remainder of this section ("Use of AI") is an edited Claude response to a prompt (described next). Otherwise, this README document was written entirely by the developer.

The following are Claude's summary of instances where I intervened in technical or business logic or when I rejected an AI-generated design recommendation. This is a sample - not a comprehensive list - of these types of human/AI decision points.

<details>
  <summary>
    <b>[Claude]: Technical and Business Logic Errors You Caught and Corrected</b>
  </summary>

  - **`DateTable` Week Ending Date formula producing Sundays instead of Saturdays.** The initial `WEEKDAY([Date], 2)` formula was off by one day, producing Sundays. You caught it immediately. I then compounded the error by proposing `[Date] + (6 - WEEKDAY([Date], 1))` which you correctly showed would always land on Friday, not Saturday. The correct `MOD(7 - WEEKDAY([Date], 1), 7)` formula required your intervention to arrive at.

  - **Power Apps Weekday StartOfWeek parameter (1 vs 2).** I used `Weekday(Today(), 2) (Monday=1 scheme)` in the `varCurrentWeekEnding` formula. You caught that this would produce Sunday instead of Saturday and asked me to verify. Confirmed: the correct parameter is 1 (Sunday=1 scheme).

  - **`WeekBridge` solving the double-counting problem claim.** I incorrectly claimed that `WeekBridge` solved the straddling week double-counting problem in monthly reporting. You correctly identified that `WeekBridge` has no month context of its own and cannot solve that problem — the filter reaching `Submissions` would be identical with or without `WeekBridge`. I conceded the error and corrected the explanation.

  - **`AVERAGEX` zero-hours inflation.** I proposed `AVERAGEX(VALUES(Submissions[SubmittedByEmail]), [ILRP])` for team average measures. You caught that zero-worked-hours weeks would return 0 from `[ILRP]` and those zeros would invalidly pull down the average. The `FILTER(..., [WH - Total] > 0)` wrapper was added to all four averaging measures as a result.

  - **Power Automate `Get Current Reporting Week` returning the coming Saturday instead of the last elapsed Saturday.** I proposed `addDays(startOfDay(utcNow()), sub(6, mod(add(dayOfWeek(utcNow()), 6), 7)))` which returned the coming Saturday rather than the last elapsed Saturday. You caught the business logic error — a submission shouldn't be expected for a week until that Saturday has actually arrived.

  - **Power Automate school year expression type mismatch errors.** Multiple iterations of the `Get Current School Year` expression failed with type mismatch errors (`int()` on `utcNow('M')`, `addYears()` not existing, etc.). While these were syntax/API errors rather than logic errors per se, you identified the correct direction each time and pushed through multiple failed attempts to arrive at the working solution.

  - **ILFT non-cumulative denominator wrong for multiple users.** You spotted that `[ILFT]` was returning incorrect values for multi-user selections because `SUM(TA_LeaveData[TOTAL_LEAVE_HOURS])` was aggregating all selected users' leave before subtracting from 40. The correct pattern — `SUMX(TA_LeaveData, MAX(0, 40 - TOTAL_LEAVE_HOURS))` — was your direction, iterating row by row before summing.

  </details><br>

<details>
  <summary>
    <b>[Claude]: Design/Architecture Recommendations You Rejected</b>
  </summary><br>
    
  - **Db2 connection from the Power App.** I proposed having the Power App read directly from Db2 using the Power Apps Db2 connector. You rejected it on cost grounds (Premium connector licensing) and correctly pushed for SharePoint as the read layer for the app, keeping Db2 as a Power BI-only data source.

  - **`SubmittedBy` as a SharePoint Person column.** I initially built the `Submissions` list schema with `SubmittedBy` as a Person column type. You pushed back, noting that the entire solution uses email as the user identifier and the Person column's Claims string construction was fragile. You chose plain text email — which was cleaner and more consistent with the rest of the architecture.

  - **HolidayData-only SharePoint list for the Power App.** I proposed creating a small `HolidayData` SharePoint list with just holiday hours per week to avoid the full Db2 export. You correctly pointed out that the Power App validation logic needed all leave types (PTO, sick, holiday) to enforce the 40-hour cap — not just holidays.

  - **Hard block on submissions under 40 hours (Rule 1).** I proposed blocking or warning on submissions where total hours < 40. You rejected it on business logic grounds, noting that team members should be able to self-report truthfully even if under-performing, and that compliance monitoring is a management concern, not a form concern.

  - **Child flow architecture for Power Automate.** I recommended a duplicate flow approach to accomodate varying trigger times on different days. You identified the cleaner architectural pattern (child flows), pushed for it, it hit a tooling constraint, and you made a pragmatic call to accept the duplication rather than continue fighting the tooling.

</details>

## Key Technical Decisions

  - **Incorporate external database.** Using an external (to M365) cloud database (IBM Db2) to store time and attendance data was a more realistic simulated data source than simply connecting to a file or another SharePoint list. This enables the developer to test query delegation and to avoid implementation snags like Power BI Service requiring that all data connections in a model using a data gateway must be routed through that gateway in order to enable either manual or scheduled model refreshes from within Power BI service.

  - **Service accounts and security groups.** The solution was designed to be used and maintained as self-sufficiently as possible by a non-technical team. Using a service account for back-end authenticaions (e.g. app licenses and data connections) and mail-enabled security groups for front-end app authorization and row-level-security allows the team to maintain the solution as team staffing evolves with a simple IT helpdesk ticket to update group membership - never having to venture into a Power BI workspace or the authentication settings of Power Apps or Power Automate. Note that to minimize development costs, for this prototype a dedicated service account was not used however a production implementation would.

  - **Avoid premium features.** The solution was designed to use only standard features within all of the apps to ensure that no additional costs (licensing, data storage) would be incurred for a client running on the Microsoft 365 A3 tier.

  - **Data gateway hosting.** A production deployment would host the gateway on a dedicated server or cloud VM. The prototype implementation uses a developer workstation gateway to avoid additional infrastructure costs.

## What I Would Do Differently

  - **Power BI Data model.** I would replace the `DateTable` and `WeekBridge` calculated tables with a connection to the `ReportingPeriods` SharePoint list and add calculated columns if necessary for any additional metadata needed by the model specifically. I initially defined the current `DateTable` as a proper date table anticipating using it for standard DAX time intelligence functions. The `WeekBridge` table evolved to "bridge" the gap between the daily granulatrity of `DateTable` and the weekly granularity of the fact tables. `ReportingPeriods` was initially included in the data model but it was removed given that it became redundant of `WeekBridge`. Since `WeekBridge` was calculated, it eliminated a manual data maintenance task (maintaining `ReportingPeriods`). However, the other solution components ended up needing a comprehensive list of reporting periods for their operations and I decided that the annual maintenance burden of maintaining an explicit list was a valid trade-off for avoiding the duplicative instantiation of the calculated logic in each of the apps independently (if the logic ever changed, it would require incursions into each app). By that point, `WeekBridge` was already baked into most of the Power BI measures and all of the visuals. For this prototype, I am logging this as a backlog item and confirming that it has zero functional impact on the solution.

# Skills Demonstrated

## Technical Components

  - Microsoft 365
    - Power BI (Desktop and Service)
    - Power Query
    - DAX
    - Power Apps
    - Power Fx
    - Power Automate
    - Office apps - Excel, Word
    - SharePoint
    - M365 Entra Admin
  - Python (data seeding)
  - SQL (data seeding)
  - GitHub
  - Markdown (this README)
  - VS Code

## Technical Skills

  - ETL
  - Data Modeling
  - API configuration (IBM Db2 cloud)
  - Business application integration
  - AI pair programming
  - UX Design

## Business Competencies

  - Business analysis and requirements gathering
  - Translating business requirements into technical specifications
  - Process modernization and automation
  - Communication to non-technical and technical audiences
  - Clear and comprehensive documentation
