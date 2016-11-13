#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import traceback
from MySQLdb.cursors import DictCursor
from models import DB_CONFIG_HDP as DB_CONFIG
from datetime import datetime, timedelta

class MABCoupon(object):
    def __init__(self, *args, **kwargs):
        self.conn = MySQLdb.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            passwd=DB_CONFIG['passwd'],
            db='CRAWLING',
            port=int(DB_CONFIG['port']),
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor,
            use_unicode=True
        )
        self.conn.autocommit(False)
        self.cursor = self.conn.cursor()

    def get_site_coupon(self, shop_site_name):
        try:
            if shop_site_name == "GAP":
                query = """
                    SELECT
                        DISTINCT(coupon_code)
                    FROM
                        crawled_coupon_deal
                    WHERE
                        reg_date >= %s
                        AND (
                            coupon_target_site_name = 'GAP'
                            OR coupon_target_site_name = 'BANANAREPUBLIC'
                            OR coupon_target_site_name = 'ATHLETA'
                            OR coupon_target_site_name = 'OLDNAVY'
                        )
                        AND coupon_code is not null
                        AND coupon_code != ''
                """
                bind = ((datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),)
            elif shop_site_name == "CARTERS":
                query = """
                    SELECT
                        DISTINCT(coupon_code)
                    FROM
                        crawled_coupon_deal
                    WHERE
                        reg_date >= %s
                        AND (
                            coupon_target_site_name = 'CARTERS'
                            OR coupon_target_site_name = 'OSHKOSH'
                        )
                        AND coupon_code is not null
                        AND coupon_code != ''
                """
                bind = ((datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),)
            elif shop_site_name == "BEAUTY":
                query = """
                    SELECT
                        DISTINCT(coupon_code)
                    FROM
                        crawled_coupon_deal
                    WHERE
                        reg_date >= %s
                        AND (
                            coupon_target_site_name = 'BEAUTY'
                            OR coupon_target_site_name = 'DRUGSTORE'
                        )
                        AND coupon_code is not null
                        AND coupon_code != ''
                """
                bind = ((datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),)
            else:
                query = """
                    SELECT
                        DISTINCT(coupon_code)
                    FROM
                        crawled_coupon_deal
                    WHERE
                        reg_date >= %s
                        and coupon_target_site_name = %s
                        AND coupon_code is not null
                        AND coupon_code != ''
                """
                bind = ((datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"), shop_site_name)
            self.cursor.execute(query, bind)
            result = self.cursor.fetchall()

            return result
        except:
            self.disconnect()
            return False

    def disconnect(self):
        try:
            self.conn.close()
        except Exception:
            raise Exception(traceback.format_exc())
