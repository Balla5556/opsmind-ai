---
{"runbook_id":"RB-INF-001","title":"CPU saturation","service":"payment-api","domain":"infrastructure","scenarios":["cpu_saturation"],"tags":["cpu","latency","http-errors"]}
---
# CPU saturation

## Symptoms
- CPU utilization exceeds 85% with increased latency and error rate.

## Thresholds and signals
- Treat sustained CPU above 90% as critical when it coincides with request failures.

## Possible causes
- Expensive request paths, an inefficient deployment, or insufficient compute capacity.

## Investigation steps
1. Confirm CPU pressure by service instance.
2. Compare CPU, request volume, latency, and recent deployments.
3. Capture approved profiling data for the busiest request paths.

## Safe immediate remediation
- Shift traffic away from unhealthy instances after approval.

## Long-term prevention
- Set CPU capacity alerts and profile high-cost endpoints.
