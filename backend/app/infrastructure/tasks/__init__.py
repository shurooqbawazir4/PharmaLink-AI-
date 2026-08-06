"""Celery tasks. Each wraps the exact same application-layer service
methods the sync API endpoints call — no logic lives here beyond wiring a
fresh DB session + repositories/services and running the async call.
"""
