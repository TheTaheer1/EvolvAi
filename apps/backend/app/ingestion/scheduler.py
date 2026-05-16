"""Placeholder for optional scheduled ingestion.

Step 3 keeps live ingestion manually triggered by API/UI by default. A future
automation can call the same services from Celery beat without changing the
normalization pipeline.
"""
