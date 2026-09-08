---
{"runbook_id":"RB-DB-001","title":"Database connection pool exhaustion","service":"payment-api","domain":"database","scenarios":["db_pool_exhaustion"],"tags":["database","connections","latency","http-errors"]}
---
# Database connection pool exhaustion

## Symptoms
- Database connection utilization is above 90%.
- API latency and HTTP 5xx errors increase while CPU can remain normal.

## Thresholds and signals
- Investigate at 85% utilization; treat 95% or higher as critical.
- Corroborate with elevated latency, error rate, and queued requests.

## Possible causes
- Connections are leaked or not returned to the pool.
- Long-running queries retain connections.
- Pool capacity is too small for a legitimate traffic increase.

## Investigation steps
1. Inspect active, idle, and waiting database connections.
2. Identify long-running queries and the calling service instances.
3. Compare connection utilization with request volume and CPU usage.

## Safe immediate remediation
- Apply connection limits or shed non-critical traffic using an approved change.
- Restart unhealthy workers only after human approval.

## Long-term prevention
- Add pool wait-time alerts and connection lifecycle instrumentation.
- Set explicit connection timeouts and validate connection cleanup in tests.
