import os
import sys
import json
import django

def response_hook(span, request, response):
    span.set_attribute(
      "http.get.params",
      json.dumps(request.GET)
    )
    #span.set_attribute(
    #  "http.post.params",
    #  json.dumps(request.POST)
    #)
    pass

def add_instrumentation():
    from opentelemetry import trace
    from opentelemetry.sdk import resources
    from opentelemetry.sdk.trace import TracerProvider

    attrs = {
        resources.PROCESS_RUNTIME_NAME: sys.implementation.name,
        resources.PROCESS_RUNTIME_VERSION: '.'.join(map(str, sys.implementation.version)),
        resources.PROCESS_RUNTIME_DESCRIPTION: sys.version,
        resources.PROCESS_COMMAND_ARGS: sys.argv,
        resources.ResourceAttributes.WEBENGINE_NAME: "django",
        resources.ResourceAttributes.WEBENGINE_VERSION: django.__version__,
    }
    if os.getenv('K_SERVICE') is not None:
        attrs["faas.name"] = os.getenv('K_SERVICE')
        attrs["cloud.platform"] = "gcp_cloud_run"
        attrs["gcp.resource_type"] = "cloud_run"
    if os.getenv('K_REVISION') is not None:
        attrs["faas.version"] = os.getenv('K_REVISION')

    resource = resources.Resource(attributes=attrs)

    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    if os.getenv('CLOUD_TRACE_ENABLED') is not None:
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.propagators.cloud_trace_propagator import (
            CloudTraceFormatPropagator,
        )
        from opentelemetry.propagate import set_global_textmap
        trace_provider.add_span_processor(
            BatchSpanProcessor(CloudTraceSpanExporter())
        )
        set_global_textmap(CloudTraceFormatPropagator())
    elif os.getenv('TRACE_ENABLED') is not None:
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
        trace_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )

    from opentelemetry.instrumentation.django import DjangoInstrumentor
    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True, response_hook=response_hook)

    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    Psycopg2Instrumentor().instrument(enable_commenter=True, commenter_options={})

    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    RequestsInstrumentor().instrument()
