# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Time Tracking plugin API routes.

The route modules register on the shared router in ``common``; importing them
here keeps the original route order.
"""

from . import entries, leave, reports, settings
from .common import router

__all__ = ["entries", "leave", "reports", "router", "settings"]
