#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import traceback
import inspect

from lib.iLogger import set_logger
from models.membership import MABMembership

import selenium.webdriver.support.expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lib import iCheck

class ABResetSiteAccountDummy(object):
    WAIT_INTERVAL = 3
    WAIT_INTERVAL_SHORT = 1
    WAIT_INTERVAL_LONG = 5

    def __init__(self, **kwargs):
        self.m_membership = MABMembership()
        self.account_seq = None
        self.shop_site_no = None
        self.shop_site_name = None
        self.user_id = None
        self.user_passwd = None
        self.ilogger = None

    def set_data(self, **kwargs):
        self.account_seq = kwargs.get('account_seq')
        self.shop_site_no = kwargs.get('shop_site_no')
        self.shop_site_name = kwargs.get('shop_site_name')
        self.user_id = kwargs.get('user_id')
        self.user_passwd = kwargs.get('user_passwd')
        self.ilogger = kwargs.get('ilogger')
        init_log = {
            'account_seq': self.account_seq,
            'shop_site_no': self.shop_site_no,
            'shop_site_name': self.shop_site_name,
            'user_id': self.user_id,
            'user_passwd': self.user_passwd
        }
        self.ilogger.info('RESET_SITE_ACCOUNT_DATA')
        self.ilogger.info(json.dumps(init_log))


    def get_site_account_to_reset(self):
        result = self.m_membership.get_site_account_to_reset()
        return result

    def reset_site_account(self, seq):
        self.m_membership.update_shop_dummy_account_status(seq, '0')

    def set_site_account_fault(self, seq):
        self.m_membership.update_shop_dummy_account_status(seq, '9')

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
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('INIT BROWSER: ERROR')
            raise Exception()

    def close_browser(self):
        self.ilogger.info('CLOSE_BROWSER: START')
        try:
            if self.br:
                self.br.quit()
            self.ilogger.info('CLOSE_BROWSER: DONE')
        except:
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('CLOSE_BROWSER: ERROR')

    def login_gap(self):
        self.ilogger.info('LOGIN (GAP): START')
        try:
            self.br.get('https://secure-www.gap.com/profile/sign_in.do')
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//input[@id="emailAddress"]')))
            emailAddress = self.br.find_element_by_xpath('//input[@id="emailAddress"]')
            password = self.br.find_element_by_xpath('//input[@id="password"]')
            signInButton = self.br.find_element_by_xpath('//input[@id="signInButton"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            signInButton.click()
            self.ilogger.info('LOGIN (GAP): DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'GAP', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('LOGIN (GAP): ERROR')
            raise Exception()

    def set_cart_empty_gap(self):
        self.ilogger.info('SET_CART_EMPTY (GAP): START')
        try:
            self.br.get('https://secure-www.gap.com/buy/shopping_bag.do')
            els = self.br.find_elements_by_xpath('//div[@class="closeHitArea"]')
            item_count = len(els)

            self.ilogger.info('item count to remove: ' + str(item_count))

            while item_count > 0:
                el = self.br.find_element_by_xpath('//div[@class="closeHitArea"]')
                el.click()
                item_count -= 1
                self.ilogger.info('item count to remove: ' + str(item_count))
                time.sleep(1.5)

            self.ilogger.info('SET_CART_EMPTY (GAP): DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'GAP', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_CART_EMPTY (GAP): ERROR')
            return False

    def login_ralphlauren(self):
        self.ilogger.info('LOGIN (RALPHLAUREN): START')
        try:
            self.br.get('http://www.ralphlauren.com/home/index.jsp?geos=1')
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//li[@id="accountsel"]/a')))
            el_login_page_btn = self.br.find_element_by_xpath('//li[@id="accountsel"]/a')
            el_login_page_btn.click()
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//input[@id="emailId"]')))
            emailAddress = self.br.find_element_by_xpath('//input[@id="emailId"]')
            password = self.br.find_element_by_xpath('//input[@id="passwd"]')
            signInButton = self.br.find_element_by_xpath('//input[@type="submit" and @alt="Sign In"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            signInButton.click()
            self.ilogger.info('LOGIN (RALPHLAUREN): DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'RALPHLAUREN', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('LOGIN (RALPHLAUREN): ERROR')
            raise Exception()

    def set_cart_empty_ralphlauren(self):
        self.ilogger.info('SET_CART_EMPTY (RALPHLAUREN): START')
        try:
            self.br.get('http://www.ralphlauren.com/cart/index.jsp?ab=global_bag')
            xpath_remove_item = '//table[@summary="Shopping Cart Contents"]//tr/td/ul/li/a[@class="remove"]'
            els = self.br.find_elements_by_xpath(xpath_remove_item)
            item_count = len(els)
            self.ilogger.info('item count to remove: ' + str(item_count))

            while item_count > 0:
                el = self.br.find_element_by_xpath(xpath_remove_item)
                el.click()
                item_count -= 1
                self.ilogger.info('item count to remove: ' + str(item_count))
                time.sleep(1.5)

            self.ilogger.info('SET_CART_EMPTY (RALPHLAUREN): DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'RALPHLAUREN', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_CART_EMPTY (RALPHLAUREN): ERROR')
            return False

    def login_carters(self):
        self.ilogger.info('LOGIN (CARTERS): START')
        try:
            self.br.get('https://www.carters.com/my-account?id=carters')
            WebDriverWait(self.br, self.WAIT_INTERVAL).until(EC.presence_of_element_located((By.XPATH, '//input[starts-with(@id, "dwfrm_login_username_")]')))
            emailAddress = self.br.find_element_by_xpath('//input[starts-with(@id, "dwfrm_login_username_")]')
            password = self.br.find_element_by_xpath('//input[@id="dwfrm_login_password"]')
            signInButton = self.br.find_element_by_xpath('//button[@id="login_btn"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            signInButton.click()
            self.ilogger.info('LOGIN (CARTERS): DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'CARTERS', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('LOGIN (CARTERS): ERROR')
            raise Exception()

    def set_cart_empty_carters(self):
        self.ilogger.info('SET_CART_EMPTY (CARTERS): START')
        try:
            self.br.get('https://www.carters.com/cart?id=carters')
            xpath_remove_item = '//button[@type="submit" and @value="Remove Item"]'
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.element_to_be_clickable((By.XPATH, xpath_remove_item)))

            els = self.br.find_elements_by_xpath(xpath_remove_item)
            item_count = len(els)
            self.ilogger.info('item count to remove: ' + str(item_count))

            while item_count > 0:
                el = self.br.find_element_by_xpath(xpath_remove_item)
                el.click()
                item_count -= 1
                self.ilogger.info('item count to remove: ' + str(item_count))
                time.sleep(1.5)

            self.ilogger.info('SET_CART_EMPTY (RALPHLAUREN): DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'CARTERS', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_CART_EMPTY (CARTERS): ERROR')
            return False

    def login_beauty(self):
        self.ilogger.info('LOGIN (BEAUTY): START')
        try:
            self.br.get('https://www.beauty.com/user/login.asp')
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//input[@id="txtEmail"]')))
            emailAddress = self.br.find_element_by_xpath('//input[@id="txtEmail"]')
            password = self.br.find_element_by_xpath('//input[@id="txtPassword"]')
            signInButton = self.br.find_element_by_xpath('//input[@id="btnContinue"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            self.move_to_element(signInButton)
            signInButton.submit()
            self.ilogger.info('LOGIN (BEAUTY): DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'BEAUTY', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('LOGIN (BEAUTY): ERROR')
            raise Exception()

    def set_cart_empty_beauty(self):
        self.ilogger.info('SET_CART_EMPTY (BEAUTY): START')
        try:
            self.br.get('http://www.beauty.com/shoppingbag.asp')
            xpath_remove_item = '//div[@id="bag-items-in"]//div[@class="row"]//div[@class="bag-remove"]/a'
            els = self.br.find_elements_by_xpath(xpath_remove_item)
            item_count = len(els)
            self.ilogger.info('item count to remove: ' + str(item_count))

            while item_count > 0:
                el = self.br.find_element_by_xpath(xpath_remove_item)
                el.click()
                item_count -= 1
                self.ilogger.info('item count to remove: ' + str(item_count))
                time.sleep(1.5)

            self.ilogger.info('SET_CART_EMPTY (BEAUTY): DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'BEAUTY', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_CART_EMPTY (BEAUTY): ERROR')
            return False

    def login_bbw(self):
        self.ilogger.info('LOGIN (BATHANDBODYWORKS): START')
        try:
            self.br.get('http://www.bathandbodyworks.com/home/index.jsp')
            el_login_href = self.br.find_element_by_xpath('//div[@id="utilitynavigation"]//div[@class="welcome-message"]/a')
            el_login_href.click()

            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//input[@id="accEmailId"]')))
            emailAddress = self.br.find_element_by_xpath('//input[@id="accEmailId"]')
            password = self.br.find_element_by_xpath('//input[@id="accPasswd"]')
            emailAddress.send_keys(self.user_id)
            password.send_keys(self.user_passwd)
            self.br.execute_script('valLogin();return false;')
            time.sleep(1)
            self.ilogger.info('LOGIN (BATHANDBODYWORKS): DONE')
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'BATHANDBODYWORKS', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('LOGIN (BATHANDBODYWORKS): ERROR')
            raise Exception()

    def set_cart_empty_bbw(self):
        self.ilogger.info('SET_CART_EMPTY (BATHANDBODYWORKS): START')
        try:
            self.br.get('http://www.bathandbodyworks.com/cart/index.jsp')
            WebDriverWait(self.br, self.WAIT_INTERVAL_LONG).until(EC.presence_of_element_located((By.XPATH, '//div[@id="itemSummary"]')))
            xpath_remove_item = '//div[@id="itemSummary"]//table[@class="item-table"]/tbody//td[@class="quantity"]//ul[@role="presentation"]//li/a'
            els = self.br.find_elements_by_xpath(xpath_remove_item)
            item_count = len(els)
            self.ilogger.info('item count to remove: ' + str(item_count))

            while item_count > 0:
                el = self.br.find_element_by_xpath(xpath_remove_item)
                el.click()
                item_count -= 1
                self.ilogger.info('item count to remove: ' + str(item_count))
                time.sleep(1.5)

            self.ilogger.info('SET_CART_EMPTY (BATHANDBODYWORKS): DONE')
            return True
        except:
            iCheck.make_trace_html_file(self.ilogger, 'RESET_ACCOUNT', 'BATHANDBODYWORKS', inspect.stack()[0][3].strip(), inspect.stack()[0][2], self.br.page_source.encode('utf-8'))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('SET_CART_EMPTY (BATHANDBODYWORKS): ERROR')
            return False

    def move_to_element(self, element):
        try:
            self.ilogger.info('move_to_element')
            elem_y = element.location["y"]
            self.br.execute_script('window.scrollTo(0, {0})'.format(elem_y))
        except:
            self.ilogger.info('window.scrollTo(0, {0})'.format(elem_y))
            self.ilogger.error(traceback.format_exc())
            self.ilogger.info('MOVE_TO_ELEMENT: ERROR')
            raise Exception('MOVE_TO_ELEMENT: ERROR')

    def get_site_module_name(self, shop_site_name):
        li_shop_site_name = shop_site_name.split('_')
        return li_shop_site_name[0]


def reset_site_account():
    obj = ABResetSiteAccountDummy()
    tdl = obj.get_site_account_to_reset()

    if len(tdl) == 0:
        sys.exit(1)

    try:
        for row in tdl:
            shop_site_name = obj.get_site_module_name(row['shop_site_name'])
            ilogger = set_logger({
                'folder_name': 'ab_reset_site_account',
                'shop_site_name': shop_site_name,
                'order_id': row['seq'],
                'e_id': row['shop_site_no']
            })

            obj.set_data(
                account_seq=row['seq'],
                shop_site_no=row['shop_site_no'],
                shop_site_name=shop_site_name,
                user_id=row['user_id'],
                user_passwd=row['user_passwd'],
                ilogger=ilogger
            )

            obj.init_browser()

            if shop_site_name == "GAP":
                obj.login_gap()
                result = obj.set_cart_empty_gap()
            elif shop_site_name == "RALPHLAUREN":
                obj.login_ralphlauren()
                result = obj.set_cart_empty_ralphlauren()
            elif shop_site_name == "CARTERS":
                obj.login_carters()
                result = obj.set_cart_empty_carters()
            elif shop_site_name == "BEAUTY":
                obj.login_beauty()
                result = obj.set_cart_empty_beauty()
            elif shop_site_name == "BATHANDBODYWORKS":
                obj.login_bbw()
                result = obj.set_cart_empty_bbw()
            else:
                raise Exception('NO MODULE NAME: ' + shop_site_name)

            if result is True:
                obj.reset_site_account(row['seq'])
            else:
                obj.set_site_account_fault(row['seq'])

            obj.close_browser()

            for handler in ilogger.handlers:
                handler.close()
                ilogger.removeHandler(handler)
    except:
        obj.close_browser()

if __name__ == '__main__':
    reset_site_account()
