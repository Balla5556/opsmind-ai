---
{"runbook_id":"RB-SVC-001","title":"Traffic spike and overload","service":"payment-api","domain":"services","scenarios":["traffic_spike"],"tags":["traffic","network","capacity"]}
---
# Traffic spike and overload

## Symptoms
- Request volume and network traffic rise sharply; latency may follow.

## Thresholds and signals
- Investigate request volume above the service baseline and validate whether the increase is expected.

## Possible causes
- A legitimate event, abusive traffic, retry storms, or an upstream client defect.

## Investigation steps
1. Compare current volume with the baseline and client distribution.
2. Check error patterns for retry amplification.
3. Confirm whether a scheduled event explains the demand.

## Safe immediate remediation
- Apply approved rate limits or traffic shaping for non-critical traffic.

## Long-term prevention
- Define capacity plans and retry budgets for major clients.
