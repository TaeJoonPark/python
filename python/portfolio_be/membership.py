#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import traceback
from MySQLdb.cursors import DictCursor
from models import DB_CONFIG

class MABMembership(object):
    def __init__(self, *args, **kwargs):
        self.conn = MySQLdb.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            passwd=DB_CONFIG['passwd'],
            db='MEMBERSHIP',
            port=int(DB_CONFIG['port']),
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor,
            use_unicode=True
        )
        self.conn.autocommit(False)
        self.cursor = self.conn.cursor()

    def get_available_shop_dummy_account(self, shop_site_no, order_id):
        try:
            query = """
                SELECT
                    seq,
                    user_id,
                    user_passwd
                FROM
                    MEMBERSHIP.shop_account_dummy
                WHERE
                    shop_site_no = %s
                    AND status = '0'
                ORDER BY
                    seq ASC
                LIMIT 1
            """
            bind = (shop_site_no,)
            self.cursor.execute(query, bind)
            result = self.cursor.fetchone()

            if self.cursor.rowcount > 0:
                query = """
                    UPDATE
                        MEMBERSHIP.shop_account_dummy
                    SET
                        status = '1',
                        order_id = %s,
                        update_date = NOW()
                    WHERE
                        seq = %s
                """
                bind = (order_id, result['seq'])
                self.cursor.execute(query, bind)

                if self.cursor.rowcount > 0:
                    self.conn.commit()
                    return result
                else:
                    raise Exception
            else:
                return False
        except Exception:
            self.conn.rollback()
            self.disconnect()
            # raise Exception(traceback.format_exc())
            return False

    def update_shop_dummy_account_status(self, dummy_accnt_seq, status):
        try:
            query = """
                UPDATE
                    shop_account_dummy
                SET
                    status = %s,
                    update_date = NOW()
                WHERE
                    seq = %s
            """
            bind = (status, dummy_accnt_seq)
            self.cursor.execute(query, bind)

            if self.cursor.rowcount > 0:
                self.conn.commit()
                return True
            else:
                self.conn.rollback()
                return False
        except Exception:
            self.conn.rollback()
            self.disconnect()
            # raise Exception(traceback.format_exc())
            return False

    def get_member_ship_address(self, delivery_seq):
        try:
            query = """
                SELECT
                    e_id,
                    name,
                    nick_addr,
                    address1,
                    address2,
                    zip_code,
                    zip_code_new,
                    telephone,
                    cell_phone,
                FROM
                    MEMBERSHIP.delivery_info
                WHERE
                    delivery_seq = %s
            """
            bind = (delivery_seq,)
            self.cursor.execute(query, bind)
            result = self.cursor.fetchone()

            if self.cursor.rowcount > 0:
                return result
            else:
                return False
        except Exception:
            self.conn.rollback()
            self.disconnect()
            # raise Exception(traceback.format_exc())
            return False

    def get_site_account_to_reset(self):
        try:
            query = """
                SELECT
                    seq,
                    user_id,
                    user_passwd,
                    shop_site_no,
                    shop_site_name,
                    status,
                    order_id,
                    update_date
                FROM
                    MEMBERSHIP.shop_account_dummy
                WHERE
                    status = '1'
                    AND update_date < DATE_ADD(NOW(), INTERVAL -1 HOUR)
            """
            self.cursor.execute(query)
            result = self.cursor.fetchall()

            return result
        except Exception:
            self.conn.rollback()
            self.disconnect()
            return False

    def disconnect(self):
        try:
            self.conn.close()
        except Exception:
            raise Exception(traceback.format_exc())
