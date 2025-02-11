# src/utils.py

import logging

def setup_logging(log_file_path=None):
    logger = logging.getLogger("macc_posco")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_file_path:
        fh = logging.FileHandler(log_file_path)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
