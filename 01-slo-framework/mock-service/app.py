import random
import time
from fastapi import FastAPI, Response
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)

app = FastAPI(title="Mock LLM Gateway")

# -- Metrics --
# Raw sensors. Prometheus scrapes these every 15 seconds.

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    # Buckets tuned for a mix of fast and slow endpoints.
    # Anything over 5s is a problem.
    buckets=[.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)


# -- Endpoints --

@app.get("/fast")
def fast_endpoint():
    """Healthy. Quick. The happy path."""
    start = time.time()
    time.sleep(random.uniform(0.01, 0.05))
    duration = time.time() - start
    REQUEST_DURATION.labels(method="GET", endpoint="/fast").observe(duration)
    REQUEST_COUNT.labels(method="GET", endpoint="/fast", status="200").inc()
    return {"status": "ok", "latency_ms": round(duration * 1000, 1)}


@app.get("/slow")
def slow_endpoint():
    """Succeeds but takes its time. Like an expensive LLM inference call."""
    start = time.time()
    time.sleep(random.uniform(1.0, 3.0))
    duration = time.time() - start
    REQUEST_DURATION.labels(method="GET", endpoint="/slow").observe(duration)
    REQUEST_COUNT.labels(method="GET", endpoint="/slow", status="200").inc()
    return {"status": "ok", "latency_ms": round(duration * 1000, 1)}


@app.get("/flaky")
def flaky_endpoint():
    """The troublemaker. Fails ~15% of the time. This is the one that
    burns through your error budget and wakes someone up at 3am."""
    start = time.time()
    time.sleep(random.uniform(0.05, 0.2))
    duration = time.time() - start

    # 15% chance of failure. Enough to breach a 99.5% SLO.
    if random.random() < 0.30:
        REQUEST_DURATION.labels(method="GET", endpoint="/flaky").observe(duration)
        REQUEST_COUNT.labels(method="GET", endpoint="/flaky", status="500").inc()
        return Response(
            content='{"error": "internal server error"}',
            status_code=500,
            media_type="application/json"
        )

    REQUEST_DURATION.labels(method="GET", endpoint="/flaky").observe(duration)
    REQUEST_COUNT.labels(method="GET", endpoint="/flaky", status="200").inc()
    return {"status": "ok", "latency_ms": round(duration * 1000, 1)}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    """Prometheus hits this endpoint to collect everything above."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )