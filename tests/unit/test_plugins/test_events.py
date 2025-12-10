# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for plugin event bus system."""

from datetime import datetime

import pytest

from src.plugins.events import AppEvent, EventBus, EventPayload


class TestAppEvent:
    """Tests for AppEvent enum."""

    def test_user_events(self):
        """Test user event values."""
        assert AppEvent.USER_CREATED.value == "user.created"
        assert AppEvent.USER_UPDATED.value == "user.updated"
        assert AppEvent.USER_DELETED.value == "user.deleted"
        assert AppEvent.USER_LOGIN.value == "user.login"
        assert AppEvent.USER_LOGOUT.value == "user.logout"

    def test_event_events(self):
        """Test event (trip) event values."""
        assert AppEvent.EVENT_CREATED.value == "event.created"
        assert AppEvent.EVENT_UPDATED.value == "event.updated"
        assert AppEvent.EVENT_DELETED.value == "event.deleted"
        assert AppEvent.EVENT_STATUS_CHANGED.value == "event.status_changed"

    def test_company_events(self):
        """Test company event values."""
        assert AppEvent.COMPANY_CREATED.value == "company.created"
        assert AppEvent.COMPANY_UPDATED.value == "company.updated"
        assert AppEvent.COMPANY_DELETED.value == "company.deleted"

    def test_expense_events(self):
        """Test expense event values."""
        assert AppEvent.EXPENSE_CREATED.value == "expense.created"
        assert AppEvent.EXPENSE_UPDATED.value == "expense.updated"
        assert AppEvent.EXPENSE_DELETED.value == "expense.deleted"

    def test_report_events(self):
        """Test report event values."""
        assert AppEvent.REPORT_GENERATED.value == "report.generated"
        assert AppEvent.REPORT_SENT.value == "report.sent"

    def test_integration_events(self):
        """Test integration event values."""
        assert AppEvent.INTEGRATION_CONNECTED.value == "integration.connected"
        assert AppEvent.INTEGRATION_DISCONNECTED.value == "integration.disconnected"

    def test_plugin_lifecycle_events(self):
        """Test plugin lifecycle event values."""
        assert AppEvent.PLUGIN_INSTALLED.value == "plugin.installed"
        assert AppEvent.PLUGIN_ENABLED.value == "plugin.enabled"
        assert AppEvent.PLUGIN_DISABLED.value == "plugin.disabled"
        assert AppEvent.PLUGIN_UNINSTALLED.value == "plugin.uninstalled"


class TestEventPayload:
    """Tests for EventPayload dataclass."""

    def test_create_payload(self):
        """Test creating an event payload."""
        now = datetime.utcnow()
        payload = EventPayload(
            event_type=AppEvent.USER_CREATED,
            timestamp=now,
            data={"user_id": "123"},
        )
        assert payload.event_type == AppEvent.USER_CREATED
        assert payload.timestamp == now
        assert payload.data["user_id"] == "123"
        assert payload.source_plugin_id is None

    def test_create_payload_with_source(self):
        """Test creating an event payload with source plugin."""
        payload = EventPayload(
            event_type=AppEvent.EVENT_CREATED,
            timestamp=datetime.utcnow(),
            data={"event_id": "456"},
            source_plugin_id="my-plugin",
        )
        assert payload.source_plugin_id == "my-plugin"


