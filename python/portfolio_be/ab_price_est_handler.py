#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import inspect
import json
import traceback
import ConfigParser

from models.queue import MABQueue
from models.order import MABOrder
from models.membership import MABMembership
from models.coupon import MABCoupon
from models.snapshot import MABSnapshot

from lib.iLogger import set_logger
from lib.slack import report_error_slack


class ABPriceEstHandler(object):
    def __init__(self):
        self.m_queue = MABQueue()
        self.m_order = MABOrder()
        self.m_membership = MABMembership()
        self.m_coupon = MABCoupon()
        self.m_snapshot = MABSnapshot()

        self.task_info = []

    def get_in_progress_task_count(self):
        try:
            return self.m_queue.get_running_process_count('0')
        except:
            print "ERROR0"

    def get_task_info(self):
        try:
            self.task_info = self.m_queue.get_queue_seq_todo('0')

        except:
            print "ERROR"

    def update_task_status(self, status):
        try:
            result = self.m_queue.update_queue_status(self.task_info['seq'], status)

            if result == False:
                raise Exception
        except:
            print traceback.format_exc()
            print "ERROR1"

    def get_order_shop_info(self, order_id, shop_site_no):
        try:
            result = self.m_order.get_order_info(order_id, shop_site_no)

            if result == False:
                raise Exception
            else:
                self.order_info = result
        except:
            print traceback.format_exc()
            print "ERROR2"

    def get_site_account(self, shop_site_no, order_id):
        # AMAZON 예외 처리
        if shop_site_no == 1:
            self.site_account = {
                "user_id": "",
                "user_passwd": ""
            }
        else:
            try:
                result = self.m_membership.get_available_shop_dummy_account(shop_site_no, order_id)

                if result == False:
                    return False
                else:
                    self.site_account = result
                    return True
            except:
                print traceback.format_exc()
                print "ERROR3"
                return False

    def get_shipping_addresses(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.read(os.path.abspath(os.path.dirname(__file__)) + '/conf/shipping_address.conf')

            result = {}
            states = config.sections()
            for state in states:
                result[state] = dict(config.items(state))

            return result
        except:
            print traceback.format_exc()
            print "ERROR4"

    def update_price_estimated(self, order_id, order_shop_id, price_total_est, price_discount_est, price_ship_est, shipping_discount, tax_est, coupon_applied, ship_addr_est, price_policy, shop_site_no):
        try:
            result = self.m_order.update_price_estimated(order_id, order_shop_id, price_total_est, price_discount_est, price_ship_est, shipping_discount, tax_est, coupon_applied, ship_addr_est, price_policy, shop_site_no)

            if result == False:
                raise Exception
            else:
                return True
        except:
            print traceback.format_exc()
            print "ERROR5"

    def get_site_coupon(self, shop_site_name):
        try:
            result = self.m_coupon.get_site_coupon(shop_site_name)

            if result == False:
                raise Exception
            else:
                coupons = []
                for row in result:
                    coupons.append(row['coupon_code'])

                return coupons
        except:
            print traceback.format_exc()
            print "ERROR6"


def get_process_count():
    import subprocess
    import shlex
    proc1 = subprocess.Popen(shlex.split('ps aux'), stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(shlex.split('grep ab_price_est_handler'), stdin=proc1.stdout, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    proc1.stdout.close()  # Allow proc1 to receive a SIGPIPE if proc2 exits.
    # out, err = proc2.communicate()
    # print('out: {0}'.format(out))
    # print('err: {0}'.format(err))

    process_list = proc2.communicate()[0].split('\n')
    process_count = len(process_list) - 1

    return process_count


def estimate_price():
    proc = ABPriceEstHandler()
    proc_cnt = proc.get_in_progress_task_count()

    if proc_cnt >= 10:
        sys.exit(1)

    proc.get_task_info()

    if proc.task_info != False:
        order_id = proc.task_info['order_id']
        shop_site_no = proc.task_info['shop_site_no']

        proc.get_order_shop_info(order_id, proc.task_info['shop_site_no'])

        if len(proc.order_info) == 0:
            proc.update_task_status('9')
            print "NO AVALIABLE ORDER ITEMS"
            sys.exit(1)

        order_shop_id = proc.order_info[0]['order_shop_id']
        e_id = proc.order_info[0]['e_id']
        exchange_rate = proc.m_snapshot.get_gosi_exchange_rate()

        if proc.task_info['shop_site_name'].upper() == "GAP_GROUP":
            shop_site_name = "GAP"
        elif proc.task_info['shop_site_name'].upper() == "CARTERS_GROUP":
            shop_site_name = "CARTERS"
        elif proc.task_info['shop_site_name'].upper() == "BEAUTY_GROUP":
            shop_site_name = "ㅑBEAUTY"
        else:
            shop_site_name = proc.task_info['shop_site_name'].upper()

        args = {
            'folder_name': 'ab_price_estimate',
            'shop_site_name': shop_site_name,
            'order_id': order_id,
            'e_id': e_id,
        }
        ilogger = set_logger(args)
        ilogger.info('--- START PRICE ESTIMATION ---')

        module = "controllers.ab_%s" % shop_site_name.lower()
        shop_ctrl = __import__(module, fromlist=[''])
        ilogger.info('[MODULE IMPORTED] ' + module)

        result_site_account = proc.get_site_account(shop_site_no, order_id)
        if result_site_account is False:
            proc.update_task_status('3')
            ilogger.info('[UPDATE TASK STATUS] 3 - NO AVAIL SITE ACCOUNTS')
            report_error_slack(
                title='[UPDATE TASK STATUS] 3 - NO AVAIL SITE ACCOUNTS',
                order_id=order_id,
                e_id=e_id,
                shop_site_id=shop_site_no,
                shop_site_name=shop_site_name,
                module=inspect.stack()[0][3] + "()@" + os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/" + inspect.getfile(inspect.currentframe()),
                log_file_path=ilogger.handlers[0].baseFilename
            )
            sys.exit(1)
        else:
            ilogger.info('[SITE ACCOUNT INFO]')
            ilogger.info(json.dumps(proc.site_account))

        coupon_list = proc.get_site_coupon(shop_site_name)

        proc.update_task_status('1')
        ilogger.info('[UPDATE TASK STATUS] 1')

        result = shop_ctrl.do_estimate_price(
            order_id=order_id,
            e_id=e_id,
            order_shop_id=order_shop_id,
            order_info=proc.order_info,
            login_id=proc.site_account['user_id'],
            login_passwd=proc.site_account['user_passwd'],
            shipping_addr_info=proc.get_shipping_addresses(),
            site_coupon=coupon_list,
            ilogger=ilogger
        )

        ilogger.info('[EST. PRICE RESULT]')
        ilogger.info(json.dumps(result))

        if result is not False:
            if not (
                ('total_price' in result['price_info_est'])
                and ('discount_price' in result['price_info_est'])
                and ('shipping_fee' in result['price_info_est'])
                and ('shipping_discount' in result['price_info_est'])
                and ('tax_fee' in result['price_info_est'])
            ):
                proc.update_task_status('3')
                ilogger.info('[UPDATE TASK STATUS] 3 - EST. PRICE ERROR')
                report_error_slack(
                    title='[UPDATE TASK STATUS] 3 - EST. PRICE ERROR',
                    order_id=order_id,
                    e_id=e_id,
                    shop_site_id=shop_site_no,
                    shop_site_name=shop_site_name,
                    module=inspect.stack()[0][3] + "()@" + os.path.dirname(
                        os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/" + inspect.getfile(
                        inspect.currentframe()),
                    log_file_path=ilogger.handlers[0].baseFilename
                )
                sys.exit(1)

            price_policy = {
                "commission_rate": 1.098,
                "exchange_rate": exchange_rate,
                "exchange_rate_fee_krw": 20
            }

            if len(result['coupon_applied']) > 0:
                coupon_applied = ','.join(result['coupon_applied'])
            else:
                coupon_applied = ""

            final_result = proc.update_price_estimated(
                order_id,
                order_shop_id,
                result['price_info_est']['total_price'],
                result['price_info_est']['discount_price'],
                result['price_info_est']['shipping_fee'],
                result['price_info_est']['shipping_discount'],
                result['price_info_est']['tax_fee'],
                coupon_applied,
                result['ship_addr_est'],
                price_policy,
                shop_site_no
            )
            if final_result is True:
                proc.update_task_status('2')
                ilogger.info('[UPDATE TASK STATUS] 2')
        else:
            proc.update_task_status('3')
            ilogger.info('[UPDATE TASK STATUS] 3')

        ilogger.info('--- END PRICE ESTIMATION ---')

        for handler in ilogger.handlers:
            handler.close()
            ilogger.removeHandler(handler)

if __name__ == '__main__':
    estimate_price()
