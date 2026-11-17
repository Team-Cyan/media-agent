"""Calendar slots and durable at-most-once automatic scan attempts."""

import json

from media_agent.cron_schedule import latest_cron_slot

MEDIA_HASH_ID = b"media-import-scan"


def latest_slot(schedule, now):
    if schedule.cron is None:
        return None
    return latest_cron_slot(schedule.cron, schedule.timezone, now, hash_id=MEDIA_HASH_ID)


def claim_slot(store, schedule, profiles, now):
    """Observe settings and claim the latest eligible slot before running the scan.

    Changes activate on observation, not retroactively. The checkpoint is recorded
    before work starts so failures and worker interruption do not retry the slot.
    """
    fingerprint = json.dumps(schedule.model_dump(mode="json") if schedule else None, sort_keys=True)
    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,payload_json FROM media_events "
            "WHERE event='calendar_schedule_checkpoint' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        state = json.loads(row[1]) if row else None
        if not state or state["fingerprint"] != fingerprint:
            state = {"fingerprint": fingerprint, "activated": now, "attempted": None}
            if row:
                conn.execute(
                    "UPDATE media_events SET created=?,payload_json=? WHERE id=?",
                    (now, json.dumps(state), row[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO media_events(source_id,event,created,payload_json) "
                    "VALUES(NULL,'calendar_schedule_checkpoint',?,?)",
                    (now, json.dumps(state)),
                )
            return False
        if schedule is None:
            return False
        slot = latest_slot(schedule, now)
        if (
            slot is None
            or slot <= state["activated"]
            or (state["attempted"] is not None and slot <= state["attempted"])
        ):
            return False
        # A complete manual scan after the slot already satisfies it, provided
        # every currently configured profile has completed since that slot.
        completed = all(
            conn.execute(
                "SELECT 1 FROM media_scan_runs WHERE profile=? AND status='complete' "
                "AND completed>=? LIMIT 1",
                (name, slot),
            ).fetchone()
            for name in profiles
        )
        state["attempted"] = slot
        conn.execute(
            "UPDATE media_events SET payload_json=? WHERE id=?", (json.dumps(state), row[0])
        )
        return bool(profiles) and not completed


BACKGROUND_HASH_ID = b"media-import-background"


def background_window_open(store, schedule, now):
    """Persist activation and use the original slot as the fixed window start."""
    fingerprint = json.dumps(schedule.model_dump(mode="json") if schedule else None, sort_keys=True)
    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,payload_json FROM media_events "
            "WHERE event='calendar_background_checkpoint' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        state = json.loads(row[1]) if row else None
        if not state or state["fingerprint"] != fingerprint:
            state = {"fingerprint": fingerprint, "activated": now}
            if row:
                conn.execute(
                    "UPDATE media_events SET created=?,payload_json=? WHERE id=?",
                    (now, json.dumps(state), row[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO media_events(source_id,event,created,payload_json) "
                    "VALUES(NULL,'calendar_background_checkpoint',?,?)",
                    (now, json.dumps(state)),
                )
            return schedule is None
        if schedule is None:
            return True
        if schedule.cron is None:
            return False
        slot = latest_cron_slot(schedule.cron, schedule.timezone, now, hash_id=BACKGROUND_HASH_ID)
        return (
            slot is not None
            and slot > state["activated"]
            and now < slot + schedule.window_minutes * 60
        )
