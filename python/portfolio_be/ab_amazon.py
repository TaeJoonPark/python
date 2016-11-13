#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import inspect
import json
import traceback
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lib import iCheck
from lib.iLogger import set_logger

class ABShopModAmazon(object):
    def __init__(self, **kwargs):
        self.display = None
        # msg 객체
        self.msg = None
        self.result_data = None
        # log 객체
        self.ilogger = kwargs.get('ilogger')
        self.order_info = {}
        self.user_id = kwargs.get('login_id')
        self.user_passwd = kwargs.get('login_passwd')
        self.e_id = kwargs.get('e_id')
        self.country_code = '840'
        self.shop_site_name = 'AMAZON'
        self.shop_site_no = 1
        self.order_info['e_id'] = self.e_id
        self.order_info['country_code'] = self.country_code
        self.order_info['shop_site_name'] = self.shop_site_name
        self.order_info['shop_site_no'] = self.shop_site_no

def do_estimate_price(**kwargs):
    cart_info = kwargs.get('order_info')

    result = {
        'price_info_est': {
            'total_price': 0,
            'discount_price': 0,
            'shipping_fee': 0,
            'shipping_discount': 0,
            'tax_fee': 0
        },
        'coupon_applied': [],
        "ship_addr_est": "NA"
    }
    for row in cart_info:
        result['price_info_est']['total_price'] += (row['product_price'] * row['product_qty'])

    return result
