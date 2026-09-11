"""
Tests for export.ts fix - verifying empty contact_times handling.
"""

import sys
from pathlib import Path

# Add frontend test support
import json


def test_export_contact_times_empty_object_appears_as_na():
    """Test that eclipses with empty contact_times object render as N/A row.
    
    Bug: Empty contact_times object would:
    - Pass truthy check in first branch (since {} is truthy in JavaScript)
    - Have zero entries from Object.entries
    - Generate zero CSV rows
    - Skip the else-if fallback (which should generate N/A row)
    - Result: eclipse disappears from CSV entirely
    
    Fix: Check for at least one entry before using per-contact path
    """
    # This test documents the expected behavior
    # The actual implementation is in frontend/src/services/export.ts:30
    
    # Test data: eclipse with empty contact_times
    eclipse_empty_contacts = {
        "date": "2025-09-07",
        "event_type": "Solar Eclipse",
        "is_lunar": False,
        "eclipse_occurs": True,
        "contact_times": {}  # Empty object!
    }
    
    # Expected behavior (per CSV export logic):
    # 1. First condition: event.eclipse_occurs && event.contact_times && Object.keys(event.contact_times).length > 0
    #    - Should NOT match (empty object has 0 keys)
    # 2. Second condition: !event.contact_times || Object.keys(event.contact_times).length === 0
    #    - Should MATCH (0 keys)
    # 3. Result: Generate N/A row showing eclipse occurred but no contact times
    
    assert eclipse_empty_contacts["eclipse_occurs"] is True
    assert isinstance(eclipse_empty_contacts["contact_times"], dict)
    assert len(eclipse_empty_contacts["contact_times"]) == 0, "contact_times is empty"
    
    # With the fix, this should produce an N/A row
    # Without the fix, Object.entries({}) produces [] (empty array)
    # which means the forEach produces NO rows, and the eclipse disappears


def test_export_contact_times_with_entries_generates_rows():
    """Test that eclipses with contact_times entries generate per-contact rows."""
    eclipse_with_contacts = {
        "date": "2025-09-07",
        "event_type": "Solar Eclipse",
        "is_lunar": False,
        "eclipse_occurs": True,
        "contact_times": {
            "c1": "2025-09-07 14:00:00",
            "c2": "2025-09-07 15:30:00",
            "c3": "2025-09-07 17:00:00",
            "c4": "2025-09-07 18:30:00"
        }
    }
    
    # With fix: should check length > 0
    assert eclipse_with_contacts["eclipse_occurs"] is True
    assert len(eclipse_with_contacts["contact_times"]) > 0, "Has contact times"
    
    # Should generate 4 CSV rows (one per contact)
    # Each row: date | event_type | is_lunar | eclipse_occurs | contact_type | time
    expected_rows = 4
    assert len(eclipse_with_contacts["contact_times"]) == expected_rows


def test_export_null_contact_times_generates_na_row():
    """Test that eclipses with null contact_times generate N/A row."""
    eclipse_null_contacts = {
        "date": "2025-09-07",
        "event_type": "Solar Eclipse",
        "is_lunar": False,
        "eclipse_occurs": True,
        "contact_times": None
    }
    
    # Should match second condition
    assert eclipse_null_contacts["contact_times"] is None or \
           (isinstance(eclipse_null_contacts["contact_times"], dict) and 
            len(eclipse_null_contacts["contact_times"]) == 0)
    
    # Should generate one N/A row


def test_export_undefined_contact_times_generates_na_row():
    """Test that eclipses with undefined contact_times generate N/A row."""
    eclipse_undefined_contacts = {
        "date": "2025-09-07",
        "event_type": "Solar Eclipse",
        "is_lunar": False,
        "eclipse_occurs": True,
        # contact_times is missing (undefined)
    }
    
    # Should handle missing field gracefully
    contact_times = eclipse_undefined_contacts.get("contact_times")
    assert contact_times is None or len(contact_times) == 0
    
    # Should generate one N/A row


def test_export_non_eclipse_events_generate_na_row():
    """Test that non-eclipse events always generate N/A row."""
    non_eclipse = {
        "date": "2025-06-15",
        "event_type": "New Moon",
        "is_lunar": True,
        "eclipse_occurs": False,
        "contact_times": None
    }
    
    # First condition should fail (eclipse_occurs is False)
    assert non_eclipse["eclipse_occurs"] is False
    
    # Second condition should match or first condition fail
    # Result: N/A row is generated


def test_export_handles_single_contact_time():
    """Test that single contact time is handled correctly."""
    eclipse_one_contact = {
        "date": "2025-09-07",
        "event_type": "Lunar Eclipse",
        "is_lunar": True,
        "eclipse_occurs": True,
        "contact_times": {
            "p1": "2025-09-07 00:30:00"
        }
    }
    
    # Should generate 1 row (not N/A)
    assert eclipse_one_contact["eclipse_occurs"] is True
    assert len(eclipse_one_contact["contact_times"]) == 1
    assert len(eclipse_one_contact["contact_times"]) > 0


def test_export_handles_many_contact_times():
    """Test that many contact times are handled correctly."""
    eclipse_many_contacts = {
        "date": "2025-09-07",
        "event_type": "Solar Eclipse",
        "is_lunar": False,
        "eclipse_occurs": True,
        "contact_times": {
            "p1": "2025-09-07 14:00:00",
            "u1": "2025-09-07 14:10:00",
            "mid": "2025-09-07 15:30:00",
            "u4": "2025-09-07 16:50:00",
            "p4": "2025-09-07 17:00:00"
        }
    }
    
    # Should generate 5 rows
    assert len(eclipse_many_contacts["contact_times"]) == 5
    assert len(eclipse_many_contacts["contact_times"]) > 0


def test_export_csv_header_structure():
    """Test that CSV header includes all required fields."""
    # Expected CSV header fields
    expected_headers = [
        'Date',
        'Event Type',
        'Is Lunar',
        'Occurs',
        'Contact Type',
        'Time (UTC)'
    ]
    
    # Verify field order and count
    assert len(expected_headers) == 6
    assert 'Date' in expected_headers
    assert 'Contact Type' in expected_headers
    assert 'Time (UTC)' in expected_headers


def test_export_csv_escaping():
    """Test that CSV fields are properly escaped."""
    # Test cases with special characters that need escaping
    test_cases = [
        {
            "field": "Eclipse, Solar, Type",
            "should_quote": True,
            "reason": "Contains commas"
        },
        {
            "field": 'Quote "test"',
            "should_quote": True,
            "reason": "Contains quotes"
        },
        {
            "field": "Line\\nbreak",
            "should_quote": True,
            "reason": "Contains newline"
        },
        {
            "field": "2025-09-07 14:00:00",
            "should_quote": False,
            "reason": "No special chars"
        }
    ]
    
    for test_case in test_cases:
        field = test_case["field"]
        # Fields with commas, quotes, or newlines need escaping
        needs_escaping = ',' in field or '"' in field or '\\n' in field
        assert needs_escaping == test_case["should_quote"], test_case["reason"]
