# Prometheus Flask Instrumentator

[![PyPI version](https://badge.fury.io/py/prometheus-flask-instrumentator.svg)](https://pypi.python.org/pypi/prometheus-flask-instrumentator/)
[![Maintenance](https://img.shields.io/badge/maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)
[![downloads](https://img.shields.io/pypi/dm/prometheus-flask-instrumentator)](https://pypi.org/project/prometheus-flask-instrumentator/)

[![release](https://github.com/trallnag/prometheus-flask-instrumentator/workflows/release/badge.svg)](https://github.com/trallnag/prometheus-flask-instrumentator)
[![test branches](https://github.com/trallnag/prometheus-flask-instrumentator/workflows/test%20branches/badge.svg)](https://github.com/trallnag/prometheus-flask-instrumentator)
[![codecov](https://codecov.io/gh/trallnag/prometheus-flask-instrumentator/branch/master/graph/badge.svg)](https://codecov.io/gh/trallnag/prometheus-flask-instrumentator)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Small package to instrument your Flask app transparently. Install with:

    pip install prometheus-flask-instrumentator

## Fast Track

```python
from prometheus_flask_instrumentator import FlaskInstrumentator
FlaskInstrumentator(flask_app).instrument()
```

**Important: This does not expose the `/metrics` endpoint.** You will have to 
do that manually. The reason for this is that there are a multitude of 
approaches depending on specific details like running the Flask app in a 
pre-fork server like Gunicorn etc. See below for an example on how to do that 
or refer to the repository of the official Prometheus client for Python.

The API is instrumented with a single metric:

`http_request_duration_seconds{handler, method, status}`

With the time series included in this metric you can get everything from total 
requests to the average latency. Here are distinct features of this 
metric, all of them can be **configured and deactivated** if you wish:

* Status codes are grouped into `2xx`, `3xx` and so on. This reduces 
    cardinality. 
* Requests without a matching template are grouped into the handler `none`.
* If exceptions occur during request processing and no status code was returned 
    it will default to a `500` server error.
* By default, methods (`GET`, `POST`, etc.) are ignored.

## Prerequesites

You can also check the `pyproject.toml` for detailed requirements.

* `python = "^3.6"` (tested with 3.6 and 3.8)
* `fastapi = "^1"` (tested with 1.1.2)
* `prometheus-client = "^0.8.0"` (tested with 0.8.0)

Metrics endpoint exposition not included. `metrics` must be made available by 
other means for example by adding an endpoint manually (see examples) or 
relying on `start_http_server()` provided by the prometheus client library.

## Example with all parameters

```python
from prometheus_flask_instrumentator import FlaskInstrumentator

FlaskInstrumentator(
    app=flask_app,
    should_group_status_codes=False,
    should_ignore_untemplated=False,
    should_group_untemplated=False,
    should_ignore_method=False,
    excluded_handlers=[
        "admin",  # Unanchored regex.
        "^/secret/.*$"],  # Full regex example.  
    buckets=(1, 2, 3, 4,),
    label_names=("method", "handler", "status",)
).instrument()
```

## Exposing metric endpoint

Here is one way to do it:

```python
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

@app.route("/metrics")
@FlaskInstrumentator.do_not_track()
def metrics():
    data = generate_latest(REGISTRY)
    headers = {
        'Content-Type': CONTENT_TYPE_LATEST,
        'Content-Length': str(len(data))}
    return data, 200, headers
```

## Development

Developing and building this package on a local machine requires 
[Python Poetry](https://python-poetry.org/). I recommend to run Poetry in 
tandem with [Pyenv](https://github.com/pyenv/pyenv). Once the repository is 
cloned, run `poetry install` and `poetry shell`. From here you may start the 
IDE of your choice.

For formatting, the [black formatter](https://github.com/psf/black) is used.
Run `black .` in the repository to reformat source files. It will respect
the black configuration in the `pyproject.toml`.
