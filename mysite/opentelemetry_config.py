import os
import json
 
from opentelemetry import trace
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector

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
    #print("DEBUG BEGIN")
    #print("K_SERVICE".format(os.getenv('K_SERVICE')))
    #print("K_REVISION".format(os.getenv('K_REVISION')))
    #for name, value in os.environ.items():
    #    print("DEBUG: Env {0}: {1}".format(name, value))
    #print("DEBUG END")

    # MUST be run on a Google tool!
    # Detect resources from the environment
    resources = get_aggregated_resources(
        [GoogleCloudResourceDetector(raise_on_error=False)]
    )

    trace.set_tracer_provider(TracerProvider(resource=resources))

    cloud_trace_exporter = CloudTraceSpanExporter()
    if os.getenv('OTEL_SIMPLE_SPAN_PROCESSOR') is not None:
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(cloud_trace_exporter)
        )
    else:
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(cloud_trace_exporter)
        )

    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True, response_hook=response_hook)
    Psycopg2Instrumentor().instrument(enable_commenter=True, commenter_options={})
    RequestsInstrumentor().instrument()
