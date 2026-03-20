import json
import os
import time

from config import CHECK_IN_DURATION_SECONDS, PING_COOLDOWN_SECONDS, STATE_FILE


class StateManager:
    def __init__(self, filepath: str = STATE_FILE):
        self._filepath = filepath
        self._data: dict = self._empty()

    def _empty(self) -> dict:
        return {"panel": None, "ping_channel_id": None, "checkins": {}, "ping_cooldowns": {}}

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def load(self) -> None:
        if not os.path.exists(self._filepath):
            self._data = self._empty()
            return
        try:
            with open(self._filepath, "r") as f:
                data = json.load(f)
            # Basic schema validation
            if not isinstance(data.get("checkins"), dict):
                raise ValueError("bad schema")
            self._data = data
            self._data.setdefault("panel", None)
            self._data.setdefault("ping_channel_id", None)
            self._data.setdefault("ping_cooldowns", {})
        except Exception as e:
            print(f"[state] Failed to load state ({e}), starting fresh.")
            self._data = self._empty()

    # actually update the json by creating a temp file and replacing the current json
    def save(self) -> None:
        tmp = self._filepath + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._filepath)

    # -------------------------------------------------------------------------
    # Panel
    # -------------------------------------------------------------------------

    def get_panel(self) -> dict | None:
        return self._data.get("panel")

    def set_panel(self, channel_id: int | None, message_id: int | None) -> None:
        if channel_id is None or message_id is None:
            self._data["panel"] = None
        else:
            self._data["panel"] = {"channel_id": channel_id, "message_id": message_id}
        self.save()

    def clear_panel(self) -> None:
        self._data["panel"] = None
        self.save()

    # -------------------------------------------------------------------------
    # Ping channel
    # -------------------------------------------------------------------------

    def get_ping_channel_id(self) -> int | None:
        return self._data.get("ping_channel_id")

    def set_ping_channel_id(self, channel_id: int) -> None:
        self._data["ping_channel_id"] = channel_id
        self.save()

    # -------------------------------------------------------------------------
    # Check-in / Check-out
    # -------------------------------------------------------------------------

    def check_in(self, user_id: int, display_name: str, location: str) -> str:
        """
        Returns:
          "already_here"  - user was already at this location (caller should check out)
          "switched"      - user moved from another location
          "checked_in"    - fresh check-in
        """
        uid = str(user_id)
        existing = self._data["checkins"].get(uid)

        if existing:
            if existing["location"] == location:
                return "already_here"
            # Switch location
            del self._data["checkins"][uid]
            result = "switched"
        else:
            result = "checked_in"

        self._data["checkins"][uid] = {
            "location": location,
            "display_name": display_name,
            "expires_at": time.time() + CHECK_IN_DURATION_SECONDS,
        }
        self.save()
        return result

    def check_out(self, user_id: int) -> bool:
        uid = str(user_id)
        if uid in self._data["checkins"]:
            del self._data["checkins"][uid]
            self.save()
            return True
        return False

    def is_checked_in(self, user_id: int) -> bool:
        return str(user_id) in self._data["checkins"]

    def get_location(self, user_id: int) -> str | None:
        entry = self._data["checkins"].get(str(user_id))
        return entry["location"] if entry else None

    def get_checkins_at(self, location: str) -> list[dict]:
        """Returns all non-expired check-ins at the given location."""
        now = time.time()
        return [
            {"user_id": uid, **entry}
            for uid, entry in self._data["checkins"].items()
            if entry["location"] == location and entry["expires_at"] > now
        ]

    # -------------------------------------------------------------------------
    # Expiry
    # -------------------------------------------------------------------------

    def prune_expired(self) -> list[int]:
        """Remove expired check-ins. Returns list of pruned user IDs."""
        now = time.time()
        expired = [
            uid for uid, entry in self._data["checkins"].items()
            if entry["expires_at"] <= now
        ]
        if expired:
            for uid in expired:
                del self._data["checkins"][uid]
            self.save()
        return [int(uid) for uid in expired]

    # -------------------------------------------------------------------------
    # Ping cooldown
    # -------------------------------------------------------------------------

    def can_ping(self, user_id: int, location: str) -> bool:
        cooldowns = self._data["ping_cooldowns"].get(location, {})
        last = cooldowns.get(str(user_id), 0)
        return time.time() - last >= PING_COOLDOWN_SECONDS

    def record_ping(self, user_id: int, location: str) -> None:
        self._data["ping_cooldowns"].setdefault(location, {})
        self._data["ping_cooldowns"][location][str(user_id)] = time.time()
        self.save()

    def seconds_until_can_ping(self, user_id: int, location: str) -> float:
        cooldowns = self._data["ping_cooldowns"].get(location, {})
        last = cooldowns.get(str(user_id), 0)
        return max(0.0, PING_COOLDOWN_SECONDS - (time.time() - last))