class TestEventBus:
    """Tests for EventBus class."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus for each test."""
        return EventBus()

    def test_subscribe_sync_handler(self, event_bus):
        """Test subscribing a sync handler."""
        called = []

        def handler(payload):
            called.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, handler, "test-plugin")
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 1

    def test_subscribe_async_handler(self, event_bus):
        """Test subscribing an async handler."""

        async def handler(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler, "test-plugin")
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 1

    def test_subscribe_multiple_handlers(self, event_bus):
        """Test subscribing multiple handlers to same event."""

        def handler1(payload):
            pass

        def handler2(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler1, "plugin-1")
        event_bus.subscribe(AppEvent.USER_CREATED, handler2, "plugin-2")
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 2

    def test_unsubscribe_handler(self, event_bus):
        """Test unsubscribing a handler."""

        def handler(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler, "test-plugin")
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 1

        event_bus.unsubscribe(AppEvent.USER_CREATED, handler, "test-plugin")
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 0

    def test_unsubscribe_plugin(self, event_bus):
        """Test unsubscribing all handlers for a plugin."""

        def handler1(payload):
            pass

        def handler2(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler1, "test-plugin")
        event_bus.subscribe(AppEvent.USER_UPDATED, handler2, "test-plugin")

        event_bus.unsubscribe_plugin("test-plugin")

        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 0
        assert event_bus.get_subscriber_count(AppEvent.USER_UPDATED) == 0

    def test_unsubscribe_plugin_preserves_others(self, event_bus):
        """Test that unsubscribing plugin preserves other plugins' handlers."""

        def handler1(payload):
            pass

        def handler2(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler1, "plugin-1")
        event_bus.subscribe(AppEvent.USER_CREATED, handler2, "plugin-2")

        event_bus.unsubscribe_plugin("plugin-1")

        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 1

    @pytest.mark.asyncio
    async def test_publish_to_sync_handler(self, event_bus):
        """Test publishing event to sync handler."""
        received = []

        def handler(payload):
            received.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, handler)

        await event_bus.publish(
            AppEvent.USER_CREATED,
            {"user_id": "123"},
        )

        assert len(received) == 1
        assert received[0].data["user_id"] == "123"
        assert received[0].event_type == AppEvent.USER_CREATED

    @pytest.mark.asyncio
    async def test_publish_to_async_handler(self, event_bus):
        """Test publishing event to async handler."""
        received = []

        async def handler(payload):
            received.append(payload)

        event_bus.subscribe(AppEvent.EVENT_CREATED, handler)

        await event_bus.publish(
            AppEvent.EVENT_CREATED,
            {"event_id": "456"},
        )

        assert len(received) == 1
        assert received[0].data["event_id"] == "456"

    @pytest.mark.asyncio
    async def test_publish_with_source_plugin(self, event_bus):
        """Test publishing event with source plugin ID."""
        received = []

        def handler(payload):
            received.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, handler)

        await event_bus.publish(
            AppEvent.USER_CREATED,
            {"user_id": "123"},
            source_plugin_id="source-plugin",
        )

        assert received[0].source_plugin_id == "source-plugin"

    @pytest.mark.asyncio
    async def test_publish_handler_error_does_not_stop_others(self, event_bus):
        """Test that one handler error doesn't stop other handlers."""
        received = []

        def failing_handler(payload):
            raise ValueError("Handler failed")

        def working_handler(payload):
            received.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, failing_handler, "plugin-1")
        event_bus.subscribe(AppEvent.USER_CREATED, working_handler, "plugin-2")

        # Should not raise, and working handler should still be called
        await event_bus.publish(AppEvent.USER_CREATED, {"test": "data"})

        assert len(received) == 1

    def test_publish_sync(self, event_bus):
        """Test synchronous publish."""
        received = []

        def handler(payload):
            received.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, handler)

        event_bus.publish_sync(
            AppEvent.USER_CREATED,
            {"user_id": "123"},
        )

        assert len(received) == 1

    def test_publish_sync_does_not_call_async_handlers(self, event_bus):
        """Test that publish_sync doesn't call async handlers."""
        sync_received = []
        async_received = []

        def sync_handler(payload):
            sync_received.append(payload)

        async def async_handler(payload):
            async_received.append(payload)

        event_bus.subscribe(AppEvent.USER_CREATED, sync_handler)
        event_bus.subscribe(AppEvent.USER_CREATED, async_handler)

        event_bus.publish_sync(AppEvent.USER_CREATED, {"test": "data"})

        assert len(sync_received) == 1
        assert len(async_received) == 0

    def test_get_subscriber_count_no_subscribers(self, event_bus):
        """Test subscriber count with no subscribers."""
        assert event_bus.get_subscriber_count(AppEvent.USER_CREATED) == 0

    def test_get_subscribed_events(self, event_bus):
        """Test getting events a plugin is subscribed to."""

        def handler(payload):
            pass

        event_bus.subscribe(AppEvent.USER_CREATED, handler, "test-plugin")
        event_bus.subscribe(AppEvent.EVENT_CREATED, handler, "test-plugin")

        events = event_bus.get_subscribed_events("test-plugin")

        assert AppEvent.USER_CREATED in events
        assert AppEvent.EVENT_CREATED in events
        assert len(events) == 2

    def test_get_subscribed_events_empty(self, event_bus):
        """Test getting events for plugin with no subscriptions."""
        events = event_bus.get_subscribed_events("nonexistent-plugin")
        assert len(events) == 0
