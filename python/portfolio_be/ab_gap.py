#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import inspect
import json
import traceback
from datetime import datetime, date, timedelta
from lxml import objectify

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lib import iCheck
from lib.slack import report_error_slack

import selenium.webdriver.support.expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

class ABShopModGap(object):
    BASE_URL = 'https://secure-www.gap.com'
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

        # selenium 객체
        self.br = None

        self.max_retry = 0

        self.item_to_add = kwargs.get('items')
        self.order_info = dict()

        self.order_id = kwargs.get('order_id')
        self.user_id = kwargs.get('login_id')
        self.user_passwd = kwargs.get('login_passwd')
        self.e_id = kwargs.get('e_id')
        self.country_code = '840'
        self.shop_site_name = 'GAP_GROUP'
        self.shop_site_no = 9999
        self.user_coupon = kwargs.get('user_coupon')
        self.order_info['order_id'] = self.order_id
        self.order_info['e_id'] = self.e_id
        self.order_info['country_code'] = self.country_code
        self.order_info['shop_site_name'] = self.shop_site_name
        self.order_info['shop_site_no'] = self.shop_site_no
        self.signup_coupon = ()
        self.new_payment_form = False

    def init_browser(self):
        self.ilogger.info('INIT_BROWSER: START')
        try:
            # PhantomJS configuration
            from selenium import webdriver
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
            dcap["phantomjs.page.settings.loadImages"] = 'false'
            self.br = webdriver.PhantomJS(executable_path="phantomjs", desired_capabilities=dcap, service_log_path='/var/log/afterbuy/ghostdriver.log')
            self.br.maximize_window()
            self.br.delete_all_cookies()

            self.ilogger.info('INIT BROWSER: DONE')
        except:
            self.msg = json.dumps({'result': False, 'message': 'PYMF0027'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('INIT BROWSER: ERROR')
            raise Exception({
                'ab_error': 'INIT_BROWSER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def login(self):
        self.ilogger.info('LOGIN: START')
        try:
            self.br.get('https://secure-www.gap.com/profile/sign_in.do')
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//input[@id="emailAddress"]')))
            emailAddress = self.br.find_element_by_xpath('//input[@id="emailAddress"]')
            password = self.br.find_element_by_xpath('//input[@id="password"]')
            signInButton = self.br.find_element_by_xpath('//input[@id="signInButton"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            signInButton.click()
            self.ilogger.info('LOGIN: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('LOGIN: ERROR')
            raise Exception({
                'ab_error': 'LOGIN: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def add_cart(self):
        self.ilogger.info('ADD_CART: START')
        try:
            for item in self.item_to_add:
                self.ilogger.info(item)

                # product_url
                if 'oldnavy.gap.com' in item['product_url']:
                    domain = 'm.oldnavy.gap.com'
                elif 'athleta.gap.com' in item['product_url']:
                    domain = 'm.athleta.gap.com'
                elif 'bananarepublic.gap.com' in item['product_url']:
                    domain = 'm.bananarepublic.gap.com'
                else:
                    domain = 'm.gap.com'

                url_add_to_cart = 'http://'+domain+'/buy/inlineShoppingBagAdd.do?skuid='+item['product_id']+'&quantity'+item['product_id']+'='+str(item['qty'])+'&sfl'+item['product_id']+'=false&cid'+item['product_id']+'=&_='
                self.br.get(url_add_to_cart)
                time.sleep(0.5)

            self.ilogger.info('ADD_CART: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0002'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('ADD_CART: ERROR')
            raise Exception({
                'ab_error': 'ADD_CART: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_cart_info(self):
        self.ilogger.info('GET_CART_INFO: START')
        try:
            self.br.get('https://secure-www.gap.com/buy/shopping_bag.do')

            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.page_source.encode('utf-8'))
            item_rows = '(//div[contains(@class,"lineItemsContainer")]/div[@class="ng-scope"])'
            items = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//div[contains(@class,"lineItemsContainer")]/div[@class="ng-scope"]')
            product_list = []

            # 빈 장바구니 경우 종료
            if not items:
                self.ilogger.info('No products found in basket 1')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0004'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('GET_CART_INFO: ERROR - EMPTY CART')
                raise Exception({
                    'ab_error': 'GET_CART_INFO: ERROR - EMPTY CART',
                    'ab_module': inspect.stack()[0][3]
                })

            brand_name_list = []
            for i_idx, item in enumerate(items):
                product = {
                    'country_code': self.country_code,
                    'shop_site_name': self.shop_site_name,
                    'shop_site_no': self.shop_site_no
                }

                product_cnt = iCheck.get_value_by_xpath(self.ilogger, item, './/option[@selected]/text()')
                if product_cnt:
                    product['product_cnt'] = product_cnt

                product_no = iCheck.get_value_by_xpath(self.ilogger, item, './/dd[contains(@class,"productSku")]/@alt')
                product['product_no'] = product_no

                product_name = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//dd[@class="productName"]/a/text()')
                product['product_name'] = product_name

                brand_name = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="brandLogo"]/div/@class', """\-(.*)""")

                if brand_name is not None:
                    if 'gap' in brand_name.lower():
                        if product_name.startswith('Factory'):
                            brand_name = 'GAP_FACTORY'
                        else:
                            brand_name = 'GAP'
                    if 'on' in brand_name.lower():
                        brand_name = 'OLDNAVY'
                    if 'br' in brand_name.lower():
                        if product_name.startswith('Factory'):
                            brand_name = 'BANANAREPUBLIC_FACTORY'
                        else:
                            brand_name = 'BANANAREPUBLIC'
                    if 'at' in brand_name.lower():
                        brand_name = 'ATHLETA'

                    brand_name_list.append(brand_name)
                    product['brand_name'] = brand_name

                    image_URL = iCheck.get_value_by_xpath(self.ilogger, item, './/img/@src')
                    product['image_URL'] = self.BASE_URL + image_URL

                    product_url = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//dd[@class="productName"]/a/@href')
                    product['product_url'] = product_url

                    product_color = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Color")]]/dd/a/text()')
                    product['product_color'] = product_color

                    product_size = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Size")]]/dd/a/text()')
                    product['product_size'] = product_size

                    product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span[contains(@class,"font9")]/text()', r"""([0-9.,]+)""")
                    if product_price_tmp:
                        product_price = product_price_tmp.replace(',', '')
                        self.ilogger.debug('product_price = {pp}'.format(pp=product_price))
                        product['product_price'] = float(product_price)
                        product['discount_price'] = 0.00
                    # else:
                    #     product_price_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span//span[contains(@class,"font8")]/text()', r"""([0-9.,]+)""")
                    #     product_price_sale_tmp = iCheck.get_value_by_xpath(self.ilogger, item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span//span[contains(@class,"font9")]/text()', r"""([0-9.,]+)""")
                    #
                    #     if product_price_tmp and product_price_sale_tmp:
                    #         product_price = product_price_tmp.replace(',', '')
                    #         product_price_sale = product_price_sale_tmp.replace(',', '')
                    #         self.ilogger.debug('product_price = {pp}'.format(pp=product_price))
                    #         self.ilogger.debug('discount_price = {pp}'.format(pp=product_price_sale))
                    #         product['product_price'] = float(product_price)
                    #         product['discount_price'] = round(float(product_price) - float(product_price_sale), 2)

                    product_list.append(product)

            self.order_info['products'] = product_list
            self.ilogger.info('PRODUCT_LIST')
            self.ilogger.info(product_list)
            self.ilogger.info('GET_CART_INFO: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('GET_CART_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_CART_INFO: ERROR',
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

    def set_delivery_type(self):
        self.ilogger.info('SET_DELIVERY_TYPE: START')

        try:
            time.sleep(self.WAIT_INTERVAL)
            self.ilogger.info('select_delivery_type')
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.page_source.encode('utf-8'))
            self.ilogger.info('will collect delivery_type info')
            # 배송 타입 추출 후 각 상품에 매칭.
            each_type_list = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//div[@class="list-group shippingListGroup"]//div[./input[@ng-disabled="false"]]')
            each_d_info_list = []
            for each_type in each_type_list:
                each_d_info = {}
                delivery_group = iCheck.get_value_by_xpath(self.ilogger, each_type, './input/@name')
                each_d_info['delivery_group'] = delivery_group

                delivery_value = iCheck.get_value_by_xpath(self.ilogger, each_type, './input/@id')
                each_d_info['delivery_value'] = delivery_value

                # delivery_info_text_01 = iCheck.get_values_by_xpath(self.ilogger, each_type, './label/div[@class="g-1-2"]/text()')
                # delivery_info_text_02 = iCheck.get_values_by_xpath(self.ilogger, each_type, './label/div[@class="g-1-2"]/span/text()')
                # each_d_info['delivery_title'] = delivery_info_text_01[0] + ' ' + delivery_info_text_02[0]
                each_d_info['delivery_title'] = iCheck.get_value_by_xpath(self.ilogger, each_type, './label/text()[2]')
                each_d_info['delivery_detail'] = ''

                delivery_fee = iCheck.get_value_by_xpath(self.ilogger, each_type, './label/span/text()', r"""([0-9.,]+)""")
                if delivery_fee:
                    each_d_info['delivery_fee'] = delivery_fee.replace(',', '')
                else:
                    each_d_info['delivery_fee'] = '0'
                each_d_info_list.append(each_d_info)

            for o_product in self.order_info['products']:
                o_product['shop_site_delivery_info'] = each_d_info_list

            # print each_d_info_list
            delivery_type_value = each_d_info_list[0]['delivery_value']
            self.ilogger.info('delivery value {:}'.format(delivery_type_value))

            is_default = False
            if '6003' in delivery_type_value or '2100' in delivery_type_value:
                is_default = True
            else:
                self.ilogger.info('no default')

            btn_xpath = '//div[./input[@id="{d_id}"]]/input'.format(d_id=delivery_type_value)
            if not self.set_delivery_value(btn_xpath):
                self.ilogger.info('failed to select')
                if is_default:
                    self.ilogger.info('try again')
                    # 값 변경 후 재시도.
                    if '6003' in delivery_type_value:
                        delivery_type_value = delivery_type_value.replace('6003', '1304')
                    elif '1304' in delivery_type_value:
                        delivery_type_value = delivery_type_value.replace('1304', '6003')
                    btn_xpath = '//div[./input[@id="{d_id}"]]/input'.format(d_id=delivery_type_value)
                    if not self.set_delivery_value(btn_xpath):
                        self.ilogger.error('can not found selected delivery type')
                        self.ilogger.info('SET_DELIVERY_TYPE: ERROR-1')
                        raise Exception({
                            'ab_error': 'SET_DELIVERY_TYPE: ERROR-1',
                            'ab_module': inspect.stack()[0][3]
                        })
                else:
                    self.ilogger.info('SET_DELIVERY_TYPE: ERROR-2')
                    raise Exception({
                        'ab_error': 'SET_DELIVERY_TYPE: ERROR-2',
                        'ab_module': inspect.stack()[0][3]
                    })
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.msg = json.dumps({'result': False, 'message': 'PYMF0031'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_DELIVERY_TYPE: ERROR')
            raise Exception({
                'ab_error': 'SET_DELIVERY_TYPE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.page_source.encode('utf-8'))
            selected_delivery_type_xpath = btn_xpath + '/@checked'
            checked_input_value = iCheck.get_element_by_xpath(self.ilogger, page_tree, selected_delivery_type_xpath)
            if checked_input_value is not None:
                self.ilogger.info('successfully selected delivery type to {dt}'.format(dt=each_d_info_list[0]['delivery_value']))
                self.ilogger.info('SET_DELIVERY_TYPE: DONE')
            else:
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
                self.ilogger.info('Failed to select delivery type')
                self.msg = json.dumps({'result': False, 'message': 'PYMF0035'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('SET_DELIVERY_TYPE: ERROR-3')
                raise Exception({
                    'ab_error': 'SET_DELIVERY_TYPE: ERROR-3',
                    'ab_module': inspect.stack()[0][3]
                })

    def set_delivery_value(self, delievery_xpath):
        self.ilogger.info('SET_DELIVERY_VALUE: START')
        try:

            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, delievery_xpath)))
            delivery_type_elem = self.br.find_element_by_xpath(delievery_xpath)
            self.move_to_element(delivery_type_elem)
            delivery_type_elem.click()
            time.sleep(self.WAIT_INTERVAL)
            self.ilogger.info('SET_DELIVERY_VALUE: DONE')
            return True
        except:
            self.ilogger.error(traceback.format_exc())
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.info('SET_DELIVERY_VALUE: ERROR')
            return False

    def checkout(self):
        self.ilogger.info('CHECKOUT: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//button[contains(@class,"shoppingBagCheckoutButton")]')))
            checkout_btn = self.br.find_element_by_xpath('//button[contains(@class,"shoppingBagCheckoutButton")]')
            self.move_to_element(checkout_btn)
            checkout_btn.click()

            if self.check_shipping_page():
                checkout_btn2 = self.br.find_element_by_xpath('//button[contains(@class,"shoppingBagCheckoutButton")]')
                self.move_to_element(checkout_btn2)
                checkout_btn2.click()
        except:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECKOUT: ERROR')
            raise Exception({
                'ab_error': 'CHECKOUT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            try:
                self.move_back_to_shipping_address()
            except:
                pass
            finally:
                if '/checkout/order.do' in self.br.current_url:
                    self.ilogger.info('GOT SHIPPING ADDRESS')
                    self.ilogger.info('CHECKOUT: DONE')
                else:
                    iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
                    self.ilogger.info('Failed to move to shipping address page now:'+self.br.current_url)
                    self.msg = json.dumps({'result': False, 'message': 'PYMF0037'}, ensure_ascii=False, encoding='utf-8')
                    self.ilogger.info('CHECKOUT: ERROR-1')
                    raise Exception({
                        'ab_error': 'CHECKOUT: ERROR-1',
                        'ab_module': inspect.stack()[0][3]
                    })

    def set_shipping_info(self, shipping_addr):
        self.ilogger.info('SET_SHIPPING_INFO: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="shippingAddressFieldGroup4-shippingFirstName"]')))

            el_first_name = self.br.find_element_by_xpath('//input[@id="shippingAddressFieldGroup4-shippingFirstName"]')
            self.move_to_element(el_first_name)
            el_first_name.clear()
            el_first_name.send_keys(shipping_addr['first_name'])

            el_last_name = self.br.find_element_by_xpath('//input[@id="shippingAddressFieldGroup4-shippingLastName"]')
            self.move_to_element(el_last_name)
            el_last_name.clear()
            el_last_name.send_keys(shipping_addr['last_name'])

            el_street_addr_01 = self.br.find_element_by_xpath(
                '//input[@id="shippingAddressFieldGroup4-shippingAddressLine1"]')
            self.move_to_element(el_street_addr_01)
            el_street_addr_01.clear()
            el_street_addr_01.send_keys(shipping_addr['street_addr_01'])

            el_street_addr_02 = self.br.find_element_by_xpath(
                '//input[@id="shippingAddressFieldGroup4-shippingAddressLine2"]')
            self.move_to_element(el_street_addr_02)
            el_street_addr_02.clear()
            el_street_addr_02.send_keys(shipping_addr['street_addr_02'])

            el_city = self.br.find_element_by_xpath('//input[@id="shippingAddressFieldGroup4-shippingCity"]')
            self.move_to_element(el_city)
            el_city.clear()
            el_city.send_keys(shipping_addr['city'])

            el_state = self.br.find_element_by_xpath('//select[@id="shippingAddressFieldGroup4-shippingState"]')
            self.move_to_element(el_state)
            el_state_xpath = '//select[@id="shippingAddressFieldGroup4-shippingState"]/option[@value="{ov}"]'.format(
                ov=shipping_addr['state'])
            detail_state = el_state.find_element_by_xpath(el_state_xpath)
            detail_state.click()

            el_zipcode = self.br.find_element_by_xpath('//input[@id="shippingAddressFieldGroup4-shippingPostalCode"]')
            self.move_to_element(el_zipcode)
            el_zipcode.clear()
            el_zipcode.send_keys(shipping_addr['zipcode'])

            el_phone = self.br.find_element_by_xpath('//input[@id="shippingDayPhone"]')
            self.move_to_element(el_phone)
            el_phone.clear()
            el_phone.send_keys(shipping_addr['phone'])

            self.br.execute_script('ccm.shipping.openBillingShippingOverLayModule();')

            self.check_addr_popup()

            is_clicked = self.check_edit_shipping_address()
            if not is_clicked:
                self.ilogger.info('!!! can not click btn')
                self.br.execute_script('ccm.shipping.openBillingShippingOverLayModule();')
        except:
            iCheck.make_screen_shot(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br)
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.msg = json.dumps({'result': False, 'message': 'PYMF0022'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_SHIPPING_INFO: ERROR')
            raise Exception({
                'ab_error': 'SET_SHIPPING_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            is_clicked = self.check_edit_shipping_address()
            if is_clicked:
                has_bill = self.check_edit_billing_info()
                if has_bill:
                    self.br.execute_script('ccm.billing.getBillingEdit();')
                    has_input = self.check_set_billing_info()
                    if has_input:
                        self.ilogger.info('GOT SHIPPING METHOD PAGE')
                    else:
                        self.ilogger.info('can not clicked payment edit btn')
                        self.br.execute_script('ccm.billing.getBillingEdit();')

                self.ilogger.info('SET_SHIPPING_INFO: DONE')
            else:
                iCheck.make_screen_shot(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br)
                self.ilogger.info('Failed to move to SHIPPING METHOD PAGE now:{c_url}'.format(c_url=self.br.current_url))
                self.msg = json.dumps({'result': False, 'message': 'PYMF0001'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('SET_SHIPPING_INFO: ERROR-1')
                raise Exception({
                    'ab_error': 'SET_SHIPPING_INFO: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })

    def open_shipping_addr_form(self):
        self.ilogger.info('OPEN_SHIPPING_ADDR_FORM: START')
        try:
            self.br.execute_script("ccm.shipping.getShippingEdit();")
            if not self.check_set_shipping_address():
                self.ilogger.info('refresh selenium @ open_shipping_addr_form')
                self.br.refresh()

                self.ilogger.info('OPEN_SHIPPING_ADDR_FORM: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
        self.ilogger.info('OPEN_SHIPPING_ADDR_FORM: ERROR')

    # 주소 정정 및 빌링 어드레스 복사를 묻는 팝업 닫기
    def check_addr_popup(self):
        self.ilogger.info('CHECK_ADDR_POPUP: START')
        try:
            self.ilogger.info('check_addr_popup addr yes popup')
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.element_to_be_clickable((By.XPATH, '//input[@id="updateBillingSameAsShippingYesButton"]')))
            self.ilogger.info('show addr popup')
            self.br.execute_script('checkout.controller.modules.updateBillingWithShipping.getUpdateBillingWithShippingRequest(false);')
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_ADDR_POPUP: WARN-1')

        try:
            self.ilogger.info('check_addr_popup confirm addr popup')
            addr_popup_confirm_btn_xpath = '//div[@id="addressVerificationPanel" and not(contains(@style,"none"))]//input[@id="addressVerificationConfirmAddressButton"]'
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.element_to_be_clickable((By.XPATH, addr_popup_confirm_btn_xpath)))
            self.ilogger.info('show addr confirm popup')
            addr_popup_confirm_btn = self.br.find_element_by_xpath(addr_popup_confirm_btn_xpath)
            self.move_to_element(addr_popup_confirm_btn)
            addr_popup_confirm_btn.click()
            self.ilogger.info('CHECK_ADDR_POPUP: DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_ADDR_POPUP: WARN-2')
            return False

    def check_set_shipping_address(self):
        self.ilogger.info('CHECK_SET_SHIPPING_ADDRESS: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//div[@id="shippingInput" and not(contains(@style,"none"))]')))
            self.ilogger.info('show set_shipping_address field')
            self.ilogger.info('CHECK_SET_SHIPPING_ADDRESS: DONE')
            return True
        except:
            self.ilogger.info('did not show set_shipping_address field')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_SET_SHIPPING_ADDRESS: WARN')
            return False

    def check_edit_shipping_address(self):
        self.ilogger.info('CHECK_EDIT_SHIPPING_ADDRESS: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@id="shippingSummary" and not(contains(@style,"none"))]')))
            self.ilogger.info('success check_edit_shipping_address')
            self.ilogger.info('CHECK_EDIT_SHIPPING_ADDRESS: DONE')
            return True
        except:
            self.ilogger.info('fail check_edit_shipping_address in except')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_EDIT_SHIPPING_ADDRESS: WARN')
            return False

    def check_set_billing_info(self):
        self.ilogger.info('CHECK_SET_BILLING_INFO: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//div[@id="billingInput" and not(contains(@style,"none"))]')))
            self.ilogger.info('success check_set_billing_info')
            self.ilogger.info('CHECK_SET_BILLING_INFO: DONE')
            return True
        except:
            self.ilogger.info('fail check_set_billing_info')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_SET_BILLING_INFO: WARN')
            return False

    def check_edit_billing_info(self):
        self.ilogger.info('CHECK_EDIT_BILLING_INFO: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@id="billingSummary" and not(contains(@style,"none"))]')))
            self.ilogger.info('success check_edit_billing_info')
            self.ilogger.info('CHECK_EDIT_BILLING_INFO: DONE')
            return True
        except:
            self.ilogger.info('fail check_edit_billing_info')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_EDIT_BILLING_INFO: WARN')
            return False

    def set_payment_info(self):
        self.ilogger.info('SET_PAYMENT_INFO: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//select[@id="billingCreditCardId"]')))
            move_elem = self.br.find_element_by_xpath('//select[@id="billingCreditCardId"]')
            self.move_to_element(move_elem)

            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//input[@id="billingExpirationMonth"]')))
            try:
                move_elem = self.br.find_element_by_xpath('//select[@id="billingCreditCardId"]')
                self.move_to_element(move_elem)
                move_elem.click()
                self.ilogger.debug('clicked select box')
                card_type_xpath = '//select[@id="billingCreditCardId"]/option[@value="{ov}"]'.format(ov="-1")
                self.ilogger.debug('card_type_xpath='+card_type_xpath)
                try:
                    WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.visibility_of_element_located((By.XPATH, card_type_xpath)))
                    detail_c_type = move_elem.find_element_by_xpath(card_type_xpath)
                    self.move_to_element(detail_c_type)
                    detail_c_type.click()
                    self.ilogger.debug('clicked select option')
                except:
                    self.ilogger.info('No History of used card information')
            except:
                self.ilogger.info('Not found select box')

            el_card_no = self.br.find_element_by_xpath('//input[@id="billingCardNumber"]')
            self.move_to_element(el_card_no)
            el_card_no.clear()
            el_card_no.send_keys('4140030446942906')
            time.sleep(0.5)

            el_month = self.br.find_element_by_xpath('//input[@id="billingExpirationMonth"]')
            self.move_to_element(el_month)
            el_month.clear()
            el_month.send_keys('10')
            time.sleep(0.5)

            el_year = self.br.find_element_by_xpath('//input[@id="billingExpirationYear"]')
            self.move_to_element(el_year)
            el_year.clear()
            el_year.send_keys('2020')
            time.sleep(0.5)

            el_cvc = self.br.find_element_by_xpath('//input[@id="billingCardCvvNumber"]')
            self.move_to_element(el_cvc)
            el_cvc.clear()
            el_cvc.send_keys('548')
            time.sleep(0.5)

            # 카드 정보 저장 여부 uncheck
            el_checkbox = self.br.find_element_by_xpath('//input[@id="saveCreditCardAsDefault"]')
            self.move_to_element(el_checkbox)
            el_checkbox.click()
            self.ilogger.info(':::UNCHECK SAVE CARD INFO:::')

            # shipping addr을 billing addr로 쓸지 여부 uncheck
            # el_checkbox = self.br.find_element_by_xpath('//input[@id="billingSameAsShippingCheck"]')
            # self.move_to_element(el_checkbox)
            # el_checkbox.click()

            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),
                                        inspect.stack()[0][2], self.br.page_source.encode('utf-8'))

            try:
                WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="billingAddressFieldGroup4-billingFirstName"]')))
                first_name_eng = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingFirstName"]')
                self.move_to_element(first_name_eng)
                self.ilogger.info(':::DIRECT MOVE TO INPUT BILLING INFO:::')
            except:
                # same as shipping address checkbox unchecked
                WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//input[@id="billingSameAsShippingCheck"]')))
                move_elem = self.br.find_element_by_xpath('//input[@id="billingSameAsShippingCheck"]')
                self.move_to_element(move_elem)
                move_elem.click()
                self.ilogger.info(':::UNCHECK SAME AS SHIPPING ADDR:::')

            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="billingAddressFieldGroup4-billingFirstName"]')))
            el_first_name = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingFirstName"]')
            self.move_to_element(el_first_name)
            el_first_name.clear()
            el_first_name.send_keys('After')

            el_last_name = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingLastName"]')
            self.move_to_element(el_last_name)
            el_last_name.clear()
            el_last_name.send_keys('Buy')

            el_street_addr_01 = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingAddressLine1"]')
            self.move_to_element(el_street_addr_01)
            el_street_addr_01.clear()
            el_street_addr_01.send_keys('700 Cornell Dr E7.')

            el_street_addr_02 = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingAddressLine2"]')
            self.move_to_element(el_street_addr_02)
            el_street_addr_02.clear()
            el_street_addr_02.send_keys('Hotdolph')

            el_city = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingCity"]')
            self.move_to_element(el_city)
            el_city.clear()
            el_city.send_keys('Wilmington')

            el_state = self.br.find_element_by_xpath('//select[@id="billingAddressFieldGroup4-billingState"]')
            self.move_to_element(el_state)
            el_state_xpath = '//select[@id="billingAddressFieldGroup4-billingState"]/option[@value="DE"]'
            detail_state = el_state.find_element_by_xpath(el_state_xpath)
            detail_state.click()

            el_zipcode = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingPostalCode"]')
            self.move_to_element(el_zipcode)
            el_zipcode.clear()
            el_zipcode.send_keys('19801')

            el_phone = self.br.find_element_by_xpath('//input[@id="billingAddressFieldGroup4-billingDayPhone"]')
            self.move_to_element(el_phone)
            el_phone.clear()
            el_phone.send_keys('302-999-9961')

            # 쿠폰 코드 입력
            # el_coupon = self.br.find_element_by_xpath('//input[@id="billingInputPromoRewardCode"]')
            # self.move_to_element(el_coupon)
            # time.sleep(0.5)
            # el_coupon.clear()
            # time.sleep(0.5)
            # el_coupon.send_keys('EXTRA')
            # self.br.execute_script("checkout.controller.modules.billing.promotions.getPromotionCodeApplyRequest('billingInputPromoRewardCode');")
            # time.sleep(self.WAIT_INTERVAL_SHORT)

            self.ilogger.info('SET_PAYMENT_INFO: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.msg = json.dumps({'result': False, 'message': 'PYMF0007'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_PAYMENT_INFO: ERROR')
            raise Exception({
                'ab_error': 'SET_PAYMENT_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def set_coupon_code(self, coupon_code):
        self.ilogger.info('SET_COUPON_CODE: START')
        try:
            el_coupon = self.br.find_element_by_xpath('//input[@id="billingInputPromoRewardCode"]')
            # print "[C] " + el_coupon.get_attribute("name")
            self.move_to_element(el_coupon)
            time.sleep(0.5)
            el_coupon.clear()
            time.sleep(0.5)
            el_coupon.send_keys(coupon_code)
            # print "[C] " + el_coupon.get_attribute("value")
            self.br.execute_script("checkout.controller.modules.billing.promotions.getPromotionCodeApplyRequest('billingInputPromoRewardCode');")
            time.sleep(self.WAIT_INTERVAL_SHORT)
            self.ilogger.info('SET_COUPON_CODE: DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.msg = json.dumps({'result': False, 'message': 'PYMF0007'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_COUPON_CODE: ERROR')
            raise Exception({
                'ab_error': 'SET_COUPON_CODE: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def get_coupon_code_applied(self):
        adjusted_coupon_list = []
        page_source = self.br.page_source.encode('utf-8')
        page_tree = iCheck.parse_htmlpage(self.ilogger, page_source)
        # 쿠폰 적용 확인
        adjusted_elems = iCheck.get_elements_by_xpath(self.ilogger, page_tree,
                                                      '//p[@id="billingPromoCodeAppliedList"]/span[@class="promoSummaryCode"]')
        if adjusted_elems is not None:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),
                                        inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.info('adjusted_coupon count is {0}'.format(len(adjusted_elems)))
            for adj_coupon in adjusted_elems:
                c_code = iCheck.get_value_by_xpath(self.ilogger, adj_coupon, './text()', r"""Applied:(.*)""")
                self.ilogger.debug('adjusted_coupon :' + c_code)
                adjusted_coupon_list.append(c_code)

        if len(adjusted_coupon_list) > 0:
            adjusted_coupon_list_str = ','.join(adjusted_coupon_list)
            self.order_info['site_coupon_code'] = adjusted_coupon_list_str
            self.ilogger.info('Adjusted coupon list= ' + adjusted_coupon_list_str)
        else:
            iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),
                                        inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.info('No coupon adjusted')
        return adjusted_coupon_list

    def review_order(self):
        self.ilogger.info('REVIEW_ORDER: START')
        try:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="billingContinueButton"]')))
            contiune_btn = self.br.find_element_by_xpath('//input[@id="billingContinueButton"]')
            self.move_to_element(contiune_btn)
            contiune_btn.click()

            self.check_addr_popup()
            has_biiling_summary = self.check_edit_billing_info()
            if not has_biiling_summary:
                WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="billingContinueButton"]')))
                contiune_btn = self.br.find_element_by_xpath('//input[@id="billingContinueButton"]')
                self.move_to_element(contiune_btn)
                contiune_btn.click()
        except:
            iCheck.make_screen_shot(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br)
            self.msg = json.dumps({'result': False, 'message': 'PYMF0033'}, ensure_ascii=False, encoding='utf-8')
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('REVIEW_ORDER: ERROR')
            raise Exception({
                'ab_error': 'REVIEW_ORDER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            time.sleep(self.WAIT_INTERVAL)
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.page_source.encode('utf-8'))
            submit_btn = iCheck.get_element_by_xpath(self.ilogger, page_tree, '//div[@id="orderPlacementInput" and not(contains(@style,"none"))]')

            if submit_btn is not None:
                self.ilogger.info('got review page')
                time.sleep(1)
                self.ilogger.info('REVIEW_ORDER: DONE')
            else:
                card_error_txt = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//label[@for="billingCardNumber"]//span[@class="cssHide labelErrorMessage"]/text()')
                if card_error_txt is not None:
                    self.ilogger.info('{:=^20}'.format('CARD ERROR'))
                    self.msg = json.dumps({'result': False, 'message': 'PYMF0007'}, ensure_ascii=False, encoding='utf-8')
                    self.ilogger.info('REVIEW_ORDER: ERROR-1')
                    raise Exception({
                        'ab_error': 'REVIEW_ORDER: ERROR-1',
                        'ab_module': inspect.stack()[0][3]
                    })
                iCheck.make_screen_shot(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br)
                iCheck.make_trace_html_file(self.ilogger, self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
                self.ilogger.info('Failed to move to review page now:' + self.br.current_url)
                self.msg = json.dumps({'result': False, 'message': 'PYMF0033'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('REVIEW_ORDER: ERROR-2')
                raise Exception({
                    'ab_error': 'REVIEW_ORDER: ERROR-2',
                    'ab_module': inspect.stack()[0][3]
                })

    def place_order(self):
        self.ilogger.info('PLACE_ORDER: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.visibility_of_element_located((By.XPATH, '//input[@id="placeOrderButton"]')))
            submit_btn = self.br.find_element_by_xpath('//input[@id="placeOrderButton"]')
            self.move_to_element(submit_btn)
            submit_btn.click()
        except:
            iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0005'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('PLACE_ORDER: ERROR')
            raise Exception({
                'ab_error': 'PLACE_ORDER: ERROR',
                'ab_module': inspect.stack()[0][3]
            })
        else:
            time.sleep(self.WAIT_INTERVAL_LONG)

            if '/checkout/orderConfirm.do' in self.br.current_url:
                ordered_no = self.get_order_no()
                if ordered_no is None:
                    self.ilogger.info('CAN NOT FOUND ORDER NO')
                    self.ilogger.info('PLACE_ORDER: ERROR-1')
            else:
                iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
                has_btn = self.has_submit_btn()
                if has_btn:
                    iCheck.make_trace_html_file(self.ilogger,self.e_id, self.shop_site_name, inspect.stack()[0][3].strip(),inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
                    self.check_card_error()
                    self.msg = json.dumps({'result': False, 'message': 'PYMF0005'}, ensure_ascii=False, encoding='utf-8')
                    self.ilogger.info('PLACE_ORDER: ERROR-2')
                    raise Exception({
                        'ab_error': 'PLACE_ORDER: ERROR-2',
                        'ab_module': inspect.stack()[0][3]
                    })
                else:
                    ordered_no = self.get_order_no()

            self.ilogger.info('PLACE_ORDER: DONE')
            return ordered_no

    def get_order_no(self):
        self.ilogger.info('GET_ORDER_NO: START')
        try:
            # 결제 후 페이지 소스 저장
            page_source = self.br.page_source.encode('utf-8')
            iCheck.make_html_file_eid(self.ilogger, self.e_id,self.shop_site_name, page_source)
            page_tree = iCheck.parse_htmlpage(self.ilogger,page_source)
            ordered_no = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//span[@class="orderNumber"]/text()')
            if ordered_no is not None:
                self.ilogger.info('ORDER NUMBER'+ordered_no)
            else:
                ordered_no = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//*[contains(text(),"var orderID")]/text()',r"""var orderID = \"(.*)\";""")
                if ordered_no is not None:
                    self.ilogger.info('IN SCRIPT ORDER NUMBER'+ordered_no)
                else:
                    ordered_no = None

            self.ilogger.info('GET_ORDER_NO: DONE')
            return ordered_no
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('GET_ORDER_NO: ERROR')
            raise Exception({
                'ab_error': 'GET_ORDER_NO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def has_submit_btn(self):
        self.ilogger.info('HAS_SUBMIT_BTN: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.invisibility_of_element_located((By.XPATH, '//input[@id="placeOrderButton"]')))
            self.ilogger.info('NOT FOUND SUBMIT BUTTON')
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.invisibility_of_element_located((By.XPATH, '//input[@id="billingContinueButton"]')))
            self.ilogger.info('HAS_SUBMIT_BTN: DONE-1')
            return False
        except:
            self.ilogger.info('CAN NOT PROGRESS SUBMIT')
            self.ilogger.debug(traceback.format_exc())
            self.ilogger.info('HAS_SUBMIT_BTN: DONE-2')
            return True

    def check_card_error(self):
        self.ilogger.info('CHECK_CARD_ERROR: START')
        has_err = False
        try:
            time.sleep(self.WAIT_INTERVAL)
            page_tree = iCheck.parse_htmlpage(self.ilogger, self.br.page_source.encode('utf-8'))
            card_err = iCheck.get_element_by_xpath(self.ilogger, page_tree,'//div[@id="billingModuleError" or @id="billingSummaryModuleError" and not(contains(@style,"none"))]')
            if card_err is not None:
                has_err = True
                card_err_txt = iCheck.get_element_by_xpath(self.ilogger, card_err, './/li/text()')
                self.ilogger.error(card_err_txt)
                self.msg = json.dumps({'result': False, 'message': 'PYMF0041'}, ensure_ascii=False, encoding='utf-8')
                self.ilogger.info('CHECK_CARD_ERROR: ERROR')
                raise Exception({
                    'ab_error': 'CHECK_CARD_ERROR: ERROR',
                    'ab_module': inspect.stack()[0][3]
                })

            self.ilogger.info('CHECK_CARD_ERROR: DONE')
        except:
            self.ilogger.info('CHECK_CARD_ERROR: ERROR-1')
            if has_err:
                raise Exception({
                    'ab_error': 'CHECK_CARD_ERROR: ERROR-1',
                    'ab_module': inspect.stack()[0][3]
                })
            self.ilogger.debug(traceback.format_exc())

    # TODO: 가격 정책 결정되어 수정 필요
    def get_price_info_from_checkout_page(self, checkout_page_source):
        try:
            page_tree = iCheck.parse_htmlpage(self.ilogger, checkout_page_source)

            price_info = {
                'price_before_discount': iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryMerchandiseCharge"]/text()', r"""([0-9.,]+)"""),
                'price_shipping': iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryShippingCharge"]/text()'),
                'tax': iCheck.get_value_by_xpath(self.ilogger, page_tree, '//span[@id="orderSummarySalesTax"]/text()', r"""([0-9.,]+)"""),
                'price_after_discount': iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryTotal"]/text()', r"""([0-9.,]+)"""),
                'price_discount': iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryTotalDiscountGainedCharge"]/text()', r"""([0-9.,]+)""")
            }

            return price_info
        except:
            self.br.quit()
            # sys.exit(1)

    def get_price_info(self):
        self.ilogger.info('GET_PRICE_INFO: START')
        try:
            time.sleep(self.WAIT_INTERVAL_SHORT)
            tmp_order_info = {}
            page_source = self.br.page_source.encode('utf-8')
            page_tree = iCheck.parse_htmlpage(self.ilogger, page_source)
            if self.order_info.get('raw_price'):
                self.ilogger.info('has raw_price'+json.dumps(self.order_info.get('raw_price')))
                tmp_order_info['total_price'] = self.order_info['raw_price']['total_price']
            else:
                total_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryMerchandiseCharge"]/text()', r"""([0-9.,]+)""")
                if total_price:
                    tmp_order_info['total_price'] = total_price.replace(',', '')

            shipping_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryShippingCharge"]/text()', r"""([0-9.,]+)""")
            if shipping_fee:
                tmp_order_info['shipping_fee'] = shipping_fee.replace(',', '')
            else:
                tmp_order_info['shipping_fee'] = '0'

            tmp_order_info['shipping_discount'] = '0'

            tax_fee = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//span[@id="orderSummarySalesTax"]/text()', r"""([0-9.,]+)""")
            if tax_fee:
                tmp_order_info['tax_fee'] = tax_fee.replace(',', '')

            est_price = iCheck.get_value_by_xpath(self.ilogger, page_tree, '//td[@id="orderSummaryTotal"]/text()', r"""([0-9.,]+)""")
            if est_price:
                tmp_order_info['est_price'] = est_price.replace(',', '')

            # 쿠폰 적용 후 상품에 대한 할인이 될경우 각 상품 discount에 적용 후 전체 discount에 합산 가격 적용
            item_products = iCheck.get_elements_by_xpath(self.ilogger, page_tree, '//ol[@id="shoppingBagDetailLineItemDisplay"]/li')
            sum_discount_price = 0
            if item_products is not None:
                sum_discount_price = 0
                for p_item in item_products:
                    # 상품당 할인이 2개이상 될수있음.
                    p_item_discount_price = 0
                    promo_elems = iCheck.get_elements_by_xpath(self.ilogger, p_item, './/dd[@class="promoGrey promoDiscount"]')
                    if promo_elems is not None:
                        for promo_elem in promo_elems:
                            promo_text = iCheck.get_value_by_xpath(self.ilogger, promo_elem, './text()', r"""([0-9.,]+)""")
                            if promo_text is not None:
                                promo_text = promo_text.replace(',', '')
                                p_item_discount_price += float(promo_text)
                        product_no = iCheck.get_value_by_xpath(self.ilogger, p_item, './/div[@class="sku"]/text()')
                        for product_info in self.order_info['products']:
                            if product_info['product_no'] == product_no:
                                product_info['discount_price'] = p_item_discount_price
                                sum_discount_price += float(p_item_discount_price)
                                break
            tmp_order_info['discount_price'] = str(sum_discount_price)

            self.ilogger.debug(json.dumps(tmp_order_info))
            self.ilogger.info('GET_PRICE_INFO: DONE')
            return tmp_order_info
        except:
            self.ilogger.error(traceback.format_exc())
            self.msg = json.dumps({'result': False, 'message': 'PYMF0021'}, ensure_ascii=False, encoding='utf-8')
            self.ilogger.info('GET_PRICE_INFO: ERROR')
            raise Exception({
                'ab_error': 'GET_PRICE_INFO: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def move_to_element(self, element):
        try:
            self.ilogger.info('move_to_element')
            elem_y = element.location["y"]
            self.br.execute_script('window.scrollTo(0, {0})'.format(elem_y))
        except:
            self.ilogger.info('window.scrollTo(0, {0})'.format(elem_y))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_TO_ELEMENT: ERROR')
            raise Exception({
                'ab_error': 'MOVE_TO_ELEMENT: ERROR',
                'ab_module': inspect.stack()[0][3]
            })

    def close_browser(self):
        self.ilogger.info('CLOSE_BROWSER: START')
        try:
            if self.br:
                self.br.quit()
            self.ilogger.info('CLOSE_BROWSER: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CLOSE_BROWSER: ERROR')

    def dump(obj):
        for attr in dir(obj):
            if hasattr(obj, attr):
                print("obj.%s = %s" % (attr, getattr(obj, attr)))

    def check_shipping_page(self):
        self.ilogger.info('CHECK_SHIPPING_PAGE: START')
        try:
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.invisibility_of_element_located((By.XPATH, '//button[contains(@class,"shoppingBagCheckoutButton")]')))
            self.ilogger.info('CHECK_SHIPPING_PAGE: DONE-1')
            return False
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CHECK_SHIPPING_PAGE: DONE-2')
            return True

    def move_back_to_shipping_address(self):
        self.ilogger.info('MOVE_BACK_TO_SHIPPING_ADDRESS: START')
        try:
            self.br.refresh()
            if not self.check_set_shipping_address():
                time.sleep(self.WAIT_INTERVAL)
                self.ilogger.debug('try again ccm.shipping.getShippingEdit();')
                self.br.execute_script("ccm.shipping.getShippingEdit();")

            self.ilogger.info('MOVE_BACK_TO_SHIPPING_ADDRESS: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_BACK_TO_SHIPPING_ADDRESS: ERROR')


def do_estimate_price(**kwargs):
    cart_info = kwargs.get('order_info')
    items = []
    for item in cart_info:
        _item = {}
        _item['product_id'] = item['product_id']
        _item['qty'] = item['product_qty']
        _item['product_url'] = item['product_url']
        items.append(_item)

    shipping_addr_info = kwargs.get('shipping_addr_info')
    coupon_code = kwargs.get('site_coupon')

    ship_addr_state = "NJ"

    try:
        gap = ABShopModGap(
            order_id=kwargs.get('order_id'),
            e_id=kwargs.get('e_id'),
            login_id=kwargs.get('login_id'),
            login_passwd=kwargs.get('login_passwd'),
            items=items,
            ilogger=kwargs.get('ilogger')
        )

        gap.init_browser()
        gap.login()
        gap.add_cart()

        gap.close_browser()
        gap.init_browser()
        gap.login()

        gap.get_cart_info()
        gap.set_delivery_type()
        gap.checkout()
        gap.set_shipping_info(shipping_addr_info['NJ'])

        price_info_est = gap.get_price_info()
        gap.set_total_price(price_info_est, True)
        if float(price_info_est['tax_fee']) > 0:
            gap.ilogger.info('::: CHANGE-SHIPPING-ADDR: START :::')
            gap.open_shipping_addr_form()
            gap.set_shipping_info(shipping_addr_info['DE'])
            price_info_est = gap.get_price_info()
            ship_addr_state = "DE"
            gap.ilogger.info('::: CHANGE-SHIPPING-ADDR: END :::')

        gap.set_payment_info()

        coupon_applied = []
        if coupon_code is not False and len(coupon_code) > 0:
            for code in coupon_code:
                gap.set_coupon_code(code)
            coupon_applied = gap.get_coupon_code_applied()

        # price_info_est = gap.get_price_info()
        # gap.set_total_price(price_info_est, False)

        gap.review_order()
        price_info_est = gap.get_price_info()
        gap.set_total_price(price_info_est, False)

        gap.close_browser()

        result = {
            "price_info_est": price_info_est,
            "order_info": gap.order_info,
            "coupon_applied": coupon_applied,
            "ship_addr_est": ship_addr_state
        }

        return result
    except Exception as e:
        gap.close_browser()
        report_error_slack(
            title=e.args[0]['ab_error'] if 'ab_error' in e.args[0] else e,
            order_id=gap.order_info['order_id'] if 'order_id' in gap.order_info else '',
            e_id=gap.order_info['e_id'] if 'e_id' in gap.order_info else '',
            shop_site_id=gap.order_info['shop_site_no'] if 'shop_site_no' in gap.order_info else '',
            shop_site_name=gap.order_info['shop_site_name'] if 'shop_site_name' in gap.order_info else '',
            module=e.args[0]['ab_module'] + "()@" + inspect.getfile(inspect.currentframe()) if 'ab_module' in e.args[0] else '',
            log_file_path=gap.ilogger.handlers[0].baseFilename
        )
        return False
