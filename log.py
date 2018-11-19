import logging
import datetime

def setup_custom_logger(name, log_level=logging.INFO):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    
    fh = logging.FileHandler('totenkun_'  + '_'+str(datetime.date.today())+'.log')
    logger.addHandler(fh)
    fh.setFormatter(formatter)
    return logger