import contextlib
import json
import os
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from mysite.opentelemetry_config import add_instrumentation, response_hook


class ResponseHookTests(SimpleTestCase):
    def test_query_parameters_are_recorded_on_the_span(self):
        request = RequestFactory().get("/polls/", {"page": "2", "q": "otel"})
        span = mock.Mock()

        response_hook(span, request, mock.Mock())

        span.set_attribute.assert_called_once()
        name, value = span.set_attribute.call_args.args
        self.assertEqual(name, "http.get.params")
        self.assertEqual(json.loads(value), {"page": "2", "q": "otel"})

    def test_only_the_last_value_of_a_repeated_parameter_is_recorded(self):
        """QueryDict serialises to its last value per key, multi values are dropped."""
        request = RequestFactory().get("/polls/?tag=a&tag=b")
        span = mock.Mock()

        response_hook(span, request, mock.Mock())

        _, value = span.set_attribute.call_args.args
        self.assertEqual(json.loads(value), {"tag": "b"})

    def test_request_without_query_parameters(self):
        request = RequestFactory().get("/polls/")
        span = mock.Mock()

        response_hook(span, request, mock.Mock())

        _, value = span.set_attribute.call_args.args
        self.assertEqual(json.loads(value), {})


class ApplicationTests(SimpleTestCase):
    """Smoke tests: the entry points must be importable without instrumentation."""

    def test_asgi_application(self):
        from mysite.asgi import application

        self.assertIsNotNone(application)

    def test_wsgi_application(self):
        from mysite.wsgi import application

        self.assertIsNotNone(application)


class AddInstrumentationTests(SimpleTestCase):
    """The exporter is selected by environment variables, check every branch.

    Everything that would touch global state (the tracer provider) or the
    network (the exporters) is mocked out.
    """

    def call_add_instrumentation(self, env):
        patches = {
            "provider": mock.patch("opentelemetry.sdk.trace.TracerProvider"),
            "set_tracer_provider": mock.patch("opentelemetry.trace.set_tracer_provider"),
            "django": mock.patch("opentelemetry.instrumentation.django.DjangoInstrumentor"),
            "psycopg2": mock.patch("opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor"),
            "requests": mock.patch("opentelemetry.instrumentation.requests.RequestsInstrumentor"),
            "batch": mock.patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"),
            "simple": mock.patch("opentelemetry.sdk.trace.export.SimpleSpanProcessor"),
            "cloud_exporter": mock.patch(
                "opentelemetry.exporter.cloud_trace.CloudTraceSpanExporter"
            ),
            "set_global_textmap": mock.patch("opentelemetry.propagate.set_global_textmap"),
        }
        with mock.patch.dict(os.environ, env, clear=True), contextlib.ExitStack() as stack:
            mocks = {name: stack.enter_context(p) for name, p in patches.items()}
            add_instrumentation()
        return mocks

    def test_console_exporter_is_used_when_only_trace_enabled_is_set(self):
        mocks = self.call_add_instrumentation({"TRACE_ENABLED": "1"})

        provider = mocks["provider"].return_value
        provider.add_span_processor.assert_called_once_with(mocks["simple"].return_value)
        mocks["batch"].assert_not_called()
        mocks["set_global_textmap"].assert_not_called()

    def test_cloud_trace_exporter_and_propagator_are_used(self):
        mocks = self.call_add_instrumentation({"CLOUD_TRACE_ENABLED": "1"})

        provider = mocks["provider"].return_value
        provider.add_span_processor.assert_called_once_with(mocks["batch"].return_value)
        mocks["batch"].assert_called_once_with(mocks["cloud_exporter"].return_value)
        mocks["set_global_textmap"].assert_called_once()
        mocks["simple"].assert_not_called()

    def test_instrumentors_are_always_enabled(self):
        mocks = self.call_add_instrumentation({"TRACE_ENABLED": "1"})

        mocks["django"].return_value.instrument.assert_called_once()
        mocks["psycopg2"].return_value.instrument.assert_called_once()
        mocks["requests"].return_value.instrument.assert_called_once()

    def test_no_span_processor_without_the_environment_variables(self):
        """asgi.py only calls add_instrumentation() when tracing is enabled."""
        mocks = self.call_add_instrumentation({})

        mocks["provider"].return_value.add_span_processor.assert_not_called()
