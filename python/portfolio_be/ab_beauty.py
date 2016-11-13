#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import inspect
import json
import traceback

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lib import iCheck
from lib.slack import report_error_slack

import mechanize
import urllib

from mechanize import TextControl
from lxml import html
from lxml import etree

class ABShopModBeauty(object):
    BASE_URL = 'http://www.swaddledesigns.com/'
    WAIT_INTERVAL = 3
    WAIT_INTERVAL_SHORT = 1
    WAIT_INTERVAL_LONG = 5

    def __init__(self, **kwargs):
        self.display = None
        # msg 객체
        self.msg = None
        self.result_data = None
        # log 객체
        self.ilogger = kwargs.get('ilogger')

        self.br = None
        self.cookies = mechanize.CookieJar()
        # EBATES 쿠키 리스트
        # self.cookies_list = kwargs.get('cookies_list')

        self.order_id = kwargs.get('order_id')
        self.user_id = kwargs.get('login_id')
        self.user_passwd = kwargs.get('login_passwd')
        self.e_id = kwargs.get('e_id')
        self.item_to_add = kwargs.get('items')
        self.country_code = '840'
        self.shop_site_name = 'BEAUTY_GROUP'
        self.shop_site_no = 9997
        self.user_coupon = kwargs.get('user_coupon')

        self.order_info = dict()
        self.order_info['order_id'] = self.order_id
        self.order_info['e_id'] = self.e_id
        self.order_info['country_code'] = self.country_code
        self.order_info['shop_site_name'] = self.shop_site_name
        self.order_info['shop_site_no'] = self.shop_site_no

    def init_browser(self):
        self.ilogger.info('INIT_BROWSER: START')
        try:
            # browserowser
            self.br = mechanize.Browser()
            # Cookie 복사
            # if self.cookies_list:
            #     iCheck.copy_cookie(self.ilogger, self.cookies_list, self.cookies)
            self.ilogger.info('in init browser cookie {:}'.format(self.cookies))
            self.br.set_cookiejar(self.cookies)
            # browserowser options
            self.br.set_handle_equiv(True)
            self.br.set_handle_gzip(False)
            self.br.set_handle_redirect(True)
            self.br.set_handle_referer(False)
            self.br.set_handle_robots(False)
            # Follows refresh 0 but not hangs on refresh > 0
            self.br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
            # Want debugging messages?
            self.br.set_debug_http(False)
            self.br.set_debug_redirects(False)
            self.br.set_debug_responses(False)
            # self.br.add_handler(PrettifyHandler())
            self.br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.11 Safari/537.36')]
            self.ilogger.info('INIT_BROWSER: DONE')
        except:
            self.msg = json.dumps({'result': False, 'message': 'PYMF0020'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('INIT_BROWSER: ERROR')
            self.ilogger.error(traceback.format_exc())
            self.close_browser()
            raise Exception({
                'ab_error': 'INIT_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def login(self):
        self.ilogger.info('LOGIN: START')
        try:
            if self.br.request:
                self.ilogger.info(self.br.request.header_items())
            self.br.open('https://www.beauty.com/user/login.asp')
            self.br.select_form(nr=1)
            self.br.form['txtEmail'] = self.user_id
            self.br.form['txtPassword'] = self.user_passwd
            self.br.submit()
        except:
            self.ilogger.info('LOGIN: ERROR-1')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'LOGIN: ERROR-1',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_source = self.br.response().read()
            if 'Sign Out' in page_source:
                self.order_info['site_ID'] = self.user_id
                self.ilogger.info('Login Success')
                self.ilogger.info('LOGIN: DONE')
            else:
                if self.br.response() is not None:
                    iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('Login Fail')
                self.ilogger.info('LOGIN: ERROR-2')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
                raise Exception({
                    'ab_error': 'LOGIN: ERROR-2',
                    'ab_module': inspect.stack()[0][3]
                })

    def add_cart(self):
        self.ilogger.info('ADD_CART: START')
        try:
            for item in self.item_to_add:
                self.ilogger.info(item)
                url_add_to_cart = 'http://www.beauty.com/cart.asp?product='+str(item['product_id'])+'&txtQuantity='+str(item['qty'])
                self.br.open(url_add_to_cart)
                time.sleep(0.5)
            self.ilogger.info('ADD_CART: DONE')
        except:
            self.ilogger.info('ADD_CART: ERROR')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'ADD_CART: ERROR',
                'ab_module': inspect.stack()[0][3]
            })


    def get_cart_info(self):
        self.ilogger.info('GET_CART_INFO: START')
        try:
            self.br.open('http://www.beauty.com/cart.asp')
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            items = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//div[@id="bag-items-in"]/div[@class="row"]')
            product_list = []

            # 빈 장바구니 경우 종료
            if not items:
                self.ilogger.info('No products found in basket 1')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0004'}, ensure_ascii=False, encoding='utf-8')
                raise Exception('cart is empty')

            self.ilogger.info('{pcnt} order products will be crawled'.format(pcnt=len(items)))
            for item in items:
                product = {
                    'country_code': self.country_code,
                    'shop_site_name': self.shop_site_name,
                    'shop_site_no': self.shop_site_no,
                    'brand_name': 'BEAUTY&amp;DRUGSTORE'
                }

                product_cnt = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="bag-qty"]/input/@value | .//div[@class="bag-qty"]/b/text()')
                if product_cnt:
                    product['product_cnt'] = product_cnt

                product_no = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="bag-qty"]//div[@class="bag-remove"]/a/@href', """trxp2=(.*)""")
                product['product_no'] = product_no

                image_URL = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="image"]/img/@src')
                product['image_URL'] = image_URL

                product_name = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="description"]/a/text()[1]| .//div[@class="description"]/text()[1]')
                if product_name:
                    product_name = product_name[:3].replace('-', '') + product_name[3:]
                    product['product_name'] = product_name.strip()

                product_url = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="description"]/a/@href')
                if product_url:
                    product['product_url'] = self.BASE_URL + product_url
                else:
                    product['product_url'] = None

                product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="total"]/h2/text()', r"""([0-9.,]+)""")
                if product_price_tmp:
                    product_price = product_price_tmp.replace(',', '')
                    product['product_price'] = str(float(product_price) / float(product_cnt))
                else:
                    product['product_price'] = '0'

                # 할인 금액을 찾을수 없음.
                product['discount_price'] = '0'

                product_list.append(product)

            self.order_info['products'] = product_list
            self.ilogger.info('PRODUCT_LIST: ' + json.dumps(product_list))
            self.ilogger.info('GET_CART_INFO: DONE')

            return product_list
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('GET_CART_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_CART_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_zipcode_for_tax_est(self, zipcode):
        self.ilogger.info('SET_ZIPCODE_FOR_TAX_EST: START')
        try:
            self.br.select_form(nr=1)
            self.br.form['txtSTEZip'] = zipcode
            getestx = TextControl(type='text', name='imgbtnGetEstimate.x', attrs={'value': '48'})
            getesty = TextControl(type='text', name='imgbtnGetEstimate.y', attrs={'value': '8'})
            elements = [getestx, getesty]
            for element in elements:
                element.add_to_form(self.br.form)
            self.br.submit()
            self.ilogger.info('SET_ZIPCODE_FOR_TAX_EST: DONE')
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('SET_ZIPCODE_FOR_TAX_EST: ERROR')
            raise Exception({
                'ab_error': 'SET_ZIPCODE_FOR_TAX_EST: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_coupon_code(self, coupon_code_list):
        self.ilogger.info('SET_COUPON_CODE: START')
        try:
            applied_coupon_list = []

            if len(coupon_code_list) > 0:
                for index, coupon_code in enumerate(coupon_code_list):
                    self.ilogger.info("coupon_code: " + coupon_code)
                    try:
                        self.br.select_form(nr=1)
                        self.br.form['code'] = coupon_code
                        btnx = TextControl(type='text', name='btnApplyCoupon.x', attrs={'value': '34'})
                        btny = TextControl(type='text', name='btnApplyCoupon.y', attrs={'value': '11'})
                        elements = [btnx, btny]
                        for element in elements:
                            element.add_to_form(self.br.form)
                        self.br.submit()
                    except:
                        self.ilogger.error('coupon except')
                        self.ilogger.error(traceback.format_exc())

                    page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())

                    # 쿠폰 적용 확인 현재 적용가능쿠폰코드가 없어 확인 불가.
                    has_errmsg = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//input[@id="applyCoupon"]/@value')
                    if 'your entry is not valid' not in has_errmsg:
                        applied_coupon_list.append(coupon_code)
                        tmp_order_info = self.get_price_info()
                        if float(tmp_order_info['est_price']) < float(self.order_info['est_price']):
                            for i_key, i_value in tmp_order_info.items():
                                self.order_info[i_key] = i_value

                if len(applied_coupon_list) > 0:
                    final_coupon_list_str = ','.join(applied_coupon_list)
                    self.order_info['site_coupon_code'] = final_coupon_list_str
                    self.ilogger.info('Adjusted coupon list= ' + final_coupon_list_str)
                else:
                    self.ilogger.info('No coupon applied')
            else:
                self.ilogger.info('No coupon available')

            self.ilogger.info('SET_COUPON_CODE: DONE')
            return applied_coupon_list
        except:
            self.ilogger.info('SET_COUPON_CODE: ERROR')
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_COUPON_CODE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_price_info(self):
        self.ilogger.info('GET_PRICE_INFO: START')
        try:
            tmp_order_info = {}
            page_source = self.br.response().read()
            detail_html = html.fromstring(page_source)
            page_tree = etree.ElementTree(detail_html)

            total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@class="bagtotals"]//th[@class="bagtotalamount"]/text()', r"""([0-9.,]+)""")
            if total_price:
                tmp_order_info['total_price'] = total_price.replace(',', '')

            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@class="bagtotals"]//td[@class="bagtotalshippingamount"]//text()', r"""([0-9.,]+)""")
            if shipping_fee:
                tmp_order_info['shipping_fee'] = shipping_fee.replace(',', '')
            else:
                tmp_order_info['shipping_fee'] = '0'
            tmp_order_info['shipping_discount'] = '0'

            # 확인불가.적용가능 쿠폰없음.
            # discount_price_tmp = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[@class="shipPromo"]/td/text()', r"""([0-9.,]+)""")
            # if discount_price_tmp:
            #     tmp_order_info['discount_price'] = discount_price_tmp.replace(',', '')
            # else:
            #     tmp_order_info['discount_price'] = '0'
            tmp_order_info['discount_price'] = '0'

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@class="bagtotals"]//td[@class="bagtotaltaxamount"]//text()', r"""([0-9.,]+)""")
            if tax_fee:
                tmp_order_info['tax_fee'] = tax_fee.replace(',', '')
            else:
                tmp_order_info['tax_fee'] = '0'

            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@class="bagtotals"]//td[@class="bagtotalorderamount"]//text()', r"""([0-9.,]+)""")
            if est_price:
                tmp_order_info['est_price'] = est_price.replace(',', '')

            self.ilogger.info('GET_PRICE_INFO: DONE')
            return tmp_order_info
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('GET_PRICE_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_PRICE_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_total_price(self, detail_price_info, is_raw):
        self.ilogger.info('SET_TOTAL_PRICE: START')
        try:
            if is_raw:
                self.ilogger.info('SET RAW PRICE')
                self.order_info['raw_price'] = detail_price_info

            for i_key, i_value in detail_price_info.items():
                self.order_info[i_key] = i_value

            self.ilogger.info('SET_TOTAL_PRICE: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_TOTAL_PRICE: ERROR')
            raise Exception({
                'ab_error': 'SET_TOTAL_PRICE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def close_browser(self):
        self.ilogger.info('CLOSE_BROWSER: START')
        try:
            self.br.close()
            self.ilogger.info('CLOSE_BROWSER: DONE')
        except:
            self.ilogger.info('CLOSE_BROWSER: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'CLOSE_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })


def do_estimate_price(**kwargs):
    cart_info = kwargs.get('order_info')
    items = []
    for item in cart_info:
        _item = {}
        _item['product_id'] = item['product_id']
        _item['qty'] = item['product_qty']
        items.append(_item)

    shipping_addr_info = kwargs.get('shipping_addr_info')
    coupon_code = kwargs.get('site_coupon')

    ship_addr_state = "NJ"

    try:
        beauty = ABShopModBeauty(
            order_id=kwargs.get('order_id'),
            e_id=kwargs.get('e_id'),
            login_id=kwargs.get('login_id'),
            login_passwd=kwargs.get('login_passwd'),
            items=items,
            ilogger=kwargs.get('ilogger')
        )

        beauty.init_browser()
        beauty.login()

        beauty.add_cart()
        beauty.get_cart_info()

        coupon_applied = []
        if coupon_code is not False and len(coupon_code) > 0:
            coupon_applied = beauty.set_coupon_code(coupon_code)

        beauty.set_zipcode_for_tax_est(shipping_addr_info['NJ']['zipcode'])
        price_info = beauty.get_price_info()

        if float(price_info['tax_fee']) > 0:
            beauty.ilogger.info('::: CHANGE-SHIPPING-ADDR: START :::')
            beauty.set_zipcode_for_tax_est(shipping_addr_info['DE']['zipcode'])
            price_info = beauty.get_price_info()
            ship_addr_state = "DE"
            beauty.ilogger.info('::: CHANGE-SHIPPING-ADDR: END :::')

        beauty.set_total_price(price_info, True)
        beauty.close_browser()

        result = {
            "price_info_est": price_info,
            "order_info": beauty.order_info,
            "coupon_applied": coupon_applied,
            "ship_addr_est": ship_addr_state
        }

        return result
    except Exception as e:
        beauty.close_browser()

        report_error_slack(
            title=e.args[0]['ab_error'] if 'ab_error' in e.args[0] else e,
            order_id=beauty.order_info['order_id'] if 'order_id' in beauty.order_info else '',
            e_id=beauty.order_info['e_id'] if 'e_id' in beauty.order_info else '',
            shop_site_id=beauty.order_info['shop_site_no'] if 'shop_site_no' in beauty.order_info else '',
            shop_site_name=beauty.order_info['shop_site_name'] if 'shop_site_name' in beauty.order_info else '',
            module=e.args[0]['ab_module'] + "()@" + inspect.getfile(inspect.currentframe()) if 'ab_module' in e.args[0] else '',
            log_file_path=beauty.ilogger.handlers[0].baseFilename
        )

        return False
