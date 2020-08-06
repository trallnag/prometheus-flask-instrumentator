import os

from flask import Flask
import pytest
from prometheus_client import REGISTRY

from prometheus_flask_instrumentator import Instrumentator

# ==============================================================================
# Setup

METRIC = "http_request_duration_seconds"
COUNT = f"{METRIC}_counts"
SUM = f"{METRIC}_sum"
BUCKETS = f"{METRIC}_buckets"


def create_app() -> "app":
    app = Flask(__name__)

    # Unregister all collectors.
    collectors = list(REGISTRY._collector_to_names.keys())
    print(f"before unregister collectors={collectors}")
    for collector in collectors:
        REGISTRY.unregister(collector)
    print(f"after unregister collectors={list(REGISTRY._collector_to_names.keys())}")

    # Import default collectors.
    from prometheus_client import platform_collector
    from prometheus_client import process_collector
    from prometheus_client import gc_collector

    # Re-register default collectors.
    process_collector.ProcessCollector()
    platform_collector.PlatformCollector()
    gc_collector.GCCollector()

    @app.route("/")
    def home():
        return "Hello World!"

    @app.route("/path/<page_name>")
    def other_page(page_name):
        return page_name

    @app.route("/to/exclude")
    def exclude():
        return "Exclude me!"

    @app.route("/server_error")
    def server_error():
        raise Exception("Test")
        return "will ever get here"

    @app.route("/ignored")
    @Instrumentator.do_not_track()
    def ignored():
        return "HALLO"

    return app


def get_response(client, path: str) -> "response":
    response = client.get(path)

    print(f"\nResponse  path='{path}' status='{response.status_code}':\n")
    for line in response.data.split(b"\n"):
        print(line.decode())

    return response


def assert_is_not_multiprocess(response) -> None:
    assert response.status_code == 200
    assert b"Multiprocess" not in response.data
    assert b"# HELP process_cpu_seconds_total" in response.data


def assert_request_count(
    expected: float,
    name: str = "http_request_duration_seconds_count",
    handler: str = "/",
    method: str = "GET",
    status: str = "2xx",
) -> None:
    result = REGISTRY.get_sample_value(
        name, {"handler": handler, "method": method, "status": status}
    )
    print(
        (
            f"{name} handler={handler} method={method} status={status} "
            f"result={result} expected={expected}"
        )
    )
    assert result == expected
    assert result + 1.0 != expected


# ==============================================================================
# Tests


def test_app():
    app = create_app()
    client = app.test_client()

    response = get_response(client, "/")
    assert response.status_code == 200
    assert b"Hello World!" in response.data

    response = get_response(client, "/path/whatever")
    assert response.status_code == 200
    assert b"whatever" in response.data

    response = get_response(client, "/metrics")
    assert response.status_code == 404


def test_metrics_endpoint_availability():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")

    response = get_response(client, "/metrics")
    assert_is_not_multiprocess(response)
    assert_request_count(1)
    assert METRIC.encode() in response.data


def test_parameter_existence():
    app = create_app()
    instrumentator = Instrumentator().instrument(app)

    assert hasattr(instrumentator, "should_group_status_codes")
    assert instrumentator.should_group_status_codes is True

    assert hasattr(instrumentator, "should_ignore_untemplated")
    assert instrumentator.should_ignore_untemplated is False

    assert hasattr(instrumentator, "should_group_untemplated")
    assert instrumentator.should_group_untemplated is True


def test_label_names():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")

    response = get_response(client, "/metrics")
    assert_is_not_multiprocess(response)
    assert_request_count(1)
    assert b'method="' in response.data
    assert b'handler="' in response.data
    assert b'status="' in response.data


# ------------------------------------------------------------------------------
# Test status code. should_group_status_codes.


