"""Shared helpers: database access and input normalization."""
from .db import db
from .phone import normalize_phone

__all__ = ["db", "normalize_phone"]
