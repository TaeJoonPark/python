#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import json
import traceback
import sys
import os
import httplib

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

def get_exchange_rate():
    exchange_rate_info_raw = None
    result = {}

    today = datetime.now()

    conn = httplib.HTTPSConnection("unipass.customs.go.kr")
    conn.request("GET",
                 "/csp/myc/bsopspptinfo/dclrSpptInfo/WeekFxrtQryCtr/retrieveWeekFxrt.do?pageIndex=1&pageUnit=100&aplyDt=" + today.strftime("%Y-%m-%d") + "&weekFxrtTpcd=2")
    res = conn.getresponse()

    if res.status == 200:
        exchange_rate_info_raw = res.read()

    conn.close()

    if exchange_rate_info_raw is not None:
        exchange_rate_info = json.loads(exchange_rate_info_raw)

        for item in exchange_rate_info['items']:
            if item['currCd'] == "USD":
                usd_exc_info = item
                break

        result = {
            "year": today.year,
            "week": today.strftime('%U'),
            "apply_start_date": usd_exc_info['aplyDtStrtDd'],
            "apply_end_date": usd_exc_info['aplyDtEndDd'],
            "rate": usd_exc_info['weekFxrt']
        }

    return result

def update_exchange_rate(rate_info):
    from models.snapshot import MABSnapshot

    try:
        m_snapshot = MABSnapshot()
        m_snapshot.update_gosi_exchange_rate(rate_info)
    except:
        m_snapshot.disconnect()
    finally:
        m_snapshot.disconnect()


if __name__ == '__main__':
    rate_info = get_exchange_rate()
    update_exchange_rate(rate_info)