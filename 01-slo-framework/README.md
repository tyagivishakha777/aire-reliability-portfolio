# SLO Monitoring Framework

(I used this document [here](https://sre.google/workbook/alerting-on-slos/) to device up the thresholds for this project. It really helped me understand the math behind the standards. Must read in my opinion.)

A working SLO stack. Mock API, Prometheus, Grafana, burn-rate alerts, runbook. Everything in Docker Compose.

The mock API has three endpoints. `/fast` is the happy path. `/slow` simulates expensive queries. `/flaky` is the one that causes problems — fails about 15% of the time. Enough to breach a 99.5% SLO and burn through an error budget in hours.

## Run it

```bash
cd 01-slo-framework
docker compose up --build -d

pip install httpx
python load-generator.py 5
```

Grafana on port 3000 (admin/admin). Prometheus on 9090. The SLO dashboard is under the SLO folder. Give it two minutes and the gauges start moving.

## Architecture

```
load-generator.py ──→ mock-api (:8000)
                         │
                    /metrics
                         │
                    prometheus (:9090)
                    ├── recording rules (SLIs)
                    └── alert rules (burn rates)
                         │
                    grafana (:3000)
                    └── SLO Overview dashboard
```

## What's being measured

**Availability SLI** — fraction of requests that didn't return a 5xx. Target: 99.5%.

**Latency SLI** — fraction of requests that finished under 200ms. Target: 95%.

**Error budget** — 0.5% of requests are allowed to fail over a 30-day window. The dashboard shows how much of that budget is left. When it hits zero, you stop shipping features and fix things.

## Alerts

Two burn-rate alerts. Both use multi-window detection — a short window to catch problems fast, a long window to confirm it's not a blip. Both must fire before anyone gets paged.

**Critical (14.4x burn rate)** — budget gone in ~2 days. Page immediately.

**Warning (3x burn rate)** — budget gone in ~10 days. Ticket it. Investigate during business hours.

Single-window alerts fire on every minor spike. Useless. The dual-window approach fixed that.

## Design decisions

**Why 99.5% and not 99.9%?**
A 99.9% target on a new service leaves almost no room for deploys, experiments, or expected failures. 99.5% gives 3.6 hours of allowed downtime per month. That's a meaningful budget you can actually spend — and argue about in a meeting.

**Why recording rules?**
Dashboards that compute SLIs from raw counters on every load are expensive at scale. Recording rules pre-compute them every 30 seconds. Dashboards stay fast. Alerts stay cheap.

**Why not just use Grafana alerting?**
Prometheus alerting evaluates rules close to the data. No network hop, no dashboard dependency. If Grafana goes down, alerts still fire.

## What I took away from this

Error budgets turn "be more reliable" into a number. That number makes the conversation between engineering and product actually productive. "We have 2 hours of budget left" is concrete. "We need to be more reliable" is not.

The `/flaky` endpoint at 15% error rate burns budget at roughly 30x the sustainable rate. Even a small error percentage on a high-traffic endpoint drains it fast. I didn't fully understand that until I watched it happen on the dashboard in real time.

## What different error rates do to your budget

Three experiments. Same system, same traffic pattern. Only difference is how often /flaky fails.

For each one, I let the load generator run for about 5 minutes so the graphs have enough data. Then I Changed line 37 in app.py: "if random.random() < 0.05 or 0.15 oe 0.30"



### 5% error rate — burns at ~10x sustainable
![5% error rate](./docs/experiments/flaky-05pct.png)
Availability sits at 98.7%. Budget at -162%. Already gone. 5% doesn't sound like much. It's ten times what a 99.5% SLO allows. The error rate chart shows small, steady failures — 0.03 to 0.06 req/s. Nothing dramatic to look at. But the budget is bleeding out quietly.

### 15% error rate — burns at ~30x sustainable
![15% error rate](./docs/experiments/flaky-15pct.png)
Availability drops to 97.6%. Budget at -387%. The error rate chart gets choppier — spikes to 0.08 req/s. Deep red across the board. This is the page-someone-now zone. A full 30-day budget would be gone in hours at this rate.

### 30% error rate — burns at ~60x sustainable
![30% error rate](./docs/experiments/flaky-30pct.png)
93.5% availability. Budget at -1202%. Twelve times over. Error rate chart is sustained at 0.15–0.20 req/s. Everything is red. This isn't a flaky endpoint anymore. This is something fundamental broken.

### The interesting part
Look at the latency charts across all three. p50, p95, p99 — they barely move. The system doesn't look slow. It looks fine. The failing requests return 500s almost instantly so they don't register as a latency problem. That's the whole point of measuring availability separately from latency. Latency alone would have told you nothing was wrong.
Note: The Latency SLI gauge shows "No data" in all three — that's a dashboard config issue, not a data issue. Worth fixing but doesn't affect the availability story. I will try and fix that in the future. 