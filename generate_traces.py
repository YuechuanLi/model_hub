import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Define resource attributes
resource = Resource(
    attributes={"service.name": "test-service", "service.version": "1.0.0"}
)

# Setup Tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure OTLP Exporter (sending to local SigNoz collector)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

print("Sending dummy traces to SigNoz...")

for i in range(10):
    with tracer.start_as_current_span("parent-operation") as parent:
        parent.set_attribute("iteration", i)
        print(f"Generated trace {i+1}/10")

        with tracer.start_as_current_span("child-task") as child:
            child.set_attribute("task.id", f"task-{i}")
            time.sleep(0.1)  # Simulate work

print("Done! Check SigNoz dashboard.")
