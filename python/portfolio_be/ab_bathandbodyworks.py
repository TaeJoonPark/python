#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import inspect
import json
import traceback
import mechanize
import urllib
#
# from lxml import html
# from lxml import etree

from selenium.webdriver.support.ui import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lib import iCheck
from lib.slack import report_error_slack

class ABShopModBathAndBodyWorks(object):
    BASE_URL = 'http://www.bathandbodyworks.com'

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
        self.selenium_br = None
        self.cookies = mechanize.CookieJar()
        # EBATES 쿠키 리스트
        # self.cookies_list = kwargs.get('cookies_list')

        self.order_id = kwargs.get('order_id')
        self.user_id = kwargs.get('login_id')
        self.user_passwd = kwargs.get('login_passwd')
        self.e_id = kwargs.get('e_id')
        self.item_to_add = kwargs.get('items')
        self.country_code = '840'
        self.shop_site_name = 'BATHANDBODYWORKS'
        self.shop_site_no = kwargs.get('order_shop_id')
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
            raise Exception({
                'ab_error': 'INIT_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def init_selenium_browser(self):
        self.ilogger.info('INIT_SELENIUM_BROWSER: START')
        try:
            from selenium import webdriver
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0'
            dcap["phantomjs.page.settings.loadImages"] = "false"
            service_args = ['--proxy-type=none',]
            self.selenium_br = webdriver.PhantomJS(executable_path="phantomjs", desired_capabilities=dcap, service_log_path='/var/log/afterbuy/ghostdriver.log', service_args=service_args)
            self.selenium_br.get('http://www.bathandbodyworks.com/home/index.jsp')
            self.selenium_br.delete_all_cookies()
            self.ilogger.info('Make selenium Object & delete cookies')
            for cookie in self.cookies:
                self.selenium_br.add_cookie({'name': cookie.name, 'value': cookie.value, 'path': '/', 'domain': cookie.domain})

            self.ilogger.info('INIT_SELENIUM_BROWSER: DONE')
        except:
            self.msg = json.dumps({'result': False, 'message': 'PYMF0020'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('INIT_SELENIUM_BROWSER: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'INIT_SELENIUM_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def login(self):
        self.ilogger.info('LOGIN: START')
        try:
            if self.br.request:
                self.ilogger.info(self.br.request.header_items())
            self.br.open('http://www.bathandbodyworks.com/home/index.jsp')
            action_url = 'https://www.bathandbodyworks.com/coreg/index.jsp'
            form = mechanize.HTMLForm(action=action_url, method='POST')
            form.new_control(name='token', type='hidden', attrs={'value': ''})
            form.new_control(name='crm', type='hidden', attrs={'value': ''})
            form.new_control(name='step', type='hidden', attrs={'value': 'login'})
            form.new_control(name='email', type='text', attrs={'value': self.user_id})
            form.new_control(name='password', type='text', attrs={'value': self.user_passwd})
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
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            login_xpath = '//script[contains(text(),"{uid}")]'.format(uid=self.user_id)
            myprofile_elem = iCheck.get_element_by_xpath(self.ilogger, page_tree, login_xpath)
            if myprofile_elem is not None:
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
                url_add_to_cart = 'http://www.bathandbodyworks.com/cartHandler/ajax.jsp'
                params = {
                    'action': 'skuAddToCart',
                    'prod_0': item['product_id'],
                    'qty_0': item['qty']
                }
                post_data = urllib.urlencode(params)
                self.br.open(url_add_to_cart, post_data)
                time.sleep(0.5)
            self.ilogger.info('ADD_CART: DONE')
        except:
            self.ilogger.info('ADD_CART: ERROR')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'ADD_CART: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_cart_info(self):
        self.ilogger.info('GET_CART_INFO: START')
        try:
            self.br.open('http://www.bathandbodyworks.com/cart/index.jsp')
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
            items = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//table[@class="item-table"]//tr[./td]')
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
                    'brand_name': self.shop_site_name
                }

                product_cnt = iCheck.get_value_by_xpath(self.ilogger, item, './/td[@class="quantity"]/input/@value')
                if product_cnt:
                    product['product_cnt'] = product_cnt

                product_no = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="product-details"]/dl[./dt[contains(text(),"Item #")]]/dd[2]/text()')
                product['product_no'] = product_no

                image_URL = iCheck.get_value_by_xpath(self.ilogger, item, './/div[contains(@class,"product-image")]/img/@src')
                if image_URL is not None and 'http' not in image_URL:
                    image_URL = self.BASE_URL + image_URL
                product['image_URL'] = image_URL

                product_name = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="product-details"]/h4/a/text()')
                product['product_name'] = product_name

                product_url = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="product-details"]/h4/a/@href')
                product['product_url'] = self.BASE_URL + product_url

                product_size = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="product-details"]//dd[contains(text(),"mL") or contains(text(),"oz")]/text()')
                product['product_size'] = product_size

                product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './td[@class="price" and not(.//*)]/text() | ./td[@class="price"]/div[@class="nowPrice"]/text()', r"""([0-9.,]+)""")
                if product_price_tmp:
                    product_price = product_price_tmp.replace(',', '')
                    product['product_price'] = product_price
                else:
                    product['product_price'] = '0'

                product['discount_price'] = '0'

                product_list.append(product)

            self.order_info['products'] = product_list
            self.ilogger.info('GET_CART_INFO: DONE')

            return product_list
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.response().read())
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('GET_CART_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_CART_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def move_to_checkout(self):
        self.ilogger.info('MOVE_TO_CHECKOUT: START')
        try:
            if self.selenium_br is None:
                self.init_selenium_browser()
            self.selenium_br.get(self.br.geturl())
            WebDriverWait(self.selenium_br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//button[@id="checkout-top"]')))
            checkout_btn = self.selenium_br.find_element_by_xpath('//button[@id="checkout-top"]')
            checkout_btn.click()
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.selenium_br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_TO_CHECKOUT: ERROR')
            raise Exception({
                'ab_error': 'MOVE_TO_CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_text = self.check_page()
            if page_text != 'address':
                self.ilogger.debug('This page is not address page')
                self.move_back_to_checkout()
            else:
                print 'self.br.current_url: '+self.selenium_br.current_url
                self.ilogger.info('MOVE_TO_CHECKOUT: DONE')

    def move_back_to_checkout(self):
        self.ilogger.info('MOVE_BACK_TO_CHECKOUT: START')
        try:
            WebDriverWait(self.selenium_br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//ol[@id="progress"]/li[@id="progress-address"]/a')))
            self.selenium_br.execute_script('store.checkout.doLink("editAddress");')
            self.ilogger.info('MOVE_BACK_TO_CHECKOUT: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.selenium_br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_BACK_TO_CHECKOUT: ERROR')
            raise Exception({
                'ab_error': 'MOVE_BACK_TO_CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def check_page(self):
        self.ilogger.info('CHECK_PAGE: START')
        try:
            WebDriverWait(self.selenium_br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//li[@class="current"]')))
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.selenium_br.page_source.encode('utf-8'))
            current_value = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//li[@class="current"]/@id')
            if current_value is not None:
                self.ilogger.info('CHECK_PAGE :' + current_value)
                if 'progress-address' in current_value:
                    return 'address'
                elif 'progress-shipping' in current_value:
                    return 'shipping'
                elif 'progress-payment' in current_value:
                    return 'payment'
                elif 'progress-review' in current_value:
                    return 'review'
                elif 'progress-confirm' in current_value:
                    return 'confirm'
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_PAGE: ERROR')
            raise Exception({
                'ab_error': 'CHECK_PAGE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_coupon_code(self, coupon_code_list):
        self.ilogger.info('SET_COUPON_CODE: START')
        try:
            coupon_code = self.apply_coupon_code(coupon_code_list)

            applied_coupon_list = []
            if coupon_code != "":
                applied_coupon_list.append(coupon_code)

                self.order_info['site_coupon_code'] = coupon_code
                self.ilogger.info('Applied coupon list= '+coupon_code)
                # 가장 할인이 많이 된 쿠폰 적용(하나씩밖에 적용인 안되어 기존코드가 날라간 상태이므로)
                self.apply_coupon_code(applied_coupon_list)
            else:
                self.ilogger.info('No coupon adjusted')

            self.ilogger.info('SET_COUPON_CODE: DONE')
            return applied_coupon_list
        except:
            self.ilogger.info('SET_COUPON_CODE: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_COUPON_CODE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def apply_coupon_code(self, coupon_code_list):
        self.ilogger.info('APPLY_COUPON_CODE: START')
        try:
            applied_coupon = ""
            for index, coupon_code in enumerate(coupon_code_list):
                self.ilogger.info("coupon_code: " + coupon_code)
                try:
                    action_url = 'http://www.bathandbodyworks.com/applypromocode.jsp'
                    form = mechanize.HTMLForm(action=action_url, method='POST')
                    form.new_control(name='formView', type='hidden', attrs={'value': 'redirect:/cart/index.jsp'})
                    form.new_control(name='successView', type='hidden', attrs={'value': 'redirect:/cart/index.jsp'})
                    form.new_control(name='promoCode', type='text', attrs={'value': coupon_code})
                    self.br.form = form
                    self.br.submit()

                    page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())
                    el_applied_coupon = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//ul[@class="error cartCommand"]//text()')
                    est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[.//span[contains(text(),"Order Total")]]/td[2]/span/text()', r"""([0-9.,]+)""")

                    if el_applied_coupon is None and est_price is not None:
                        if float(est_price) < float(self.order_info['est_price']):
                            applied_coupon = coupon_code
                            self.order_info['est_price'] = est_price
                except:
                    self.ilogger.error('coupon except')
                    self.ilogger.error(traceback.format_exc())
                    continue

            return applied_coupon
        except:
            self.ilogger.info('APPLY_COUPON_CODE: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'APPLY_COUPON_CODE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })


    def set_billing_address(self, billing_addr):
        self.ilogger.info('SET_BILLING_ADDRESS: START')
        try:
            WebDriverWait(self.selenium_br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//input[@id="billingAddress.address.firstName"]')))
            time.sleep(self.WAIT_INTERVAL)
            first_name_eng = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.firstName"]')
            self.move_to_element(first_name_eng)
            first_name_eng.clear()
            first_name_eng.send_keys(billing_addr['first_name'])

            last_name_eng = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.lastName"]')
            self.move_to_element(last_name_eng)
            last_name_eng.clear()
            last_name_eng.send_keys(billing_addr['last_name'])

            street_address1 = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.address1"]')
            self.move_to_element(street_address1)
            street_address1.clear()
            street_address1.send_keys(billing_addr['street_addr_01'])

            street_address2 = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.address2"]')
            self.move_to_element(street_address2)
            street_address2.clear()
            street_address2.send_keys(billing_addr['street_addr_02'])

            city = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.city"]')
            self.move_to_element(city)
            city.clear()
            city.send_keys(billing_addr['city'])

            state = self.selenium_br.find_element_by_xpath('//select[@id="billingAddress.address.state"]')
            self.move_to_element(state)
            state_xpath = '//select[@id="billingAddress.address.state"]/option[@value="{ov}"]'.format(ov=billing_addr['state'])
            detail_state = state.find_element_by_xpath(state_xpath)
            detail_state.click()

            zipcode = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.address.postalCode"]')
            self.move_to_element(zipcode)
            zipcode.clear()
            zipcode.send_keys(billing_addr['zipcode'])

            phone = self.selenium_br.find_element_by_xpath('//input[@id="billingAddress.phone"]')
            self.move_to_element(phone)
            phone.clear()
            phone.send_keys(billing_addr['phone'])

            option_radio = self.selenium_br.find_element_by_xpath('//input[@id="shipOption2"]')
            self.move_to_element(option_radio)
            option_radio.click()

            self.ilogger.info('SET_BILLING_ADDRESS: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.selenium_br.page_source.encode('utf-8'))
            self.msg = json.dumps({'result': False, 'message': 'PYMF0022'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('SET_BILLING_ADDRESS: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_BILLING_ADDRESS: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_shipping_address(self, shipping_addr):
        self.ilogger.info('SET_SHIPPING_ADDRESS: START')
        try:
            WebDriverWait(self.selenium_br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//input[@id="shippingAddress.address.firstName"]')))
            first_name_eng = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.firstName"]')
            self.move_to_element(first_name_eng)
            time.sleep(self.WAIT_INTERVAL)
            first_name_eng.clear()
            first_name_eng.send_keys(shipping_addr['first_name'])

            last_name_eng = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.lastName"]')
            self.move_to_element(last_name_eng)
            last_name_eng.clear()
            last_name_eng.send_keys(shipping_addr['last_name'])

            street_address1 = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.address1"]')
            self.move_to_element(street_address1)
            street_address1.clear()
            street_address1.send_keys(shipping_addr['street_addr_01'])

            street_address2 = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.address2"]')
            self.move_to_element(street_address2)
            street_address2.clear()
            street_address2.send_keys(shipping_addr['street_addr_02'])

            city = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.city"]')
            self.move_to_element(city)
            city.clear()
            city.send_keys(shipping_addr['city'])

            state = self.selenium_br.find_element_by_xpath('//select[@id="shippingAddress.address.state"]')
            self.move_to_element(state)
            state_xpath = '//select[@id="shippingAddress.address.state"]/option[@value="{ov}"]'.format(ov=shipping_addr['state'])
            detail_state = state.find_element_by_xpath(state_xpath)
            detail_state.click()

            zipcode = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.address.postalCode"]')
            self.move_to_element(zipcode)
            zipcode.clear()
            zipcode.send_keys(shipping_addr['zipcode'])

            phone = self.selenium_br.find_element_by_xpath('//input[@id="shippingAddress.phone"]')
            self.move_to_element(phone)
            phone.clear()
            phone.send_keys(shipping_addr['phone'])

            self.selenium_br.execute_script('document.forms["address"].submit();')
            self.ilogger.info('SET_SHIPPING_ADDRESS: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.selenium_br.page_source.encode('utf-8'))
            self.ilogger.info('SET_SHIPPING_ADDRESS: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_SHIPPING_ADDRESS: ERROR',
                'ab_module': inspect.stack()[0][3]
            })


    def get_price_info(self, is_selenium):
        self.ilogger.info('GET_PRICE_INFO: START')
        try:
            tmp_order_info = {}
            if is_selenium:
                time.sleep(self.WAIT_INTERVAL)

                """
                self.ilogger.debug('self.br.current_url: ' + self.selenium_br.current_url)
                page_tree = iCheck.parse_htmlpage(self.ilogger, self.selenium_br.page_source.encode('utf-8'))
                current_value = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//li[@class="current"]/@id')
                self.ilogger.debug('current_value: ' + current_value)
                if current_value == 'progress-address':
                    err_msg = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//ul[@class="error"]//li/text()')
                    if err_msg:
                        self.ilogger.debug('err_msg: ' + err_msg)
                    iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name,
                                                inspect.stack()[0][3].strip(), inspect.stack()[0][2],
                                                self.selenium_br.page_source.encode('utf-8'))
                """

                page_tree = iCheck.parse_htmlpage(self.ilogger, self.selenium_br.page_source.encode('utf-8'))
            else:
                page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.response().read())

            total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[.//span[contains(text(),"Merchandise Subtotal")]]/td[2]/span/text()', r"""([0-9.,]+)""")
            if total_price:
                tmp_order_info['total_price'] = total_price.replace(',', '')
            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[./td[contains(text(),"Estimated Shipping & Handling")]]/td[2]/text()', r"""([0-9.,]+)""")
            if shipping_fee:
                tmp_order_info['shipping_fee'] = shipping_fee.replace(',', '')

            discount_price_tmp = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[@class="promo"]/td[2]/text()', r"""([0-9.,]+)""")
            if discount_price_tmp:
                tmp_order_info['discount_price'] = discount_price_tmp.replace(',', '')
            else:
                tmp_order_info['discount_price'] = '0'

            tmp_order_info['shipping_discount'] = '0'

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[./td[contains(text(),"Sales Tax")]]/td[2]/text()', r"""([0-9.,]+)""")
            if tax_fee:
                tmp_order_info['tax_fee'] = tax_fee.replace(',', '')
            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//table[@summary="Estimated Total Cost"]//tr[.//span[contains(text(),"Order Total")]]/td[2]/span/text()', r"""([0-9.,]+)""")
            if est_price:
                tmp_order_info['est_price'] = est_price.replace(',', '')

            self.ilogger.info('GET_PRICE_INFO: DONE')
            return tmp_order_info
        except:
            self.ilogger.info('GET_PRICE_INFO: ERROR')
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            raise Exception({
                'ab_error': 'GET_PRICE_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_total_price(self, detail_price_info, is_raw):
        try:
            self.ilogger.info('SET TOTAL PRICE')
            if is_raw:
                self.ilogger.info('SET RAW PRICE')
                self.order_info['raw_price'] = detail_price_info
            for i_key, i_value in detail_price_info.items():
                self.order_info[i_key] = i_value
        except:
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'SET_TOTAL_PRICE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def move_to_element(self, element):
        self.ilogger.info('MOVE_TO_ELEMENT: START')
        try:
            elem_y = element.location["y"]
            self.selenium_br.execute_script('window.scrollTo(0, {0})'.format(elem_y))
            self.ilogger.info('MOVE_TO_ELEMENT: DONE')
        except:
            self.ilogger.info('MOVE_TO_ELEMENT: ERROR')
            self.ilogger.error(traceback.format_exc())

    def close_browser(self):
        self.ilogger.info('CLOSE_BROWSER: START')
        try:
            if self.br:
                self.br.close()
            self.ilogger.info('CLOSE_BROWSER: DONE')
        except:
            self.ilogger.info('CLOSE_BROWSER: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'CLOSE_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def close_selenium_browser(self):
        self.ilogger.info('CLOSE_SELENIUM_BROWSER: START')
        try:
            if self.selenium_br:
                self.selenium_br.quit()
            self.ilogger.info('CLOSE_SELENIUM_BROWSER: DONE')
        except:
            self.ilogger.info('CLOSE_SELENIUM_BROWSER: ERROR')
            self.ilogger.error(traceback.format_exc())
            raise Exception({
                'ab_error': 'CLOSE_SELENIUM_BROWSER: ERROR',
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
        bbw = ABShopModBathAndBodyWorks(
            order_id=kwargs.get('order_id'),
            e_id=kwargs.get('e_id'),
            login_id=kwargs.get('login_id'),
            login_passwd=kwargs.get('login_passwd'),
            items=items,
            ilogger=kwargs.get('ilogger')
        )

        bbw.init_browser()
        bbw.login()

        bbw.add_cart()
        bbw.get_cart_info()
        price_info = bbw.get_price_info(False)
        if price_info:
            bbw.set_total_price(price_info, True)

        coupon_applied = []
        if coupon_code is not False and len(coupon_code) > 0:
            coupon_applied = bbw.set_coupon_code(coupon_code)
            bbw.get_cart_info()

        bbw.move_to_checkout()
        bbw.set_billing_address(shipping_addr_info['NJ'])
        bbw.set_shipping_address(shipping_addr_info['NJ'])
        price_info = bbw.get_price_info(True)

        if float(price_info['tax_fee']) > 0:
            bbw.ilogger.info('::: CHANGE-SHIPPING-ADDR: START :::')
            bbw.move_back_to_checkout()
            bbw.set_billing_address(shipping_addr_info['NJ'])
            bbw.set_shipping_address(shipping_addr_info['DE'])
            price_info = bbw.get_price_info(True)
            ship_addr_state = "DE"
            bbw.ilogger.info('::: CHANGE-SHIPPING-ADDR: END :::')

        bbw.close_browser()
        bbw.close_selenium_browser()

        result = {
            "price_info_est": price_info,
            "order_info": bbw.order_info,
            "coupon_applied": coupon_applied,
            "ship_addr_est": ship_addr_state
        }

        return result
    except Exception as e:
        bbw.close_browser()
        bbw.close_selenium_browser()

        report_error_slack(
            title=e.args[0]['ab_error'] if 'ab_error' in e.args[0] else e,
            order_id=bbw.order_info['order_id'] if 'order_id' in bbw.order_info else '',
            e_id=bbw.order_info['e_id'] if 'e_id' in bbw.order_info else '',
            shop_site_id=bbw.order_info['shop_site_no'] if 'shop_site_no' in bbw.order_info else '',
            shop_site_name=bbw.order_info['shop_site_name'] if 'shop_site_name' in bbw.order_info else '',
            module=e.args[0]['ab_module'] + "()@" + inspect.getfile(inspect.currentframe()) if 'ab_module' in e.args[0] else '',
            log_file_path=bbw.ilogger.handlers[0].baseFilename
        )

        return False

"""
if __name__ == '__main__':
    from lib.iLogger import set_logger
    args = {
        'folder_name': 'ab_price_estimate',
        'shop_site_name': 'BATHANDBODYWORKS',
        'order_id': 1234567890,
        'e_id': 11740,
    }
    ilogger = set_logger(args)

    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read('../conf/shipping_address.conf')
    result = {}
    states = config.sections()
    for state in states:
        result[state] = dict(config.items(state))
    shipping_addr_info = result

    order_info = [
        {'product_id': '4004121|7268476', 'product_qty': 1},
        {'product_id': '23437836|16654379', 'product_qty': 1},
        {'product_id': '84194446|23259512', 'product_qty': 1},
        {'product_id': '60840696|20950378', 'product_qty': 1},
        {'product_id': '60840686|20950390', 'product_qty': 4}
    ]

    site_coupon = [
        'SUMMER4U',
        'FREESUMMERFUN',
        'YOUGLOWGIRL',
        'WELOVESALE',
        'OMGYAY',
        'WAHOO',
        'CELEBRATE'
    ]

    do_estimate_price(
        order_id=1234567890,
        e_id=11740,
        order_shop_id=28,
        order_info=order_info,
        login_id='gdhong88+2wsx@gmail.com',
        login_passwd='Dkdlelqm2wsx',
        shipping_addr_info=shipping_addr_info,
        site_coupon=site_coupon,
        ilogger=ilogger
    )
"""
