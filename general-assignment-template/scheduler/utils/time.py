from datetime import timedelta, timezone as dt_tz

JST = dt_tz(timedelta(hours=9))

def to_jst_iso(dt_utc):
    return dt_utc.astimezone(JST).isoformat()