def test_grouped_status_codes():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    client.post("/")  # -> 405 -> 4xx
    client.post("/")  # -> 405 -> 4xx
    client.get("/")  # -> 200 -> 2xx
    client.get("/")  # -> 200 -> 2xx
    client.get("/")  # -> 200 -> 2xx

    response = get_response(client, "/metrics")
    assert_is_not_multiprocess(response)
    assert_request_count(3)
    assert b'status="2xx"' in response.data
    assert b'status="4xx"' in response.data
    assert b'status="405"' not in response.data


def test_ungrouped_status_codes():
    app = create_app()
    Instrumentator(should_group_status_codes=False).instrument(app).expose(app)
    client = app.test_client()

    client.post("/")  # -> 405
    client.post("/")  # -> 405
    client.get("/")  # -> 200

    response = get_response(client, "/metrics")
    assert b'status="2xx"' not in response.data
    assert b'status="200"' in response.data
    assert b'status="4xx"' not in response.data
    assert b'status="405"' in response.data


# ------------------------------------------------------------------------------
# Test handler templation handling.


def test_ignore_untemplated():
    app = create_app()
    Instrumentator(should_ignore_untemplated=True).instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")  # Exists
    get_response(client, "/fefwefwe4533")  # Does not exist
    get_response(client, "/booogo")  # Does not exist

    response = get_response(client, "/metrics")
    assert b'status="4xx"' not in response.data
    assert b'status="404"' not in response.data
    assert b'status="2xx"' in response.data
    assert b'handler="/fefwefwe4533"' not in response.data
    assert b'handler="none"' not in response.data


def test_include_untemplated_dont_group():
    app = create_app()
    Instrumentator(should_group_untemplated=False).instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")  # Exists
    get_response(client, "/this_does_not_exist")

    response = get_response(client, "/metrics")
    assert b'handler="/this_does_not_exist"' in response.data
    assert b'handler="none"' not in response.data
    assert b'status="4xx"' in response.data


def test_include_untemplated_group():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")  # Exists
    get_response(client, "/this_does_not_exist")

    response = get_response(client, "/metrics")
    assert b'handler="/this_does_not_exist"' not in response.data
    assert b'handler="none"' in response.data
    assert b'status="4xx"' in response.data


# ------------------------------------------------------------------------------
# Test label names


def test_default_label_names():
    app = create_app()
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")

    for label in instrumentator.label_names:
        assert f'{label}="'.encode() in response.data

    for label in ("endpoint", "path", "status_code"):
        assert f'{label}="'.encode() not in response.data


def test_custom_label_names():
    app = create_app()
    instrumentator = Instrumentator(label_names=("a", "b", "c",))
    instrumentator.instrument(app).expose(app)
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")

    for label in (
        "a",
        "b",
        "c",
    ):
        assert f'{label}="'.encode() in response.data

    for label in (
        "method",
        "handler",
        "status",
    ):
        assert f'{label}="'.encode() not in response.data


# ------------------------------------------------------------------------------
# Test exclusion of paths


def test_do_not_track_decorator():
    app = create_app()
    instrumentator = Instrumentator(excluded_handlers=[])
    instrumentator.instrument(app).expose(app)
    client = app.test_client()

    client.get("/ignored")
    client.get("/ignored")
    client.get("/")

    response = get_response(client, "/metrics")
    assert b'handler="/ignored"' not in response.data
    assert b'handler="/"' in response.data


def test_exclude_paths():
    app = create_app()
    instrumentator = Instrumentator(excluded_handlers=["/to/exclude"])
    instrumentator.instrument(app).expose(app)
    client = app.test_client()

    client.get("/")
    client.get("/to/exclude")
    client.get("/to/exclude")

    response = get_response(client, "/metrics")
    assert b'handler="/"' in response.data
    assert b'handler="/to/exclude"' not in response.data


# ------------------------------------------------------------------------------


def test_bucket_without_inf():
    app = create_app()
    Instrumentator(buckets=(1, 2, 3,)).instrument(app).expose(app)
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")
    assert b"http_request_duration_seconds_bucket" in response.data


