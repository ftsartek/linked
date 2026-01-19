"""Notes functionality integration tests.

These tests verify the notes CRUD operations and SSE events.
Notes are associated with solar systems within maps.

Note: test_state fixture is required as a dependency to ensure authentication
runs first (via pytest-order), and to track created note IDs. Most tests use
test_state.map_id which is the test user's own map with full edit access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.factories.static_data import (
    ALLIANCE_SHARED_MAP_ID,
    J123456_SYSTEM_ID,
    JITA_SYSTEM_ID,
)
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Note Creation Tests
# =============================================================================


@pytest.mark.order(700)
async def test_create_note_minimal(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test creating a note with only required fields."""
    assert test_state.map_id is not None, "No map created - test_01_maps must run first"

    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
            "content": "This is a test note.",
        },
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"

    data = response.json()
    assert "note_id" in data

    # Store for later tests
    test_state.note_ids.append(UUID(data["note_id"]))


@pytest.mark.order(701)
async def test_create_note_with_title(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test creating a note with optional title."""
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
            "content": "Note with a title.",
            "title": "Important Info",
        },
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"

    data = response.json()
    test_state.note_ids.append(UUID(data["note_id"]))


@pytest.mark.order(702)
async def test_create_note_with_expiry(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test creating a note with expiration date."""
    expiry = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
            "content": "This note expires in a week.",
            "date_expires": expiry,
        },
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"

    data = response.json()
    test_state.note_ids.append(UUID(data["note_id"]))


@pytest.mark.order(703)
async def test_create_note_full(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test creating a note with all fields."""
    expiry = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": J123456_SYSTEM_ID,
            "content": "Full note content with all fields.",
            "title": "Complete Note",
            "date_expires": expiry,
        },
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"

    data = response.json()
    test_state.note_ids.append(UUID(data["note_id"]))


@pytest.mark.order(705)
async def test_create_note_on_different_system(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test creating a note on a different system than previous tests."""
    from tests.factories.static_data import AMARR_SYSTEM_ID

    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": AMARR_SYSTEM_ID,
            "content": "Note on Amarr system.",
        },
    )
    assert response.status_code == 201, f"Failed to create note: {response.text}"

    data = response.json()
    assert "note_id" in data

    # Verify it can be retrieved
    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{AMARR_SYSTEM_ID}/notes")
    assert response.status_code == 200
    notes_data = response.json()
    assert len(notes_data["notes"]) > 0
    assert any(n["content"] == "Note on Amarr system." for n in notes_data["notes"])


@pytest.mark.order(710)
async def test_create_note_requires_content(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that content is required for note creation."""
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
        },
    )
    assert response.status_code == 400


@pytest.mark.order(711)
async def test_create_note_requires_system_id(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that solar_system_id is required for note creation."""
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "content": "Note without system ID.",
        },
    )
    assert response.status_code == 400


