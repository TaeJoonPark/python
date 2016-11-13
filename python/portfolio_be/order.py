#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import traceback
from MySQLdb.cursors import DictCursor
from models import DB_CONFIG

class MABOrder(object):
    def __init__(self, *args, **kwargs):
        self.conn = MySQLdb.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            passwd=DB_CONFIG['passwd'],
            db='SERVICE',
            port=int(DB_CONFIG['port']),
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor,
            use_unicode=True
        )
        self.conn.autocommit(False)
        self.cursor = self.conn.cursor()

    # 장바구니 select
    def get_order_info(self, order_id, shop_site_no=None):
        try:
            query = """
                SELECT
                    o.order_id,
                    o.order_id_alias,
                    o.e_id,
                    o.order_status,
                    os.order_shop_id,
                    os.shop_site_no,
                    os.shop_site_name,
                    oi.item_id,
                    oi.product_id,
                    oi.product_name,
                    oi.product_option,
                    oi.product_qty,
                    oi.product_price,
                    oi.discount_price,
                    oi.product_url,
                    oi.image_url
                FROM
                    SERVICE.AB_order o
                    INNER JOIN
                        SERVICE.AB_order_shop os
                        ON
                            o.order_id = os.order_id
                    INNER JOIN
                        SERVICE.AB_order_item oi
                        ON
                            os.order_shop_id = oi.order_shop_id
                WHERE
                    o.order_id = %s
            """
            bind = [int(order_id)]

            if shop_site_no is not None:
                query += """
                    AND os.shop_site_no = %s
                """
                bind.append(int(shop_site_no))

            bind = tuple(bind)
            self.cursor.execute(query, bind)
            result = self.cursor.fetchall()

            return result
        except Exception:
            self.disconnect()
            # raise Exception(traceback.format_exc())
            return False

    # 결제 예상 금액 업데이트
    def update_price_estimated(self, order_id, order_shop_id, price_total_est, price_discount_est, price_ship_est, shipping_discount, tax_est, coupon_applied, ship_addr_est, price_policy, shop_site_no=None):
        try:
            query = """
                UPDATE
                    SERVICE.AB_order_shop
                SET
                    price_est_done_flag = '1',
                    price_total_est = %s,
                    price_discount_est = %s,
                    price_ship_est = %s,
                    price_ship_discount_est = %s,
                    tax_est = %s,
                    coupon_applied_est = %s,
                    ship_addr_est = %s,
                    update_date = NOW()
                WHERE
                    order_shop_id = %s
            """
            bind = (price_total_est, price_discount_est, price_ship_est, shipping_discount, tax_est, coupon_applied, ship_addr_est, order_shop_id)
            self.cursor.execute(query, bind)

            # GAP_GROUP 예외 처리
            if shop_site_no is not None and shop_site_no == 9999:
                query = """
                    UPDATE
                        SERVICE.AB_order_shop
                    SET
                        price_est_done_flag = '1',
                        update_date = NOW()
                    WHERE
                        order_id = %s
                        AND shop_site_no IN (4, 5, 6, 30)
                """
                bind = (order_id,)
                self.cursor.execute(query, bind)
            # CARTERS_GROUP 예외 처리
            elif shop_site_no is not None and shop_site_no == 9998:
                query = """
                    UPDATE
                        SERVICE.AB_order_shop
                    SET
                        price_est_done_flag = '1',
                        update_date = NOW()
                    WHERE
                        order_id = %s
                        AND shop_site_no IN (8, 9)
                """
                bind = (order_id,)
                self.cursor.execute(query, bind)
            # CARTERS_GROUP 예외 처리
            elif shop_site_no is not None and shop_site_no == 9997:
                query = """
                    UPDATE
                        SERVICE.AB_order_shop
                    SET
                        price_est_done_flag = '1',
                        update_date = NOW()
                    WHERE
                        order_id = %s
                        AND shop_site_no IN (36, 26)
                """
                bind = (order_id,)
                self.cursor.execute(query, bind)

            # 쇼핑몰별 결졔 예정 금액이 모두 계산되었으면 결과를 AB_order에 업데이트
            query = """
                SELECT
                    COUNT(*) AS cnt
                FROM
                    SERVICE.AB_order_shop
                WHERE
                    order_id = %s
                    AND price_est_done_flag = '0'
            """
            bind = (order_id,)
            self.cursor.execute(query, bind)
            result = self.cursor.fetchone()

            if result['cnt'] == 0:
                query = """
                    SELECT
                        IFNULL(SUM(price_total_est), 0) AS price_total_est,
                        IFNULL(SUM(price_discount_est), 0) AS price_discount_est,
                        IFNULL(SUM(price_ship_est), 0) AS price_ship_est,
                        IFNULL(SUM(price_ship_discount_est), 0) AS price_ship_discount_est,
                        IFNULL(SUM(tax_est), 0) AS tax_est
                    FROM
                        SERVICE.AB_order_shop
                    WHERE
                        order_id = %s
                """
                bind = (order_id,)
                self.cursor.execute(query, bind)
                result = self.cursor.fetchone()
                # print result

                price_estimated_raw = (result['price_total_est'] - result['price_discount_est']) + (result['price_ship_est'] - result['price_ship_discount_est']) + result['tax_est']
                price_estimated_krw = price_estimated_raw * (price_policy['exchange_rate'] + price_policy['exchange_rate_fee_krw'])
                price_estimated = round(price_estimated_krw * price_policy['commission_rate'])

                query = """
                    UPDATE
                        AB_order
                    SET
                        price_estimated = %s,
                        order_status = '1',
                        update_date = NOW()
                    WHERE
                        order_id = %s
                """
                bind = (price_estimated, order_id)
                self.cursor.execute(query, bind)

            self.conn.commit()

            return True
        except Exception:
            self.conn.rollback()
            self.disconnect()
            # raise Exception(traceback.format_exc())
            return False

    def disconnect(self):
        try:
            self.conn.close()
        except Exception:
            raise Exception(traceback.format_exc())

