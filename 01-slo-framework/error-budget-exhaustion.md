# Error Budget Exhaustion



Use this runbook when `HighErrorBurnRate_Critical` fires or the budget gauge drops below 25%. Something is eating through your allowed failures faster than it should.

## First — confirm it's real

Open Grafana → SLO Overview.

Check if the error rate is spiking across all endpoints or just one. If it's just one, that's your starting point. If it's everything, think bigger — DNS, load balancer, upstream dependency.

Check Prometheus targets page (`:9090/targets`). If scrape targets are down, you might be looking at a metrics gap, not an actual outage. Different problem.

## Find the source

Look at the "Error Rate by Endpoint" panel. The answer is usually obvious.

Now in my fake-scenario, the endpoint '/flaky' is the problem child. If it were real, I would: check what changed. New deploy? Dependency went sideways? Config change? 

If nothing changed, I would look at traffic patterns. A sudden spike in requests can push a borderline endpoint over the edge.

## How bad is it

| Burn Rate | Budget gone in | What to do |
|-----------|---------------|------------|
| > 14.4x   | ~2 days        | Page. Incident. Now. |
| > 6x      | ~5 days        | Urgent ticket. Don't wait. |
| > 3x      | ~10 days       | Standard ticket. Investigate soon. |
| > 1x      | ~30 days       | Keep an eye on it. |

## Fix it

**One bad endpoint** — disable it, rate-limit it, or route traffic away from it. Stop the bleeding first. Diagnose after.

**Bad deploy** — roll back. Don't debug in production with your budget draining.

**Dependency down** — circuit breaker. Serve degraded responses. Something is better than a 500.

**Overloaded** — scale out or shed non-critical traffic. If you can't scale, you need to drop something.

## Tell people

Post in the incidents channel. Keep it factual: what's happening, who's looking at it, what's the impact, when's the next update. No speculation. No reassurance. Just the situation.

## After

Write a postmortem within 48 hours. While it's fresh.

Ask yourself two things: should the SLO target change, and should the alert thresholds change. Sometimes the answer to both is yes. Sometimes the system is fine and the failure was a one-off. Either way, write it down.