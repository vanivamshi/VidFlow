import json
import logging
from typing import Callable, Optional

from confluent_kafka import Consumer, Producer

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    def publish(self, topic: str, key: str, value: dict) -> None:
        self._producer.produce(
            topic,
            key=key.encode(),
            value=json.dumps(value).encode(),
            callback=self._delivery_callback,
        )
        self._producer.flush()

    @staticmethod
    def _delivery_callback(err, msg):
        if err:
            logger.error("Kafka delivery failed: %s", err)
        else:
            logger.debug("Delivered to %s [%s]", msg.topic(), msg.partition())


class KafkaConsumer:
    def __init__(self, bootstrap_servers: str, group_id: str, topics: list[str]):
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
        })
        self._consumer.subscribe(topics)

    def consume(self, handler: Callable[[dict], None]) -> None:
        logger.info("Starting Kafka consumer...")
        try:
            while True:
                msg = self._consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error("Consumer error: %s", msg.error())
                    continue
                payload = json.loads(msg.value().decode())
                handler(payload)
        except KeyboardInterrupt:
            pass
        finally:
            self._consumer.close()
