#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on 2015. 06. 03.
@author: jubr
'''

import re
import traceback
from controllers import AB_BASE_PATH

html_escape_table = {
   "&": "&amp;",
   '"': "&quot;",
   "'": "&apos;",
   ">": "&gt;",
   "<": "&lt;"
}


def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)


def html_unescape(text):
    import HTMLParser
    try:
        return HTMLParser.HTMLParser().unescape(text)
    except:
        return text



# 단일 data에 대한 추출과 정규식을 통한 데이터 가공
def get_value_by_xpath(ilogger, page_tree, target_xpath, rex=None, use_escape=False):
    # ilogger.info('get_value_by_xpath: '+target_xpath)
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_tmp = page_tree.xpath(target_xpath)
            if target_value_tmp:
                target_value = target_value_tmp[0]
                if rex:
                    target_value_tmp = re.search(rex, target_value)
                    if target_value_tmp:
                        target_value = target_value_tmp.group(1)
                    else:
                        # ilogger.debug('PYMF0017')
                        ilogger.debug('not matched regular expression: {re}     data:{da}'.format(re=rex,da=target_value))
                        return None
                if use_escape:
                    target_value = html_escape(target_value.strip())
                else:
                    target_value = target_value.strip()
                return target_value
            else:
                # ilogger.debug('PYMF0016')
                ilogger.debug('not found xpath: {xp}'.format(xp=target_xpath))
                return None
        else:
            ilogger.debug('PYMF0015')
            return None
    except:
        ilogger.error(traceback.format_exc())
        return None


def check_rex(ilogger, raw_data, rex):
    try:
        import re
        # target_value_tmp = re.search(r"""([0-9.,]+)""", raw_data)
        target_value_tmp = re.search(rex, raw_data)
        if target_value_tmp:
            target_value = target_value_tmp.group(1)
            return target_value.strip()
        else:
            return raw_data
    except:
        ilogger.info(traceback.format_exc())


def convert_productname(product_name):
    try:
        if product_name is not None:
            product_name = html_unescape(product_name)
            tmp_product_list = re.findall(r"""(\w+)""", re.sub(r"\s", "", product_name.lower()))
            if tmp_product_list is not None and len(tmp_product_list) > 0:
                short_product_name = ''.join(tmp_product_list)
                return short_product_name
        else:
            return product_name
    except:
        print traceback.format_exc()
        return product_name


# 복수 data에 대한 추출만 허용
def get_values_by_xpath(ilogger, page_tree, target_xpath):
    # ilogger.info('get_value_by_xpath: '+target_xpath)
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_tmp = page_tree.xpath(target_xpath)
            if target_value_tmp:
                return target_value_tmp
            else:
                # ilogger.debug('PYMF0016')
                ilogger.debug('not found xpath: {xp}'.format(xp=target_xpath))
                return None
        else:
            ilogger.debug('PYMF0015')
            return None
    except:
        ilogger.debug(traceback.format_exc())
        return None


# 복수 Eleements 추출
def get_elements_by_xpath(ilogger, page_tree, target_xpath):
    # ilogger.info('get_elements_by_xpath: '+target_xpath)
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_list = page_tree.xpath(target_xpath)
            if target_value_list:
                return target_value_list
            else:
                # ilogger.debug('PYMF0016')
                ilogger.debug('not found xpath: {xp}'.format(xp=target_xpath))
                return None
        else:
            ilogger.debug('PYMF0015')
            return None
    except:
        ilogger.error(traceback.format_exc())
        return None

# 하나의 Eleement 추출
def get_element_by_xpath(ilogger, page_tree, target_xpath):
    # ilogger.info('get_element_by_xpath: '+target_xpath)
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_list = page_tree.xpath(target_xpath)
            if target_value_list:
                return target_value_list[0]
            else:
                # ilogger.debug('PYMF0016')
                ilogger.debug('not found xpath: {xp}'.format(xp=target_xpath))
                return None
        else:
            ilogger.debug('PYMF0015')
            return None
    except:
        ilogger.error(traceback.format_exc())
        return None


def check_unicode(ilogger,data_list):
    try:
        for data in data_list:
            for k, v in data.items():
                if k == 'products':
                    for pp in data[k]:
                        for pk, pv in pp.items():
                            if isinstance(pv, unicode):
                                pp[pk] = pv.encode('utf-8')

                if isinstance(v, unicode):
                    data[k] = v.encode('utf-8')
    except:
        ilogger.error(traceback.format_exc())



# 주문배대지 비교함수
# member_addr_info: 사용자 배대지 정보 목록
# collect_addr_info: 주문정보내역에서 수집한 배대지 정보
def compare_shipping_address(ilogger, member_addr_info, collect_addr_info):
    ilogger.info('compare_shipping_address')
    try:
        for m_addr_info in member_addr_info:
            import json
            # ilogger.info(json.dumps(m_addr_info))
            m_zip_code = m_addr_info.get('zip_code','00000')
            c_zip_code = collect_addr_info.get('shop_zip_code','00000')
            # ilogger.info('from db'+m_zip_code)
            # ilogger.info('from user'+c_zip_code)
            if m_zip_code and c_zip_code and len(m_zip_code) >= 5 and len(c_zip_code) >= 5:
                # ilogger.info('from db'+m_zip_code)
                # ilogger.info('from user'+c_zip_code)
                m_zip_code = m_zip_code[:5]
                c_zip_code = c_zip_code[:5]
                if m_zip_code == c_zip_code:
                    d_site_no = m_addr_info.get('delivery_site_no')
                    ilogger.info('found matched address delivery_site_no={ds}'.format(ds=d_site_no))
                    return d_site_no
        return None
    except:
        ilogger.error(traceback.format_exc())
        return None


# lxml 페이지 파싱.
# is_broken : 태그가 닫히지 않아 구조가 깨져있는 page source일경우 TRUE로 설정하면 모듈에서 자동으로 태그를 맞춰준다.
def parse_htmlpage(ilogger, page_source, is_broken=False):
    try:
        from lxml import html
        from lxml import etree
        if is_broken:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_source, 'html5lib')
            page_source = soup.prettify()
        detail_html = html.fromstring(page_source)
        page_tree = etree.ElementTree(detail_html)
        return page_tree
    except:
        ilogger.error(traceback.format_exc())
        return False


# HTML 파일 생성.
def make_html_file(ilogger, file_name, page_source):
    try:
        with open(file_name, 'w') as h_file:
            h_file.write(page_source)
        # webbrowser.open(file_name)
        return True
    except:
        ilogger.error(traceback.format_exc())
        return False


def make_html_file_eid(ilogger, e_id, site_name, page_source):
    try:
        import os
        from datetime import datetime
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/html'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{eid}_{stn}_{d}_payment.html'.format(eid=e_id, stn=site_name, d=now)
        with open(folder+file_name, 'w') as h_file:
            h_file.write(page_source)
        return True
    except:
        ilogger.error(traceback.format_exc())
        return False


def make_error_html_file(ilogger, e_id, fname, page_source):
    try:
        import os
        from datetime import datetime
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/error_html'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{eid}_{fn}_{d}.html'.format(eid=e_id, fn=fname, d=now)
        with open(folder+file_name, 'w') as h_file:
            h_file.write(page_source)
        return True
    except:
        ilogger.error(traceback.format_exc())
        return False


def make_trace_html_file(ilogger, e_id, shop_site_name, func_name, line_no, page_source):
    try:
        import os
        from datetime import datetime
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/trace_html'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{eid}_{ssn}_{fn}{line_no}_{d}.html'.format(eid=e_id,ssn=shop_site_name, fn=func_name,line_no=line_no, d=now)
        with open(folder+file_name, 'w') as h_file:
            h_file.write(page_source)

        return True
    except:
        ilogger.error(traceback.format_exc())
        return False


def download_capcha_image(ilogger, e_id,queue_idx, shop_site_name, download_url):
    try:
        import os
        from datetime import datetime
        import urllib
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/capcha_image'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{:}_{:}_{:}_{:}.png'.format(e_id,queue_idx, shop_site_name,now)
        ilogger.info(folder+file_name)

        urllib.urlretrieve(download_url, folder+file_name)
        return folder+file_name
    except:
        ilogger.error(traceback.format_exc())
        return False


def save_capcha_image(ilogger, e_id,queue_idx, shop_site_name, image_data):
    try:
        import os
        from datetime import datetime
        import urllib
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/capcha_image'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{:}_{:}_{:}_{:}.png'.format(e_id,queue_idx, shop_site_name,now)
        ilogger.info(folder+file_name)
        with open(folder+file_name, "wb") as fh:
            fh.write(image_data.decode('base64'))
        return folder+file_name
    except:
        ilogger.error(traceback.format_exc())
        return False


def break_capcha(ilogger, image_fullpath):
    try:
        # 아마존 1단계 캡차이미지 해독 함수.
        ilogger.info('break captcha')
        from PIL import Image
        from pytesser import image_to_string
        image = Image.open(image_fullpath)
        captcha_text_tmp = image_to_string(image,cleanup=True)
        captcha_text =''.join(captcha_text_tmp.split())
        ilogger.info('extract captcha text from image TEXT = {:}'.format(captcha_text))
        target_value_tmp = re.search(r'\W', captcha_text)
        ilogger.info('any character(not number ,alphabet) from noise captcha image: {:}'.format(target_value_tmp))
        if target_value_tmp:
            target_value = target_value_tmp.group()
            ilogger.info('any character(not number ,alphabet) from noise captcha image: {:}'.format(target_value))
            return False
        return captcha_text
    except:
        ilogger.error(traceback.format_exc())
        return False


def make_screen_shot(ilogger, e_id, shop_site_name, func_name, line_no, selenium_browser):
    try:
        from datetime import datetime
        import os
        base_path = AB_BASE_PATH
        now_tmp = datetime.now()
        now = now_tmp.strftime("%H%M%S")
        folder = base_path +'/log/{y}/{m}/{d}/controllers/trace_screen_shot'.format(y=now_tmp.strftime("%Y"), m=now_tmp.strftime("%m"), d=now_tmp.strftime("%d"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_name = '/{eid}_{ssn}_{fn}{line_no}_{d}.png'.format(eid=e_id,ssn=shop_site_name, fn=func_name,line_no=line_no, d=now)
        selenium_browser.get_screenshot_as_file(folder+file_name)
    except:
        ilogger.error(traceback.format_exc())
        return False



# Forms 출력.
def show_forms(ilogger, browser):
    try:
        for i, bb in enumerate(browser.forms()):
            ilogger.info('{:}{:}'.format(i,bb))
    except:
        ilogger.error(traceback.format_exc())
        return False


#string 입력시 size 만큼 글자수를 자른후 다시 돌려줌
def get_abbreviate(ilogger, string, size):
    try:
        if isinstance(string, basestring):
            if len(string) < size:
                return string
            elif len(string) > size:
                return string[:size]
            else:
                return string
        else:
            return ''
    except:
        ilogger.error(traceback.format_exc())
        return ''


# 주어진 control_name이 몇번째 form에 있는지 찾는 함수
# 랜덤으로 form이 바껴 하드코딩으로 인한 빈번한 오류로 인해 추가.
def get_form_index(ilogger, browser, control_name):
    try:
        set_idx = 0
        is_found = False
        for index, avail_form in enumerate(browser.forms()):
            for f_idx, avail_cont in enumerate(avail_form.controls):
                if avail_cont.name is not None:
                    if control_name in avail_cont.name:
                        set_idx = index
                        is_found = True
                        break
            if is_found:
                break
        if not is_found:
            ilogger.error('NOT FORUND ENTER ADDRESS INPUT FORM')
            return False
        return set_idx
    except:
        ilogger.error(traceback.format_exc())
        return False


def compare_final_price(ilogger, current_price_info, final_price_info):
    import json
    msg = None
    try:
        ilogger.info('compare_final_price')
        crnt_price = float(current_price_info['total_price']) + float(current_price_info['tax_fee']) - float(current_price_info['discount_price'])
        final_price = float(final_price_info['total_price']) + float(final_price_info['tax_fee']) - float(final_price_info['discount_price'])

        ilogger.info('CURRENT PRICE = {cp}'.format(cp=crnt_price))
        ilogger.info('FINAL PRICE = {fp}'.format(fp=final_price))

        if crnt_price <= final_price:
            ilogger.info('CHEAPER THAN FINAL OR EQUAL final:{f}  current:{c}'.format(f=final_price_info['est_price'], c=current_price_info['est_price']))
        else:
            ilogger.info(
                'EXPENSIVE final est:{fe}   total={tt}   discount:{fd}    shipping_fee:{fs}  tax_fee:{ft}    current est:{ce}   current_total={ctt}    discount:{cd}   shipping_fee:{cs}   tax_fee:{ct}'
                    .format(fe=final_price_info['est_price'], tt=final_price_info['total_price'], fd=final_price_info['discount_price'], fs=final_price_info['shipping_fee'], ft=final_price_info['tax_fee'],
                    ce=current_price_info['est_price'], ctt=current_price_info['total_price'], cd=current_price_info['discount_price'], cs=current_price_info['shipping_fee'], ct=current_price_info['tax_fee'],)
            )
            msg = json.dumps({'result': False, 'message': 'PYMF0006'}, ensure_ascii=False, encoding='utf-8')
    except:
        msg = json.dumps({'result': False, 'message': 'PYMF0024'}, ensure_ascii=False, encoding='utf-8')
        ilogger.error(traceback.format_exc())
    finally:
        return msg


def get_tracking_tmp_no(ilogger):
    try:
        from random import randrange
        ilogger.info('get_tracking_tmp_no')
        prefix_track_no = 'NOT'
        suffix_track_no = randrange(1000000000, 10000000000)
        track_no = prefix_track_no + str(suffix_track_no)
        ilogger.info('track_no = ' + track_no)
        return track_no, 'UPS'
    except:
        ilogger.error(traceback.format_exc())
        return None, None


def get_delivery_request_tmp_no(ilogger):
    try:
        from random import randrange
        ilogger.info('get_delivery_request_tmp_no')
        prefix_request_no = 'EBIRD'
        suffix_request_no = randrange(10000, 100000)
        request_no = prefix_request_no + str(suffix_request_no)
        ilogger.info('request_tmp_no = ' + request_no)
        return request_no
    except:
        ilogger.error(traceback.format_exc())
        return None


# def check_value(ilogger, ordered_info_list):
#     try:
#         ilogger.info('get_tracking_tmp_no')
#         base_keys = ['order_no', 'e_id', 'reg_date', 'country_code', 'site_ID',
#                      'shop_payment_date', 'shop_site_no', 'shop_site_name', 'shop_order_url', 'shop_site_delivery_type',
#                      'currency', 'total_price', 'discount_price', 'shipping_fee', 'shipping_discount',
#                      'tax_fee', 'payment_info', 'carrier', 'tracking_no', 'current_status',
#                      'shop_full_name', 'shop_first_name_eng', 'shop_last_name_eng', 'shop_address1', 'shop_address2',
#                      'shop_city', 'shop_state', 'shop_country', 'shop_us_phone', 'shop_zip_code',
#                      'delivery_site_no', 'delivery_state', 'delivery_ID', 'site_coupon_code', 'etc_discout_price_info']
#
#         for ordered_info in ordered_info_list:
#             for data_key, data_value in ordered_info.items():
#                 if data_key not in base_keys:
#                     base_keys.remove(data_key)
#                     print 'NOT!!!!!',data_key, data_value
#                 print base_keys
#         return ordered_info_list
#     except:
#         ilogger.error(traceback.format_exc())


def toNumber(ilogger, number):
    n = 0.0
    try:
        n = float(number)
    except:
        ilogger.debug(traceback.format_exc())
        n = 0.0
    finally:
        return n

def get_carrier(tracking_no):
    try:
        if tracking_no is None:
            return 'UPS'
        else:
            if not isinstance(tracking_no,str):
                tracking_no = str(tracking_no)
            if tracking_no.startswith('1Z'):
                return 'UPS'
            elif tracking_no.startswith('91'):
                return 'USPS'
            elif len(tracking_no) in (12, 15):
                return 'FEDEX'
            else:
                return 'UNKNOWN'
    except:
        return 'UPS'


def get_request_data(queue_idx, stype=None):
    from sfb.utils.decrypt import AES_Decrypter
    from sfb.dao.walker_dao import WalkerDAO
    import json
    walker_obj = WalkerDAO()
    try:
        request_data_str = walker_obj.get_request_data(queue_idx, stype)
        req_data = json.loads(request_data_str.get('REQUEST_DATA'),encoding='utf-8')
        for key, value in req_data['member_info'].items():
            if isinstance(value, unicode):
                req_data['member_info'][key] = str(value.encode('utf-8'))
            else:
                req_data['member_info'][key] = str(value)
        encrypt_data = {}
        if req_data.get('site_PW'):
            encrypt_data['site_PW'] = req_data.get('site_PW')
        if req_data.get('delivery_PW'):
            encrypt_data['delivery_PW'] = req_data.get('delivery_PW')
        if req_data.get('customer_payment_info'):
            encrypt_data['card_no'] = req_data.get('customer_payment_info').get('card_no')
            encrypt_data['expire_month'] = req_data.get('customer_payment_info').get('expire_month')
            encrypt_data['expire_year'] = req_data.get('customer_payment_info').get('expire_year')
            encrypt_data['card_first_name'] = req_data.get('customer_payment_info').get('card_first_name')
            encrypt_data['card_last_name'] = req_data.get('customer_payment_info').get('card_last_name')
            encrypt_data['current_cvc'] = req_data.get('customer_payment_info').get('current_cvc')
            encrypt_data['card_type'] = req_data.get('customer_payment_info').get('card_type')
        decrypted_data = AES_Decrypter.get_decrypt_data(req_data['member_info'], encrypt_data)
        if decrypted_data is None:
            print json.dumps({'result': False, 'message': 'PYMF0026'}, ensure_ascii=False, encoding='utf-8')
            return None
        for decrypted_key, decrypted_value in decrypted_data.items():
            if decrypted_key in ['card_no', 'expire_month', 'expire_year', 'card_first_name', 'card_last_name', 'current_cvc', 'card_type']:
                req_data['customer_payment_info'][decrypted_key] = decrypted_value
            else:
                req_data[decrypted_key] = decrypted_value
        return req_data
    except:
        print traceback.format_exc()
    finally:
        walker_obj.close_connection()


def update_response_data(ilogger, REQ_DATA, response_data='', result_message=''):
    from sfb.dao.walker_dao import WalkerDAO
    walker_obj = WalkerDAO()
    try:
        update_row_cnt = walker_obj.update_response_data(ilogger, REQ_DATA, response_data, result_message)
        walker_obj.mysql_commit()
        return update_row_cnt
    except:
        ilogger.error(traceback.format_exc())
    finally:
        walker_obj.close_connection()


def set_product_status(ilogger, product_list, status_code):
    try:
        # status_code 0 미수집 1 수집 2 전송완료 3 취소
        if isinstance(product_list,tuple) or isinstance(product_list,list):
            for product in product_list:
                product['status_code'] = status_code
        else:
            product_list['status_code'] = status_code
    except:
        ilogger.error(traceback.format_exc())

def random_wait(start=3,end=8):
    try:
        import time
        import random
        wait_time = random.randrange(start,end)
        time.sleep(wait_time)
    except:
        print traceback.format_exc()

def find_carrier(ilogger, pacakage_info,tracking_no):
    try:
        import json
        import requests
        ilogger.info('{:=^50}'.format('find_carrier'))
        api_key = '18e9142f-01d8-438d-80cc-d82c6ab608a3'
        header = {
        'Content-Type': 'application/json; charset=utf-8',
        'aftership-api-key': api_key
        }
        base_api_url = 'https://api.aftership.com/v4'
        if pacakage_info['shop_zip_code']:
            shop_zip_code = pacakage_info['shop_zip_code'].split('-')
        else:
            return pacakage_info
        body = {
            "tracking":
            {
                "tracking_number": tracking_no,
                "tracking_postal_code": shop_zip_code[0]
            }
        }
        api_detail_url = '/couriers/detect'
        response = requests.request('POST', base_api_url+api_detail_url, headers=header,data=json.dumps(body))
        ilogger.info('{:=^50}'.format(tracking_no))
        ilogger.info(response.text)
        response_json = json.loads(response.text)
        if response_json.get('data'):
            if response_json.get('data').get('couriers'):
                pacakage_info['find_carrier'] = response_json.get('data').get('couriers')[0].get('slug')
        return pacakage_info
    except:
        ilogger.error(traceback.format_exc())


def set_tracking_no(ilogger, track_detail):
    try:
        ilogger.info('set_tracking_no')
        tmp_tracking_no_dict = {}
        if track_detail.get('products'):
            for product_detail in track_detail.get('products'):
                if product_detail.get('tracking_no') is not None and not product_detail.get('tracking_no').startswith('NOT') and product_detail.get('tracking_no') not in tmp_tracking_no_dict.keys():
                    tmp_tracking_no_dict[product_detail.get('tracking_no')] = product_detail.get('carrier','unknown')
        return tmp_tracking_no_dict
    except:
        ilogger.error(traceback.format_exc())


def refine_track_data(ilogger, track_info, msg):
    try:
        # 데이터 정제
        import json
        ilogger.info('refine_track_data')
        for track_detail in track_info.get('track_data'):
            if track_detail.get('update_delivery_site_USTN') == 0 and track_detail.get('products'):
                all_update = True
                need_update = False
                status_list = []
                for product_detail in track_detail.get('products'):
                    # 0 미수집 1 수집 2 배대지업데이트 3 상품취소
                    status_list.append(product_detail.get('status_code'))

                ilogger.info('status list {:}'.format(status_list))
                status_list = list(set(status_list))
                ilogger.info('remove duplicate status list {:}'.format(status_list))

                if 0 not in status_list:
                    tmp_tracking_no_info = set_tracking_no(ilogger, track_detail)
                    if tmp_tracking_no_info:
                        ilogger.info('tmp_tracking_no_info {:}'.format(tmp_tracking_no_info))
                        track_detail['tracking_no'] = ','.join(tmp_tracking_no_info.keys())
                        track_detail['carrier'] = ','.join(tmp_tracking_no_info.values())
                    ilogger.info(track_detail.get('products'))
                    if 3 in status_list:
                        # 부분상품완료 업데이트 경우 (더이상 트래킹조회필요없음) 0이 없음
                        ilogger.info('It is done. Some of products are updated tracking number HDP_idx {:} order_no {:}'.format(track_detail.get('HDP_idx'),track_detail.get('order_no')))
                        track_detail['update_delivery_site_USTN'] = 2
                        msg = json.dumps({'result': True, 'message': ' PYMS0011'}, encoding='utf-8')
                    else:
                        # 모든상품완료 업데이트 경우 (더이상 트래킹조회필요없음) 0이 없음
                        ilogger.info('Every product is updated tracking number HDP_idx {:} order_no {:}'.format(track_detail.get('HDP_idx'),track_detail.get('order_no')))
                        track_detail['update_delivery_site_USTN'] = 1
                        msg = json.dumps({'result': True, 'message': ' PYMS0012'}, encoding='utf-8')
                else:
                    something_update_list = list(set(status_list) - set([0]))
                    if something_update_list:
                        # 일부상품 업데이트 경우 (추후 트래킹조회 필요)
                        tmp_tracking_no_info = set_tracking_no(ilogger, track_detail)
                        if tmp_tracking_no_info:
                            ilogger.info('tmp_tracking_no_info {:}'.format(tmp_tracking_no_info))
                            track_detail['tracking_no'] = ','.join(tmp_tracking_no_info.keys())
                            track_detail['carrier'] = ','.join(tmp_tracking_no_info.values())
                        ilogger.info(track_detail.get('products'))
                        ilogger.info('Need to be run next time. Products are updated tracking number HDP_idx {:} order_no {:}'.format(track_detail.get('HDP_idx'),track_detail.get('order_no')))
                        track_detail['update_delivery_site_USTN'] = 0
                        msg = json.dumps({'result': True, 'message': ' PYMS0013'}, encoding='utf-8')
                    else:
                        # 모든상품 업데이트 되지 않음 (추후 트래킹조회 필요)
                        ilogger.info('None of products are updated tracking number HDP_idx {:} order_no {:}'.format(track_detail.get('HDP_idx'),track_detail.get('order_no')))
                        track_detail['update_delivery_site_USTN'] = 0
                        msg = json.dumps({'result': True, 'message': ' PYMS0014'}, encoding='utf-8')
            else:
                if not track_detail.get('products'):
                    ilogger.info('Do not have product detail information {:}'.format(track_detail.get('products')))
                    msg = json.dumps({'result': False, 'message': ' PYMF0078'}, encoding='utf-8')
                elif track_detail.get('update_delivery_site_USTN') != 0:
                    msg = json.dumps({'result': True, 'message': ' PYMS0015'}, encoding='utf-8')
                    ilogger.info('already has update_delivery_site_USTN {:}'.format(track_detail.get('update_delivery_site_USTN')))
        return track_info, msg
    except:
        ilogger.error(traceback.format_exc())


def update_tracking_info(ilogger,args):
    from sfb.dao.tracking_dao import TrackingDAO
    tracking_dao_obj = TrackingDAO()
    row_cnt_main = 0
    row_cnt_detail = 0
    try:
        ilogger.info('Update tracking data')
        ilogger.info('{:}'.format(args.get('track_data')))
        # update result_shopping
        row_cnt_main = tracking_dao_obj.update_tracking_no(ilogger, args.get('track_data'))
        # update result_shopping_detail
        row_cnt_detail = tracking_dao_obj.update_product_tracking_no(ilogger, args.get('track_data'))
    except:
        ilogger.error(traceback.format_exc())
    else:
        tracking_dao_obj.mysql_commit()
    finally:
        tracking_dao_obj.close_connection()
        return row_cnt_main, row_cnt_detail


def copy_cookie(ilogger,cookie_list, cookie_obj):
    try:
        import mechanize
        ilogger.info('copy_cookie')
        ilogger.info('BEFORE COOKIE {:}'.format(cookie_obj))
        for s_cookie in cookie_list:
            ilogger.info('selenium cookie {:}'.format(s_cookie))
            domain_initial_dot_value = s_cookie.get('domain').startswith('.')
            cookie_obj.set_cookie(mechanize.Cookie(version=0, name=s_cookie['name'], value=s_cookie['value'], port=None, port_specified=False, domain=s_cookie['domain'], domain_specified=True, domain_initial_dot=domain_initial_dot_value, path=s_cookie['path'], path_specified=True, secure=s_cookie['secure'], expires=s_cookie.get('expiry'),discard=False, comment=None, comment_url=None, rest={'HttpOnly': s_cookie.get('httponly')}, rfc2109=False))
        ilogger.info('AFTER COOKIE {:}'.format(cookie_obj))
    except:
        ilogger.error(traceback.format_exc())

