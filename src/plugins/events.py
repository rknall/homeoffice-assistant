# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Event bus for plugin system communication."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AppEvent(str, Enum):
    """Application events that plugins can subscribe to."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # Event (trip) events
    EVENT_CREATED = "event.created"
    EVENT_UPDATED = "event.updated"
    EVENT_DELETED = "event.deleted"
    EVENT_STATUS_CHANGED = "event.status_changed"

    # Company events
    COMPANY_CREATED = "company.created"
    COMPANY_UPDATED = "company.updated"
    COMPANY_DELETED = "company.deleted"

    # Expense events
    EXPENSE_CREATED = "expense.created"
    EXPENSE_UPDATED = "expense.updated"
    EXPENSE_DELETED = "expense.deleted"

    # Report events
    REPORT_GENERATED = "report.generated"
    REPORT_SENT = "report.sent"

    # Integration events
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"

    # Plugin lifecycle events
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"


@dataclass
class EventPayload:
    """Payload for an application event."""

    event_type: AppEvent
    timestamp: datetime
    data: dict[str, Any]
    source_plugin_id: str | None = None  # None means from host app


# Type alias for event handlers
EventHandler = Callable[[EventPayload], Any]


class EventBus:
    """Central event bus for application-wide events.

    Plugins can subscribe to events and receive notifications when
    actions occur in the application. Events are delivered asynchronously.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[AppEvent, list[tuple[str | None, EventHandler]]] = (
            defaultdict(list)
        )
        self._async_handlers: dict[
            AppEvent, list[tuple[str | None, EventHandler]]
        ] = defaultdict(list)

    def subscribe(
        self,
        event_type: AppEvent,
        handler: EventHandler,
        plugin_id: str | None = None,
    ) -> None:
        """Subscribe to an event.

        Args:
            event_type: Event type to subscribe to
            handler: Function to call when event fires (sync or async)
            plugin_id: ID of subscribing plugin (for tracking/unsubscribe)
        """
        if asyncio.iscoroutinefunction(handler):
            self._async_handlers[event_type].append((plugin_id, handler))
        else:
            self._handlers[event_type].append((plugin_id, handler))

        logger.debug(
            f"Subscribed {'plugin ' + plugin_id if plugin_id else 'host'} "
            f"to event {event_type.value}"
        )

    def unsubscribe(
        self,
        event_type: AppEvent,
        handler: EventHandler,
        plugin_id: str | None = None,
    ) -> None:
        """Unsubscribe from an event.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler function to remove
            plugin_id: Plugin ID that subscribed
        """
        entry = (plugin_id, handler)
        if entry in self._handlers[event_type]:
            self._handlers[event_type].remove(entry)
        if entry in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(entry)

    def unsubscribe_plugin(self, plugin_id: str) -> None:
        """Remove all handlers for a plugin.

        Args:
            plugin_id: Plugin ID whose handlers should be removed
        """
        for event_type in list(self._handlers.keys()):
            self._handlers[event_type] = [
                (pid, handler)
                for pid, handler in self._handlers[event_type]
                if pid != plugin_id
            ]
        for event_type in list(self._async_handlers.keys()):
            self._async_handlers[event_type] = [
                (pid, handler)
                for pid, handler in self._async_handlers[event_type]
                if pid != plugin_id
            ]

        logger.debug(f"Unsubscribed all handlers for plugin {plugin_id}")

    async def publish(
        self,
        event_type: AppEvent,
        data: dict[str, Any],
        source_plugin_id: str | None = None,
    ) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data payload
            source_plugin_id: ID of plugin that generated event (None for host)
        """
        payload = EventPayload(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            source_plugin_id=source_plugin_id,
        )

        # Call sync handlers
        for plugin_id, handler in self._handlers.get(event_type, []):
            try:
                handler(payload)
            except Exception as e:
                logger.error(
                    f"Error in sync event handler for {event_type.value} "
                    f"(plugin: {plugin_id}): {e}"
                )

        # Call async handlers
        for plugin_id, handler in self._async_handlers.get(event_type, []):
            try:
                await handler(payload)
            except Exception as e:
                logger.error(
                    f"Error in async event handler for {event_type.value} "
                    f"(plugin: {plugin_id}): {e}"
                )

    def publish_sync(
        self,
        event_type: AppEvent,
        data: dict[str, Any],
        source_plugin_id: str | None = None,
    ) -> None:
        """Publish an event synchronously (sync handlers only).

        Use this when you need to publish from sync code and can't await.
        Note: Async handlers will NOT be called.

        Args:
            event_type: Type of event
            data: Event data payload
            source_plugin_id: ID of plugin that generated event
        """
        payload = EventPayload(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            source_plugin_id=source_plugin_id,
        )

        for plugin_id, handler in self._handlers.get(event_type, []):
            try:
                handler(payload)
            except Exception as e:
                logger.error(
                    f"Error in sync event handler for {event_type.value} "
                    f"(plugin: {plugin_id}): {e}"
                )

        # Log warning if async handlers exist but weren't called
        if self._async_handlers.get(event_type):
            logger.warning(
                f"Event {event_type.value} has async handlers that were "
                "not called due to sync publish"
            )

    def get_subscriber_count(self, event_type: AppEvent) -> int:
        """Get the number of subscribers for an event type.

        Args:
            event_type: Event type to check

        Returns:
            Number of subscribers
        """
        sync_count = len(self._handlers.get(event_type, []))
        async_count = len(self._async_handlers.get(event_type, []))
        return sync_count + async_count

    def get_subscribed_events(self, plugin_id: str) -> list[AppEvent]:
        """Get all events a plugin is subscribed to.

        Args:
            plugin_id: Plugin ID to check

        Returns:
            List of event types the plugin is subscribed to
        """
        events = set()
        for event_type, handlers in self._handlers.items():
            if any(pid == plugin_id for pid, _ in handlers):
                events.add(event_type)
        for event_type, handlers in self._async_handlers.items():
            if any(pid == plugin_id for pid, _ in handlers):
                events.add(event_type)
        return list(events)


# Global event bus singleton
event_bus = EventBus()
