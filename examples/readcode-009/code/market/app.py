"""HTTP API for the delivery marketplace.

Customers authenticate with their API key; operations staff (support, finance,
dispatch) with the admin key. The payment provider calls /webhooks/provider.
The provider client and the clock are passed in so they can be replaced in tests.
"""
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from . import catalog, db, dispatch, orders, payments, payouts
from .pricing import PricingError, quote
from .seed import ADMIN_KEY


class CartItem(BaseModel):
    item_id: str
    quantity: int = 1


class OrderIn(BaseModel):
    restaurant_id: str
    items: list[CartItem]
    promo_code: Optional[str] = None
    payment_method: str = "pm_card_visa"


class QuoteIn(BaseModel):
    restaurant_id: str
    items: list[CartItem]
    promo_code: Optional[str] = None


class RefundIn(BaseModel):
    amount: int = Field(gt=0)


def error(status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"message": message})


def order_json(conn, row) -> dict:
    return {**{k: row[k] for k in row.keys()}, "lines": orders.lines(conn, row["id"])}


def create_app(db_path: str, provider, clock=time.time, admin_key: str = ADMIN_KEY) -> FastAPI:
    app = FastAPI(title="Delivery marketplace")
    conn = db.connect(db_path)
    now = lambda: db.now_ms(clock)  # noqa: E731

    def customer(authorization: str = Header(default="")) -> str:
        scheme, _, token = authorization.partition(" ")
        row = conn.execute("SELECT id FROM customers WHERE api_key = ?", (token,)).fetchone() if scheme == "Bearer" else None
        if row is None:
            raise error(401, "Invalid or missing API key.")
        return row["id"]

    def staff(authorization: str = Header(default="")) -> None:
        if authorization != f"Bearer {admin_key}":
            raise error(403, "Operations staff only.")

    def run(fn, *args):
        try:
            return fn(*args)
        except (catalog.NotFound, orders.OrderError) as e:
            raise error(404 if isinstance(e, catalog.NotFound) else 400, str(e))
        except (PricingError, payments.PaymentError, dispatch.NoCourier) as e:
            raise error(400, str(e))

    # ---- customers
    @app.get("/restaurants")
    def restaurants(open_now: bool = Query(default=False)):
        return catalog.list_restaurants(conn, clock(), open_only=open_now)

    @app.get("/restaurants/{restaurant_id}/menu")
    def menu(restaurant_id: str):
        return run(catalog.menu, conn, restaurant_id)

    @app.post("/quote")
    def get_quote(body: QuoteIn, _: str = Depends(customer)):
        return run(quote, conn, body.restaurant_id, [i.model_dump() for i in body.items], body.promo_code)

    @app.post("/orders")
    def place_order(body: OrderIn, cust: str = Depends(customer)):
        restaurant = run(catalog.get_restaurant, conn, body.restaurant_id)
        if not catalog.is_open(restaurant, clock()):
            raise error(400, f"{restaurant['name']} is closed right now.")
        order_id = run(orders.place, conn, provider, cust, body.restaurant_id, [i.model_dump() for i in body.items],
                       body.promo_code, body.payment_method, now())
        return order_json(conn, orders.get(conn, order_id))

    @app.get("/orders/{order_id}")
    def get_order(order_id: str, cust: str = Depends(customer)):
        return order_json(conn, run(orders.get, conn, order_id, cust))

    @app.post("/orders/{order_id}/cancel")
    def cancel_order(order_id: str, cust: str = Depends(customer)):
        run(orders.cancel, conn, provider, order_id, now(), cust)
        return order_json(conn, orders.get(conn, order_id))

    # ---- payment provider
    @app.post("/webhooks/provider")
    def provider_webhook(event: dict):
        return {"result": payments.handle_event(conn, event, now())}

    # ---- operations staff
    @app.post("/admin/orders/{order_id}/accept", dependencies=[Depends(staff)])
    def accept(order_id: str):
        run(orders.accept, conn, order_id, now())
        return order_json(conn, orders.get(conn, order_id))

    @app.post("/admin/orders/{order_id}/dispatch", dependencies=[Depends(staff)])
    def assign(order_id: str):
        courier = run(dispatch.assign, conn, order_id, now())
        return {"order_id": order_id, "courier_id": courier}

    @app.post("/admin/orders/{order_id}/picked_up", dependencies=[Depends(staff)])
    def picked_up(order_id: str):
        run(orders.picked_up, conn, order_id, now())
        return order_json(conn, orders.get(conn, order_id))

    @app.post("/admin/orders/{order_id}/delivered", dependencies=[Depends(staff)])
    def delivered(order_id: str):
        run(orders.delivered, conn, order_id, now())
        return order_json(conn, orders.get(conn, order_id))

    @app.post("/admin/orders/{order_id}/refund", dependencies=[Depends(staff)])
    def refund(order_id: str, body: RefundIn):
        refund_id = run(payments.refund, conn, provider, order_id, body.amount, now())
        return {"refund_id": refund_id, "status": "pending"}

    @app.get("/admin/couriers", dependencies=[Depends(staff)])
    def couriers():
        return {"available": dispatch.available_couriers(conn),
                "all": [dict(r) for r in conn.execute("SELECT * FROM couriers ORDER BY id")]}

    @app.post("/admin/payouts/run", dependencies=[Depends(staff)])
    def run_payouts():
        return payouts.run(conn, now())

    @app.get("/admin/reconciliation", dependencies=[Depends(staff)])
    def reconciliation():
        """Orders whose charge does not equal what the restaurant is paid on plus fees and tax."""
        out = []
        for o in conn.execute("SELECT * FROM orders ORDER BY created_ms").fetchall():
            net = sum(l["net"] for l in orders.lines(conn, o["id"]))
            expected = net + o["delivery_fee"] + o["tax"]
            if expected != o["total"]:
                out.append({"order_id": o["id"], "total": o["total"], "lines_net_plus_fees": expected,
                            "difference": o["total"] - expected})
        return {"mismatched": out}

    return app
