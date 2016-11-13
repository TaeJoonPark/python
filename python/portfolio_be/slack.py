#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib2
import json
from collections import OrderedDict


def report_error_slack(**kwargs):
    data = OrderedDict([
        ('title', kwargs.get('title')),
        ('order_id', kwargs.get('order_id')),
        ('e_id', kwargs.get('e_id')),
        ('shop_site_id', kwargs.get('shop_site_id')),
        ('shop_site_name', kwargs.get('shop_site_name')),
        ('module', kwargs.get('module')),
        ('log_file_path', kwargs.get('log_file_path'))
    ])

    message = ""
    for key, value in data.items():
        if key == "title":
            message += "*" + str(value) + "*\n"
        else:
            message += key + ": " + str(value) + "\n"

    slack_api_url = "https://hooks.slack.com/services/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"
    data = {
        "text": message.strip()
    }
    req = urllib2.Request(slack_api_url, json.dumps(data))
    req.add_header('Content-type', 'application/json')
    urllib2.urlopen(req)


# if __name__ == '__main__':
#     send_error_info()
