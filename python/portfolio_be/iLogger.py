#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
import time
import os
from controllers import AB_BASE_PATH


def set_logger(args):
    folder_name = args.get('folder_name', 'DEFAULT')
    logger_name = args.get('shop_site_name', 'DEFAULT')
    order_id = args.get('order_id')
    e_id = args.get('e_id')
    # queue_idx = args.get('queue_idx')

    base_path = AB_BASE_PATH
    logger = logging.getLogger(__name__)
    now_tmp = datetime.now()
    now = now_tmp.strftime("%H%M%S")

    folder = base_path +'/log/{y}/{m}/{d}/{fn}'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"), fn=folder_name)
    if not os.path.exists(folder):
        os.makedirs(folder)

    logger.setLevel(logging.DEBUG)
    # create a file handler
    log_full_path = "{logpath}/{order_id}_{e_id}_{shop_site_name}_{now}_{microsec}.log".format(logpath=folder, order_id=order_id, e_id=e_id, shop_site_name=logger_name, now=now, microsec=int(round(time.time() * 1000)))
    handler = logging.FileHandler(log_full_path)
    handler.setLevel(logging.DEBUG)
    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(handler)
    return logger