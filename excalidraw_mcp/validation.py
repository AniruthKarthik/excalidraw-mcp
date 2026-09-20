"""Shared validation rules used by MCP contracts and document normalization."""

import re


COLOR_PATTERN = r"(?:transparent|#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{4}|#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{8})"


def valid_color(value):
    return isinstance(value, str) and re.fullmatch(COLOR_PATTERN, value) is not None
