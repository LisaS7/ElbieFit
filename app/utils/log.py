import logging
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


logging.basicConfig(level=LOG_LEVEL, format=FORMAT, stream=sys.stdout, force=True)

logger = logging.getLogger("elbiefit")
