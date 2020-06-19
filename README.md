# Prometheus Flask Instrumentator

Simple way to instrument your Flask API with a default metric without the need for a
distinct exporter or manually instrumenting every single request method.

Uses the hooks `before_request`, `after_request` and `teardown_request` to record data.

Paths can be excluded from being tracked using regex patterns or explicitly with the
`do_not_track` annotation inside the `FlaskInstrumentator` class.

## Prerequesites

This package relies on the Prometheus Python client already set-up and ready since it uses
the default collector, registry and so on.

## Example

```python
from flask import current_app
from prometheus_flask_instrumentator import FlaskInstrumentator

flask_instrumentator = FlaskInstrumentator(
    app=current_app,
    identifier="url_rule",
    excluded_paths=[
        "swagger",
        "internal",
        "ping"
    ],
    buckets=(0, 2, 4, 8, float("inf"))
)

flask_instrumentator.instrument()
```
