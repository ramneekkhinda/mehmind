"""OpenTelemetry setup for MeshMind referee service."""

import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from fastapi import FastAPI


def setup_otel(app: FastAPI) -> None:
    """Setup OpenTelemetry for the FastAPI application."""
    
    # Get configuration from environment
    service_name = os.getenv("OTEL_SERVICE_NAME", "meshmind-referee")
    jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")
    
    # Setup trace provider
    trace_provider = TracerProvider()
    
    # Add span processors
    if jaeger_endpoint:
        jaeger_exporter = JaegerExporter(
            collector_endpoint=jaeger_endpoint
        )
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set the trace provider
    trace.set_tracer_provider(trace_provider)
    
    # Setup metrics provider
    metric_readers = []
    
    if otlp_endpoint:
        otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
        metric_readers.append(PeriodicExportingMetricReader(otlp_metric_exporter))
    
    if metric_readers:
        meter_provider = MeterProvider(metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument Redis
    try:
        RedisInstrumentor().instrument()
    except Exception:
        pass  # Redis might not be available
    
    # Instrument asyncpg
    try:
        AsyncPGInstrumentor().instrument()
    except Exception:
        pass  # PostgreSQL might not be available


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)


# Create common meters and counters
def create_metrics():
    """Create common metrics."""
    meter = get_meter("meshmind.referee")
    
    # Decision metrics
    decision_counter = meter.create_counter(
        name="meshmind.decisions.total",
        description="Total number of decisions made",
        unit="1"
    )
    
    decision_duration = meter.create_histogram(
        name="meshmind.decisions.duration",
        description="Duration of decision making",
        unit="ms"
    )
    
    # Hold metrics
    hold_counter = meter.create_counter(
        name="meshmind.holds.total",
        description="Total number of hold operations",
        unit="1"
    )
    
    # Budget metrics
    budget_counter = meter.create_counter(
        name="meshmind.budgets.total",
        description="Total number of budget operations",
        unit="1"
    )
    
    budget_spending = meter.create_counter(
        name="meshmind.budgets.spending",
        description="Total budget spending",
        unit="usd"
    )
    
    return {
        "decision_counter": decision_counter,
        "decision_duration": decision_duration,
        "hold_counter": hold_counter,
        "budget_counter": budget_counter,
        "budget_spending": budget_spending
    }


# Global metrics instance
METRICS = create_metrics()
