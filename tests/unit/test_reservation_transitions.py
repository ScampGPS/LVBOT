from reservations.queue.reservation_transitions import (
    add_to_waitlist,
    apply_status_update,
)


def test_apply_status_update_mutates_reservation():
    reservation = {"status": "pending", "attempts": 0}

    updated = apply_status_update(reservation, "scheduled", attempts=1)

    assert updated["status"] == "scheduled"
    assert updated["attempts"] == 1
    # Ensure mutation happens in place
    assert reservation["status"] == "scheduled"


def test_add_to_waitlist_sets_fields():
    reservation = {"status": "pending"}

    add_to_waitlist(reservation, position=2)

    assert reservation["status"] == "waitlisted"
    assert reservation["waitlist_position"] == 2
    assert reservation["original_position"] == 2
