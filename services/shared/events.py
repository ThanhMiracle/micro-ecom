import json
import pika
from typing import Any, Callable, Dict

EXCHANGE = "microshop.events"

def publish(rabbitmq_url: str, event_type: str, payload: Dict[str, Any]) -> None:
    conn = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    body = json.dumps({"type": event_type, "payload": payload}).encode("utf-8")
    ch.basic_publish(exchange=EXCHANGE, routing_key=event_type, body=body, properties=pika.BasicProperties(delivery_mode=2))
    conn.close()

def consume(
    rabbitmq_url: str,
    queue_name: str,
    bindings: list[str],
    handler: Callable[[str, Dict[str, Any]], None],
) -> None:
    conn = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    ch.queue_declare(queue=queue_name, durable=True)

    for rk in bindings:
        ch.queue_bind(queue=queue_name, exchange=EXCHANGE, routing_key=rk)

    def _cb(chx, method, props, body: bytes):
        try:
            msg = json.loads(body.decode("utf-8"))
            handler(msg.get("type", method.routing_key), msg.get("payload", {}))
            chx.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            # if handler fails, requeue for retry
            chx.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    ch.basic_qos(prefetch_count=10)
    ch.basic_consume(queue=queue_name, on_message_callback=_cb)
    ch.start_consuming()