@pytest.mark.order(715)
async def test_create_note_read_only_map(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that creating a note on a read-only map is rejected."""
    # ALLIANCE_SHARED_MAP_ID is shared with read-only access
    response = await test_client.post(
        f"/maps/{ALLIANCE_SHARED_MAP_ID}/notes",
        json={
            "solar_system_id": J123456_SYSTEM_ID,
            "content": "Should not be created.",
        },
    )
    assert response.status_code == 401


# =============================================================================
# Note Retrieval Tests
# =============================================================================


@pytest.mark.order(720)
async def test_get_system_notes(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test getting notes for a system with notes."""
    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{JITA_SYSTEM_ID}/notes")
    assert response.status_code == 200, f"Failed to get notes: {response.text}"

    data = response.json()
    assert "solar_system_id" in data
    assert data["solar_system_id"] == JITA_SYSTEM_ID
    assert "notes" in data
    assert len(data["notes"]) > 0


@pytest.mark.order(721)
async def test_get_system_notes_empty(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test getting notes for a system without notes."""
    # Use a system that hasn't had notes added
    from tests.factories.static_data import HED_GP_SYSTEM_ID

    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{HED_GP_SYSTEM_ID}/notes")
    assert response.status_code == 200, f"Failed to get notes: {response.text}"

    data = response.json()
    assert data["solar_system_id"] == HED_GP_SYSTEM_ID
    assert data["notes"] == []


@pytest.mark.order(722)
async def test_get_system_notes_enriched(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that notes include enriched creator information."""
    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{JITA_SYSTEM_ID}/notes")
    assert response.status_code == 200

    data = response.json()
    assert len(data["notes"]) > 0

    note = data["notes"][0]
    # Should have enriched creator name
    assert "created_by" in note
    assert "created_by_name" in note
    assert note["created_by_name"] is not None


# =============================================================================
# Note Update Tests
# =============================================================================


@pytest.mark.order(740)
async def test_update_note_content(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test updating note content."""
    assert len(test_state.note_ids) > 0, "No notes created to update"
    note_id = test_state.note_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/notes/{note_id}",
        json={
            "content": "Updated content.",
        },
    )
    assert response.status_code == 200, f"Failed to update note: {response.text}"

    data = response.json()
    assert data["note_id"] == str(note_id)


@pytest.mark.order(741)
async def test_update_note_title(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test updating note title."""
    assert len(test_state.note_ids) > 0
    note_id = test_state.note_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/notes/{note_id}",
        json={
            "title": "New Title",
        },
    )
    assert response.status_code == 200, f"Failed to update note: {response.text}"


@pytest.mark.order(742)
async def test_update_note_expiry(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test updating note expiration date."""
    assert len(test_state.note_ids) > 0
    note_id = test_state.note_ids[0]

    new_expiry = (datetime.now(UTC) + timedelta(days=14)).isoformat()
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/notes/{note_id}",
        json={
            "date_expires": new_expiry,
        },
    )
    assert response.status_code == 200, f"Failed to update note: {response.text}"


@pytest.mark.order(745)
async def test_update_note_multiple_fields(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test updating multiple note fields at once."""
    assert len(test_state.note_ids) > 0
    note_id = test_state.note_ids[0]

    new_expiry = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/notes/{note_id}",
        json={
            "title": "Multi-field Update",
            "content": "Content updated with title.",
            "date_expires": new_expiry,
        },
    )
    assert response.status_code == 200, f"Failed to update note: {response.text}"

    # Verify the updates by fetching notes
    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{JITA_SYSTEM_ID}/notes")
    assert response.status_code == 200
    notes_data = response.json()

    # Find our updated note
    updated_note = next((n for n in notes_data["notes"] if n["id"] == str(note_id)), None)
    assert updated_note is not None
    assert updated_note["title"] == "Multi-field Update"
    assert updated_note["content"] == "Content updated with title."


@pytest.mark.order(750)
async def test_update_note_not_found(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that updating non-existent note returns 404."""
    fake_note_id = "00000000-0000-0000-0000-000000009999"
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/notes/{fake_note_id}",
        json={
            "content": "Should not work.",
        },
    )
    assert response.status_code == 404


# =============================================================================
# Note Deletion Tests
# =============================================================================


@pytest.mark.order(760)
async def test_delete_note(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test soft-deleting a note."""
    # Create a note specifically for deletion
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
            "content": "Note to be deleted.",
        },
    )
    assert response.status_code == 201
    note_id = UUID(response.json()["note_id"])

    # Delete it
    response = await test_client.delete(f"/maps/{test_state.map_id}/notes/{note_id}")
    assert response.status_code == 202, f"Failed to delete note: {response.text}"

    data = response.json()
    assert data["note_id"] == str(note_id)


@pytest.mark.order(761)
async def test_delete_note_idempotent(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that deleting an already-deleted note returns 404."""
    # Create a note to delete
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": JITA_SYSTEM_ID,
            "content": "Note to test double delete.",
        },
    )
    assert response.status_code == 201
    note_id = UUID(response.json()["note_id"])

    # Delete it first time
    response = await test_client.delete(f"/maps/{test_state.map_id}/notes/{note_id}")
    assert response.status_code == 202

    # Delete it second time - should return 404
    response = await test_client.delete(f"/maps/{test_state.map_id}/notes/{note_id}")
    assert response.status_code == 404


@pytest.mark.order(765)
async def test_delete_note_not_found(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that deleting non-existent note returns 404."""
    fake_note_id = "00000000-0000-0000-0000-000000009999"
    response = await test_client.delete(f"/maps/{test_state.map_id}/notes/{fake_note_id}")
    assert response.status_code == 404


@pytest.mark.order(770)
async def test_deleted_note_not_in_list(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test that deleted notes are excluded from the notes list."""
    # Create and delete a note
    response = await test_client.post(
        f"/maps/{test_state.map_id}/notes",
        json={
            "solar_system_id": J123456_SYSTEM_ID,
            "content": "Unique content for deletion test xyz123.",
        },
    )
    assert response.status_code == 201
    note_id = response.json()["note_id"]

    # Delete it
    response = await test_client.delete(f"/maps/{test_state.map_id}/notes/{note_id}")
    assert response.status_code == 202

    # Verify it's not in the list
    response = await test_client.get(f"/maps/{test_state.map_id}/systems/{J123456_SYSTEM_ID}/notes")
    assert response.status_code == 200

    data = response.json()
    note_ids = [n["id"] for n in data["notes"]]
    assert note_id not in note_ids
