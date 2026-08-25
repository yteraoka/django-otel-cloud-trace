"""End to end tests for the OpenTelemetry instrumentation.

Unlike the unit tests in ``mysite/tests.py`` these tests really run
``add_instrumentation()`` and check the spans that are produced while Django
handles a request. The spans are collected with an in-memory exporter instead
of being sent to Cloud Trace.
"""

import datetime
import io
import os
from unittest import mock

import requests
from django.test import TestCase
from django.utils import timezone
from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import get_global_textmap, set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from urllib3 import HTTPResponse

from mysite.opentelemetry_config import add_instrumentation
from polls.models import Question

sent_requests = []


def fake_adapter_send(self, request, **kwargs):
    """Answer any outgoing request without touching the network.

    ``requests`` is patched below the point where the instrumentation hooks in,
    so the client span is still created exactly as it would be in production.
    The prepared requests are recorded to check the headers that were sent.
    """
    sent_requests.append(request)
    response = requests.Response()
    response.status_code = 200
    response.url = request.url
    response.request = request
    response.raw = HTTPResponse(
        body=io.BytesIO(b"{}"),
        status=200,
        preload_content=False,
    )
    return response


class InstrumentationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # No environment variable is set, so no exporter is registered and
        # nothing is sent anywhere. The tracer provider and the instrumentation
        # of Django, psycopg2 and requests are set up as in production.
        with mock.patch.dict(os.environ, {}, clear=True):
            add_instrumentation()

        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider), (
            "add_instrumentation() did not install an SDK tracer provider "
            f"(got {provider!r}), another test may have set one before"
        )

        cls.exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(cls.exporter))
        cls.addClassCleanup(cls.uninstrument)

    @classmethod
    def uninstrument(cls):
        DjangoInstrumentor().uninstrument()
        Psycopg2Instrumentor().uninstrument()
        RequestsInstrumentor().uninstrument()

    def setUp(self):
        super().setUp()
        self.exporter.clear()
        sent_requests.clear()
        self.question = Question.objects.create(
            question_text="What is new?",
            pub_date=timezone.now() - datetime.timedelta(days=1),
        )

    def spans_of_kind(self, kind):
        return [span for span in self.exporter.get_finished_spans() if span.kind == kind]

    def get_server_span(self):
        spans = self.spans_of_kind(SpanKind.SERVER)
        self.assertEqual(len(spans), 1, f"expected one server span, got {spans}")
        return spans[0]

    def test_request_produces_a_server_span(self):
        response = self.client.get(f"/polls/{self.question.id}/")
        self.assertEqual(response.status_code, 200)

        span = self.get_server_span()
        self.assertTrue(span.context.is_valid)
        # This is the name that shows up in Cloud Trace
        self.assertEqual(span.name, "GET polls/<int:pk>/")
        self.assertEqual(span.attributes["http.method"], "GET")
        self.assertEqual(span.attributes["http.scheme"], "http")
        self.assertEqual(
            span.attributes["http.url"], f"http://testserver/polls/{self.question.id}/"
        )
        self.assertEqual(span.attributes["http.status_code"], 200)
        self.assertEqual(span.attributes["http.route"], "polls/<int:pk>/")

    def test_response_hook_adds_the_query_parameters(self):
        self.client.get(f"/polls/{self.question.id}/", {"utm_source": "test"})

        span = self.get_server_span()
        self.assertEqual(span.attributes["http.get.params"], '{"utm_source": "test"}')

    def test_error_response_is_recorded(self):
        response = self.client.get("/polls/1234/")
        self.assertEqual(response.status_code, 404)

        span = self.get_server_span()
        self.assertEqual(span.attributes["http.status_code"], 404)

    @mock.patch("requests.adapters.HTTPAdapter.send", fake_adapter_send)
    def test_outgoing_request_becomes_a_child_span(self):
        """The httpbin call of IndexView must show up as a client span."""
        response = self.client.get("/polls/")
        self.assertEqual(response.status_code, 200)

        server_span = self.get_server_span()
        client_spans = self.spans_of_kind(SpanKind.CLIENT)
        self.assertEqual(len(client_spans), 1, f"expected one client span, got {client_spans}")
        client_span = client_spans[0]

        self.assertEqual(client_span.attributes["http.method"], "GET")
        self.assertEqual(client_span.attributes["http.url"], "https://httpbin.org/delay/2")
        self.assertEqual(client_span.attributes["http.status_code"], 200)

        # Both spans belong to the same trace and the client span is a child of
        # the span of the incoming request.
        self.assertEqual(client_span.context.trace_id, server_span.context.trace_id)
        self.assertEqual(client_span.parent.span_id, server_span.context.span_id)

    @mock.patch("requests.adapters.HTTPAdapter.send", fake_adapter_send)
    def test_trace_context_is_sent_to_the_external_service(self):
        """The outgoing request carries the trace context (W3C by default)."""
        self.client.get("/polls/")

        client_span = self.spans_of_kind(SpanKind.CLIENT)[0]

        self.assertEqual(len(sent_requests), 1)
        headers = sent_requests[0].headers
        self.assertIn("traceparent", headers)
        self.assertIn(format(client_span.context.trace_id, "032x"), headers["traceparent"])
        self.assertIn(format(client_span.context.span_id, "016x"), headers["traceparent"])

    def test_incoming_cloud_trace_context_is_used(self):
        """With the Cloud Trace propagator the trace id of the caller is kept.

        ``add_instrumentation()`` installs this propagator when
        ``CLOUD_TRACE_ENABLED`` is set, see ``AddInstrumentationTests``.
        """
        previous = get_global_textmap()
        set_global_textmap(CloudTraceFormatPropagator())
        self.addCleanup(set_global_textmap, previous)

        trace_id = "105445aa7843bc8bf206b12000100000"
        self.client.get(
            f"/polls/{self.question.id}/",
            headers={"x-cloud-trace-context": f"{trace_id}/1;o=1"},
        )

        span = self.get_server_span()
        self.assertEqual(format(span.context.trace_id, "032x"), trace_id)
        self.assertEqual(span.parent.span_id, 1)
