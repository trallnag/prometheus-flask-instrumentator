# Prometheus Flask Instrumentator

[![PyPI version](https://badge.fury.io/py/prometheus-flask-instrumentator.svg)](https://pypi.python.org/pypi/prometheus-flask-instrumentator/)
[![Maintenance](https://img.shields.io/badge/maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)
[![downloads](https://img.shields.io/pypi/dm/prometheus-flask-instrumentator)](https://pypi.org/project/prometheus-flask-instrumentator/)

![release](https://github.com/trallnag/prometheus-flask-instrumentator/workflows/release/badge.svg)
![test branches](https://github.com/trallnag/prometheus-flask-instrumentator/workflows/test%20branches/badge.svg)
[![codecov](https://codecov.io/gh/trallnag/prometheus-flask-instrumentator/branch/master/graph/badge.svg)](https://codecov.io/gh/trallnag/prometheus-flask-instrumentator)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Small package to instrument your Flask app transparently.

    pip install prometheus-flask-instrumentator

## Fast Track

```python
from prometheus_flask_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

With this the Flask app is instrumented and all Prometheus metrics can be 
scraped via the `/metrics` endpoint. 

The exporter includes the single metric `http_request_duration_seconds`. 
Basically everything around it can be configured and deactivated. These 
options include:

* Status codes are grouped into `2xx`, `3xx` and so on.
* Requests without a matching template are grouped into the handler `none`.
* Renaming of labels and the metric.
* Regex patterns to ignore certain routes.
* Decimal rounding of latencies.

See the *Example with all parameters* for all possible options or check 
out the documentation itself.

## Example with all parameters

```python
from prometheus_flask_instrumentator import PrometheusFlaskInstrumentator

PrometheusFlaskInstrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=False,
    should_group_untemplated=False,
    should_round_latency_decimals=True,
    excluded_handlers=[
        "admin",            # Unanchored regex.
        "^/secret/.*$"],    # Full regex example.  
    buckets=(1, 2, 3, 4,),
    metric_name="flask_http"
    label_names=("flask_method", "flask_handler", "flask_status",),
    round_latency_decimals=3,
).instrument(app).expose(app, "/prometheus_metrics")
```

It is important to notice that you don't have to use the `expose()` method if 
adding the endpoint directly to the Flask app does not suit you. There are many 
other ways to expose the metrics.

## Prerequesites

* `python = "^3.6"` (tested with 3.6 and 3.8)
* `flask = "^1"` (tested with 1.1.2)
* `prometheus-client = "^0.8.0"` (tested with 0.8.0)

## Development

Developing and building this package on a local machine requires 
[Python Poetry](https://python-poetry.org/). I recommend to run Poetry in 
tandem with [Pyenv](https://github.com/pyenv/pyenv). Once the repository is 
cloned, run `poetry install` and `poetry shell`. From here you may start the 
IDE of your choice.

For formatting, the [black formatter](https://github.com/psf/black) is used.
Run `black .` in the repository to reformat source files. It will respect
the black configuration in the `pyproject.toml`.
