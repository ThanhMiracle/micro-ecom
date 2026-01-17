import os
import threading
from fastapi import FastAPI
from shared.events import consume
from .emailer import send_email

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

app = FastAPI(title="notification-service")

def handler(event_type: str, payload: dict):
    if event_type == "user.registered":
        email = payload["email"]
        verify_url = payload["verify_url"]
        send_email(
            email,
            "Verify your MicroShop account",
            f"<h3>Welcome to MicroShop</h3><p>Please verify your email:</p><p><a href='{verify_url}'>{verify_url}</a></p>",
        )

    elif event_type == "payment.succeeded":
        email = payload["email"]
        order_id = payload["order_id"]
        total = payload["total"]
        send_email(
            email,
            "Payment confirmed - MicroShop",
            f"<h3>Payment successful</h3><p>Order <b>#{order_id}</b> is paid.</p><p>Total: <b>${total}</b></p>",
        )

@app.on_event("startup")
def startup():
    # Run consumer in background thread inside the container
    t = threading.Thread(
        target=lambda: consume(
            rabbitmq_url=RABBITMQ_URL,
            queue_name="notification-service",
            bindings=["user.registered", "payment.succeeded"],
            handler=handler,
        ),
        daemon=True,
    )
    t.start()

@app.get("/health")
def health():
    return {"ok": True}
