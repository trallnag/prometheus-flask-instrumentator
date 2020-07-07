# Prometheus Flask Instrumentator

![Version](https://img.shields.io/github/v/release/trallnag/prometheus-flask-instrumentator?label=Release)

Small package to instrument your Flask app transparently. Install with:

    pip install prometheus-flask-instrumentator

## Prerequesites

Metrics endpoint exposition not included. `metrics` must be made available by 
other means for example by adding an endpoint manually (see examples) or 
relying on `start_http_server()` provided by the prometheus client library.

## Usage

The following code excerpt instruments the Flask app. But it **does not** 
create and expose any kind of `/metrics` endpoint. This has to be handled 
elsewhere. The reason for this is that there are a multitude of approaches 
depending on specific details like running the Flask app in a pre-fork server 
like Gunicorn etc.

The `instrument()` method shall only be called once during run-time, else an 
error will be thrown.

**Minimal example:**

```python
from prometheus_flask_instrumentator import FlaskInstrumentator

FlaskInstrumentator(flask_app).instrument()
```

**Example with all possible parameters:**

```python
from prometheus_flask_instrumentator import FlaskInstrumentator

FlaskInstrumentator(
    app=flask_app,
    excluded_paths=[
        "admin",  # Unanchored regex.
        "^/secret/.*$"],  # Full regex example.  
    buckets=(1, 2, 3, 4,),
    identifier="url_rule",
    ignore_without_handler=True,
    group_status_codes=False,
    label_names=("method", "handler", "status",)
).instrument()
```

**Adding rule to Flask app for metric exposition:**

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