# ------------------------------------------------------------------------------


def test_unhandled_server_error():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/server_error")
    assert response.status_code == 500

    response = get_response(client, "/metrics")
    assert b'handler="/server_error"' in response.data
    assert b'status="5xx"' in response.data


# ------------------------------------------------------------------------------


def test_custom_endpoint():
    app = create_app()
    Instrumentator().instrument(app).expose(app, "/custom_metrics")
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")
    assert b"http_request_duration_seconds_bucket" not in response.data

    response = get_response(client, "/custom_metrics")
    assert b"http_request_duration_seconds_bucket" in response.data


# ------------------------------------------------------------------------------


def test_custom_metric_name():
    app = create_app()
    Instrumentator(metric_name="xzy").instrument(app).expose(app)
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")
    assert b"http_request_duration_seconds_bucket" not in response.data
    assert b"xzy_bucket" in response.data


# ------------------------------------------------------------------------------
# Test decimal rounding.


def calc_entropy(decimal_str: str):
    decimals = [int(x) for x in decimal_str]
    print(decimals)
    entropy = 0
    for i in range(len(decimals)):
        if i != 0:
            entropy += abs(decimals[i] - decimals[i - 1])
    return entropy


def test_entropy():
    assert calc_entropy([1, 0, 0, 4, 0]) == 9


def test_default_no_rounding():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    client.get("/")
    client.get("/")
    client.get("/")

    _ = get_response(client, "/metrics")

    result = REGISTRY.get_sample_value(
        "http_request_duration_seconds_sum",
        {"handler": "/", "method": "GET", "status": "2xx"},
    )

    assert len(str(result)) >= 10

    entropy = calc_entropy(str(result).split(".")[1][4:])

    assert entropy > 15


def test_rounding():
    app = create_app()
    Instrumentator(should_round_latency_decimals=True).instrument(
        app
    ).expose(app)
    client = app.test_client()

    client.get("/")
    client.get("/")
    client.get("/")

    _ = get_response(client, "/metrics")

    result = REGISTRY.get_sample_value(
        "http_request_duration_seconds_sum",
        {"handler": "/", "method": "GET", "status": "2xx"},
    )

    print(result)
    entropy = calc_entropy(str(result).split(".")[1][4:])

    assert entropy < 10


# ------------------------------------------------------------------------------


def is_prometheus_multiproc_set():
    if "prometheus_multiproc_dir" in os.environ:
        pmd = os.environ["prometheus_multiproc_dir"]
        if os.path.isdir(pmd):
            return True
    else:
        return False


# The environment variable MUST be set before anything regarding Prometheus is
# imported. That is why we cannot simply use `tempfile` or the fixtures
# provided by pytest. Test with:
#       mkdir -p /tmp/test_multiproc;
#       export prometheus_multiproc_dir=/tmp/test_multiproc;
#       pytest -k test_multiprocess_with_var_set;
#       rm -rf /tmp/test_multiproc;
#       unset prometheus_multiproc_dir


@pytest.mark.skipif(
    is_prometheus_multiproc_set() is False,
    reason="Environment variable must be set before starting Python process.",
)
def test_multiprocess_with_var_set():
    app = create_app()
    Instrumentator().instrument(app).expose(app)
    client = app.test_client()

    get_response(client, "/")

    response = get_response(client, "/metrics")
    assert response.status_code == 200
    assert b"Multiprocess" in response.data
    assert b"# HELP process_cpu_seconds_total" not in response.data
    assert b"http_request_duration_seconds" in response.data


@pytest.mark.skipif(
    is_prometheus_multiproc_set() is True, reason="Just test handling of env detection."
)
def test_multiprocess_with_var_not_set(monkeypatch, tmp_path):
    monkeypatch.setenv("prometheus_multiproc_dir", "DOES/NOT/EXIST")

    app = create_app()
    with pytest.raises(Exception):
        Instrumentator(buckets=(1, 2, 3,)).instrument(app).expose(app)
