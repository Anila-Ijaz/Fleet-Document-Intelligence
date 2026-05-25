# n8n Orchestration Workflow

This folder contains the n8n workflow that ties the services into an automated
document-intake pipeline — the "process automation" layer of the project.

## What it does

```
Webhook (document arrives)
   → Extract Fields (calls the extraction service, LLM structured output)
   → Triage (calls the LangGraph agent service)
   → Route by Action:
        • escalate        → notify (high value / low confidence)
        • flag_for_review → review queue
        • auto_approve     → done, no human needed
```

This mirrors a real fleet-leasing back-office flow: most documents flow straight
through, and only the risky or ambiguous ones reach a human.

## Running it

1. Start n8n (added to `docker-compose.yml` as the `n8n` service):
   ```bash
   docker compose up n8n
   ```
2. Open http://localhost:5678
3. Import `fleet_document_intake.json` (Workflows → Import from File).
4. Activate the workflow.
5. Send a document to the webhook:
   ```bash
   curl -X POST http://localhost:5678/webhook/fleet-intake \
     -F "data=@../sample_docs/rechnung_beispiel.txt"
   ```

The service URLs in the workflow (`http://extraction:8000`, `http://agent:8000`) use
Docker network DNS, so n8n must run in the same compose network (it does).

## Why n8n

The job posting names n8n explicitly. This workflow demonstrates orchestrating
multiple AI services into a branching business process without writing glue code for
the routing — which is exactly what a low-code automation tool like n8n is for.
