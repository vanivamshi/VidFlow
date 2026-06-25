from prometheus_client import Counter, Histogram, make_asgi_app

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "endpoint"],
)


def setup_metrics(app, service_name: str):
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    return service_name
