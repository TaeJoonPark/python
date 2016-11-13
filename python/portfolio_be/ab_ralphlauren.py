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

import re
import mechanize
import urllib

class ABShopModRalphLauren(object):
    BASE_URL = 'https://secure-ralphlauren.com'
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
        self.shop_site_name = 'RALPHLAUREN'
        self.shop_site_no = 3
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
            self.br.open('https://www.ralphlauren.com/checkout/index.jsp?process=login')
            action_url = 'https://www.ralphlauren.com/coreg/index.jsp'
            form = mechanize.HTMLForm(action=action_url, method='POST')
            form.new_control(name='token', type='text', attrs={'id': 'token', 'value': ''})
            form.new_control(name='crm', type='text', attrs={'id': 'crm', 'value': ''})
            form.new_control(name='step', type='text', attrs={'id': 'step', 'value': 'login'})
            form.new_control(name='email', type='text', attrs={'id': 'email', 'value': self.user_id})
            form.new_control(name='password', type='text', attrs={'id': 'password', 'value': self.user_passwd})
            form.new_control(name='x', type='text', attrs={'id': 'x', 'value': '0'})
            form.new_control(name='y', type='text', attrs={'id': 'y', 'value': '0'})
            self.br.form = form
            self.br.submit()
        except:
            self.ilogger.info('LOGIN: EORROR_1')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'LOGIN: EORROR-1',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_source = self.br.response().read()
            if 'Welcome Back' in page_source or 'Hello' in page_source:
                self.order_info['site_ID'] = self.user_id
                self.ilogger.info('Login Success')
                self.ilogger.info('LOGIN: DONE')
            else:
                self.ilogger.info('Login Fail')
                self.ilogger.info('LOGIN: EORROR_2')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
                raise Exception({
                    'ab_error': 'LOGIN: EORROR-2',
                    'ab_module': inspect.stack()[0][3]
                })

    def add_cart(self):
        self.ilogger.info('ADD_CART: START')
        try:
            for item in self.item_to_add:
                self.ilogger.info(item)
                url_add_to_cart = 'http://www.ralphlauren.com/cartHandler/index.jsp'
                params = {
                    'action': 'skuAddToCart',
                    'prod_0': item['product_id'],
                    'qty_0': item['qty']
                }
                post_data = urllib.urlencode(params)
                self.br.open(url_add_to_cart, post_data)
                time.sleep(0.5)

            time.sleep(self.WAIT_INTERVAL_SHORT)
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
            self.br.open('http://www.ralphlauren.com/cart/index.jsp?ab=global_bag')
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            items = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//form[@id="shoppingCartCommand"]//table//tr[.//table[@class="prodDetail"]]')
            product_list = []

            if not items:
                self.ilogger.info('No products found in basket 1')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0004'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('GET_CART_INFO: ERROR_1')
                raise Exception({
                    'ab_error': 'GET_CART_INFO: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

            for item in items:
                product = {
                    'country_code': self.country_code,
                    'brand_name': self.shop_site_name,
                    'shop_site_name': self.shop_site_name,
                    'shop_site_no': self.shop_site_no
                }
                product_cnt = iCheck.get_value_by_xpath(self.ilogger, item, './/input[contains(@class,"quantity")]/@value')
                self.ilogger.info(product_cnt)
                if product_cnt:
                    product['product_cnt'] = product_cnt

                product_no = iCheck.get_value_by_xpath(self.ilogger, item, './/input[@class="quantity"]/@name', r"""\[(.*)\]""")
                self.ilogger.debug(product_no)
                if product_no:
                    product['product_no'] = product_no

                image_URL = iCheck.get_value_by_xpath(self.ilogger, item, './/td[contains(@class,"description")]//img/@src')
                if image_URL is not None:
                    if 'http://www.ralphlauren.com' in image_URL:
                        product['image_URL'] = image_URL
                    else:
                        product['image_URL'] = 'http://www.ralphlauren.com'+image_URL

                product_name = iCheck.get_value_by_xpath(self.ilogger, item, './/td[contains(@class,"description")]//a[not(@class="img")]/strong/text()')
                product['product_name'] = product_name

                product_url = iCheck.get_value_by_xpath(self.ilogger, item, './/td[contains(@class,"description")]//a[not(@class="img")]/@href')
                product['product_url'] = product_url

                product_color = iCheck.get_value_by_xpath(self.ilogger, item, './/table[@class="prodDetail"]//tr[./th[contains(text(),"Color")]]/td/text()')
                product['product_color'] = product_color

                product_size = iCheck.get_value_by_xpath(self.ilogger, item, './/table[@class="prodDetail"]//tr[./th[contains(text(),"Size")]]/td/text()')
                product['product_size'] = product_size

                product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/td[@class="currency"][1]/text()', r"""([0-9.,]+)""")
                if product_price_tmp:
                    product_price = product_price_tmp.replace(',', '')
                    product['product_price'] = product_price

                discount_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/td[@class="currency"][2]//div[@class="specialprice"]/text()', r"""([0-9.,]+)""")
                if discount_price_tmp:
                    discount_price = discount_price_tmp.replace(',', '')
                    self.ilogger.debug('DS='+discount_price)
                    product['discount_price'] = float(float(product['product_price']) * float(product_cnt) - float(discount_price)) / float(product_cnt)
                else:
                    product['discount_price'] = '0'
                product_list.append(product)

            self.order_info['products'] = product_list
            self.ilogger.info('GET_CART_INFO: DONE')
            # self.ilogger.info('CART_INFO: ' + json.dumps(product_list))
        except:
            self.ilogger.info('GET_CART_INFO: ERROR_2')
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'GET_CART_INFO: ERROR-2',
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
                        self.br.select_form(nr=5)
                        self.br.form['promoCode'] = coupon_code
                        self.br.submit()
                    except:
                        self.ilogger.error('coupon except')
                        self.ilogger.error(traceback.format_exc())

                    page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())

                    # 쿠폰 적용 확인
                    has_errmsg = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//input[@id="promoCode"]/@class')
                    if 'error' not in has_errmsg:
                        applied_coupon_list.append(coupon_code)

                if applied_coupon_list:
                    adjusted_coupon_list_str = ','.join(applied_coupon_list)
                    self.order_info['site_coupon_code'] = adjusted_coupon_list_str
                    self.ilogger.info('applied coupon list: ' + adjusted_coupon_list_str)
                else:
                    self.ilogger.info('no coupon applied')
            else:
                self.ilogger.info('no coupon available')

            self.ilogger.info('SET_COUPON_CODE: DONE')
            return applied_coupon_list
        except:
            self.ilogger.info('SET_COUPON_CODE: ERROR')
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_COUPON_CODE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_price_info_from_cart(self):
        self.ilogger.info('GET_PRICE_INFO_FROM_CART: START')
        try:
            tmp_order_info = {}
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())

            if self.order_info.get('raw_price'):
                self.ilogger.info('has raw_price'+json.dumps(self.order_info.get('raw_price')))
                tmp_order_info['total_price'] = self.order_info['raw_price']['total_price']
                iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            else:
                total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[./th[contains(text(),"Subtotal")]]/td/text()', r"""([0-9.,]+)""")
                if total_price:
                    tmp_order_info['total_price'] = total_price.replace(',', '')

            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[./th[contains(text(),"Estimated Shipping")]]/td/text()', r"""([0-9.,]+)""")
            if shipping_fee:
                tmp_order_info['shipping_fee'] = shipping_fee.replace(',', '')

            shipping_discount = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[./th[contains(translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"),"free shipping")]]/td/nobr/text()', r"""([0-9.,]+)""")
            if shipping_discount:
                tmp_order_info['shipping_discount'] = shipping_discount.replace(',', '')
            else:
                tmp_order_info['shipping_discount'] = '0'

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[@class="salesTax"]/td/text()', r"""([0-9.,]+)""")
            if tax_fee:
                tmp_order_info['tax_fee'] = tax_fee.replace(',', '')

            # 상품에 쿠폰코드가 적용되어 상품가격이 직접할인되기때문에 전체할인가격을 각 상품 할인 가격을 더해 적용.
            tmp_t_discount_price = 0
            if self.order_info.get('products'):
                for product in self.order_info.get('products'):
                    if product.get('discount_price'):
                        tmp_t_discount_price = tmp_t_discount_price + float(product.get('discount_price')) * float(product['product_cnt'])
            tmp_order_info['discount_price'] = str(tmp_t_discount_price)

            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Order Details"]//tr[@class="total last"]/td/text()', r"""([0-9.,]+)""")
            if est_price:
                tmp_order_info['est_price'] = est_price.replace(',', '')

            if tmp_order_info.get('est_price') is not None and tmp_order_info.get('total_price') is not None:
                f_est_price = iCheck.toNumber(self.ilogger, tmp_order_info.get('est_price'))

                f_total_price = iCheck.toNumber(self.ilogger, tmp_order_info.get('total_price'))
                f_tax_fee = iCheck.toNumber(self.ilogger, tmp_order_info.get('tax_fee'))
                f_shipping_fee = iCheck.toNumber(self.ilogger, tmp_order_info.get('shipping_fee'))

                f_shipping_discount = iCheck.toNumber(self.ilogger, tmp_order_info.get('shipping_discount'))
                f_discount_price = iCheck.toNumber(self.ilogger, tmp_order_info.get('discount_price'))

                tmp_est = f_total_price + f_tax_fee + f_shipping_fee - f_shipping_discount - f_discount_price
                if f_est_price < tmp_est:
                    self.ilogger.info('est price = {:} tmp_est = {:}'.format(f_est_price, tmp_est))
                    self.ilogger.info('before discount price = {:}'.format(f_discount_price))
                    tmp_order_info['discount_price'] = format(f_discount_price + (tmp_est - f_est_price), ".2f")
                    self.ilogger.info('after discount price = {:}'.format(tmp_order_info['discount_price']))

            self.ilogger.info('GET_PRICE_INFO_FROM_CART: DONE')
            return tmp_order_info
        except:
            self.ilogger.info('GET_PRICE_INFO_FROM_CART: ERROR')
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'GET_PRICE_INFO_FROM_CART: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def move_to_checkout(self):
        self.ilogger.info('MOVE_TO_CHECKOUT: START')
        try:
            self.br.select_form(nr=2)
            self.br.form.set_all_readonly(False)
            self.br.form['checkout'] = 'Y'
            self.br.submit()
        except:
            self.ilogger.info('MOVE_TO_CHECKOUT: ERROR')
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'MOVE_TO_CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            current_tab_text = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//li[@class="current"]/text()')
            if 'addresses' in current_tab_text.lower():
                self.ilogger.info('MOVE_TO_CHECKOUT: DONE')
            else:
                self.ilogger.info('MOVE_TO_CHECKOUT: ERROR-1')
                self.ilogger.info('Failed to move to shipping address page now:'+self.br.geturl())
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                raise Exception({
                    'ab_error': 'MOVE_TO_CHECKOUT: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

    def get_price_info_in_checkout(self):
        self.ilogger.info('GET_PRICE_INFO_IN_CHECKOUT: START')
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            price_info = {}

            total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[./th[contains(text(),"Subtotal")]]/td/text()', r"""([0-9.,]+)""")
            price_info['total_price'] = total_price.replace(',', '') if total_price else "0"

            discount_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[@class="promo"][1]/td/nobr/text()', r"""([0-9.,]+)""")
            price_info['discount_price'] = discount_price.replace(',', '') if discount_price else "0"

            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[./th[contains(text(),"Shipping")]]/td/text()', r"""([0-9.,]+)""")
            price_info['shipping_fee'] = shipping_fee.replace(',', '') if shipping_fee else "0"

            shipping_discount = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[@class="promo"][2]/td/nobr/text()', r"""([0-9.,]+)""")
            price_info['shipping_discount'] = shipping_discount.replace(',', '') if shipping_discount else "0"

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[@class="salesTax"]/td/text()', r"""([0-9.,]+)""")
            price_info['tax_fee'] = tax_fee.replace(',', '') if tax_fee else "0"

            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[@class="total last"]/td/text()', r"""([0-9.,]+)""")
            price_info['est_price'] = est_price.replace(',', '') if est_price else "0"

            self.ilogger.info('GET_PRICE_INFO_IN_CHECKOUT: DONE')
            return price_info
        except:
            self.ilogger.info('GET_PRICE_INFO_IN_CHECKOUT: ERROR')
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')

    def set_shipping_address(self, shipping_addr):
        self.ilogger.info('SET_SHIPPING_ADDRESS: START')
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            addr_type = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//fieldset[contains(@class,"address")]/h3/text()')
            addr_type = addr_type.lower()
            action_url = 'https://www.ralphlauren.com/checkout.jsp'
            form = mechanize.HTMLForm(action=action_url, method='POST')

            el_address_list = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//tr[.//td/table[@summary="Address" and @class="AddressItem"]]')
            ship_addr_radio_val = None
            if len(el_address_list) > 0:
                for el_address in el_address_list:
                    addr_values = iCheck.get_values_by_xpath(self.ilogger, el_address, './/td[@class="address"]/text()')
                    addr_text = ""

                    for _addr in addr_values:
                        _addr = _addr.replace('\n', '')
                        _addr = _addr.replace('\t', '')
                        _addr = _addr.strip()
                        addr_text += _addr

                    if shipping_addr['zipcode'] in addr_text.strip():
                        ship_addr_radio_val = iCheck.get_value_by_xpath(self.ilogger, el_address, './/input[@name="shipOpt"]/@value')
                        break

            if ship_addr_radio_val is None:
                ship_addr_radio_val = "2"

            # key 값 가져오기.
            self.br.select_form(nr=0)
            flowExecutionKey = self.br.form['_flowExecutionKey']

            self.br.select_form(nr=3)
            form.new_control(name='chooseBA', type='text', attrs={'id': 'chooseBA', 'value': '1'})
            form.new_control(name='shipOpt', type='text', attrs={'id': 'shipOpt', 'value': ship_addr_radio_val})

            form.new_control(name='_eventId_continue', type='text', attrs={'id': '_eventId', 'value': 'Continue Checkout'})
            form.new_control(name='_flowExecutionKey', type='text', attrs={'id': '_flowExecutionKey', 'value': flowExecutionKey})
            form.new_control(name='ignoreBillingAddressSuggestions', type='text', attrs={'id': 'ignoreBillingAddressSuggestions', 'value': 'false'})
            form.new_control(name='ignoreShippingAddressSuggestions', type='text', attrs={'id': 'ignoreShippingAddressSuggestions', 'value': 'false'})
            form.new_control(name='onlyValidateUSandCA', type='text', attrs={'id': 'onlyValidateUSandCA', 'value': 'true'})
            form.new_control(name='shipOption', type='text', attrs={'id': 'shipOption', 'value': ship_addr_radio_val})

            # Shpping Address
            form.new_control(name='shippingAddress.address.address1', type='text', attrs={'id': 'shippingAddress.address.address1', 'value': shipping_addr['street_addr_01']})
            form.new_control(name='shippingAddress.address.address2', type='text', attrs={'id': 'shippingAddress.address.address2', 'value': shipping_addr['street_addr_02']})
            form.new_control(name='shippingAddress.address.address3', type='text', attrs={'id': 'shippingAddress.address.address3', 'value': ''})
            form.new_control(name='shippingAddress.address.city', type='text', attrs={'id': 'shippingAddress.address.city', 'value': shipping_addr['city']})
            form.new_control(name='shippingAddress.address.country', type='text', attrs={'id': 'shippingAddress.address.country', 'value': 'US'})
            form.new_control(name='shippingAddress.address.firstName', type='text', attrs={'id': 'shippingAddress.address.firstName', 'value': shipping_addr['first_name']})
            form.new_control(name='shippingAddress.address.id', type='text', attrs={'id': 'shippingAddress.address.id', 'value': '0'})
            form.new_control(name='shippingAddress.address.lastName', type='text', attrs={'id': 'shippingAddress.address.lastName', 'value': shipping_addr['last_name']})
            form.new_control(name='shippingAddress.address.postalCode', type='text', attrs={'id': 'shippingAddress.address.postalCode', 'value': shipping_addr['zipcode']})
            form.new_control(name='shippingAddress.address.state', type='text', attrs={'id': 'shippingAddress.address.state', 'value': shipping_addr['state']})
            form.new_control(name='shippingAddress.phone', type='text', attrs={'id': 'shippingAddress.phone', 'value': shipping_addr['phone']})

            # Billing Address
            form.new_control(name='billingAddress.address.address1', type='text', attrs={'id': 'shippingAddress.address.address1', 'value': shipping_addr['street_addr_01']})
            form.new_control(name='billingAddress.address.address2', type='text', attrs={'id': 'shippingAddress.address.address2', 'value': shipping_addr['street_addr_02']})
            form.new_control(name='billingAddress.address.address3', type='text', attrs={'id': 'shippingAddress.address.address3', 'value': ''})
            form.new_control(name='billingAddress.address.city', type='text', attrs={'id': 'shippingAddress.address.city', 'value': shipping_addr['city']})
            form.new_control(name='billingAddress.address.country', type='text', attrs={'id': 'shippingAddress.address.country', 'value': 'US'})
            form.new_control(name='billingAddress.address.firstName', type='text', attrs={'id': 'shippingAddress.address.firstName', 'value': shipping_addr['first_name']})
            form.new_control(name='billingAddress.address.id', type='text', attrs={'id': 'shippingAddress.address.id', 'value': '0'})
            form.new_control(name='billingAddress.address.lastName', type='text', attrs={'id': 'shippingAddress.address.lastName', 'value': shipping_addr['last_name']})
            form.new_control(name='billingAddress.address.postalCode', type='text', attrs={'id': 'shippingAddress.address.postalCode', 'value': shipping_addr['zipcode']})
            form.new_control(name='billingAddress.address.state', type='text', attrs={'id': 'shippingAddress.address.state', 'value': shipping_addr['state']})
            form.new_control(name='billingAddress.phone', type='text', attrs={'id': 'shippingAddress.phone', 'value': shipping_addr['phone']})

            self.br.form = form
            self.br.submit()
            self.ilogger.info('done add_shipping_address submit')
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0022'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_SHIPPING_ADDRESS: ERROR-1')
            raise Exception({
                'ab_error': 'SET_SHIPPING_ADDRESS: ERROR-1',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            current_tab_text = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//li[@class="current"]/text()')
            self.ilogger.debug('current tab text '+current_tab_text)
            if 'shipping' in current_tab_text.lower():
                self.ilogger.info('SET_SHIPPING_ADDRESS: DONE')
            else:
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),
                                            inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('Failed to move to SHIPPING METHOD PAGE now:'+self.br.geturl())
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('SET_SHIPPING_ADDRESS: ERROR-2')
                raise Exception({
                    'ab_error': 'SET_SHIPPING_ADDRESS: ERROR-2',
                    'ab_module': inspect.stack()[0][3]
                })

    def move_to_address_tab_in_checkout(self):
        self.ilogger.info('MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: START')
        try:
            self.br.select_form(nr=0)
            flowExecutionKey = self.br.form['_flowExecutionKey']

            action_url = 'https://www.ralphlauren.com/checkout.jsp'
            form = mechanize.HTMLForm(action=action_url, method='POST')
            # etc
            form.new_control(name='_eventId', type='text', attrs={'id': '_eventId', 'value': 'editAddress'})
            form.new_control(name='_flowExecutionKey', type='text', attrs={'id': '_flowExecutionKey', 'value': flowExecutionKey})
            self.br.form = form
            self.br.submit()
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: ERROR')
            raise Exception({
                'ab_error': 'MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            current_tab_text = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//li[@class="current"]/text()')
            self.ilogger.debug('current tab text '+current_tab_text)
            if 'addresses' in current_tab_text.lower():
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: DONE')
            else:
                self.ilogger.info('Failed to move to ADDRESS PAGE now:'+self.br.geturl())
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: ERROR-1')
                raise Exception({
                    'ab_error': 'MOVE_TO_ADDRESS_TAB_IN_CHECKOUT: ERROR-1',
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
        rl = ABShopModRalphLauren(
            order_id=kwargs.get('order_id'),
            e_id=kwargs.get('e_id'),
            login_id=kwargs.get('login_id'),
            login_passwd=kwargs.get('login_passwd'),
            items=items,
            ilogger=kwargs.get('ilogger')
        )

        rl.init_browser()
        rl.login()
        rl.add_cart()
        rl.get_cart_info()

        coupon_applied = []
        if coupon_code is not False and len(coupon_code) > 0:
            coupon_applied = rl.set_coupon_code(coupon_code)
            rl.get_cart_info()

        rl.move_to_checkout()
        rl.set_shipping_address(shipping_addr_info['NJ'])
        price_info_in_checkout = rl.get_price_info_in_checkout()
        if float(price_info_in_checkout['tax_fee']) > 0:
            rl.ilogger.info('::: CHANGE-SHIPPING-ADDR: START :::')
            rl.move_to_address_tab_in_checkout()
            rl.set_shipping_address(shipping_addr_info['DE'])
            price_info_in_checkout = rl.get_price_info_in_checkout()
            ship_addr_state = "DE"
            rl.ilogger.info('::: CHANGE-SHIPPING-ADDR: END :::')

        rl.close_browser()
        result = {
            "price_info_est": price_info_in_checkout,
            "order_info": rl.order_info,
            "coupon_applied": coupon_applied,
            "ship_addr_est": ship_addr_state
        }

        return result
    except Exception as e:
        rl.close_browser()
        report_error_slack(
            title=e.args[0]['ab_error'] if 'ab_error' in e.args[0] else e,
            order_id=rl.order_info['order_id'] if 'order_id' in rl.order_info else '',
            e_id=rl.order_info['e_id'] if 'e_id' in rl.order_info else '',
            shop_site_id=rl.order_info['shop_site_no'] if 'shop_site_no' in rl.order_info else '',
            shop_site_name=rl.order_info['shop_site_name'] if 'shop_site_name' in rl.order_info else '',
            module=e.args[0]['ab_module'] + "()@" + inspect.getfile(inspect.currentframe()) if 'ab_module' in e.args[0] else '',
            log_file_path=rl.ilogger.handlers[0].baseFilename
        )
        return False

"""
if __name__ == '__main__':
    rl = ABShopModRalphLauren(
        order_id=9999,
        e_id=3333,
        login_id="gdhong88@gmail.com",
        login_passwd="shfwkfk",
        items=[],
        ilogger=set_logger({
            'folder_name': 'ab_price_estimate',
            'shop_site_name': 'RALPHLAUREN',
            'order_id': 7777,
            'e_id': 3333,
        })
    )

    try:
        rl.init_browser()
        rl.login()
        rl.get_cart_info()

        coupon_code_list = [
            'DAD16',
            'KIDS16'
        ]
        rl.set_coupon_code(coupon_code_list)
        rl.get_cart_info()

        price_info = rl.get_price_info_from_cart()
        # print price_info

        rl.move_to_checkout()
        rl.set_shipping_address('NJ')
        price_info_in_checkout = rl.get_price_info_in_checkout()
        if float(price_info_in_checkout['tax_fee']) > 0:
            rl.move_to_address_tab_in_checkout()
            rl.set_shipping_address('DE')
            price_info_in_checkout = rl.get_price_info_in_checkout()

        print price_info_in_checkout

        rl.close_browser()
    except Exception as e:
        print "!!! THERE WAS AN EXCEPTION !!!"
        print e.message
        rl.close_browser()
"""
