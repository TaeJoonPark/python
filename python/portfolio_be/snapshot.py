#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import traceback
from MySQLdb.cursors import DictCursor
from models import DB_CONFIG

class MABSnapshot(object):
    def __init__(self, *args, **kwargs):
        self.conn = MySQLdb.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            passwd=DB_CONFIG['passwd'],
            db='SNAPSHOT',
            port=int(DB_CONFIG['port']),
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor,
            use_unicode=True
        )
        self.conn.autocommit(False)
        self.cursor = self.conn.cursor()

    def update_gosi_exchange_rate(self, rate_info):
        try:
            query = """
                INSERT INTO
                    SNAPSHOT.gosi_exchange_rate
                    (
                        rate_year,
                        rate_week,
                        exchange_rate,
                        country,
                        reg_date
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        'USA',
                        NOW()
                    )
                    ON DUPLICATE KEY
                        UPDATE
                            exchange_rate = %s
            """
            bind = (
                rate_info['year'],
                rate_info['week'],
                rate_info['rate'],
                rate_info['rate'],
            )
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

    def get_gosi_exchange_rate(self):
        try:
            query = """
                SELECT
                    exchange_rate
                FROM
                    SNAPSHOT.gosi_exchange_rate
                ORDER BY
                    seq DESC
                LIMIT 1
            """
            self.cursor.execute(query)
            result = self.cursor.fetchone()

            if self.cursor.rowcount > 0:
                return result['exchange_rate']
            else:
                return False
        except:
            self.disconnect()
            raise Exception(traceback.format_exc())

    def disconnect(self):
        try:
            self.conn.close()
        except Exception:
            raise Exception(traceback.format_exc())
