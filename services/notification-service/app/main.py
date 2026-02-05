import os
import threading
import logging
from fastapi import FastAPI
from shared.events import consume
from .emailer import send_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

app = FastAPI(title="notification-service")


def handler(event_type: str, payload: dict):
    """
    Handle events consumed from RabbitMQ.
    Expected payload for user.registered:
      { "email": "...", "verify_url": "..." }
    """
    try:
        if event_type == "user.registered":
            email = payload["email"]
            verify_url = payload["verify_url"]

            send_email(
                to_email=email,
                subject="Verify your MicroShop account",
                html_body=(
                    "<h3>Welcome to MicroShop</h3>"
                    "<p>Please verify your email:</p>"
                    f"<p><a href='{verify_url}'>{verify_url}</a></p>"
                ),
            )
            logger.info("Sent verification email to %s", email)

        elif event_type == "payment.succeeded":
            email = payload["email"]
            order_id = payload["order_id"]
            total = payload["total"]

            send_email(
                to_email=email,
                subject="Payment confirmed - MicroShop",
                html_body=(
                    "<h3>Payment successful</h3>"
                    f"<p>Order <b>#{order_id}</b> is paid.</p>"
                    f"<p>Total: <b>${total}</b></p>"
                ),
            )
            logger.info("Sent payment email to %s (order #%s)", email, order_id)

        else:
            logger.info("Ignoring event_type=%s payload=%s", event_type, payload)

    except KeyError as e:
        logger.exception("Missing required field %s in payload: %s", e, payload)
    except Exception:
        logger.exception("Handler failed for event_type=%s payload=%s", event_type, payload)


@app.on_event("startup")
def startup():
    """
    Run consumer in background thread inside the container.
    """
    def run_consumer():
        try:
            logger.info("Starting RabbitMQ consumer...")
            consume(
                rabbitmq_url=RABBITMQ_URL,
                queue_name="notification-service",
                bindings=["user.registered", "payment.succeeded"],
                handler=handler,
            )
        except Exception:
            logger.exception("RabbitMQ consumer crashed")

    t = threading.Thread(target=run_consumer, daemon=True)
    t.start()
    logger.info("Consumer thread started")


@app.get("/health")
def health():
    return {"ok": True}
