# Incident Response Framework

## Overview
This document defines how engineering and operations teams classify, escalate, mitigate, and conduct post-mortems for operational incidents affecting EKIP services.

## Severity Levels & SLOs
Incidents are categorized into four severity tiers based on customer impact and service degradation:

- **SEV-1 (Critical Outage)**: Core user-facing functionality completely unavailable for >50% of users. Data loss or security breach detected.
  - Initial Response SLO: 5 minutes.
  - Update Frequency: Every 15 minutes.
  - Escalation: On-call lead, VP of Engineering, Incident Commander paged automatically via PagerDuty.
- **SEV-2 (Major Degradation)**: Significant latency increase (>2x p99 baseline), partial service disruption, or degradation of non-critical features.
  - Initial Response SLO: 15 minutes.
  - Update Frequency: Every 30 minutes.
  - Escalation: Primary and secondary on-call engineers paged.
- **SEV-3 (Minor Disruption)**: Isolated bug affecting a small subset (<5%) of users or internal administrative tools. No customer data loss.
  - Initial Response SLO: 2 hours during business hours.
  - Update Frequency: Daily or on resolution.
- **SEV-4 (Low Impact)**: Minor cosmetic issue, non-critical background task failure, or documentation discrepancy. Handled as a standard backlog ticket.

## Incident Escalation Workflow
When an alert fires or an anomaly is detected:
1. **Acknowledge Alert**: On-call engineer acknowledges the PagerDuty page within the response SLO.
2. **Open Incident Channel**: Run Slack shortcut `/incident start` to create `#incident-YYYYMMDD-<name>` and spin up a Zoom bridge.
3. **Assign Roles**:
   - **Incident Commander (IC)**: Drives overall triage, coordinates tasks, controls communication flow.
   - **Operations Lead**: Runs investigative diagnostics, reviews logs and metrics in Datadog/Grafana.
   - **Communications Lead**: Posts updates to status page `status.ekip.internal` and internal stakeholders.
4. **Triage & Mitigate**: Prioritize restoring service health over finding root cause (e.g. restart pods, scale replicas, rollback release, toggle feature flags).

## Post-Mortem & Blameless Review
For all SEV-1 and SEV-2 incidents, a blameless post-mortem must be conducted within 3 business days:
1. Construct a chronological timeline of events leading up to and during the incident.
2. Identify contributing factors using the "5 Whys" methodology without assigning individual blame.
3. Define concrete action items (preventative fixes, alerting improvements, runbook updates) with assigned owners and Jira ticket IDs.
4. Archive finalized post-mortem in the engineering knowledge base under `/incidents/postmortems/`.
