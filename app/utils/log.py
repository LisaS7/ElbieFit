import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

root = logging.getLogger()
root.setLevel(LOG_LEVEL)

for h in list(root.handlers):  # pragma: no cover
    root.removeHandler(h)

noisy_loggers = [
    "botocore",
    "boto3",
    "urllib3",
]

for name in noisy_loggers:
    logging.getLogger(name).setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(FORMAT))
root.addHandler(handler)

logging.basicConfig(level=LOG_LEVEL, format=FORMAT, stream=sys.stdout, force=True)

logger = logging.getLogger("elbiefit")
logger.setLevel(LOG_LEVEL)
logger.propagate = True

logger.debug(f"Logger initialised level={LOG_LEVEL}")
