from prometheus_client import Histogram
from flask import Flask, request
from timeit import default_timer
from functools import wraps
import re


class FlaskInstrumentator:
    def __init__(
        self,
        app: Flask,
        excluded_paths: list = None,
        buckets: tuple = Histogram.DEFAULT_BUCKETS,
        identifier: str = "url_rule",
        ignore_without_handler: bool = False,
        group_status_codes: bool = True,
        label_names: tuple = ("method", "handler", "status",),
    ):
        """
        :param app: Flask application used.

        :param excluded_paths: This list of strings will be regex. compiled. 
        Matched patterns will not be recorded.
        
        :param buckets: Override default buckets. Defaults to Prometheus 
        histogram default.

        :param identifier: Property of Flask request object used to identify a 
        request. For example `path` or `url_rule`.

        :param ignore_without_handler: Should a request to a non-existing handler
        be ignored or not? By default `/doesnotexist` -> `None`.

        :param group_status_codes: Groups all status codes into `1xx`, `2xx` 
        and so on.
        
        :param label_names: Sets the labelnames of the metric. `x[0]` -> `POST`, 
        `PUT` etc. `x[1]` -> `/getorder`, `/login` etc. `x[2]` -> `500`, `503`.         
        """

        self.app = app

        if buckets[len(buckets) - 1] == float("inf"):
            self.buckets = buckets
        else:
            self.buckets = buckets + float("inf")

        self.identifier = identifier
        self.ignore_without_handler = ignore_without_handler
        self.group_status_codes = group_status_codes
        self.label_names = label_names

        if excluded_paths:
            self.excluded_paths = [re.compile(path) for path in excluded_paths]
        else:
            self.excluded_paths = []

    def instrument(self):
        """Performs the actual instrumentation by using Flask hooks."""

        histogram = Histogram(
            name="http_request_duration_seconds",
            documentation="Duration of HTTP requests in seconds",
            labelnames=self.label_names,
            buckets=self.buckets,
        )

        @self.app.before_request
        def act_before_request():
            if self.shall_be_ignored(request):
                return

            if any(
                spattern.search(request.path) for spattern in self.excluded_paths
            ) or hasattr(request, "_custom_do_not_track"):
                request._custom_do_not_track = True
                return
            else:
                request._custom_start_time = default_timer()

        @self.app.after_request
        def act_after_request(response):
            if self.shall_be_ignored(request):
                return response

            # Record duration of request for histogram.
            total_time = max(default_timer() - request._custom_start_time, 0)

            histogram.labels(
                *self.create_label_tuple(
                    request.method,
                    getattr(request, self.identifier),
                    str(response.status_code),
                )
            ).observe(total_time)

            return response

        @self.app.teardown_request
        def act_on_teardown_request(exception=None):
            if not exception or self.shall_be_ignored(request):
                return

            total_time = max(default_timer() - request._custom_start_time, 0)

            histogram.labels(
                *self.create_label_tuple(
                    request.method, getattr(request, self.identifier), "500"
                )
            ).observe(total_time)

    def create_label_tuple(self, method: str, handler: str, code: str) -> tuple:
        if self.group_status_codes:
            code = code[0] + "xx"
        return (
            method,
            handler,
            code,
        )

    def shall_be_ignored(self, request) -> bool:
        if hasattr(request, "_custom_do_not_track"):
            return True
        if self.ignore_without_handler and not request.url_rule:
            return True
        return False

    @staticmethod
    def do_not_track():
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                request._custom_do_not_track = True
                return f(*args, **kwargs)

            return wrapper

        return decorator
