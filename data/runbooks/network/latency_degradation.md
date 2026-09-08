---
{"runbook_id":"RB-NET-001","title":"API latency degradation","service":"payment-api","domain":"network","scenarios":["latency_degradation"],"tags":["latency","errors","database"]}
---
# API latency degradation

## Symptoms
- P95 API latency and HTTP errors are elevated without a single dominant resource signal.

## Thresholds and signals
- Investigate latency above 800 ms when it coincides with an elevated error rate.

## Possible causes
- Downstream dependency degradation, inefficient queries, network delays, or overload.

## Investigation steps
1. Compare latency with CPU, memory, database utilization, and request volume.
2. Identify whether failures are concentrated in one endpoint or dependency.
3. Review recent dependency and deployment changes.

## Safe immediate remediation
- Route non-critical traffic away from the affected path after approval.

## Long-term prevention
- Instrument dependency latency and define endpoint-level SLOs.
