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

class ABShopModCarters(object):
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
        self.shop_site_name = 'CARTERS_GROUP'
        self.shop_site_no = 9998
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
            self.br.open('https://www.carters.com/my-account')
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            action_url = iCheck.get_value_by_xpath(self.ilogger,page_tree,'//form[@id="dwfrm_login"]/@action')
            self.ilogger.debug('request_url= {:}'.format(action_url))
            email_id = iCheck.get_value_by_xpath(self.ilogger,page_tree,'//input[contains(@id,"dwfrm_login_username_")]/@id')
            securekey = iCheck.get_value_by_xpath(self.ilogger,page_tree,'//input[@name="dwfrm_login_securekey"]/@value')

            form = mechanize.HTMLForm(action=action_url, method='POST')
            form.new_control(name=email_id, type='text', attrs={'value': self.user_id})
            form.new_control(name='dwfrm_login_password', type='text', attrs={'value': self.user_passwd})
            form.new_control(name='dwfrm_login_rememberme', type='text', attrs={'value': 'true'})
            form.new_control(name='dwfrm_login_login', type='text', attrs={'value': 'Sign in'})
            form.new_control(name='dwfrm_login_securekey', type='hidden', attrs={'value': securekey})
            self.br.form = form
            self.br.submit()
        except:
            self.ilogger.info('LOGIN: EORROR-1')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'LOGIN: ERROR-1',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            myprofile_elem = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//li[@class="myprofile"]')
            if myprofile_elem is not None:
                self.order_info['site_ID'] = self.user_id
                self.ilogger.info('Login Success')
                self.ilogger.info('LOGIN: DONE')
            else:
                if self.br.response() is not None:
                    iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('Login Fail')
                self.ilogger.info('LOGIN: EORROR-2')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
                raise Exception({
                    'ab_error': 'LOGIN: ERROR-2',
                    'ab_module': inspect.stack()[0][3]
                })

    def get_cart_info(self):
        self.ilogger.info('GET_CART_INFO: START')
        try:
            self.br.open('http://www.carters.com/cart')
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            items = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//table[@id="cart-table"]//tr[@class="cart-row"]')
            product_list = []
            brand_name_list = []

            if not items:
                self.ilogger.info('No products found in basket 1')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0004'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('GET_CART_INFO: ERROR-1')
                raise Exception({
                    'ab_error': 'GET_CART_INFO: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

            for item in items:
                product = {
                    'country_code': self.country_code,
                    'shop_site_name': self.shop_site_name,
                    'shop_site_no': self.shop_site_no
                }
                product_cnt = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-quantity desktopvisible"]/div/select//option[@selected="selected"]/@value')
                if product_cnt:
                    product['product_cnt'] = product_cnt

                product_status_check = iCheck.get_element_by_xpath(self.ilogger, item, './td[@class="item-quantity-details"]/ul/li[contains(text(), "Out Of Stock")]')
                if product_status_check is not None:
                    product['product_outstock'] = True

                product_no_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-details"]/div[@class="product-list-item"]/div[@class="name"]/a[@href]/@href')
                if product_no_tmp is not None:
                    product_no_tmp2 = product_no_tmp.split('/')[-1]
                    product_no_tmp3 = product_no_tmp2.split('.')
                    if len(product_no_tmp3) > 0:
                        product['product_no'] = product_no_tmp3[0]

                product_name = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-details"]/div[@class="product-list-item"]/div[@class="name"]/a[@href]/text()')
                if product_name:
                    product['product_name'] = product_name
                else:
                    if product.get('product_outstock'):
                        product['product_name'] = 'Out Of Stock'
                    else:
                        product['product_name'] = 'No TITLE'

                brand_name = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="mini-cart-brand"]/div/@class')
                if 'carters' in brand_name.lower():
                    brand_name = 'CARTERS'
                elif 'oshkosh' in brand_name.lower():
                    brand_name = 'OSHKOSH'
                brand_name_list.append(brand_name)
                product['brand_name'] = brand_name

                image_URL = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-image"]/img[@src]/@src')
                product['image_URL'] = image_URL

                product_url = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-details"]/div[@class="product-list-item"]/div[@class="name"]/a[@href]/@href')
                product['product_url'] = product_url

                product_color = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-details"]/div[@class="product-list-item"]/div[@class="attribute Color"]/span[@class="value"]/text()')
                product['product_color'] = product_color

                product_size = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="item-details"]/div[@class="product-list-item"]/div[@class="attribute Size"]/span[@class="value"]/text()')
                product['product_size'] = product_size

                product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/td[@class="item-total"]//span[@class="price-total"]/text()', r"""([0-9.,]+)""")
                if product_price_tmp:
                    product_price = product_price_tmp.replace(',', '')
                    product['product_price'] = str(float(product_price) / float(product['product_cnt']))

                product['discount_price'] = '0'

                product_list.append(product)

            self.order_info['products'] = product_list
            self.ilogger.info('PRODUCT_LIST: ' + json.dumps(product_list))
            self.ilogger.info('GET_CART_INFO: DONE')

            # print product_list
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

    def move_to_checkout(self):
        self.ilogger.info('MOVE_TO_CHECKOUT: START')
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            action_url = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//form[@name="dwfrm_cart"]/@action')
            form = mechanize.HTMLForm(action=action_url, method='POST')
            form.new_control(name='dwfrm_cart_checkoutCart', type='hidden', attrs={'value': 'Checkout'})
            form.new_control(name='id', type='hidden', attrs={'value': 'carters'})
            form.new_control(name='fromOshKosh', type='hidden', attrs={'value': 'false'})
            self.br.form = form
            self.br.submit()
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.info('MOVE_TO_CHECKOUT: ERROR')
            raise Exception({
                'ab_error': 'MOVE_TO_CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            shipping_address_elem = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//div[contains(@class,"shippingForm") and not(contains(@style,"none"))]')
            if shipping_address_elem is not None:
                self.ilogger.info('GOT SHIPPING ADDRESS')
                self.ilogger.info('MOVE_TO_CHECKOUT: DONE')
            else:
                if self.br.response() is not None:
                    iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('Failed to move to shipping address page now:'+self.br.geturl())
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('MOVE_TO_CHECKOUT: ERROR-1')
                raise Exception({
                    'ab_error': 'MOVE_TO_CHECKOUT: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

    def set_shipping_address(self, shipping_addr):
        self.ilogger.info('SET_SHIPPING_ADDRESS: START')
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            action_url = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//script[contains(text(),"singleshippingURL")]/text()', r"""singleshippingURL = \"([\w\d:/\-. ]+)\"""")

            form = mechanize.HTMLForm(action=action_url, method='POST')
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_firstName', type='text', attrs={'value': shipping_addr['first_name']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_lastName', type='text', attrs={'value': shipping_addr['last_name']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_address1', type='text', attrs={'value': shipping_addr['street_addr_01']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_address2', type='text', attrs={'value': shipping_addr['street_addr_02']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_country', type='select', attrs={'__select': {}, 'value': 'US', 'selected': True})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_city', type='text', attrs={'value': shipping_addr['city']})
            form.new_control(name='SelectedState', type='hidden', attrs={'value': ''})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_states_state', type='select', attrs={'__select': {}, 'value': shipping_addr['state'], 'selected': True})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_zip', type='text', attrs={'value': shipping_addr['zipcode']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_addressFields_phone', type='text', attrs={'value': shipping_addr['phone']})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_shippingMethodID', type='radio', attrs={'value': 'STANDARD', 'checked': True})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_isGift', type='radio', attrs={'value': 'false', 'checked': True})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_giftMessage', type='text', attrs={'value': ''})
            form.new_control(name='dwfrm_singleshipping_shippingAddress_save', type='text', attrs={'id': 'dwfrm_singleshipping_shippingAddress_save', 'value': 'Continue Checkout'})
            securekey = iCheck.get_value_by_xpath(self.ilogger,page_tree,'//input[@name="dwfrm_singleshipping_securekey"]/@value')
            form.new_control(name='dwfrm_singleshipping_securekey', type='hidden', attrs={'value': securekey})
            self.br.form = form
            self.br.submit()
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0022'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_SHIPPING_ADDRESS: ERROR')
            raise Exception({
                'ab_error': 'SET_SHIPPING_ADDRESS: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            self.check_addr_popup()
            if 'How do you want to pay' in self.br.response().read():
                self.ilogger.info('Got Billing info page')
                self.ilogger.info('SET_SHIPPING_ADDRESS: DONE')
            else:
                if self.br.response() is not None:
                    iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
                self.ilogger.info('Failed to move to Billing info page now:' + self.br.geturl())
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('SET_SHIPPING_ADDRESS: ERROR-1')
                raise Exception({
                    'ab_error': 'SET_SHIPPING_ADDRESS: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

    def check_addr_popup(self):
        self.ilogger.info('CHECK_ADDR_POPUP: START')
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            has_popup = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//div[@class="enter_partial"]//form[contains(@action,"checkout.shipping.saveAVSForm()")]')
            if has_popup is not None:
                self.br.select_form(nr=0)
                action_url = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//script[contains(text(),"avsURL ")]/text()', r"""avsURL = \"(.*)\"""")
                form = mechanize.HTMLForm(action=action_url, method='POST')
                form.new_control(name='dwfrm_addForm_useOrig', type='text', attrs={'value': 'true'})
                form.new_control(name='dwfrm_addForm_useOrig', type='text', attrs={'value': 'true'})
                form.new_control(name='format', type='text', attrs={'value': 'ajax'})
                form.new_control(name='format', type='text', attrs={'value': 'ajax'})
                form.new_control(name='', type='text', attrs={'value': ''})
                for i, each_control in enumerate(self.br.form.controls):
                    if each_control.name is not None and each_control.name != 'dwfrm_addForm_reSubmit':
                        form.new_control(name=each_control.name, type='text', attrs={'value': each_control.value})
                        if each_control.name == 'dwfrm_addForm_add2':
                            form.new_control(name='dwfrm_addForm_apt', type='text', attrs={'value': each_control.value})
                self.br.form = form
                self.br.submit()
            self.ilogger.info('CHECK_ADDR_POPUP: DONE')
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_ADDR_POPUP: ERROR')
            raise Exception({
                'ab_error': 'CHECK_ADDR_POPUP: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_price_info(self, is_checkout=False):
        self.ilogger.info('GET_PRICE_INFO: START')
        try:
            if is_checkout:
                self.br.open('https://www.carters.com/on/demandware.store/Sites-Carters-Site/default/COBilling-UpdateSummary?format=ajax&format=ajax&format=ajax&format=ajax')

            tmp_order_info = {}
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-subtotal"]/td[2]/text()', r"""([0-9.,]+)""")
            if total_price:
                tmp_order_info['total_price'] = total_price.replace(',', '')

            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-shipping"]/td[2]/text()', r"""([0-9.,]+)""")
            if shipping_fee:
                tmp_order_info['shipping_fee'] = shipping_fee.replace(',', '')

            discount_price_tmp = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-discount discount"]/td[2]/text()', r"""([0-9.,]+)""")
            if discount_price_tmp:
                tmp_order_info['discount_price'] = discount_price_tmp.replace(',', '')
            else:
                tmp_order_info['discount_price'] = '0'

            discount_price_tmp = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-shipping-discount discount"]/td[2]/text()', r"""([0-9.,]+)""")
            if discount_price_tmp:
                tmp_order_info['shipping_discount'] = discount_price_tmp.replace(',', '')
            else:
                tmp_order_info['shipping_discount'] = '0'

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-sales-tax"]/td[2]/text()', r"""([0-9.,]+)""")
            if tax_fee:
                tmp_order_info['tax_fee'] = tax_fee.replace(',', '')

            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//tr[@class="order-total"]/td[2]/text()', r"""([0-9.,]+)""")
            if est_price:
                tmp_order_info['est_price'] = est_price.replace(',', '')

            self.ilogger.info('GET_PRICE_INFO: DONE')
            return tmp_order_info
        except:
            if self.br.response() is not None:
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('GET_PRICE_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_PRICE_INFO: ERROR',
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

    def add_cart(self):
        self.ilogger.info('ADD_CART: START')
        try:
            for item in self.item_to_add:
                self.ilogger.info(item)
                url_add_to_cart = 'http://www.carters.com/on/demandware.store/Sites-Carters-Site/default/Cart-AddProduct?format=ajax'
                params = {
                    'Quantity': item['qty'],
                    'cartAction': 'add',
                    'pid': item['product_id']
                }
                post_data = urllib.urlencode(params)
                self.br.open(url_add_to_cart, post_data)
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

    def set_total_price(self, price_info, is_raw):
        self.ilogger.info('SET_TOTAL_PRICE: START')
        # self.ilogger.info('[order_info] ' + json.dumps(self.order_info))
        # self.ilogger.info('[price_info] ' + json.dumps(price_info))
        try:
            if is_raw is True:
                self.ilogger.info('SET RAW PRICE')
                self.order_info['raw_price'] = price_info
            # for i_key, i_value in price_info.items():
            #     self.order_info[i_key] = i_value
            self.ilogger.info('SET_TOTAL_PRICE: DONE')
        except:
            self.ilogger.info('SET_TOTAL_PRICE: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_TOTAL_PRICE: ERROR',
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
                        page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
                        action_url = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//form[@name="dwfrm_cart"]/@action')
                        form = mechanize.HTMLForm(action=action_url, method='POST')
                        form.new_control(name='id', type='hidden', attrs={'value': 'carters'})
                        form.new_control(name='dwfrm_cart_addCoupon', type='hidden', attrs={'value': 'dwfrm_cart_addCoupon'})
                        form.new_control(name='dwfrm_cart_couponCode', type='hidden', attrs={'value': coupon_code})
                        form.new_control(name='fromOshKosh', type='hidden', attrs={'value': 'false'})
                        self.br.form = form
                        self.br.submit()
                    except:
                        self.ilogger.error('coupon except')
                        self.ilogger.error(traceback.format_exc())

                # 쿠폰 적용 확인.
                page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
                coupon_xpath = '//tr[@class="rowcoupons" and .//div[@class="name"]]'
                adjusted_coupon_elems = iCheck.get_elements_by_xpath(self.ilogger, page_tree, coupon_xpath)
                if adjusted_coupon_elems is not None:
                    for a_coupon in adjusted_coupon_elems:
                        adjusted_coupon_code = iCheck.get_value_by_xpath(self.ilogger, a_coupon, './self::*[.//td[@class="item-total"]/span[not(contains(@class,"notapplied"))]]/td[@class="item-image"]/div[@class="name"]/text()', r"""code: \n(.*)""")
                        if adjusted_coupon_code is not None:
                            applied_coupon_list.append(adjusted_coupon_code)
                if applied_coupon_list:
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
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_COUPON_CODE: ERROR',
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
        carters = ABShopModCarters(
            order_id=kwargs.get('order_id'),
            e_id=kwargs.get('e_id'),
            login_id=kwargs.get('login_id'),
            login_passwd=kwargs.get('login_passwd'),
            items=items,
            ilogger=kwargs.get('ilogger')
        )

        carters.init_browser()
        carters.login()

        carters.add_cart()
        price_info = carters.get_cart_info()
        carters.set_total_price(price_info, True)

        coupon_applied = []
        if coupon_code is not False and len(coupon_code) > 0:
            coupon_applied = carters.set_coupon_code(coupon_code)
            price_info = carters.get_cart_info()
            carters.set_total_price(price_info, False)

        carters.move_to_checkout()
        carters.set_shipping_address(shipping_addr_info['NJ'])
        price_info = carters.get_price_info(True)

        if float(price_info['tax_fee']) > 0:
            carters.ilogger.info('::: CHANGE-SHIPPING-ADDR: START :::')
            carters.get_cart_info()
            carters.move_to_checkout()
            carters.set_shipping_address(shipping_addr_info['DE'])
            price_info = carters.get_price_info(True)
            carters.set_total_price(price_info, False)
            ship_addr_state = "DE"
            carters.ilogger.info('::: CHANGE-SHIPPING-ADDR: END :::')

        carters.close_browser()

        result = {
            "price_info_est": price_info,
            "order_info": carters.order_info,
            "coupon_applied": coupon_applied,
            "ship_addr_est": ship_addr_state
        }

        return result
    except Exception as e:
        carters.close_browser()
        report_error_slack(
            title=e.args[0]['ab_error'] if 'ab_error' in e.args[0] else e,
            order_id=carters.order_info['order_id'] if 'order_id' in carters.order_info else '',
            e_id=carters.order_info['e_id'] if 'e_id' in carters.order_info else '',
            shop_site_id=carters.order_info['shop_site_no'] if 'shop_site_no' in carters.order_info else '',
            shop_site_name=carters.order_info['shop_site_name'] if 'shop_site_name' in carters.order_info else '',
            module=e.args[0]['ab_module'] + "()@" + inspect.getfile(inspect.currentframe()) if 'ab_module' in e.args[0] else '',
            log_file_path=carters.ilogger.handlers[0].baseFilename
        )
        return False
