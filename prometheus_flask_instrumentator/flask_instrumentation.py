from typing import Tuple

from prometheus_client import Histogram
from flask import Flask, request
from timeit import default_timer
from functools import wraps
import re


class FlaskInstrumentator:
    def __init__(
        self,
        app: Flask,
        should_group_status_codes: bool = True,
        should_ignore_untemplated: bool = False,
        should_group_untemplated: bool = True,
        should_ignore_method: bool = True,
        excluded_handlers: list = ["/metrics"],
        buckets: tuple = Histogram.DEFAULT_BUCKETS,
        label_names: tuple = ("method", "handler", "status",),
    ):
        """
        :param app: Flask application used.

        :param should_group_status_codes: Groups all status codes into `1xx`, `2xx` 
            and so on.

        :param should_ignore_untemplated: Should a request to a non-existing handler
            be ignored or not? By default False.

        :param should_group_untemplated: Should requests without a matching 
            template be grouped to handler None? Defaults to True.

        :param should_ignore_method: Should methods (GET, POST, etc.) be ignored? 
            If True, the label value will always be "ignored". Defaults to True.

        :param excluded_handlers: This list of strings will be regex. compiled. 
            Matched patterns will not be recorded. Defaults to ["/metrics"].

        :param buckets: Override default buckets. Defaults to Prometheus 
            histogram default.
        
        :param label_names: Sets the labelnames of the metric. `x[0]` -> `POST`, 
            `PUT` etc. `x[1]` -> `/getorder`, `/login` etc. `x[2]` -> `500`.         
        """

        self.app = app

        self.should_group_status_codes = should_group_status_codes
        self.should_ignore_untemplated = should_ignore_untemplated
        self.should_group_untemplated = should_group_untemplated
        self.should_ignore_method = should_ignore_method

        if excluded_handlers:
            self.excluded_handlers = [re.compile(path) for path in excluded_handlers]
        else:
            self.excluded_handlers = []

        if buckets[-1] == float("inf"):
            self.buckets = buckets
        else:
            self.buckets = buckets + (float("inf"),)

        self.label_names = label_names

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
            
            request._custom_start_time = default_timer()

        @self.app.after_request
        def act_after_request(response):
            if self.shall_be_ignored(request):
                return response

            total_time = max(default_timer() - request._custom_start_time, 0)

            histogram.labels(
                *self.create_label_tuple(
                    request.method,
                    request.url_rule,
                    request.path,
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
                    request.method, request.url_rule, request.path, "500"
                )
            ).observe(total_time)

    def create_label_tuple(
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

        return (method, handler, code,)

    def shall_be_ignored(self, request) -> bool:
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
