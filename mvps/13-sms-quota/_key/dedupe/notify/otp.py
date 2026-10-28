"""Login codes. The auth service calls send_otp when a customer asks for a code (codes expire in 10 minutes)."""
from . import log

BODY = "Your Shopwell login code is {code}. It expires in 10 minutes."


def send_otp(client, conn, phone, code, now):
    for attempt in range(3):
        try:
            resp = client.send(phone, BODY.format(code=code), client_ref=f"otp:{phone}:{code}")
        except client.Timeout:
            log.record(conn, now, "otp", phone, "timeout", None)
            continue
        except client.RateLimited as e:
            log.record(conn, now, "otp", phone, "rate_limited", e.headers)
            conn.commit()
            return False
        log.record(conn, now, "otp", phone, "sent", resp["headers"])
        conn.commit()
        return True
    conn.commit()
    return False
