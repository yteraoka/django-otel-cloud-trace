import os
import json
 
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Import instrumentation packages here

resource = Resource(attributes={
    "appsignal.config.language_integration": "python",
    "appsignal.config.app_path": os.path.dirname(__file__),
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

cloud_trace_exporter = CloudTraceSpanExporter()
if os.getenv('OTEL_SIMPLE_SPAN_PROCESSOR') is not None:
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(cloud_trace_exporter)
    )
else:
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(cloud_trace_exporter)
    )

def response_hook(span, request, response):
    span.set_attribute(
        "appsignal.request.parameters",
        json.dumps({
            "GET": request.GET,
            "POST": request.POST
        })
    )
    pass

def add_instrumentation():
    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True, response_hook=response_hook)
    Psycopg2Instrumentor().instrument(enable_commenter=True, commenter_options={})
