import logging
import sys


def setup_logging(service_name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format=f'{{"service":"{service_name}","level":"%(levelname)s","message":"%(message)s"}}',
        stream=sys.stdout,
    )
    return logging.getLogger(service_name)
