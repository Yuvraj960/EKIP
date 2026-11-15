# data/sample_docs/ — Demo Document Corpus

This folder contains the demo engineering documents indexed by EKIP.

## Indexed Corpus Files

1. `authentication_guide.md` — OAuth2 flows (PKCE, client credentials, refresh tokens) and token specifications.
2. `deployment_runbook.md` — Canary deployment steps, database rollback procedures, and health checks.
3. `incident_response.md` — Incident classification (SEV-1/2/3), escalation protocols, and blameless post-mortem methodology.
4. `api_reference.md` — System REST endpoints, schemas, error codes, and rate limits.

## Ground Truth Testing

These documents serve as verifiable ground truth for the evaluation benchmark in `data/evals/`:
- **Answerable**: Queries directly documented (e.g., token lifetimes, canary thresholds) return citations and `SUFFICIENT` evidence status.
- **Ambiguous**: Partially documented queries return `PARTIAL` evidence status.
- **Unanswerable**: Unrelated technical or general queries return `INSUFFICIENT` evidence status with zero hallucination.
