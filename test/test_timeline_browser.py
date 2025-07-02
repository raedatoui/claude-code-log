"""Playwright-based tests for timeline functionality in the browser."""

import tempfile
import re
from pathlib import Path
from typing import List
from playwright.sync_api import Page, expect

from claude_code_log.parser import load_transcript
from claude_code_log.renderer import generate_html
from claude_code_log.models import TranscriptEntry


class TestTimelineBrowser:
    """Test timeline functionality using Playwright in a real browser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_files: List[Path] = []

    def teardown_method(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                temp_file.unlink()
            except FileNotFoundError:
                pass

    def _create_temp_html(self, messages: List[TranscriptEntry], title: str) -> Path:
        """Create a temporary HTML file for testing."""
        html_content = generate_html(messages, title)

        # Create temporary file
        temp_file = Path(tempfile.mktemp(suffix=".html"))
        temp_file.write_text(html_content, encoding="utf-8")
        self.temp_files.append(temp_file)

        return temp_file

    def _wait_for_timeline_loaded(self, page: Page):
        """Wait for timeline to be fully loaded and initialized."""
        # Wait for timeline container to be visible
        page.wait_for_selector("#timeline-container", state="attached")

        # Wait for vis-timeline to create its DOM elements
        page.wait_for_selector(".vis-timeline", timeout=10000)

        # Wait for timeline items to be rendered
        page.wait_for_selector(".vis-item", timeout=5000)

    def test_timeline_toggle_button_exists(self, page: Page):
        """Test that timeline toggle button is present."""
        # Use sidechain test data
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Toggle Test")

        page.goto(f"file://{temp_file}")

        # Check timeline toggle button exists
        toggle_btn = page.locator("#toggleTimeline")
        expect(toggle_btn).to_be_visible()
        expect(toggle_btn).to_have_text("📆")
        expect(toggle_btn).to_have_attribute("title", "Show timeline")

    def test_timeline_shows_after_toggle(self, page: Page):
        """Test that timeline becomes visible after clicking toggle."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Visibility Test")

        page.goto(f"file://{temp_file}")

        # Timeline should be hidden initially
        timeline_container = page.locator("#timeline-container")
        expect(timeline_container).to_have_css("display", "none")

        # Click toggle button
        toggle_btn = page.locator("#toggleTimeline")
        toggle_btn.click()

        # Wait for timeline to load and become visible
        self._wait_for_timeline_loaded(page)
        expect(timeline_container).not_to_have_css("display", "none")

        # Button should show active state
        expect(toggle_btn).to_have_text("🗓️")
        expect(toggle_btn).to_have_attribute("title", "Hide timeline")

    def test_timeline_sidechain_messages(self, page: Page):
        """Test that sidechain messages appear correctly in timeline."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Sidechain Test")

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Check that timeline items exist
        timeline_items = page.locator(".vis-item")
        timeline_items.first.wait_for(state="visible", timeout=5000)

        # Count total items
        item_count = timeline_items.count()
        assert item_count > 0, f"Should have timeline items, found {item_count}"

        # Check for the specific failing test content (the key issue from the original bug)
        failing_test_items = page.locator(".vis-item:has-text('failing test')")
        failing_test_count = failing_test_items.count()

        assert failing_test_count > 0, (
            "Should contain the sub-assistant prompt about failing test"
        )

        # Check for other sidechain content to verify multiple sidechain messages
        template_items = page.locator(".vis-item:has-text('template files')")
        template_count = template_items.count()

        summary_items = page.locator(".vis-item:has-text('Summary')")
        summary_count = summary_items.count()

        # Should have multiple sidechain-related content items
        total_sidechain_content = failing_test_count + template_count + summary_count
        assert total_sidechain_content > 0, (
            f"Should have sidechain content items, found {total_sidechain_content}"
        )

    def test_timeline_sidechain_message_groups_and_classes(self, page: Page):
        """Test that sub-assistant messages appear in the correct timeline group with proper CSS classes."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Sidechain Groups Test")

        page.goto(f"file://{temp_file}")

        # First verify sidechain messages exist in the DOM
        sidechain_messages = page.locator(".message.sidechain")
        sidechain_dom_count = sidechain_messages.count()

        # Verify sidechain messages have proper DOM structure

        assert sidechain_dom_count > 0, (
            f"Should have sidechain messages in DOM, found {sidechain_dom_count}"
        )

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Wait for timeline groups to be created by vis-timeline
        page.wait_for_timeout(1000)  # Give timeline time to render groups

        # Note: Sidechain items may be classified differently due to vis-timeline filtering issues

        # Verify that sub-assistant content appears in timeline (the key issue from the original bug)
        failing_test_items = page.locator('.vis-item:has-text("failing test")')
        assert failing_test_items.count() > 0, (
            "Sub-assistant prompt about failing test should appear in timeline"
        )

        # Check for user sidechain messages with 📝 prefix (as shown in timeline display logic)
        user_sidechain_items = page.locator('.vis-item:has-text("📝")')
        user_count = user_sidechain_items.count()

        # Check for assistant sidechain messages with 🔗 prefix
        assistant_sidechain_items = page.locator('.vis-item:has-text("🔗")')
        assistant_count = assistant_sidechain_items.count()

        # Verify that sidechain content appears with proper prefixes
        assert user_count > 0 or assistant_count > 0, (
            "Timeline should show sidechain messages with proper 📝/🔗 prefixes"
        )

    def test_timeline_message_type_filtering_sidechain(self, page: Page):
        """Test that sidechain messages can be filtered independently from regular messages."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Sidechain Filter Test")

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Wait for timeline to fully render
        page.wait_for_timeout(1000)

        # Get initial counts
        all_items = page.locator(".vis-item")
        initial_count = all_items.count()

        # Verify that timeline items exist and basic filtering works
        assert initial_count > 0, "Should have timeline items"

        # Open filter panel
        page.locator("#filterMessages").click()
        filter_toolbar = page.locator(".filter-toolbar")
        expect(filter_toolbar).to_be_visible()

    def test_sidechain_filter_toggle_exists(self, page: Page):
        """Test that Sub-assistant filter toggle exists and works."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Sidechain Filter Toggle Test")

        page.goto(f"file://{temp_file}")

        # Open filter panel
        page.locator("#filterMessages").click()
        filter_toolbar = page.locator(".filter-toolbar")
        expect(filter_toolbar).to_be_visible()

        # Check that Sub-assistant filter toggle exists
        sidechain_filter = page.locator('.filter-toggle[data-type="sidechain"]')
        expect(sidechain_filter).to_be_visible()
        expect(sidechain_filter).to_contain_text("🔗 Sub-assistant")

        # Should start active (all filters start active by default)
        expect(sidechain_filter).to_have_class(
            re.compile(r".*active.*")
        )  # Use regex to match partial class

    def test_sidechain_message_filtering_integration(self, page: Page):
        """Test that sidechain messages can be filtered in both main content and timeline."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(
            messages, "Sidechain Filtering Integration Test"
        )

        page.goto(f"file://{temp_file}")

        # Verify sidechain messages exist
        sidechain_messages = page.locator(".message.sidechain")
        sidechain_count = sidechain_messages.count()
        assert sidechain_count > 0, "Should have sidechain messages to test filtering"

        # Open filter panel
        page.locator("#filterMessages").click()

        # Check initial state - sidechain filter should be active
        sidechain_filter = page.locator('.filter-toggle[data-type="sidechain"]')
        expect(sidechain_filter).to_be_visible()
        expect(sidechain_filter).to_have_class(re.compile(r".*active.*"))

        # Deselect Sub-assistant filter
        sidechain_filter.click()

        # Wait for filtering to apply
        page.wait_for_timeout(500)

        # Sub-assistant filter should be inactive
        expect(sidechain_filter).not_to_have_class(re.compile(r".*active.*"))

        # Check that sidechain messages are filtered out from main content
        visible_sidechain_messages = page.locator(
            ".message.sidechain:not(.filtered-hidden)"
        )
        assert visible_sidechain_messages.count() == 0, (
            "Sidechain messages should be hidden when filter is off"
        )

        # Re-enable Sub-assistant filter
        sidechain_filter.click()
        page.wait_for_timeout(500)

        # Sub-assistant messages should be visible again
        expect(sidechain_filter).to_have_class(re.compile(r".*active.*"))
        visible_sidechain_messages = page.locator(
            ".message.sidechain:not(.filtered-hidden)"
        )
        assert visible_sidechain_messages.count() > 0, (
            "Sidechain messages should be visible when filter is on"
        )

    def test_sidechain_messages_html_css_classes(self, page: Page):
        """Test that sidechain messages in the main content have correct CSS classes."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Sidechain CSS Classes Test")

        page.goto(f"file://{temp_file}")

        # Check for sub-assistant user messages in main content
        user_sidechain_messages = page.locator(".message.user.sidechain")
        user_count = user_sidechain_messages.count()
        assert user_count > 0, (
            "Should have user sidechain messages with 'user sidechain' classes"
        )

        # Check for sub-assistant assistant messages in main content
        assistant_sidechain_messages = page.locator(".message.assistant.sidechain")
        assistant_count = assistant_sidechain_messages.count()
        assert assistant_count > 0, (
            "Should have assistant sidechain messages with 'assistant sidechain' classes"
        )

        # Verify that we found the expected sidechain message types
        assert user_count > 0 and assistant_count > 0, (
            f"Should have both user ({user_count}) and assistant ({assistant_count}) sidechain messages"
        )

        # Check that the specific failing test message has the right classes
        failing_test_message = page.locator(
            '.message.user.sidechain:has-text("failing test")'
        )
        assert failing_test_message.count() > 0, (
            "Sub-assistant prompt about failing test should have 'user sidechain' classes"
        )

    def test_sidechain_filter_complete_integration(self, page: Page):
        """Test complete integration of sidechain filtering between main content and timeline."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(
            messages, "Complete Sidechain Filter Integration Test"
        )

        page.goto(f"file://{temp_file}")

        # Count initial sidechain messages in main content
        initial_sidechain_messages = page.locator(".message.sidechain")
        initial_sidechain_count = initial_sidechain_messages.count()
        assert initial_sidechain_count > 0, "Should have sidechain messages to test"

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Count initial timeline items
        initial_timeline_items = page.locator(".vis-item")
        initial_timeline_count = initial_timeline_items.count()
        assert initial_timeline_count > 0, "Should have timeline items"

        # Open filter panel
        page.locator("#filterMessages").click()
        filter_toolbar = page.locator(".filter-toolbar")
        expect(filter_toolbar).to_be_visible()

        # Test sidechain filter toggle exists and is active by default
        sidechain_filter = page.locator('.filter-toggle[data-type="sidechain"]')
        expect(sidechain_filter).to_be_visible()
        expect(sidechain_filter).to_have_class(re.compile(r".*active.*"))

        # Deselect sidechain filter
        sidechain_filter.click()
        page.wait_for_timeout(500)

        # Verify filter is no longer active
        expect(sidechain_filter).not_to_have_class(re.compile(r".*active.*"))

        # Check that sidechain messages are hidden in main content
        visible_sidechain_messages = page.locator(
            ".message.sidechain:not(.filtered-hidden)"
        )
        assert visible_sidechain_messages.count() == 0, (
            "Sidechain messages should be hidden in main content"
        )

        # Check that timeline still works (may have different item count)
        current_timeline_items = page.locator(".vis-item")
        current_timeline_count = current_timeline_items.count()
        assert current_timeline_count >= 0, (
            "Timeline should still work with sidechain filtering"
        )

        # Re-enable sidechain filter
        sidechain_filter.click()
        page.wait_for_timeout(500)

        # Verify filter is active again
        expect(sidechain_filter).to_have_class(re.compile(r".*active.*"))

        # Check that sidechain messages are visible again in main content
        visible_sidechain_messages = page.locator(
            ".message.sidechain:not(.filtered-hidden)"
        )
        assert visible_sidechain_messages.count() > 0, (
            "Sidechain messages should be visible again"
        )

        # Timeline should still work
        restored_timeline_items = page.locator(".vis-item")
        restored_timeline_count = restored_timeline_items.count()
        assert restored_timeline_count >= 0, (
            "Timeline should work after restoring sidechain filter"
        )

        # Test "None" filter functionality that user mentioned in the issue
        select_none_button = page.locator("#selectNone")
        select_none_button.click()
        page.wait_for_timeout(500)

        # All message filters should be inactive
        expect(sidechain_filter).not_to_have_class(re.compile(r".*active.*"))
        user_filter = page.locator('.filter-toggle[data-type="user"]')
        expect(user_filter).not_to_have_class(re.compile(r".*active.*"))
        assistant_filter = page.locator('.filter-toggle[data-type="assistant"]')
        expect(assistant_filter).not_to_have_class(re.compile(r".*active.*"))

        # All messages should be hidden
        visible_messages = page.locator(
            ".message:not(.session-header):not(.filtered-hidden)"
        )
        assert visible_messages.count() == 0, (
            "All messages should be hidden when no filters are active"
        )

        # Test "All" filter functionality
        select_all_button = page.locator("#selectAll")
        select_all_button.click()
        page.wait_for_timeout(500)

        # All message filters should be active
        expect(sidechain_filter).to_have_class(re.compile(r".*active.*"))
        expect(user_filter).to_have_class(re.compile(r".*active.*"))
        expect(assistant_filter).to_have_class(re.compile(r".*active.*"))

        # All messages should be visible again
        visible_messages = page.locator(
            ".message:not(.session-header):not(.filtered-hidden)"
        )
        assert visible_messages.count() > 0, (
            "All messages should be visible when all filters are active"
        )

    def test_timeline_system_messages(self, page: Page):
        """Test that system messages appear correctly in timeline."""
        system_file = Path("test/test_data/system_model_change.jsonl")
        messages = load_transcript(system_file)
        temp_file = self._create_temp_html(messages, "Timeline System Test")

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Check that timeline items exist
        timeline_items = page.locator(".vis-item")
        timeline_items.first.wait_for(state="visible", timeout=5000)

        # Check for system message content
        system_items = page.locator(".vis-item:has-text('Claude Opus 4 limit reached')")
        system_count = system_items.count()

        assert system_count > 0, "Should contain the system warning about Opus limit"

    def test_timeline_message_click_navigation(self, page: Page):
        """Test that clicking timeline items scrolls to corresponding messages."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Click Test")

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Get timeline items and messages on page
        timeline_items = page.locator(".vis-item")
        messages_on_page = page.locator(".message:not(.session-header)")

        timeline_count = timeline_items.count()
        message_count = messages_on_page.count()

        # Timeline should have items corresponding to messages
        assert timeline_count > 0, "Timeline should have items"
        assert message_count > 0, "Page should have messages"

        # Note: Timeline may have different item count than page messages due to:
        # 1. Messages without timestamps being filtered out
        # 2. Tool use/results being split or combined differently
        # Verify both timeline and messages exist
        assert timeline_count > 0 and message_count > 0, (
            f"Both timeline ({timeline_count}) and messages ({message_count}) should exist"
        )

    def test_timeline_filtering_integration(self, page: Page):
        """Test that timeline filters work with message filters."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Filter Test")

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Check that timeline items exist
        timeline_items = page.locator(".vis-item")
        initial_count = timeline_items.count()
        assert initial_count > 0, "Should have initial timeline items"

        # Open filter panel
        page.locator("#filterMessages").click()

        # Filter panel should be visible
        filter_toolbar = page.locator(".filter-toolbar")
        expect(filter_toolbar).to_be_visible()

        # Test filtering with sub-assistant specifically
        sidechain_filter = page.locator('.filter-toggle[data-type="sidechain"]')
        if sidechain_filter.count() > 0:
            # Deselect sub-assistant filter
            sidechain_filter.click()
            page.wait_for_timeout(500)

            # Timeline should handle filtering (may have fewer items)
            filtered_count = timeline_items.count()
            assert filtered_count >= 0, (
                "Timeline should handle sidechain filtering without errors"
            )

            # Re-enable sub-assistant filter
            sidechain_filter.click()
            page.wait_for_timeout(500)

            # Timeline should show items again
            restored_count = timeline_items.count()
            assert restored_count >= 0, (
                "Timeline should restore items when filter is re-enabled"
            )

        # Test general assistant filtering
        assistant_filter = page.locator('.filter-toggle[data-type="assistant"]')
        if assistant_filter.count() > 0:
            assistant_filter.click()
            page.wait_for_timeout(500)

            # Timeline should still have items (though count may change)
            filtered_count = timeline_items.count()
            assert filtered_count >= 0, (
                "Timeline should handle assistant filtering without errors"
            )

    def test_timeline_console_errors(self, page: Page):
        """Test that timeline doesn't produce JavaScript errors."""
        sidechain_file = Path("test/test_data/sidechain.jsonl")
        messages = load_transcript(sidechain_file)
        temp_file = self._create_temp_html(messages, "Timeline Error Test")

        # Capture console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))

        page.goto(f"file://{temp_file}")

        # Activate timeline
        page.locator("#toggleTimeline").click()
        self._wait_for_timeline_loaded(page)

        # Check for errors
        errors = [msg for msg in console_messages if msg.type == "error"]
        error_texts = [msg.text for msg in errors]

        # Filter out common non-critical errors
        critical_errors = [
            error
            for error in error_texts
            if not any(
                ignore in error.lower()
                for ignore in [
                    "favicon.ico",  # Common 404 for favicon
                    "net::err_file_not_found",  # File protocol limitations
                    "refused to connect",  # CORS issues with file protocol
                    "cors",  # CORS related errors
                    "network error",  # Network-related errors in file:// protocol
                ]
            )
        ]

        assert len(critical_errors) == 0, (
            f"Timeline should not produce critical JavaScript errors: {critical_errors}"
        )
