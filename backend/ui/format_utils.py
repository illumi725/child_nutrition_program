"""Shared UI formatting helpers."""

from datetime import datetime


def format_display_date(date_val) -> str:
    if not date_val:
        return ""
    date_str = str(date_val).strip()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except ValueError:
        return date_str
