from loguru import logger
from prometheus_client import Counter, start_http_server

_NAMESPACE = "pwdreminder"

runs = Counter(
    "runs",
    "How many task main task has been run",
    namespace=_NAMESPACE,
)


errors = Counter(
    "errors",
    "Errors counter",
    namespace=_NAMESPACE,
)


notifications_sent = Counter(
    "notifications_sent",
    "How many notifications were sent",
    ["kind"],
    namespace=_NAMESPACE,
)
notifications_sent.labels("email")
notifications_sent.labels("portals")


def start_server() -> None:
    logger.info("Starting metrics server")
    start_http_server(8000)
