# Production Deployment & Rollback Runbook

## Overview
This runbook provides step-by-step procedures for deploying changes to production environments and executing emergency rollbacks. All deployments are zero-downtime rolling deployments managed by Kubernetes and Helm.

## Pre-Deployment Checklist
Before triggering a production deployment, ensure the following requirements are met:
1. All automated integration and regression tests have passed on `main` branch.
2. The pull request has at least two peer approvals, including one from code owners.
3. Database migrations (if any) have been tested in staging and verified to be backward-compatible.
4. On-call engineer has been notified in `#ops-deployments` Slack channel.
5. Deployment window is open: Tuesday through Thursday, 10:00 AM to 3:00 PM UTC. Friday deployments require Engineering VP sign-off.

## Deployment Procedure
Deployments are executed using the deployment pipeline CLI tool `ekip-deploy`:

1. **Tag Release**: Create a semantic version release tag: `git tag v1.4.2 && git push origin v1.4.2`.
2. **Trigger Build**: Run `ekip-deploy build --tag v1.4.2`. This generates the signed container images and runs vulnerability scans.
3. **Execute Canary Deployment**: Deploy 10% traffic canary pod: `ekip-deploy canary start --version v1.4.2 --weight 10`.
4. **Monitor Canary Metrics**: Monitor error rate and p99 latency for 15 minutes in Grafana dashboard `production-canary`.
5. **Promote Full Rollout**: If error rate remains below 0.1%, promote to 100%: `ekip-deploy promote --version v1.4.2`.
6. **Post-Deployment Verification**: Run synthetic health checks: `curl https://api.ekip.internal/health/deep`.

## Rollback Procedure
If p99 latency spikes above 500ms or 5xx error rate exceeds 1% during or immediately following deployment:

1. **Initiate Automated Rollback**: Execute `ekip-deploy rollback --service ekip-backend --target previous`.
2. **Verify Pod Status**: Confirm pods are transitioning to the previous stable revision: `kubectl rollout status deployment/ekip-backend -n prod`.
3. **Database Migration Rollback**: If the release included a migration, run the down-migration script: `alembic downgrade -1`.
4. **Flush Cache**: Purge Redis query cache if schema or serialization changes occurred: `redis-cli -h cache.prod FLUSHDB ASYNC`.
5. **Notify Incident Channel**: Post rollback notification and summary in `#ops-deployments` and `#incident-response`.
