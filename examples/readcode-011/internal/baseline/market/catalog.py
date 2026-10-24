"""Restaurants, menus and opening hours."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


class NotFound(Exception):
    pass


def get_restaurant(conn, restaurant_id: str):
    row = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
    if row is None:
        raise NotFound(f"No such restaurant: {restaurant_id}")
    return row


def menu(conn, restaurant_id: str) -> list[dict]:
    get_restaurant(conn, restaurant_id)
    rows = conn.execute("SELECT id, name, price FROM menu_items WHERE restaurant_id = ? ORDER BY name",
                        (restaurant_id,)).fetchall()
    return [dict(r) for r in rows]


def _hhmm(text: str) -> time:
    h, m = text.split(":")
    return time(int(h), int(m))


def local_time(restaurant, now_s: float) -> datetime:
    """The restaurant's wall-clock time at the given moment."""
    now_utc = datetime.fromtimestamp(now_s, timezone.utc)
    return now_utc.astimezone(ZoneInfo(restaurant["timezone"]))


def is_open(restaurant, now_s: float) -> bool:
    """Open hours are local wall-clock times. Hours that end after midnight
    (e.g. 18:00-02:00) wrap into the next day."""
    t = local_time(restaurant, now_s).time()
    opens, closes = _hhmm(restaurant["opens_at"]), _hhmm(restaurant["closes_at"])
    if opens <= closes:
        return opens <= t < closes
    return t >= opens or t < closes


def list_restaurants(conn, now_s: float, open_only: bool = False) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM restaurants ORDER BY name").fetchall():
        open_now = is_open(r, now_s)
        if open_only and not open_now:
            continue
        out.append({"id": r["id"], "name": r["name"], "open_now": open_now,
                    "hours": f"{r['opens_at']}-{r['closes_at']}",
                    "local_time": local_time(r, now_s).strftime("%a %H:%M")})
    return out
