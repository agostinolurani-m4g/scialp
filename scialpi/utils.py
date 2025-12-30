"""Utility functions for the ``scialpi-log`` package."""

from __future__ import annotations

import datetime as _dt
import re


def slugify(text: str) -> str:
    """Converts a string into a filesystem-friendly slug.

    This function replaces non-alphanumeric characters with hyphens,
    collapses multiple hyphens into a single one and strips leading
    and trailing hyphens. The result is lowercased.

    Parameters
    ----------
    text: str
        The input text to slugify.

    Returns
    -------
    str
        A slugified version of the text.
    """
    text = text.lower()
    # Replace any non-word (a-zA-Z0-9_) character with a hyphen
    slug = re.sub(r"[\W_]+", "-", text)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def parse_date(date_str: str) -> _dt.date:
    """Parse a date in ``YYYY-MM-DD`` format to a ``date`` object.

    Parameters
    ----------
    date_str: str
        The date string to parse.

    Returns
    -------
    datetime.date
        The parsed date.

    Raises
    ------
    ValueError
        If the date string is invalid.
    """
    return _dt.datetime.strptime(date_str, "%Y-%m-%d").date()