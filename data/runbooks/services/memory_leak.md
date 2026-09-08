---
{"runbook_id":"RB-SVC-002","title":"Memory leak","service":"payment-api","domain":"services","scenarios":["memory_leak"],"tags":["memory","latency","workers"]}
---
# Memory leak

## Symptoms
- Memory utilization trends upward over time, followed by latency or errors.

## Thresholds and signals
- Investigate sustained memory over 85% or monotonic growth across deployments.

## Possible causes
- Retained application objects, unbounded caches, or worker lifecycle defects.

## Investigation steps
1. Compare memory growth by instance and deployment version.
2. Review cache growth and approved heap diagnostics.
3. Check for worker restarts or out-of-memory events.

## Safe immediate remediation
- Drain an unhealthy instance and restart it only with human approval.

## Long-term prevention
- Add memory trend alerts and bounded cache policies.
