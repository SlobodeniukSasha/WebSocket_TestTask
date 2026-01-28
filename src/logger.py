import logging


def make_logger(module_name):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(module_name)

    logger_formatter = logging.Formatter('[%(asctime)s]:[%(module)s] - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(logger_formatter)
    logger.addHandler(handler)
    return logger