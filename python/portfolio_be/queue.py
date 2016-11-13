#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import traceback
from MySQLdb.cursors import DictCursor
from models import DB_CONFIG

class MABQueue(object):
    def __init__(self, *args, **kwargs):
        self.conn = MySQLdb.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            passwd=DB_CONFIG['passwd'],
            db='QUEUE',
            port=int(DB_CONFIG['port']),
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor,
            use_unicode=True
        )
        self.conn.autocommit(False)
        self.cursor = self.conn.cursor()

    def get_running_process_count(self, ab_type):
        query = """
            SELECT
                COUNT(*) AS cnt
            FROM
                q_process_list
            WHERE
                status = '1'
                AND AB_type = %s
        """
        self.cursor.execute(query, (ab_type,))
        result = self.cursor.fetchone()
        if self.cursor.rowcount > 0:
            return result['cnt']
        else:
            return False

    def get_queue_seq_todo(self, ab_type):
        try:
            query = """
                SELECT
                    seq,
                    order_id,
                    shop_site_no,
                    shop_site_name
                FROM
                    q_process_list
                WHERE
                    status = '0'
                    AND AB_type = %s
                ORDER BY
                    seq ASC
                LIMIT 1
            """
            self.cursor.execute(query, (ab_type,))
            result = self.cursor.fetchone()

            if self.cursor.rowcount > 0:
                return result
            else:
                return False
        except Exception:
            self.disconnect()
            raise Exception(traceback.format_exc())

    def get_queue_info(self, queue_seq):
        try:
            query = """
                SELECT
                    order_id,
                    shop_site_no,
                    shop_site_name,
                    AB_type,
                    status,
                    payment_result,
                    error_type,
                    reg_date,
                    update_date
                FROM
                    q_process_list
                WHERE
                    seq = %s
            """
            self.cursor.execute(query, (queue_seq,))
            result = self.cursor.fetchone()

            if self.cursor.rowcount > 0:
                return result
            else:
                return False
        except Exception:
            self.disconnect()
            raise Exception(traceback.format_exc())

    def update_queue_status(self, queue_seq, status):
        try:
            query = """
                UPDATE
                    q_process_list
                SET
                    status = %s,
                    update_date = NOW()
                WHERE
                    seq = %s
            """
            bind = (status, queue_seq)
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
            raise Exception(traceback.format_exc())

    def disconnect(self):
        try:
            self.conn.close()
        except Exception:
            raise Exception(traceback.format_exc())
