from flask import Flask
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from prometheus_flask_instrumentator import FlaskInstrumentator

# ==============================================================================
# Setup

METRIC = "http_request_duration_seconds"
COUNT = f"{METRIC}_counts"
SUM = f"{METRIC}_sum"
BUCKETS = f"{METRIC}_buckets"


def create_app():
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
    @FlaskInstrumentator.do_not_track()
    def ignored():
        return "HALLO"

    @app.route("/metrics")
    @FlaskInstrumentator.do_not_track()
    def metrics():
        data = generate_latest(REGISTRY)
        headers = {"Content-Type": CONTENT_TYPE_LATEST, "Content-Length": str(len(data))}
        return data, 200, headers

    return app


def get_response(client, path: str):
    response = client.get(path)

    print(f"\nResponse  path='{path}' status='{response.status_code}':\n")
    for line in response.data.split(b"\n"):
        print(line.decode())

    return response


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
    assert response.status_code == 200
    assert METRIC.encode() not in response.data


def test_metrics_endpoint_availability():
    app = create_app()
    FlaskInstrumentator(app).instrument()
    client = app.test_client()

    get_response(client, "/")

    response = get_response(client, "/metrics")
    assert response.status_code == 200
    assert METRIC.encode() in response.data


def test_parameter_existence():
    app = create_app()
    instrumentator = FlaskInstrumentator(app)

    assert hasattr(instrumentator, "should_group_status_codes")
    assert instrumentator.should_group_status_codes is True

    assert hasattr(instrumentator, "should_ignore_untemplated")
    assert instrumentator.should_ignore_untemplated is False

    assert hasattr(instrumentator, "should_group_untemplated")
    assert instrumentator.should_group_untemplated is True


def test_label_names():
    app = create_app()
    FlaskInstrumentator(app).instrument()
    client = app.test_client()

    get_response(client, "/")

    response = get_response(client, "/metrics")
    assert b'method="' in response.data
    assert b'handler="' in response.data
    assert b'status="' in response.data


# ------------------------------------------------------------------------------
# Test status code. should_group_status_codes.


def test_grouped_status_codes():
    app = create_app()
    FlaskInstrumentator(app).instrument()
    client = app.test_client()

    client.post("/")  # -> 405 -> 4xx
    client.post("/")  # -> 405 -> 4xx
    client.get("/")  # -> 200 -> 2xx

    response = get_response(client, "/metrics")
    assert b'status="2xx"' in response.data
    assert b'status="4xx"' in response.data
    assert b'status="405"' not in response.data


def test_ungrouped_status_codes():
    app = create_app()
    FlaskInstrumentator(app=app, should_group_status_codes=False).instrument()
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
    FlaskInstrumentator(app=app, should_ignore_untemplated=True).instrument()
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
    FlaskInstrumentator(app=app, should_group_untemplated=False).instrument()
    client = app.test_client()

    get_response(client, "/")  # Exists
    get_response(client, "/this_does_not_exist")

    response = get_response(client, "/metrics")
    assert b'handler="/this_does_not_exist"' in response.data
    assert b'handler="none"' not in response.data
    assert b'status="4xx"' in response.data


def test_include_untemplated_group():
    app = create_app()
    FlaskInstrumentator(app=app).instrument()
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
    instrumentator = FlaskInstrumentator(app)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")

    for label in instrumentator.label_names:
        assert f'{label}="'.encode() in response.data

    for label in ("endpoint", "path", "status_code"):
        assert f'{label}="'.encode() not in response.data


def test_custom_label_names():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, label_names=("a", "b", "c",))
    instrumentator.instrument()
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
    instrumentator = FlaskInstrumentator(app, excluded_handlers=[])
    instrumentator.instrument()
    client = app.test_client()

    client.get("/ignored")
    client.get("/ignored")
    client.get("/")

    response = get_response(client, "/metrics")
    assert b'handler="/ignored"' not in response.data
    assert b'handler="/"' in response.data


def test_exclude_paths():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, excluded_handlers=["/to/exclude"])
    instrumentator.instrument()
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
    FlaskInstrumentator(app=app, buckets=(1, 2, 3,)).instrument()
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/metrics")
    assert b"http_request_duration_seconds_bucket" in response.data


# ------------------------------------------------------------------------------


def test_unhandled_server_error():
    app = create_app()
    FlaskInstrumentator(app=app).instrument()
    client = app.test_client()

    client.get("/")

    response = get_response(client, "/server_error")
    assert response.status_code == 500

    response = get_response(client, "/metrics")
    assert b'handler="/server_error"' in response.data
    assert b'status="5xx"' in response.data
