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

    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)

    @app.route("/")
    def home():
        return "Hello World!"

    @app.route("/path/<page_name>")
    def other_page(page_name):
        return page_name

    @app.route("/to/exclude")
    def exclude():
        return "Exclude me!"

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


def print_response(response):
    print("\nresponse.data:\n")
    for line in response.data.split(b"\n"):
        print(line.decode())


# ==============================================================================
# Tests


def test_app():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Hello World!" in response.data

    response = client.get("/path/whatever")
    assert response.status_code == 200
    assert b"whatever" in response.data


def test_metrics_endpoint_availability():
    app = create_app()
    FlaskInstrumentator(app).instrument()
    client = app.test_client()

    response = client.get("/")

    response = client.get("/metrics")
    print_response(response)

    assert response.status_code == 200
    assert METRIC.encode() in response.data


# ------------------------------------------------------------------------------
# Test status code


def test_grouped_status_codes():
    app = create_app()
    FlaskInstrumentator(app).instrument()
    client = app.test_client()

    client.get("/does_not_exist")  # -> Should be ignored.
    client.get("/does_not_exist")  # -> Should be ignored.
    client.post("/")  # -> 405 -> 4xx
    client.post("/")  # -> 405 -> 4xx
    client.get("/")  # -> 200 -> 2xx

    response = client.get("/metrics")
    print_response(response)

    assert b'"2xx"' in response.data
    assert b'"4xx"' in response.data
    assert b'"405"' not in response.data


def test_ungrouped_status_codes():
    app = create_app()
    FlaskInstrumentator(app=app, group_status_codes=False).instrument()
    client = app.test_client()

    client.get("/does_not_exist")  # -> Should be ignored.
    client.get("/does_not_exist")  # -> Should be ignored.
    client.post("/")  # -> 405
    client.post("/")  # -> 405
    client.get("/")  # -> 200

    response = client.get("/metrics")
    print_response(response)

    assert b'"2xx"' not in response.data
    assert b'"200"' in response.data
    assert b'"4xx"' not in response.data
    assert b'"405"' in response.data


# ------------------------------------------------------------------------------
# Test label names


def test_default_label_names():
    app = create_app()
    instrumentator = FlaskInstrumentator(app)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/")

    response = client.get("/metrics")
    print_response(response)

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

    response = client.get("/metrics")
    print_response(response)

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
    instrumentator = FlaskInstrumentator(app)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/ignored")
    client.get("/ignored")
    client.get("/")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="/ignored"' not in response.data
    assert b'handler="/"' in response.data


def test_exclude_paths():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, excluded_paths=["/to/exclude"])
    instrumentator.instrument()
    client = app.test_client()

    client.get("/")
    client.get("/to/exclude")
    client.get("/to/exclude")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="/"' in response.data
    assert b'handler="/to/exclude"' not in response.data


# ------------------------------------------------------------------------------
# Test identifiers.


def test_id_url_rule():
    app = create_app()
    instrumentator = FlaskInstrumentator(app)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/")
    client.get("/path/3feewfewfew")
    client.get("/path/fefefew")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="/"' in response.data
    assert b'handler="/path/<page_name>"' in response.data
    assert b"3feewfewfew" not in response.data


def test_id_path():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, identifier="path")
    instrumentator.instrument()
    client = app.test_client()

    client.get("/")
    client.get("/path/3feewfewfew")
    client.get("/path/fefefew")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="/"' in response.data
    assert b'handler="/path/<page_name>"' not in response.data
    assert b"3feewfewfew" in response.data
    assert b"fefefew" in response.data


# ------------------------------------------------------------------------------
# Test ignore_non_handlers


def test_not_ignore_non_handlers_url_rule():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="None"' in response.data
    assert b'handler="/dwdqdwqdwqdwq"' not in response.data


def test_not_ignore_non_handlers_path():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, identifier="path")
    instrumentator.instrument()
    client = app.test_client()

    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="None"' not in response.data
    assert b'handler="/dwdqdwqdwqdwq"' in response.data


def test_ignore_non_handlers_url_rule():
    app = create_app()
    instrumentator = FlaskInstrumentator(app=app, ignore_without_handler=True)
    instrumentator.instrument()
    client = app.test_client()

    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")
    client.get("/dwdqdwqdwqdwq")

    response = client.get("/metrics")
    print_response(response)

    assert b'handler="None"' not in response.data
    assert b'handler="/dwdqdwqdwqdwq"' not in response.data
