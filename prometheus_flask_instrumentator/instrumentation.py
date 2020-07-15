import re
import os
from typing import Tuple
from functools import wraps
from timeit import default_timer

from prometheus_client import Histogram
from flask import Flask, request


class PrometheusFlaskInstrumentator:
    def __init__(
        self,
        should_group_status_codes: bool = True,
        should_ignore_untemplated: bool = False,
        should_group_untemplated: bool = True,
        excluded_handlers: list = ["/metrics"],
        buckets: tuple = Histogram.DEFAULT_BUCKETS,
        metric_name: str = "http_request_duration_seconds",
        label_names: tuple = ("method", "handler", "status",),
    ):
        """
        :param should_group_status_codes: Groups all status codes into `1xx`, `2xx` 
            and so on.

        :param should_ignore_untemplated: Should a request to a non-existing handler
            be ignored or not? By default False.

        :param should_group_untemplated: Should requests without a matching 
            template be grouped to handler None? Defaults to True.

        :param excluded_handlers: This list of strings will be regex. compiled. 
            Matched patterns will not be recorded. Defaults to ["/metrics"].

        :param buckets: Override default buckets. Defaults to Prometheus 
            histogram default.

        :param metric_name: Name of the latency metric. Defaults to 
            "http_request_duration_seconds".
        
        :param label_names: Sets the labelnames of the metric. `x[0]` -> `POST`, 
            `PUT` etc. `x[1]` -> `/getorder`, `/login` etc. `x[2]` -> `500`.         
        """

        self.should_group_status_codes = should_group_status_codes
        self.should_ignore_untemplated = should_ignore_untemplated
        self.should_group_untemplated = should_group_untemplated

        if excluded_handlers:
            self.excluded_handlers = [re.compile(path) for path in excluded_handlers]
        else:
            self.excluded_handlers = []

        if buckets[-1] == float("inf"):
            self.buckets = buckets
        else:
            self.buckets = buckets + (float("inf"),)

        self.metric_name = metric_name
        self.label_names = label_names

    def instrument(self, app: Flask) -> "self":
        """Performs the actual instrumentation by using Flask hooks.
        
        :param app: Flask application to be instrumented.
        :return: self.
        """

        histogram = Histogram(
            name=self.metric_name,
            documentation="Duration of HTTP requests in seconds",
            labelnames=self.label_names,
            buckets=self.buckets,
        )

        @app.before_request
        def act_before_request():
            if self._shall_be_ignored(request):
                return

            request._custom_start_time = default_timer()

        @app.after_request
        def act_after_request(response):
            if self._shall_be_ignored(request):
                return response

            total_time = max(default_timer() - request._custom_start_time, 0)

            histogram.labels(
                *self._create_label_tuple(
                    request.method,
                    request.url_rule,
                    request.path,
                    str(response.status_code),
                )
            ).observe(total_time)

            return response

        @app.teardown_request
        def act_on_teardown_request(exception=None):
            if not exception or self._shall_be_ignored(request):
                return

            total_time = max(default_timer() - request._custom_start_time, 0)

            histogram.labels(
                *self._create_label_tuple(
                    request.method, request.url_rule, request.path, "500"
                )
            ).observe(total_time)

        return self

    def expose(self, app: Flask, endpoint: str = "/metrics") -> "self":
        """Exposes Prometheus metrics by adding endpoint to the given app.

        **Important**: There are many different ways to expose metrics. This is 
        just one of them, suited for both multiprocess and singleprocess mode. 
        Refer to the Prometheus Python client documentation for more information.

        :param app: Flask app where the endpoint should be added to.
        :param endpoint: Route of the endpoint. Defaults to "/metrics".
        :param return: self.
        """

        from prometheus_client import REGISTRY, CONTENT_TYPE_LATEST, generate_latest
        from prometheus_client import multiprocess, CollectorRegistry

        if "prometheus_multiproc_dir" in os.environ:
            pmd = os.environ["prometheus_multiproc_dir"]
            if os.path.isdir(pmd):
                registry = CollectorRegistry()
                multiprocess.MultiProcessCollector(registry)
            else:
                raise ValueError(
                    f"Env var prometheus_multiproc_dir='{pmd}' not a directory."
                )
        else:
            registry = REGISTRY

        @app.route(endpoint)
        def metrics():
            data = generate_latest(registry)
            headers = {
                "Content-Type": CONTENT_TYPE_LATEST,
                "Content-Length": str(len(data)),
            }
            return data, 200, headers

    def _create_label_tuple(
        self, method: str, url_rule: str, url_path: str, code: str
    ) -> Tuple[str, str, str]:
        """Processes label values based on config."""

        if self.should_group_status_codes:
            code = code[0] + "xx"

        # 'self.should_ignore_untemplated' will always be 'False'

        if url_rule:
            handler = url_rule
        elif self.should_group_untemplated:
            handler = "none"
        else:
            handler = url_path

        return (
            method,
            handler,
            code,
        )

    def _shall_be_ignored(self, request) -> bool:
        """Decides if the request should be ignored or not.
        
        It first checks for the `_pfi_ignore` attribute to reduce CPU cycles in 
        subsequent runs.
        """

        if hasattr(request, "_pfi_ignore") and request._pfi_ignore:
            return True

        if any(p.search(request.path) for p in self.excluded_handlers):
            request._pfi_ignore = True
            return True

        if self.should_ignore_untemplated and not request.url_rule:
            request._pfi_ignore = True
            return True

        return False

    @staticmethod
    def do_not_track():
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                request._pfi_ignore = True
                return f(*args, **kwargs)

            return wrapper

        return decorator
