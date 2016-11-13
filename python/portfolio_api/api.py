# -*- coding: utf-8 -*-
import json
import logging.handlers
import os
import pycurl
import sys
import time
import uuid
import traceback
from StringIO import StringIO
from urllib import urlencode

from flask import Flask, request, render_template, jsonify
from flask import jsonify
from flaskext.mysql import MySQL
from datetime import datetime

# from util import xpath_parser

reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

app = Flask(__name__)
mysql = MySQL()
# hansung genius
app.config['MYSQL_DATABASE_HOST'] = '172.31.15.152' if 'APP_ENV' in os.environ.keys() and os.environ['APP_ENV'] == 'PROD' else 'mdb.afterbuy.kr'
app.config['MYSQL_DATABASE_USER'] = 'kershaw'
app.config['MYSQL_DATABASE_PASSWORD'] = '0411'
app.config['MYSQL_DATABASE_DB'] = 'MEMBERSHIP'
mysql.init_app(app)
app.debug = True

# 로거 인스턴스를 만든다
logger = logging.getLogger('mylogger')
fomatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(fomatter)
logger.addHandler(streamHandler)
logger.setLevel(logging.DEBUG)

# ELB health check
@app.route('/status', methods=['GET'])
def status():
    return "OK"

#로그인 & 회원가입 API
@app.route('/api/v0/user/login', methods=['POST'])
def login():
    #Json 형태로 parameter값 받아오기
    json_dict = json.loads(request.data)
    sns_id = json_dict['sns_id'] if 'sns_id' in json_dict else None
    imei = json_dict['imei']
    email = json_dict['email'] if 'email' in json_dict else ""
    phone = json_dict['phone'] if 'phone' in json_dict else None
    nick_name = json_dict['nick_name']
    join_type = json_dict['join_type']
    result_set = {}
    logger.debug("sns_id:" + str(sns_id) + "/imei:" + str(imei) + "/email:" + str(email) + "/phone:" + str(phone) + \
                 "/nick_name:" + str(nick_name) + "/join_type:" + str(join_type))
    if sns_id == None or sns_id =="":
        logger.debug("===== No sns_id =====")
        return jsonify({'result_code':0})
    if email is None:
        email = ""
    try:
        con = mysql.connect()
        cursor = con.cursor()
        #회원 유/무 판별
        try:
            query = """
                SELECT
                    e_id
                FROM
                    MEMBERSHIP.account_info
                WHERE
                    sns_id = %s
                AND
                    join_type = %s
            """
            bind = (
                sns_id,
                join_type
            )
            cursor.execute(query, bind)
            e_id = cursor.fetchone()
            #처음 가입하는 회원일 경우
            if e_id == None:
                logger.debug("===== Member Status : NO USER =====")
                query = """
                    INSERT INTO
                        MEMBERSHIP.account_info
                        (
                            email,
                            phone,
                            nick_name,
                            join_type,
                            imei,
                            sns_id,
                            reg_date
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW()
                        )
                """
                bind = (
                    email,
                    phone,
                    nick_name,
                    join_type,
                    imei,
                    sns_id
                )
                cursor.execute(query, bind)
                e_id = cursor.lastrowid

                if cursor.rowcount > 0:
                    query = """
                        INSERT INTO
                            BILLING.account_deposit
                        VALUES
                            (
                                %s,
                                0,
                                0,
                                0
                            )
                    """
                    bind = (e_id,)
                    cursor.execute(query, bind)
                    if cursor.rowcount > 0:
                        try:
                            query = """
                                INSERT INTO
                                    BILLING.account_mileage
                                    (
                                        e_id
                                    )
                                VALUES
                                    (
                                        %s
                                    )
                            """
                            cursor.execute(query, bind)
                            query = """
                                SELECT
                                    user_code
                                FROM
                                    MEMBERSHIP.account_info
                                WHERE
                                    user_code is NOT NULL
                            """
                            cursor.execute(query,)
                            user_code_info = []
                            columns = tuple([d[0] for d in cursor.description])
                            for row in cursor:
                                user_code_info.append(dict(zip(columns, row)))
                            code = uuid.uuid1(int(e_id))

                            for row in user_code_info:
                                user_code = row['user_code']
                                if user_code == str(code)[0:6]:
                                    code = uuid.uuid1(999999 - int(e_id))
                            logger.debug(str(code)[0:6])

                            query = """
                                UPDATE
                                    MEMBERSHIP.account_info
                                SET
                                    user_code = %s
                                WHERE
                                    e_id = %s
                            """
                            bind = (
                                str(code)[0:6],
                                e_id
                            )
                            cursor.execute(query, bind)
                            logger.debug("===== Sign Up Success =====")
                            con.commit()
                        except Exception as e:
                            logger.debug(e)
                            logger.debug("===== Sign Up Failed =====")
                            return jsonify({'result_code': 0})
                else:
                    logger.debug("===== Can Not Sign Up =====")
                    return jsonify({'result_code':0})
            #이미 가입되어 있는 회원일 경우
            else:
                logger.debug("====== Member Status : USER / e_id:" + str(e_id[0]) + " =====")
                e_id = e_id[0]
                query = """
                    SELECT
                        user_code
                    FROM
                        MEMBERSHIP.account_info
                    WHERE
                        e_id = %s
                """
                bind = (e_id,)
                cursor.execute(query, bind)
                user_code = cursor.fetchone()
                if user_code[0] is None:
                    logger.debug("===== user_code Is None =====")
                    query = """
                        SELECT
                            user_code
                        FROM
                            MEMBERSHIP.account_info
                        WHERE
                            user_code is NOT NULL
                    """
                    cursor.execute(query,)
                    user_code_info = []
                    columns = tuple([d[0] for d in cursor.description])
                    for row in cursor:
                        user_code_info.append(dict(zip(columns, row)))
                    code = uuid.uuid1(int(e_id))
                    for row in user_code_info:
                        user_code = row['user_code']
                        if user_code == str(code)[0:6]:
                            code = uuid.uuid1(999999 - int(e_id))
                            ("===== Same user_code Already Exist So Create New user_code =====")
                    logger.debug("user_code:" + str(code)[0:6])

                    query = """
                        UPDATE
                            MEMBERSHIP.account_info
                        SET
                            user_code = %s
                        WHERE
                            e_id = %s
                    """
                    bind = (
                        str(code)[0:6],
                        e_id
                    )
                    cursor.execute(query, bind)
                    logger.debug("===== Success Create user_code =====")
                else:
                    logger.debug("===== user_code Is Already Exist =====")

                query = """
                    SELECT
                        phone
                    FROM
                        MEMBERSHIP.account_info
                    WHERE
                        e_id = %s
                """
                bind = (e_id,)
                cursor.execute(query, bind)
                data = cursor.fetchone()
                if data[0] == phone:
                    logger.debug("===== Match Phone Number e_id:" + str(e_id) + " =====")
                elif data[0] != phone:
                    logger.debug("===== Does Not Match Phone Number e_id:" + str(e_id) + " =====")
                    if phone == None:
                        logger.debug("===== Phone is Null =====")
                    elif phone != None:
                        query = """
                            UPDATE
                                MEMBERSHIP.account_info
                            SET
                                phone = %s
                            WHERE
                                e_id = %s
                        """
                        bind = (
                            phone,
                            e_id
                        )
                        cursor.execute(query, bind)
                        logger.debug("===== Update Success Phone Number e_id:" + str(e_id) + " =====")
            ### BOARD.announce_board의 게시글 수 ###
            # logger.debug("==== e_id:" +  str(e_id) + " =====")
            # query = """
            #     SELECT
            #         seq
            #     FROM
            #         BOARD.announce_board
            #     WHERE
            #         e_id = %s
            #     AND
            #         status = 0
            # """
            # bind = (e_id,)
            # cursor.execute(query, bind)
            # announce_board_cnt = cursor.rowcount
            # if announce_board_cnt < 1:
            #     announce_board_cnt = 0
            ### BOARD.ask_admin_board의 게시글 수 ###
            # query = """
            #     SELECT
            #         seq
            #     FROM
            #         BOARD.ask_admin_board
            #     WHERE
            #         e_id = %s
            #     AND
            #         status = 0
            # """
            # cursor.execute(query, bind)
            # ask_admin_board_cnt = cursor.rowcount
            # if ask_admin_board_cnt < 1:
            #     ask_admin_board_cnt = 0

            ### BILLING.account_deposit (내 충전금액 및 포인트??)###
            query = """
                SELECT
                    e_id
                FROM
                    BILLING.account_mileage
                WHERE
                    e_id = %s
            """
            bind = ( e_id, )
            cursor.execute(query, bind)
            if cursor.rowcount < 1:
                try:
                    query = """
                        INSERT INTO
                            BILLING.account_mileage
                            (
                                e_id
                            )
                            VALUES
                            (
                                %s
                            )
                    """
                    cursor.execute(query, bind)
                    logger.debug("===== Success Insert account_mileage =====")
                    con.commit()
                except Exception as e:
                    logger.debug(e)
                    logger.debug("===== Failed Insert account_mileage =====")
                    return jsonify({'result_code': 0})
            if phone == None:
                query = """
                    UPDATE
                        MEMBERSHIP.account_info
                    SET
                        phone = ""
                    WHERE
                        e_id = %s
                """
                cursor.execute(query, bind)
            query = """
                SELECT
                    account_info.phone,
                    account_info.nick_name,
                    account_info.user_code,
                    account_deposit.charge_price,
                    account_deposit.free_price,
                    account_mileage.mileage
                FROM
                    (
                        SELECT
                            e_id
                            ,	phone
                            ,	nick_name
                            ,	user_code
                        FROM
                            MEMBERSHIP.account_info
                        WHERE
                            e_id	=	%s
                    )	as	account_info
                JOIN
                    BILLING.account_deposit
                ON
                    account_info.e_id = account_deposit.e_id
                JOIN
                    BILLING.account_mileage
                ON
                    account_deposit.e_id = account_mileage.e_id
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            result_account_info = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result_account_info.append(dict(zip(columns,row)))

            query = """
                SELECT
                    e_id,
                    count(case	when order_status =	2 then 1 else null end)	'payment_done_cnt',
                    count(case	when order_status =	5 then 1 else null end)	'tracking_done_cnt',
                    count(case	when order_status =	6 then 1 else null end)	'delivery_payment_done_cnt',
                    count(case	when order_status =	12 then 1 else null end) 'delivery_in_progress_cnt',
                    count(case	when order_status =	13 then 1 else null end) 'delivery_done_cnt'
                FROM
                    SERVICE.AB_order
                WHERE
                    e_id = %s
                GROUP BY
                    e_id
            """
            cursor.execute(query, bind)
            result_order_status = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result_order_status.append(dict(zip(columns, row)))

            query = """
                SELECT
                    order_id
                FROM
                    SERVICE.AB_order
                WHERE
                    e_id = %s
                AND
                    0 <= order_status
                AND
                    2 > order_status
            """
            cursor.execute(query, bind)
            order_id = cursor.fetchone()
            #장바구니 order_id가 없을경우 & 결제완료 이후
            if cursor.rowcount < 1:

                tmp = {
                    'e_id':e_id,
                    'phone':result_account_info[0]['phone'],
                    'nick_name':result_account_info[0]['nick_name'],
                    'user_code':result_account_info[0]['user_code'],
                    'charge_price':result_account_info[0]['charge_price'],
                    'free_price':result_account_info[0]['free_price'],
                    'mileage':result_account_info[0]['mileage'],
                    'price_est_info':{
                        'order_id':"",
                        'result_status':""
                    },
                    'order_status':{
                        'payment_done_cnt':0,
                        'tracking_done_cnt':0,
                        'delivery_payment_done_cnt':0,
                        'delivery_in_progress_cnt':0,
                        'delivery_done_cnt':0
                    }
                }
                result = 1
                logger.debug("===== No order_id In e_id:" + str(e_id) + " =====")
                con.commit()
                con.close()
                return jsonify({'result_code':result,'result_set':tmp})
            else:
                result_order_list = []
                columns = tuple([d[0] for d in cursor.description])
                for row in cursor:
                    result_order_list.append(dict(zip(columns, row)))
                query = """
                      SELECT
                        AB_order.order_id,
                        AB_order.order_status,
                        q_process_list.status
                    FROM
                        (
                            SELECT
                                order_id
                                ,	order_status
                            FROM
                                SERVICE.AB_order
                            WHERE
                                order_id = %s
                        )	as	AB_order
                    JOIN
                        QUEUE.q_process_list
                    ON
                        AB_order.order_id = q_process_list.order_id
                """
                bind = (order_id,)
                cursor.execute(query, bind)
                if cursor.rowcount < 1:
                    tmp = {
                    'e_id':e_id,
                    'phone': result_account_info[0]['phone'],
                    'nick_name':result_account_info[0]['nick_name'],
                    'user_code':result_account_info[0]['user_code'],
                    'charge_price':result_account_info[0]['charge_price'],
                    'free_price':result_account_info[0]['free_price'],
                    'mileage': result_account_info[0]['mileage'],
                    'price_est_info':{
                        'order_id':"",
                        'result_status':""
                        },
                    'order_status': {
                        'payment_done_cnt': result_order_status[0]['payment_done_cnt'],
                        'tracking_done_cnt': result_order_status[0]['tracking_done_cnt'],
                        'delivery_payment_done_cnt': result_order_status[0]['delivery_payment_done_cnt'],
                        'delivery_in_progress_cnt': result_order_status[0]['delivery_in_progress_cnt'],
                        'delivery_done_cnt': result_order_status[0]['delivery_done_cnt']
                        }
                    }
                    result = 1
                    logger.debug("===== No q_process_list In order_id:" + str(order_id) + " =====")
                    con.commit()
                    con.close()
                    return jsonify({'result_code':result,'result_set':tmp})
                else:
                    result_queue_list = []
                    columns = tuple([d[0] for d in cursor.description])
                    for row in cursor:
                        result_queue_list.append(dict(zip(columns, row)))
                    for row in result_account_info:
                        account_info = {}
                        tmp = {
                            'e_id':e_id,
                            'phone': result_account_info[0]['phone'],
                            'nick_name':result_account_info[0]['nick_name'],
                            'user_code':result_account_info[0]['user_code'],
                            'charge_price':result_account_info[0]['charge_price'],
                            'free_price':result_account_info[0]['free_price'],
                            'mileage': result_account_info[0]['mileage'],
                            'price_est_info':{},
                            'order_status': {
                                'payment_done_cnt': result_order_status[0]['payment_done_cnt'],
                                'tracking_done_cnt': result_order_status[0]['tracking_done_cnt'],
                                'delivery_payment_done_cnt': result_order_status[0]['delivery_payment_done_cnt'],
                                'delivery_in_progress_cnt': result_order_status[0]['delivery_in_progress_cnt'],
                                'delivery_done_cnt': result_order_status[0]['delivery_done_cnt']
                            }
                        }
                        result_set = tmp
                        for row in result_queue_list:
                            queue_list = {}
                            order_status = str(row['order_status'])
                            queue_status = str(row['status'])
                            if order_status == "0" and queue_status == "4":
                                result_status = 0
                                tmp = {
                                    'order_id':row['order_id'],
                                    'result_status':result_status
                                }
                                result_set['price_est_info'] = tmp
                            else:
                                result_status = 1
                                tmp = {
                                    'order_id':row['order_id'],
                                    'result_status':result_status
                                }
                                result_set['price_est_info'] = tmp
                                result = 1
                                return jsonify({'result_code':result,'result_set':result_set})
                        result = 1
                    con.commit()
                    con.close()
                    return jsonify({'result_code':result,'result_set':result_set})
        except Exception:
            con.rollback()
            con.close()
            logger.debug("===== Error API part : /api/v0/user/login | Query Error =====")
            logger.debug(traceback.format_exc())
            if result_set == {}:
                result_set = ""
            result = 0
            return jsonify({'result_code':result,'result_set':result_set})
    except Exception:
        logger.debug("===== Error API part : /api/v0/user/login | DB Connection Error =====")
        logger.debug(traceback.format_exc())
        if result_set == {}:
            result_set = ""
        result = 0
        return jsonify({'result_code':result,'result_set':result_set})

#배송상태 refresh api
@app.route('/api/v0/user/menu_refresh/<e_id>', methods=['GET'])
def menu_refresh(e_id):
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                e_id,
                count(case	when order_status =	2 then 1 else null end)	'payment_done_cnt',
                count(case	when order_status =	5 then 1 else null end)	'tracking_done_cnt',
                count(case	when order_status =	6 then 1 else null end)	'delivery_payment_done_cnt',
                count(case	when order_status =	12 then 1 else null end)	'delivery_in_progress_cnt',
                count(case	when order_status =	13 then 1 else null end)	'delivery_done_cnt'
            FROM
                SERVICE.AB_order
            WHERE
                e_id = %s
            GROUP BY
                e_id
        """
        bind = (e_id,)
        cursor.execute(query, bind)
        menu_refresh = []
        if cursor.rowcount < 1:
            menu_refresh.append({
                                 'e_id':e_id,
                                 'payment_done_cnt':0,
                                 'tracking_done_cnt': 0,
                                 'delivery_payment_done_cnt': 0,
                                 'delivery_in_progress_cnt': 0,
                                 'delivery_done_cnt': 0
            })
        else:
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                menu_refresh.append(dict(zip(columns, row)))
        query = """
            SELECT
                seq,
                nick_name,
                title,
                contents,
                reg_date,
                modify_date
            FROM
                BOARD.announce_board
        """
        cursor.execute(query)
        announce_board = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            announce_board.append(dict(zip(columns, row)))

        query = """
            SELECT
                seq,
                nick_name,
                title,
                contents,
                reg_date,
                modify_date
            FROM
                BOARD.event_board
        """
        cursor.execute(query)
        event_board = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            event_board.append(dict(zip(columns, row)))

        query = """
            SELECT
                mileage
            FROM
                BILLING.account_mileage
            WHERE
                e_id = %s
        """
        bind = (e_id,)
        cursor.execute(query, bind)
        mileage = cursor.fetchone()

        for row in menu_refresh:
            tmp = {
                'e_id':row['e_id'],
                'mileage':mileage[0],
                'order_status':{
                    'payment_done_cnt':row['payment_done_cnt'],
                    'tracking_done_cnt':row['tracking_done_cnt'],
                    'delivery_payment_done_cnt':row['delivery_payment_done_cnt'],
                    'delivery_in_progress_cnt':row['delivery_in_progress_cnt'],
                    'delivery_done_cnt':row['delivery_done_cnt']
                },
                'announce_list':[],
                'event_list':[]
            }
            for row in announce_board:
                announce_board_tmp = {
                    'seq':row['seq'],
                    'nick_name':row['nick_name'],
                    'title':row['title'],
                    'contents':row['contents'],
                    'reg_date':str(row['reg_date']),
                    'modify_date':str(row['modify_date'])
                }
                tmp['announce_list'].append(announce_board_tmp)
                for row in event_board:
                    event_board_tmp = {
                        'seq':row['seq'],
                        'nick_name':row['nick_name'],
                        'title':row['title'],
                        'contents':row['contents'],
                        'reg_date':str(row['reg_date']),
                        'modify_date':str(row['modify_date'])
                    }
                    tmp['event_list'].append(event_board_tmp)
            return jsonify({'result_code':1, 'result_set':tmp})
    except Exception as e:
        logger.debug(e)
        con.rollback()
        con.close()
        tmp = {}
        return jsonify({'result_code':0, 'result_set':tmp})

#친구초대 코드
@app.route('/api/v0/user/friend_recommend', methods=['POST'])
def friend_recommend():
    e_id = request.form.get('e_id')
    recommend_code = request.form.get('recommend_code')

    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                recommend_code
            FROM
                MEMBERSHIP.account_info
            WHERE
                e_id = %s
        """
        bind = (e_id,)
        cursor.execute(query, bind)
        data_recommend_code = cursor.fetchone()
        if data_recommend_code[0] is None:
            query = """
                SELECT
                    user_code
                FROM
                    MEMBERSHIP.account_info
                WHERE
                    user_code = %s
            """
            bind = (recommend_code,)
            cursor.execute(query, bind)
            user_code = cursor.fetchone()
            if str(user_code[0]) == str(recommend_code):
                query = """
                    UPDATE
                        MEMBERSHIP.account_info
                    SET
                        recommend_code = %s
                    WHERE
                        e_id = %s
                """
                bind = (
                    recommend_code,
                    e_id
                )
                cursor.execute(query, bind)
                logger.debug("===== Success To Update recommend_code =====")
                con.commit()
                return jsonify({'result_code':1})
            else:
                logger.debug("===== No user_code In account_info =====")
                return jsonify({'result_code':3})

    except Exception as e:
        logger.debug(e)
        con.rollback()
        logger.debug("===== Error From friend_recommend =====")
        return jsonify({'result_code':0})
    else:
        logger.debug("===== Already recommend friend Event =====")
        return jsonify({'result_code':2})

#쿠폰입력
@app.route('/api/v0/user/insert_coupon', methods=['POST'])
def insert_coupon():
    from models.payment import MPayment
    e_id = request.form.get('e_id')
    coupon_code = request.form.get('coupon_code')

    m_payment = MPayment(logger)
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                mileage,
                coupon_code,
                exp_date
            FROM
                BILLING.AB_coupon_list
            WHERE
                coupon_code = %s
        """
        bind = (coupon_code,)
        cursor.execute(query, bind)
        if int(cursor.rowcount) < 1:
            logger.debug('===== No Coupon_code In AB_coupon_list =====')
            return jsonify({'result_code':3})
        coupon_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            coupon_info.append(dict(zip(columns, row)))
        for row in coupon_info:
            coupon_code = row['coupon_code']
            mileage = row['mileage']
            exp_date = str(row['exp_date'])
        logger.debug("e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + "/mileage:" + str(mileage) + "/exp_date:" + str(exp_date))
        if coupon_code is None:
            logger.debug('===== Does Not Exist coupon_code =====')
            return jsonify({'result_code':3})
        query = """
            SELECT
                coupon_code
            FROM
                BILLING.account_coupon_code
            WHERE
                e_id = %s
        """
        bind = (e_id,)
        cursor.execute(query, bind)
        if int(cursor.rowcount) < 1:
            query = """
                SELECT	*
                FROM	(
                 SELECT	a.imei,	a.e_id,	b.e_id	duplicate_e_id
                 FROM
                    (
                        SELECT	e_id,	imei
                        FROM	MEMBERSHIP.account_info
                        WHERE	e_id	=	%s
                    )	a
                INNER	JOIN
                MEMBERSHIP.account_info	b
                ON	a.imei	=	b.imei
                )	aa
                INNER	JOIN
                    BILLING.account_coupon_code	bb
                ON	aa.duplicate_e_id	=	bb.e_id
            """
            cursor.execute(query, bind)
            if int(cursor.rowcount) < 1:
                result = m_payment.insert_account_coupon_code(e_id, coupon_code, mileage, exp_date)
                if result is False:
                    logger.debug("===== Cannot Apply coupon e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + " =====")
                    return jsonify({'result_code':0})

                logger.debug("===== Success To Apply e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + " =====")
                return jsonify({'result_code':1})
            else:
                logger.debug("===== Already Apply e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + " =====")
                return jsonify({'result_code': 2})
        else:
            coupon_list = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                coupon_list.append(dict(zip(columns, row)))
            for row in coupon_list:
                e_coupon_code = row['coupon_code']
                if e_coupon_code == coupon_code:
                    logger.debug("===== Already Apply e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + " =====")
                    return jsonify({'result_code': 2})
                else:
                    result = m_payment.insert_account_coupon_code(e_id, coupon_code, mileage, exp_date)
                    if result is False:
                        logger.debug("===== Cannot Apply coupon e_id:" + str(e_id) + "/coupon_code:" + str(
                            coupon_code) + " =====")
                        return jsonify({'result_code': 0})
                    logger.debug("===== Success To Apply e_id:" + str(e_id) + "/coupon_code:" + str(coupon_code) + " =====")
                    return jsonify({'result_code': 1})
            return jsonify({'result_code':2})
    except Exception as e:
        logger.debug(e)
        return jsonify({'result_code': 0})

#브랜드 리스트
@app.route('/api/v0/user/brandshop_list', methods=['GET'])
def brandshop_list():
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                shop_site_no,
                shop_site_name,
                shop_site_url,
                shop_site_image_url,
                shop_site_rgb,
                shop_site_cart_url,
                shop_site_element_id
            FROM
                SNAPSHOT.shop_site_list
            WHERE
                shop_site_element_id is NOT null
        """
        cursor.execute(query)
        result = []
        columns = tuple([d[0] for d in cursor.description])

        GAP_GROUP = ['GAP', 'OLDNAVY', 'BANANAREPUBLIC', 'ATHLETA']
        CARTERS_GROUP = ['OSHKOSH', 'CARTERS']
        BEAUTY_GROUP = ['BEAUTY', 'DRUGSTORE']

        for row in cursor:
            row = list(row)

            if row[0] in [4, 5, 6, 30]:
                row[0] = 9999
            elif row[0] in [8, 9]:
                row[0] = 9998
            elif row[0] in [36, 26]:
                row[0] = 9997

            if row[1] in GAP_GROUP:
                row[1] = 'GAP_GROUP'
            elif row[1] in CARTERS_GROUP:
                row[1] = 'CARTERS_GROUP'
            elif row[1] in BEAUTY_GROUP:
                row[1] = 'BEAUTY_GROUP'

            row = tuple(row)
            result.append(dict(zip(columns,row)))

        return json.dumps(result)
    except Exception:
        con.rollback()
        con.close()
        logger.debug("===== Error API part : /api/v0/user/brandshop_list =====")
        raise Exception(traceback.format_exc())

# 배송지 추가 및 수정
@app.route('/api/v0/user/update_delivery_addr', methods=['POST'])
def update_delivery_addr():
    json_dict = json.loads(request.data)
    delivery_seq = json_dict['delivery_seq'] if 'delivery_seq' in json_dict else None
    e_id = json_dict['e_id']
    name = json_dict['name']
    nick_addr = json_dict['nick_addr']
    address1 = json_dict['address1']
    address2 = json_dict['address2']
    zip_code = json_dict['zip_code']
    address1_old = json_dict['address1_old']
    # address2_old = json_dict['addres2_old']
    telephone = json_dict['telephone']
    cell_phone = json_dict['cell_phone']
    email = json_dict['email']
    allowed_no = json_dict['allowed_no']

    con = mysql.connect()
    cursor = con.cursor()

    try:
        if delivery_seq is None or delivery_seq == "":
            query = """
                INSERT INTO
                    MEMBERSHIP.delivery_info
                    (
                        e_id,
                        name,
                        reg_date,
                        nick_addr,
                        address1,
                        address2,
                        zip_code,
                        address1_old,
                        telephone,
                        cell_phone,
                        email,
                        allowed_no
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        NOW(),
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
            """
            bind = (
                e_id,
                name,
                nick_addr,
                address1,
                address2,
                zip_code,
                address1_old,
                telephone,
                cell_phone,
                email,
                allowed_no
            )
            cursor.execute(query, bind)

            if cursor.lastrowid > 0:
                query = """
                    UPDATE
                        SERVICE.AB_order
                    SET
                        delivery_seq = %s
                    WHERE
                        e_id = %s
                    AND
                        order_status = 1
                """
                bind = (
                    cursor.lastrowid,
                    e_id
                )
                cursor.execute(query, bind)
                logger.debug("===== Success Insert delivery_seq:" + str(cursor.lastrowid) + " =====")
                result = {'delivery_seq': cursor.lastrowid}
            else:
                raise Exception()
        else:
            query = """
                UPDATE
                    MEMBERSHIP.delivery_info
                SET
                    name = %s,
                    nick_addr = %s,
                    address1 = %s,
                    address2 = %s,
                    zip_code = %s,
                    address1_old = %s,
                    telephone = %s,
                    cell_phone = %s,
                    email = %s,
                    allowed_no = %s
                WHERE
                    delivery_seq = %s
            """
            bind = (
                name,
                nick_addr,
                address1,
                address2,
                zip_code,
                address1_old,
                telephone,
                cell_phone,
                email,
                allowed_no,
                delivery_seq
            )
            cursor.execute(query, bind)

            if cursor.rowcount > 0:
                logger.debug("===== Success Update delivery_seq:" + str(delivery_seq) + " =====")
                result = {'delivery_seq': delivery_seq}
            else:
                raise Exception()

        con.commit()
    except Exception as e:
        logger.debug(e)
        con.rollback()
        con.close()
        result = {'result_code': 0}

    return jsonify(result)

#배송지 목록
@app.route('/api/v0/user/list_delivery_addr/e_id=<e_id>', methods=['GET'])
def list_delivery_addr(e_id):
    try:
        con = mysql.connect()
        cursor = con.cursor()
        try:
            cursor.execute("SELECT delivery_seq,e_id,name,nick_addr,address1,address2,zip_code,address1_old,\
                            telephone,cell_phone,email,allowed_no FROM MEMBERSHIP.delivery_info\
                            WHERE e_id = '%s' order by reg_date desc"%(e_id))
            result = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result.append(dict(zip(columns,row)))
            con.close()
            return json.dumps(result)
        except Exception as e:
            logger.debug(e)
            con.rollback()
            con.close()
            return "DB QUERY ERROR"
    except Exception as e:
        logger.debug(e)
        logger.debug("DB CONNECTION ERROR")
        return jsonify({'result_code':0})

#배송지 삭제
@app.route('/api/v0/user/del_delivery_addr', methods=['POST'])
def del_delivery_addr():
    json_dict = json.loads(request.data)
    e_id = json_dict['e_id']
    delivery_seq = json_dict['delivery_seq']
    #들어온 값 확인
    try:
        con = mysql.connect()
        cursor = con.cursor()
        try:
            cursor.execute("DELETE FROM MEMBERSHIP.delivery_info WHERE e_id = '%s' AND delivery_seq = '%s'"\
                           %(e_id,delivery_seq))
            con.commit()
            logger.debug("Success DELETE delivery address.")
            con.close()
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            con.rollback()
            con.close()
            return jsonify({'result_code':0})
    except Exception as e:
        logger.debug(e)
        logger.debug("DB CONNECTION ERROR")
        return jsonify({'result_code':0})

#장바구니 리스트
@app.route('/api/v0/user/list_cart/e_id=<e_id>', methods=['GET'])
def list_cart(e_id):
    try:
        con = mysql.connect()
        cursor = con.cursor()
        try:
            query = """
                 SELECT
                    AB_order.order_id_alias,
                    AB_order_shop.shop_site_no,
                    shop_site_list.shop_site_name,
                    AB_order_item.item_id,
                    AB_order_item.order_id,
                    AB_order_item.order_shop_id,
                    AB_order_item.e_id,
                    AB_order_item.product_name,
                    AB_order_item.product_option,
                    AB_order_item.product_qty,
                    (AB_order_item.product_price - AB_order_item.discount_price) AS product_price,
                    AB_order_item.product_url,
                    AB_order_item.image_url
                FROM
                    (
                        SELECT	*
                        FROM	SERVICE.AB_order
                        WHERE	e_id	=	%s
                        and	order_status	=	0
                    )	as	AB_order
                JOIN
                    SERVICE.AB_order_item
                ON
                    AB_order.order_id	=	AB_order_item.order_id
                JOIN
                    SERVICE.AB_order_shop
                ON
                    AB_order_item.order_shop_id = AB_order_shop.order_shop_id
                JOIN
                    SNAPSHOT.shop_site_list
                ON
                    AB_order_shop.shop_site_no = shop_site_list.shop_site_no
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            if cursor.rowcount > 0:
                result = []
                columns = tuple([d[0] for d in cursor.description])
                for row in cursor:
                    result.append(dict(zip(columns,row)))
                results = {}
                ret = {}
                cnt = 0
                ret['order_id'] = result[0]['order_id']
                for row in result:
                    qty = int(row['product_qty'])
                    cnt = cnt + (1 * qty)
                    shop_site_no = row['shop_site_no']
                    if row['product_option'] == '" "':
                        row['product_option'] = ''
                    if shop_site_no not in list(results.keys()):
                        tmp = {
                            'shop_site_no':shop_site_no,
                            'order_shop_id':row['order_shop_id'],
                            'shop_site_name':row['shop_site_name'].replace('_GROUP', ''),
                            'items':[
                                {
                                    'item_id':row['item_id'],
                                    'product_name':row['product_name'],
                                    'product_url':row['product_url'],
                                    'image_url':row['image_url'],
                                    'product_option':row['product_option'],
                                    'product_qty':row['product_qty'],
                                    'product_price':"%.2f" % row['product_price']
                                }
                            ]
                        }
                        results[shop_site_no] = tmp
                    else:
                        results[shop_site_no]['items'].append({
                            'item_id':row['item_id'],
                            'product_name':row['product_name'],
                            'product_url':row['product_url'],
                            'image_url':row['image_url'],
                            'product_option':row['product_option'],
                            'product_qty':row['product_qty'],
                            'product_price':"%.2f" % row['product_price']
                        })
                con.close()
                arr = []
                ret['list'] = results.values()
                logger.debug("e_id:" + str(e_id) + " | " + "rowcount:" + str(cnt))
                if json.dumps(ret) == json.dumps(arr):
                    time.sleep(1)
                else:
                    return json.dumps(ret)
            else:
                logger.debug("===== Nothing in the Cart =====")
                return jsonify({'result_code':0})
                # return json.dumps(results.values())
        except Exception as e:
            logger.debug(e)
            con.rollback()
            con.close()
            logger.debug("Call cart list SELECT QUERY ERROR")
            return jsonify({'result_code':0})
    except Exception as e:
        logger.debug(e)
        logger.debug("DB CONNECTION ERROR")
        return jsonify({'result_code':0})

#장바구니 추가
@app.route('/api/v0/user/add_to_cart', methods=['POST'])
def parsing_api():
    json_dict = json.loads(request.data)
    html = json_dict['html'] if 'html' in json_dict else None
    head = json_dict['extra']['head'] if 'head' in json_dict['extra'] else None
    shop_site_no = str(json_dict['shop_site_no'])
    if shop_site_no == '1':    #AMAZON
        try:
            logger.debug("===== AMAZON Parsing =====")
            amazon_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            return jsonify({'result_code':0})

    if shop_site_no == '2':
        try:
            logger.debug("===== EBAY Parsing =====")
            ebay_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            return jsonify({'result_code':0})

    elif shop_site_no == '3':   #RALPHRAUREN
        try:
            logger.debug("===== RALPHLAUREN Parsing =====")
            ralphlauren_parsing(html,head)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(traceback.format_exc())
            return jsonify({'result_code':0})

    elif shop_site_no == '25':
        try:
            logger.debug("===== 6PM.COM Parsing =====")
            sixpm_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(traceback.format_exc())
            return jsonify({'result_code':0})

    elif shop_site_no == '28':
        try:
            logger.debug("===== BATHANDBODYWORKS Parsing =====")
            bathandbodyworks_parsing(html)
            return jsonify({'result_code': 1})
        except Exception as e:
            logger.debug(traceback.format_exc())
            return jsonify({'result_code': 0})

    elif shop_site_no == '9997':    #BEAUTY_GROUP
        try:
            logger.debug("===== BEAUTY_GROUP Parsing =====")
            beauty_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            return jsonify({'result_code':0})

    elif shop_site_no == '9998':    #CARTERS_GROUP
        try:
            logger.debug("===== CARTERS_GROUP Parsing =====")
            carters_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            return jsonify({'result_code':0})


    elif shop_site_no == '9999':   #gap
        try:
            logger.debug("===== GAP_GROUP Parsing =====")
            gap_parsing(html)
            return jsonify({'result_code':1})
        except Exception as e:
            logger.debug(e)
            return jsonify({'result_code':0})
    else:
        logger.debug("No brand shop list in add_to_cart")
        return jsonify({'result_code':0})

def sixpm_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)

    items = xpath_parser.get_elements_by_xpath(html_tree, '//table[@id="cart"]/tbody/tr[@class="item"]')
    product_list = []

    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            #6PM CART PARSING
            image_URL = xpath_parser.get_value_by_xpath(item, './/a[@class="prodImg"]/img/@src')
            product['image_url'] = image_URL
            logger.debug("image_url:" + product['image_url'])

            product_url = xpath_parser.get_value_by_xpath(item, './/a[@class="name"]/@href')
            if product_url:
                product['product_url'] = "https://secure-www.6pm.com" + product_url
                logger.debug("product_url:" + product['product_url'])

            product_name = xpath_parser.get_value_by_xpath(item, './/h4[@class="title"]/a/text()')
            product['product_name'] = product_name
            logger.debug("product_name:" + product['product_name'])

            product_id = xpath_parser.get_value_by_xpath(item, './/ul[@class="details"]//li[1]/text()')
            if product_id:
                product['product_id'] = product_id
            else:
                product['product_id'] = "N/A"

            logger.debug("product_id:" + str(product['product_id']))

            product_qty = xpath_parser.get_value_by_xpath(item, './/td[@class="qty"]//input[@type="text"]/@value')
            if product_qty:
                product['product_qty'] = product_qty
            logger.debug("product_qty:" + str(product['product_qty']))

            product_option = []
            product_first_option = xpath_parser.get_elements_by_xpath(item, './/ul//li[2]/text()')
            product_option.append(str(product_first_option).replace('[\' ','').replace('\']', ''))
            logger.debug(product_first_option)

            product_second_option = xpath_parser.get_elements_by_xpath(item, './/ul//li[3]/text()')
            product_option.append(str(product_second_option).replace('[\' ', '').replace('\']', ''))
            logger.debug(product_second_option)

            product_third_option = xpath_parser.get_elements_by_xpath(item, './/ul//li[4]/text()')
            if product_third_option:
                product_option.append(str(product_third_option).replace('[\' ','').replace('\']', ''))
                logger.debug(product_third_option)
            else:
                product_third_option = ""
                product_option.append(str(product_third_option))

            product['product_option'] = '/'.join(product_option)

            logger.debug("product_option:" + product['product_option'])

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/td[@class="amt"]/text()')
            if product_price_tmp:
                product_price = product_price_tmp.replace('$', '')
                product['product_price'] = product_price
                product['discount_price'] = '0'
                logger.debug("product_price:" + str(product['product_price']))

            # discount_price_tmp = xpath_parser.get_value_by_xpath(item, './/h5[@class="z-hd-beanie msrp"]/text()')
            # if discount_price_tmp:
            #     discount_price = discount_price_tmp.replace('MSRP $', '')
            #     product['discount_price'] = (float(discount_price) * float(product['product_qty'])) - (float(product['product_price']) * float(product['product_qty']))
            #     logger.debug("discount_price:" + str(product['discount_price']))
            # else:
            #     product['discount_price'] = '0'
            product_list.append(product)
    add_to_cart(product_list)

def amazon_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//div[@data-asin]//div[contains(@class,"sc-list-item-content")]')
    product_list = []

    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            #AMAZON CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './/div[@data-old-value]/@data-old-value')
            if product_qty:
                product['product_qty'] = product_qty
            product_url = xpath_parser.get_value_by_xpath(item, './/a[./img/@src]/@href')
            if product_url:
                product['product_url'] = "https://www.amazon.com" + product_url
                product_no = product_url.split('/')
                product_no_pre = product_no[3]
                product['product_id'] = product_no_pre
            product_name = xpath_parser.get_value_by_xpath(item, './/span[@class="a-list-item"]//a/span/text()')
            product['product_name'] = str(product_name)

            product['product_option'] = ""
            # product['product_option'] = '/'.join(product_option)

            image_URL = xpath_parser.get_value_by_xpath(item, './/img/@src')
            product['image_url'] = str(image_URL)
            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/span[contains(@class,"sc-product-price sc-price-sign")]/text() | .//p[@class="a-spacing-small"][4]/span[contains(@class,"sc-price")]/text()', r"""([0-9.,]+)""")
            if product_price_tmp:
                product_price = product_price_tmp.replace(',', '')
                product['product_price'] = float(product_price)
                product['discount_price'] = 0

            product_list.append(product)
    add_to_cart(product_list)

def ebay_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//div[@class="fl  col_100p "]')
    product_list = []
    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code': 0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            # ebay CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './/div[@class="fr pb20 col_100p qtyRow"]/div[1]/text()')
            if product_qty:
                product['product_qty'] = product_qty.replace('Quantity: ','')
                logger.debug("product_qty:" + str(product_qty))
            else:
                product_qty = xpath_parser.get_value_by_xpath(item, './/div[@class="fr pb20 col_100p qtyRow"]//input/@value')
                if product_qty:
                    product['product_qty'] = product_qty
                    logger.debug("product_qty:" + str(product_qty))
                else:
                    logger.debug("No product_qty")

            product_id = xpath_parser.get_value_by_xpath(item, './/span/@id')
            product['product_id'] = str(product_id).replace('_title','')
            logger.debug("product_id:" + str(product_id).replace('_title',''))

            product_name = xpath_parser.get_value_by_xpath(item, './/div[@class="ff-ds3 fs16 mb5 fw-n sci-itmttl"]/span/a/text()')
            product['product_name'] = product_name
            logger.debug("product_name:" + str(product_name))


            image_URL = xpath_parser.get_value_by_xpath(item, './/span[@class="imgt w140 h140 lh140"]/img/@data-echo')
            if image_URL:
                product['image_url'] = str(image_URL)
                logger.debug("image_URL:" + str(image_URL))
            else:
                image_URL = xpath_parser.get_value_by_xpath(item, './/span[@class="w140 h140 lh140"]//img/@data-echo')
                if image_URL:
                    product['image_url'] = str(image_URL)
                    logger.debug("image_URL:" + str(image_URL))
                else:
                    logger.debug("No image_URL")

            product_url = xpath_parser.get_value_by_xpath(item, './/span[@id]/a/@href')
            product['product_url'] = product_url
            logger.debug("product_url:" + str(product_url))

            product_option = []
            product_first_optional = xpath_parser.get_value_by_xpath(item, './/table[@class="ItemInfoTable"]//tr[1]/td[2]/text()')
            if product_first_optional:
                product_option.append(str(product_first_optional))
                logger.debug("product_first_optional:" + str(product_first_optional))
            else:
                logger.debug("No product_first_optional")

            product_second_optional = xpath_parser.get_value_by_xpath(item, './/table[@class="ItemInfoTable"]//tr[2]/td[2]/text()')
            if product_second_optional:
                product_option.append(str(product_second_optional))
                logger.debug("product_second_optional:" + str(product_second_optional))
            else:
                logger.debug("No product_second_optional")


            product_third_optinal = xpath_parser.get_value_by_xpath(item, './/table[@class="ItemInfoTable"]//tr[3]/td[2]/text()')
            if product_third_optinal:
                product_option.append(str(product_third_optinal))
                logger.debug("product_third_optinal:" + str(product_third_optinal))
            else:
                logger.debug("No product_third_optinal")


            product_firth_optional = xpath_parser.get_value_by_xpath(item, './/table[@class="ItemInfoTable"]//tr[4]/td[2]/text()')
            if product_firth_optional:
                product_option.append(str(product_firth_optional))
                logger.debug("product_firth_option:" + str(product_firth_optional))
            else:
                logger.debug("No product_firth_optional")

            product['product_option'] = '/'.join(product_option)

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/div[@class="fw-b clr-sr"]/text()')
            if product_price_tmp:
                logger.debug("product_price:" + str(product_price_tmp).replace('US $', ''))
                product_price = product_price_tmp.replace('US $', '').replace(',', '')
                product['product_price'] = float(product_price)
                product['discount_price'] = 0
            else:
                product_price_tmp = xpath_parser.get_value_by_xpath(item, './/span[@class]//div[@class="fw-b"]/text()')
                # product_price_sale_tmp = xpath_parser.get_value_by_xpath(item,
                #                                                          './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span//span[contains(@class,"font9")]/text()',
                #                                                          r"""([0-9.,]+)""")
                if product_price_tmp:
                    product_price = product_price_tmp.replace('US $', '').replace(',', '')
                    product['product_price'] = float(product_price)
                    product['discount_price'] = 0
                    logger.debug("product_price:" + str(product_price))
                else:
                    raise Exception('No product_price')

            product_shipping_tmp = xpath_parser.get_value_by_xpath(item,'.//div[@class="fr tr m0 p0 ff-ds3 fs14 clr000 prcol140 "]/div/text()')
            if product_shipping_tmp:
                product_shipping = product_shipping_tmp.replace(' ', '').replace('+US$', '')
            else:
                product_shipping = 0
            logger.debug(product_shipping)

            product['product_shipping'] = float(product_shipping)
            logger.debug("product_shipping:" + str(product_shipping))

                # if product_price_tmp and product_price_sale_tmp:
                #     product_price = product_price_tmp.replace(',', '')
                #     product_price_sale = product_price_sale_tmp.replace(',', '')
                #     product['product_price'] = float(product_price)
                #     product['discount_price'] = round(float(product_price) - float(product_price_sale), 2)
            product_list.append(product)
    add_to_cart(product_list)


def ralphlauren_parsing(html,head):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//table[@summary="Shopping Cart Contents"]//tr[.//table[@class="prodDetail"]]')
    product_list = []
    monetateRows = head.index('monetateRows.push')
    data = head[monetateRows:]
    monetateQ = data.index('monetateQ')
    data0 = data[:monetateQ]
    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        list = data0.replace('\t', '').splitlines()
        result = []
        for line in list:
            if line != "":
                _line = line.replace('monetateRows.push({', '').replace('});', '')
                _line = _line.split(',')

                tmp = {}
                for item in _line:
                    _item = item.split(':')
                    tmp[_item[0]] = _item[1][1:-1]

                result.append(tmp)

        for idx, item in enumerate(items):
            product = {}
            #GAP CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './/input[contains(@class,"quantity")]/@value')
            if product_qty:
                product['product_qty'] = product_qty

            product_id = xpath_parser.get_value_by_xpath(item, './/table[@class="prodDetail"]//tr[./th[contains(text(),"Style")]]/td/text()')
            product['product_id'] = product_id + "|" + result[idx]['sku']
            product_name = xpath_parser.get_value_by_xpath(item, './/td[contains(@class,"description")]//a[not(@class="img")]/strong/text()')
            product['product_name'] = product_name

            image_URL = xpath_parser.get_value_by_xpath(item, './/td[contains(@class,"description")]//img/@src')
            product['image_url'] = str(image_URL)

            product_url = xpath_parser.get_value_by_xpath(item, './/td[contains(@class,"description")]//a[not(@class="img")]/@href')
            product['product_url'] = product_url

            product_option = []
            product_color = xpath_parser.get_value_by_xpath(item, './/table[@class="prodDetail"]//tr[./th[contains(text(),"Color")]]/td/text()')
            product_option.append(str(product_color))

            product_size = xpath_parser.get_value_by_xpath(item, './/table[@class="prodDetail"]//tr[./th[contains(text(),"Size")]]/td/text()')
            product_option.append(str(product_size))

            product['product_option'] = '/'.join(product_option)

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/td[@class="currency"][1]/text()', r"""([0-9.,]+)""")
            if product_price_tmp:
                product_price = product_price_tmp.replace(',', '')
                product['product_price'] = product_price

            discount_price_tmp = xpath_parser.get_value_by_xpath(item, './/td[@class="currency"][2]//div[@class="specialprice"]/text()', r"""([0-9.,]+)""")
            if discount_price_tmp:
                discount_price = discount_price_tmp.replace(',', '')
                logger.debug('DS='+discount_price)
                product['discount_price'] = float(float(product['product_price']) * float(product_qty) - float(discount_price)) / float(product_qty)
            else:
                product['discount_price'] = '0'
            product_list.append(product)

    add_to_cart(product_list)

def beauty_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//div[@id="bag-items-in"]/div[@class="row"]')
    product_list = []
    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            #BEAUTY CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './/div[@class="bag-qty"]/input/@value | .//div[@class="bag-qty"]/b/text()')
            if product_qty:
                product['product_qty'] = product_qty

            product_id = xpath_parser.get_value_by_xpath(item, './/div[@class="bag-qty"]//div[@class="bag-remove"]/a/@href', """trxp2=(.*)""")
            product['product_id'] = product_id

            image_URL = xpath_parser.get_value_by_xpath(item, './/div[@class="image"]/img/@src')
            product['image_url'] = image_URL

            product_name = xpath_parser.get_value_by_xpath(item, './/div[@class="description"]/a/text()[1]| .//div[@class="description"]/text()[1]')
            if product_name:
                product_name = product_name[:3].replace('-', '') + product_name[3:]
                product['product_name'] = product_name.strip()

            product_url = xpath_parser.get_value_by_xpath(item, './/div[@class="description"]/a/@href')
            if product_url:
                product['product_url'] = 'http://www.beauty.com/' + product_url
            else:
                product['product_url'] = None

            product['product_option'] = ""

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/div[@class="total"]/h2/text()', r"""([0-9.,]+)""")
            if product_price_tmp:
                product_price = product_price_tmp.replace(',', '')
                product['product_price'] = str(float(product_price) / float(product_qty))
            else:
                product['product_price'] = '0'

            product['discount_price'] = '0'

            product_list.append(product)
    add_to_cart(product_list)

def carters_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//table[@id="cart-table"]//tr[@class="cart-row"]')
    product_list = []
    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            #CARTERS CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div/select//option[@selected="selected"]/@value')
            if product_qty:
                product['product_qty'] = product_qty

            product_id = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div/div[@class="name"]/a[@href]/@href')
            if product_id is not None:
                product_id2 = product_id.split('/')[-1]
                product_id3 = product_id2.split('.')
                if len(product_id3) > 0:
                    product['product_id'] = product_id3[0]

            product_name = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div[@class="product-list-item clearfix"]/div[@class="name"]/a[@href]/text()')
            if product_name:
                product['product_name'] = product_name
            else:
                if product.get('product_outstock'):
                    product['product_name'] = 'Out Of Stock'
                else:
                    product['product_name'] = 'No TITLE'

            image_URL = xpath_parser.get_value_by_xpath(item, './td[@class="item-image"]/img[@src]/@src')
            product['image_url'] = str(image_URL)

            product_url = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div/div[@class="name"]/a[@href]/@href')
            product['product_url'] = product_url

            product_option = []
            product_color = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div[@class="product-list-item clearfix"]/div[@class="attribute Color"]/span[@class="value"]/text()')
            product_option.append(str(product_color))

            product_size = xpath_parser.get_value_by_xpath(item, './td[@class="item-details"]/div[@class="product-list-item clearfix"]/div[@class="attribute Size"]/span[@class="value"]/text()')
            product_option.append(str(product_size))

            product['product_option'] = '/'.join(product_option)

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/td[@class="item-total"]//span[@class="price-total"]/text()', r"""([0-9.,]+)""")
            if product_price_tmp:
                product_price = product_price_tmp.replace(',', '')
                product['product_price'] = str(float(product_price) / float(product['product_qty']))
                product['discount_price'] = 0
            product_list.append(product)
    add_to_cart(product_list)

def gap_parsing(html):
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//div[@ng-repeat="item in items"]')
    product_list = []
    if items == None:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code':0})
    if len(items) > 0:
        for idx, item in enumerate(items):
            product = {}
            #GAP CART PARSING
            product_qty = xpath_parser.get_value_by_xpath(item, './/option[@selected]/text()')
            if product_qty:
                product['product_qty'] = product_qty

            product_id = xpath_parser.get_value_by_xpath(item, './/dd[contains(@class,"productSku")]/@alt')
            product['product_id'] = product_id

            product_name = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//dd[@class="productName"]/a/text()')
            product['product_name'] = product_name

            image_URL = xpath_parser.get_value_by_xpath(item, './/img/@src')
            product['image_url'] = "https://secure-www.gap.com" + str(image_URL)

            product_url = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//dd[@class="productName"]/a/@href')
            product['product_url'] = product_url

            product_option = []
            product_color = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Color")]]/dd/a/text()')
            product_option.append(str(product_color))

            product_size = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Size")]]/dd/a/text()')
            product_option.append(str(product_size))

            product['product_option'] = '/'.join(product_option)

            product_price_tmp = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//dd/span[contains(@class,"font9")]/text()', r"""([0-9.,]+)""")
            if product_price_tmp:
                product_price = product_price_tmp.replace(',', '')
                product['product_price'] = float(product_price)
                product['discount_price'] = 0

            else:
                product_price_tmp = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span//span[contains(@class,"font8")]/text()', r"""([0-9.,]+)""")
                product_price_sale_tmp = xpath_parser.get_value_by_xpath(item, './/div[@class="productInfo"]//div[./dt[contains(text(),"Price")]]//dd/span//span[contains(@class,"font9")]/text()', r"""([0-9.,]+)""")

                if product_price_tmp and product_price_sale_tmp:
                    product_price = product_price_tmp.replace(',', '')
                    product_price_sale = product_price_sale_tmp.replace(',', '')
                    product['product_price'] = float(product_price)
                    product['discount_price'] = round(float(product_price) - float(product_price_sale), 2)
            product_list.append(product)
    add_to_cart(product_list)

def bathandbodyworks_parsing(html):
    import re
    html_tree = xpath_parser.parse_htmlpage(html)
    items = xpath_parser.get_elements_by_xpath(html_tree, '//div[@class="product product-view"]')

    if len(items) == 0:
        logger.debug("NOTHING ADD TO CART")
        return jsonify({'result_code': 0})
    else:
        product_list = []
        for idx, item in enumerate(items):
            product = {}

            product_name = xpath_parser.get_value_by_xpath(item, './/a[@class="name"]/text()')
            product['product_name'] = product_name if product_name else ""

            product_qty = xpath_parser.get_value_by_xpath(item, './/div[@class="qty"]//input[@title="Quantity"]/@value')
            product['product_qty'] = product_qty if product_qty else "0"

            product_option = xpath_parser.get_value_by_xpath(item, './/p[@class="size-availability"]//span[@class="size"]/text()')
            product['product_option'] = product_option.strip() if product_option else ""

            image_url = xpath_parser.get_value_by_xpath(item, './/div[@class="product-image"]/a/img/@src')
            product['image_url'] = image_url.strip() if image_url else ""

            product_url = xpath_parser.get_value_by_xpath(item, './/div[@class="product-image"]/a/@href')
            product['product_url'] = product_url.strip() if product_url else ""

            product_price = xpath_parser.get_value_by_xpath(item, './/p[@class="price"]//span[@class="new-price"]/text()', r"""([0-9.,]+)""")
            if product_price:
                product['product_price'] = product_price.replace(',', '')
            else:
                product_price = xpath_parser.get_value_by_xpath(item, './/p[@class="price"]/text()', r"""([0-9.,]+)""")
                if product_price:
                    product['product_price'] = product_price.replace(',', '')
                else:
                    product['product_price'] = "0"

            product['discount_price'] = "0"

            match = re.search(r'productId=\d+', product['product_url'])
            site_prod_id = match.group().replace("productId=", "") if match is not None else ""
            match = re.search(r'\d+v65.jpg', product['image_url'])
            site_sku_id = match.group().replace("v65.jpg", "") if match is not None else ""
            product['product_id'] = site_prod_id + "|" + site_sku_id if site_prod_id != "" and site_sku_id != "" else ""

            product_list.append(product)

        add_to_cart(product_list)

def add_to_cart(product_list):
    current_milli_time = lambda: int(round(time.time() * 1000))
    json_dict = json.loads(request.data)
    #AB_order
    e_id = json_dict['e_id']
    #AB_shop_no
    shop_site_no = json_dict['shop_site_no']
    shop_site_name = json_dict['shop_site_name']

    con = mysql.connect()
    cursor = con.cursor()
    #맨처음 order_id parameter값이 없을때
    query = """
        SELECT
            MAX(order_id)
        FROM
            SERVICE.AB_order
        WHERE
            e_id = %s
        AND
            order_status = 0
    """
    bind = (e_id,)
    cursor.execute(query, bind)
    order_id = cursor.fetchone()
    #해당 e_id에 order_id가 없을 경우
    logger.debug("order_id:" + str(order_id[0]))

    if order_id[0] == None or order_id[0] == "":
        try:
            logger.debug("===== First time to add to cart =====")
            #AB_order에 생성
            query = """
                INSERT INTO
                    SERVICE.AB_order
                    (
                        order_id_alias,
                        e_id,
                        order_status,
                        reg_date
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        0,
                        NOW()
                    )
            """
            bind = (
                current_milli_time(),
                e_id
            )
            cursor.execute(query, bind)
            order_id = cursor.lastrowid
            logger.debug("===== Success Create order_id : "+str(order_id)+" =====")
            #AB_order_shop에 생성
            query = """
                INSERT INTO
                    SERVICE.AB_order_shop
                    (
                        order_id,
                        e_id,
                        shop_site_no,
                        shop_site_name,
                        reg_date
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW()
                    )
            """
            bind = (
                order_id,
                e_id,
                shop_site_no,
                shop_site_name
            )
            cursor.execute(query, bind)
            order_shop_id = cursor.lastrowid
            logger.debug("===== order_shop_id : "+str(order_shop_id)+" ======")
        except Exception as e:
            logger.debug("===== Error From No order_shop_id Section =====")
            logger.debug(e)
            con.rollback()
            con.close()
    #order id가 있을 경우 => order_shop_id 여부 확인
    else:
        logger.debug("===== order_id Is Exist =====")
        query = """
            SELECT
                order_shop_id
            FROM
                SERVICE.AB_order_shop
            WHERE
                order_id = %s
            AND
                shop_site_no = %s
        """
        bind = (
            order_id[0],
            shop_site_no
        )
        cursor.execute(query, bind)
        order_shop_id = cursor.fetchone()
        #들어온 order_shop_no, order_id에 대한 order_shop_id가 없을 경우
        if order_shop_id == None:
            try:
                logger.debug("===== order_shop_id Is Not Exist =====")
                query = """
                    INSERT INTO
                        SERVICE.AB_order_shop
                        (
                            order_id,
                            e_id,
                            shop_site_no,
                            shop_site_name,
                            reg_date
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            NOW()
                        )
                """
                bind = (
                    order_id[0],
                    e_id,
                    shop_site_no,
                    shop_site_name
                )
                cursor.execute(query, bind)
                order_shop_id = cursor.lastrowid
            except Exception as e:
                logger.debug("===== Error From No order_shop_id Section =====")
                logger.debug(e)
                con.rollback()
                con.close()
        #들어온 order_shop_no, order_id에 대한 order_shop_id가 있을 경우
        else:
            try:
                logger.debug("===== order_shop_id Is Exist =====")
                query = """
                    DELETE FROM
                        SERVICE.AB_order_item
                    WHERE
                        e_id = %s
                    AND
                        order_id = %s
                    AND
                        order_shop_id = %s
                """
                bind = (
                    e_id,
                    order_id[0],
                    order_shop_id[0]
                )

                cursor.execute(query, bind)
                logger.debug("===== Finish To Clean order_id:" + str(order_id[0]) + "/shop_site_name:" +shop_site_name + " Carts =====")
            except Exception as e:
                logger.debug("===== Error From Delete After Insert Items =====")
                logger.debug(e)
                con.rollback()
                con.close()
    i = 0
    for row in product_list:
        if shop_site_no == '2' or shop_site_no == 2:
            price_ship_est = float(row['product_shipping'])
            logger.debug("price_ship_est:" + str(row['product_shipping']))
        else:
            price_ship_est = float(0)
        query = """
            INSERT INTO
                SERVICE.AB_order_item
                (
                    order_id,
                    order_shop_id,
                    e_id,
                    product_id,
                    product_name,
                    product_option,
                    product_qty,
                    product_price,
                    product_ship_price,
                    discount_price,
                    product_url,
                    image_url,
                    reg_date
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
        """
        bind = (
            order_id,
            order_shop_id,
            e_id,
            row['product_id'],
            row['product_name'],
            row['product_option'],
            row['product_qty'],
            row['product_price'],
            float(price_ship_est),
            row['discount_price'],
            row['product_url'],
            row['image_url']
        )
        cursor.execute(query, bind)
        i = i+1
    logger.debug("===== Success To Add " + str(i) + "/" + str(len(product_list)) + " Items ======")
    con.commit()
    con.close()

#아이템 삭제
@app.route('/api/v0/user/delete_item', methods=["POST"])
def delete_item():
    json_dict = json.loads(request.data)
    item_id = json_dict['item_id']
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                order_shop_id
            FROM
                SERVICE.AB_order_item
            WHERE
                item_id = %s
        """
        bind = (item_id,)
        cursor.execute(query, bind)
        order_shop_id = cursor.fetchone()
        query = """
            DELETE FROM
                SERVICE.AB_order_item
            WHERE
                item_id = %s
        """
        cursor.execute(query, bind)
        if cursor.rowcount > 0:
            query = """
                SELECT
                    item_id
                FROM
                    SERVICE.AB_order_item
                WHERE
                    order_shop_id = %s
            """
            bind = (order_shop_id[0],)
            cursor.execute(query, bind)
            if cursor.rowcount < 1:
                query = """
                    DELETE FROM
                        SERVICE.AB_order_shop
                    WHERE
                        order_shop_id = %s
                """
                bind  = (order_shop_id[0],)
                cursor.execute(query, bind)
                if cursor.rowcount > 0:
                    logger.debug("===== Success To Delete item_id:" + str(item_id) + "/order_shop_id:" + str(order_shop_id[0]) + " =====")
                    con.commit()
                    con.close()
                    result = {'result_code':1}
            else:
                logger.debug("===== Success To Delete Item But Other Item's In order_shop_id:" + str(order_shop_id[0]) + " =====")
                con.commit()
                con.close()
                result = {'result_code':1}
        else:
            logger.debug("===== Nothing Delete =====")
            result = {'result_code':1}
        return jsonify(result)
    except Exception as e:
        logger.debug(e)
        return jsonify({'result_code':0})

#결제 예정 금액 QUEUE에 넣기
@app.route('/api/v0/user/before_pay_amount', methods=["POST"])
def before_pay_amount():
    json_dict = json.loads(request.data)
    order_id = json_dict['order_id']
    try:
        con = mysql.connect()
        cursor = con.cursor()
        try:
            query = """
                SELECT
                    AB_order.order_id,
                    AB_order_shop.order_shop_id,
                    AB_order_shop.shop_site_no,
                    AB_order_shop.shop_site_name
                FROM
                    (
                        SELECT
                            order_id
                        FROM
                            SERVICE.AB_order
                        WHERE
                            order_id	=	%s
                            and	order_status	=	0
                    )	as	AB_order
                JOIN
                    SERVICE.AB_order_shop
                ON
                    AB_order.order_id = AB_order_shop.order_id
                """
            bind = (order_id,)
            cursor.execute(query, bind)
            if cursor.rowcount == 0:
                logger.debug("===== Cart is Empty =====")
                return jsonify({'result_code': 0})
            result = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result.append(dict(zip(columns, row)))
            for row in result:
                query = """
                    SELECT
                        product_ship_price
                    FROM
                        SERVICE.AB_order_item
                    WHERE
                        order_shop_id = %s
                """
                bind = (row['order_shop_id'],)
                cursor.execute(query, bind)
                product_ship_price = cursor.fetchall()
                price_ship_est = float(0)
                for total in product_ship_price:
                    price_ship_est += float(total[0])
                logger.debug("product_ship_price:" + str(price_ship_est))
                query = """
                    UPDATE
                        SERVICE.AB_order_shop
                    SET
                        price_ship_est = %s
                    WHERE
                        order_shop_id = %s
                """
                bind = (
                    price_ship_est,
                    row['order_shop_id']
                )
                cursor.execute(query, bind)
                query = """
                    SELECT
                        COUNT(*) AS cnt
                    FROM
                        QUEUE.q_process_list
                    WHERE
                        order_id = %s
                    AND
                        AB_type = 0
                    AND
                        (status = 0 OR status = 4)
                    AND
                        shop_site_no = %s
                    """
                bind = (
                    row['order_id'],
                    row['shop_site_no']
                )
                cursor.execute(query, bind)
                data = cursor.fetchone()
                if data[0] == 0:
                    query = """
                        INSERT INTO
                            QUEUE.q_process_list
                            (
                                order_id,
                                shop_site_no,
                                shop_site_name,
                                AB_type,
                                status,
                                reg_date
                            )
                            VALUES
                            (
                                %s,
                                %s,
                                %s,
                                '0',
                                '0',
                                NOW()
                            )
                        ON DUPLICATE KEY UPDATE
                            status = '0',
                            update_date = NOW()

                        """
                    bind = (
                        row['order_id'],
                        row['shop_site_no'],
                        row['shop_site_name']
                    )

                    cursor.execute(query, bind)
                    if cursor.rowcount > 0:
                        con.commit()
                        logger.debug("===== Success Insert order_id:" + str(row['order_id']) + "/shop_site_name:" \
                                     + str(row['shop_site_name']) + " Into QUEUE =====")

                    else:
                        logger.debug("===== Nothing Insert In QUEUE =====")
                        con.rollback()
                        con.close()
                        return jsonify({'result_code': 0})
                else:
                    logger.debug("===== order_id Is Already Exist In QUEUE =====")
                    query = """
                            SELECT
                                status
                            FROM
                                QUEUE.q_process_list
                            WHERE
                                order_id = %s
                            AND
                                shop_site_no = %s
                        """
                    cursor.execute(query, bind)
                    status = cursor.fetchone()
                    if status[0] == "4":
                        query = """
                                UPDATE
                                    QUEUE.q_process_list
                                SET
                                    status = 0
                                WHERE
                                    order_id = %s
                                AND
                                    shop_site_no = %s
                            """
                        cursor.execute(query, bind)
                        logger.debug("===== Update order_id:" + str(row['order_id']) + " status 0 to 4 =====")
            con.commit()
            con.close()
            return jsonify({'result_code': 1})

        except Exception as e:
            con.rollback()
            con.close()
            logger.debug(e)
            logger.debug("===== Error API part : /api/v0/user/before_pay_amount | Query Error =====")
            return jsonify({'result_code': 0})
    except Exception as e:
        logger.debug(e)
        logger.debug("===== Error API part : /api/v0/user/before_pay_amount | DB Connection Error =====")
        return jsonify({'result_code': 0})

#현재 진행상태 체크, 상태에 따라 result_code 값 response
@app.route('/api/v0/user/check_pay_amount/<order_id>', methods=['GET'])
def check_pay_amount(order_id):
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                order_id,
                shop_site_name,
                status
            FROM
                QUEUE.q_process_list
            WHERE
                order_id = %s
            AND
                status != "4"
        """
        bind = (order_id,)
        cursor.execute(query, bind)
        result = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result.append(dict(zip(columns,row)))

        if cursor.rowcount > 0:
            for row in result:
                order_id = row['order_id']
                shop_site_name = row['shop_site_name']
                status = row['status']

                if status == "2":
                    logger.debug("===== order_id:" + str(order_id) + "/shop_site_name:" + shop_site_name + " Finish =====")
                elif status == "3":
                    logger.debug("===== order_id:" + str(order_id) + "/shop_site_name:" + shop_site_name + " Fail to pay amount =====")
                    return jsonify({'result_code':3})
                elif status == "1":
                    logger.debug("===== order_id:" + str(order_id) + "/shop_site_name:" + shop_site_name + " Pay Amount Ongoing =====")
                    return jsonify({'result_code':1})
                elif status == "9":
                    logger.debug("=====No Items In order_id:" + str(order_id) + "shop_site_name:" + shop_site_name + " =====")
                    return jsonify({'result_code':9})
                else:
                    logger.debug("===== order_id:" + str(order_id) + "/shop_site_name:" + shop_site_name + " Ready To Start =====")
                    return jsonify({'result_code':0})
            logger.debug("===== order_id:" + str(order_id) + " Finish All!! =====")
            return jsonify({'result_code':2})
        else:
            logger.debug("nothing in queue")
            con.rollback()
            con.close()
            return jsonify({'result_code':9})
    except Exception as e:
        logger.debug(e)
        return jsonify({'result_code':3})

#결제 예정금액 완료시 보여줄 값
@app.route('/api/v0/user/complete_pay_amount/<order_id>', methods=['GET'])
def complete_pay_amount(order_id):
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                e_id,
                payment_mileage
            FROM
                SERVICE.AB_order
            WHERE
                order_id = %s
        """
        bind = ( order_id, )
        cursor.execute(query, bind)
        service_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            service_info.append(dict(zip(columns, row)))
        for row in service_info:
            e_id = row['e_id']
            payment_mileage = row['payment_mileage']
        if int(payment_mileage) > 0:
            query = """
                UPDATE
                    SERVICE.AB_order
                SET
                    price_estimated = price_estimated + %s,
                    payment_mileage = 0
                WHERE
                    order_id = %s
            """
            bind = (
                int(payment_mileage),
                order_id
            )
            cursor.execute(query, bind)
            query = """
                UPDATE
                    BILLING.account_mileage
                SET
                    mileage = mileage + %s
                WHERE
                    e_id = %s
                """
            bind = (
                int(payment_mileage),
                int(e_id)
            )
            cursor.execute(query, bind)
            con.commit()
            logger.debug("===== Success To Rollback mileage =====")

        query = """
            SELECT
                AB_order.e_id,
                AB_order.order_id_alias,
                AB_order.price_estimated,
                AB_order_shop.shop_site_no,
                AB_order_shop.shop_site_name,
                (AB_order_shop.price_total_est - AB_order_shop.price_discount_est + AB_order_shop.price_ship_est) 'price_total_est',
                AB_order_shop.price_discount_est,
                AB_order_shop.price_ship_est,
                AB_order_shop.tax_est,
                AB_order_item.order_id,
                AB_order_item.order_shop_id,
                AB_order_item.e_id,
                AB_order_item.product_name,
                AB_order_item.product_option,
                AB_order_item.image_url,
                AB_order_item.product_qty,
                AB_order_item.product_price,
                AB_order_item.discount_price,
                AB_order_item.product_url
            FROM
                (
                    SELECT
                        e_id
                        ,	order_id
                        ,	order_id_alias
                        ,	price_estimated
                    FROM	SERVICE.AB_order
                    WHERE	order_id	=	%s
                )	as	AB_order
            INNER	JOIN
                SERVICE.AB_order_item
            ON
                AB_order.order_id	=	AB_order_item.order_id
            JOIN
                SERVICE.AB_order_shop
            ON
                AB_order_item.order_shop_id = AB_order_shop.order_shop_id
            WHERE
                AB_order_shop.price_est_done_flag = 1
        """
        bind = (order_id,)
        cursor.execute(query, bind)
        logger.debug("rowcnt:" + str(cursor.rowcount))
        result = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result.append(dict(zip(columns,row)))

        query = """
            SELECT
                mileage
            FROM
                BILLING.account_mileage
            WHERE
                e_id = %s
        """
        bind = (result[0]['e_id'],)
        cursor.execute(query, bind)
        mileage = cursor.fetchone()

        results = {}
        ret = {}

        ret['mileage'] = mileage[0]
        ret['order_id_alias'] = result[0]['order_id_alias']
        ret['price_estimated'] = result[0]['price_estimated']
        ret['price_total_discount'] = 0.00

        for row in result:
            shop_site_no = row['shop_site_no']
            if row['product_option'] == '" "':
                row['product_option'] = ''

            if shop_site_no not in list(results.keys()):
                ret['price_total_discount'] += row['price_discount_est']
                tmp = {
                    'shop_site_no':shop_site_no,
                    'shop_site_name':row['shop_site_name'].replace('_GROUP', ''),
                    'price_total_est':"%.2f" % row['price_total_est'],
                    'price_discount_est':"%.2f" % row['price_discount_est'],
                    'price_ship_est':"%.2f" % row['price_ship_est'],
                    'tax_est':"%.2f" % row['tax_est'],
                    'items':[
                        {
                            'product_name':row['product_name'],
                            'product_url':row['product_url'],
                            'image_url':row['image_url'],
                            'product_option':row['product_option'],
                            'product_qty':row['product_qty'],
                            'product_price':"%.2f" % row['product_price'],
                            'discount_price':"%.2f" % row['discount_price']
                        }
                    ]
                }
                results[shop_site_no] = tmp
            else:
                results[shop_site_no]['items'].append({
                    'product_name':row['product_name'],
                    'product_url':row['product_url'],
                    'image_url':row['image_url'],
                    'product_option':row['product_option'],
                    'product_qty':row['product_qty'],
                    'product_price':"%.2f" % row['product_price'],
                    'discount_price':"%.2f" % row['discount_price']
                })

        ret['price_total_discount'] = str(ret['price_total_discount'])
        con.close()
        ret['list'] = results.values()
        return json.dumps(ret)
    except Exception as e:
        con.rollback()
        con.close()
        logger.debug(e)
        logger.debug("SELECT POST data error")
        return jsonify({'result_code':0})

#결제 전 마일리지 사용
@app.route('/api/v0/user/use_mileage', methods=['POST'])
def use_mileage():
    order_id = request.form.get('order_id')
    order_status = request.form.get('order_status') if 'order_status' in request.form else '1'
    mileage = request.form.get('mileage')
    total_price = request.form.get('total_price')
    con = mysql.connect()
    cursor = con.cursor()
    logger.debug("order_id:" + str(order_id) + "/order_status:" + str(order_status) + "/using_mileage:" + str(mileage) + "/total_price:" + str(total_price))
    if order_status == '1':
        try:
            query = """
                SELECT
                    e_id,
                    price_estimated
                FROM
                    SERVICE.AB_order
                WHERE
                    order_id = %s
            """
            bind = (order_id,)
            cursor.execute(query, bind)
            result = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result.append(dict(zip(columns, row)))
            e_id = result[0]['e_id']
            price_estimated = result[0]['price_estimated']

            if (int(price_estimated) - int(mileage)) == int(total_price):
                logger.debug("price_estimated:" + str(price_estimated) + " | total_price:" + str(total_price))
                query = """
                    SELECT
                        payment_mileage
                    FROM
                        SERVICE.AB_order
                    WHERE
                        order_id = %s
                """
                cursor.execute(query, bind)
                payment_mileage = cursor.fetchone()

                query = """
                    UPDATE
                        SERVICE.AB_order
                    SET
                        price_estimated = %s,
                        payment_mileage = %s + %s
                    WHERE
                        order_id = %s
                """
                bind = (
                    int(total_price),
                    int(payment_mileage[0]),
                    int(mileage),
                    order_id,
                )
                cursor.execute(query, bind)
                logger.debug("===== Success To Update e_id:" + str(e_id) + " price_estimated =====")
                con.commit()
                return jsonify({'result_code': 1})
        except Exception as e:
            logger.debug(e)
            logger.debug("===== Use mileage Failed =====")
            return jsonify({'result_code': 0})
        else:
            logger.debug("===== The price_estimated Does Not Match =====")
            return jsonify({'result_code': 0})

    elif order_status == '6':
        try:
            query = """
                SELECT
                    e_id,
                    delivery_price
                FROM
                    SERVICE.AB_order
                WHERE
                    order_id = %s
            """
            bind = (order_id,)
            cursor.execute(query, bind)
            result = []
            columns = tuple([d[0] for d in cursor.description])
            for row in cursor:
                result.append(dict(zip(columns, row)))
            e_id = result[0]['e_id']
            delivery_price = result[0]['delivery_price']
            if (int(delivery_price) - int(mileage)) == int(total_price):
                logger.debug("delivery_price:" + str(delivery_price) + " | total_price:" + str(total_price))
                query = """
                    SELECT
                        delivery_mileage
                    FROM
                        SERVICE.AB_order
                    WHERE
                        order_id = %s
                """
                cursor.execute(query, bind)
                delivery_mileage = cursor.fetchone()

                query = """
                    UPDATE
                        SERVICE.AB_order
                    SET
                        delivery_price = %s,
                        delivery_mileage = %s + %s
                    WHERE
                        order_id = %s
                """
                bind = (
                    int(total_price),
                    int(delivery_mileage[0]),
                    int(mileage),
                    order_id,
                )
                cursor.execute(query, bind)

                logger.debug("===== Success To Update e_id:" + str(e_id) + " delivery_price  =====")
                con.commit()
                return jsonify({'result_code': 1})
        except Exception as e:
            logger.debug(e)
            logger.debug("===== Use mileage Failed =====")
            return jsonify({'result_code': 0})

        else:
            logger.debug("===== The delivery_price Does Not Match =====")
            return jsonify({'result_code': 0})

    else:
        logger.debug("===== UI Position Not Correct")
        return jsonify({'result_code': 0})

#배송비 결제금액 및 마일리지 사용
@app.route('/api/v0/user/delivery_price/<order_id>', methods=['GET'])
def delivery_price(order_id):
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            SELECT
                e_id,
                delivery_mileage
            FROM
                SERVICE.AB_order
            WHERE
                order_id = %s
            AND
                order_status = 6
        """
        bind = ( order_id,)
        cursor.execute(query, bind)
        service_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            service_info.append(dict(zip(columns, row)))
        for row in service_info:
            e_id = row['e_id']
            delivery_mileage = row['delivery_mileage']

        if int(delivery_mileage) > 0:
            query = """
                UPDATE
                    SERVICE.AB_order
                SET
                    delivery_price = delivery_price + %s,
                    delivery_mileage = 0
                WHERE
                    order_id = %s
            """
            bind = (
                int(delivery_mileage),
                order_id
            )
            cursor.execute(query, bind)
            con.commit()
            logger.debug("===== Success To rollback delivery mileage =====")
        query = """
            SELECT
                delivery_price
            FROM
                SERVICE.AB_order
            WHERE
                order_id = %s
            AND
                order_status = 6
        """
        cursor.execute(query, bind)
        delivery_price = cursor.fetchone()

        query = """
            SELECT
                mileage
            FROM
                BILLING.account_mileage
            WHERE
                e_id = %s
        """
        bind = (e_id,)
        cursor.execute(query, bind)
        mileage = cursor.fetchone()

        if delivery_price is None:
            logger.debug("===== No Update order_id:" + str(order_id) + " delivery_price =====")
            return jsonify({'result_code': 0, 'result_set': {}})
        result_set = {
            'delivery_price':int(delivery_price[0]),
            'mileage':int(mileage[0])
        }
        return jsonify({'result_code':1, 'result_set':result_set})
    except Exception as e:
        logger.debug(e)
        logger.debug("===== GET order_id:" + str(order_id) + " delivery_price Error =====")
        return jsonify({'result_code': 0, 'result_set': {}})

#내 주문서 리스트
@app.route('/api/v0/user/my_order_list', methods=['POST'])
def my_order_list():
    e_id = request.form.get('e_id')
    order_status = request.form.get('order_status') if 'order_status' in request.form else 2
    limit = request.form.get('limit') if 'limit' in request.form else 10
    offset = request.form.get('offset') if 'offset' in request.form else 0
    con = mysql.connect()
    cursor = con.cursor()
    try:
        logger.debug("===== e_id:" + str(e_id) + " =====")

        query = """
            SELECT
                order_id
            FROM
                SERVICE.AB_order
            WHERE
                e_id = %s
            AND
                order_status >= %s
            LIMIT
                %s
            OFFSET
                %s
        """
        bind = (
            e_id,
            order_status,
            limit,
            offset
        )
        order_ids = []
        cursor.execute(query, bind)
        order_ids = cursor.fetchall()
        if cursor.rowcount < 1:
            return jsonify({'result':0,'result_set':{}})
        query = """
           SELECT
                order_id,
                order_id_alias,
                price_estimated,
                order_status,
                payment_date,
                tracking_done_date,
                delivery_payment_date,
                clearence_date,
                duty_paid_date,
                delivery_done_date,
                update_date
            FROM
                SERVICE.AB_order
            WHERE
                order_id
            IN
                (%s)
            ORDER BY
                order_id
            DESC
        """
        bind = ', '.join(map(lambda x: '%s', order_ids))
        query = query % bind
        cursor.execute(query, order_ids)
        order_id = cursor.fetchall()
        result_order_list = []
        result_set = {'order_list':[]}
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result_order_list.append(dict(zip(columns,row)))
        query = """
            SELECT
                order_id,
                order_shop_id,
                shop_site_no,
                shop_site_name,
                price_ship_est
            FROM
                SERVICE.AB_order_shop
            WHERE
                order_id
            IN
                (%s)
        """
        query = query % bind
        cursor.execute(query, order_ids)
        result_shop_order_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result_shop_order_info.append(dict(zip(columns,row)))
        query = """
            SELECT
                order_shop_id,
                item_id,
                product_id,
                product_name,
                product_option,
                product_qty,
                (product_price - discount_price) AS product_price,
                product_url,
                image_url
            FROM
                SERVICE.AB_order_item
            WHERE
                order_id
            IN
                (%s)
        """
        query = query % bind
        cursor.execute(query, order_ids)
        result_order_item = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result_order_item.append(dict(zip(columns,row)))
        order_list = {}
        arr_order_list = {}
        i = 0
        for row in result_order_list:
            order_id = row['order_id']
            if order_id not in list(order_list.keys()):
                tmp = {
                    'order_id':order_id,
                    'order_id_alias':row['order_id_alias'],
                    'price':row['price_estimated'],
                    'order_status':row['order_status'],
                    'payment_date':str(row['payment_date']) if row['payment_date'] is not None else "",
                    'tracking_done_date':str(row['tracking_done_date']) if row['tracking_done_date'] is not None else "",
                    'delivery_payment_date':str(row['delivery_payment_date']) if row['delivery_payment_date'] is not None else "",
                    'clearence_date':str(row['clearence_date']) if row['clearence_date'] is not None else "",
                    'duty_paid_date':str(row['duty_paid_date']) if row['duty_paid_date'] is not None else "",
                    'delivery_done_date':str(row['delivery_done_date']) if row['delivery_done_date'] is not None else "",
                    'update_date':str(row['update_date']),
                    'item_images':[],
                    'shop_order_info':[]
                }
                order_list[order_id] = tmp
                result_set['order_list'].append(tmp)
                arr_order_list = result_set['order_list'][i]
                shop_order_info = {}
                arr_shop_order_info = {}
                j = 0
                for row in result_shop_order_info:
                    order_shop_id = row['order_shop_id']
                    if order_id == row['order_id']:
                        if order_shop_id not in list(shop_order_info.keys()):
                            tmp = {
                                'order_shop_id':order_shop_id,
                                'shop_site_no':row['shop_site_no'],
                                'shop_site_name':row['shop_site_name'].replace('_GROUP', ''),
                                'price_ship_est':"%.2f" % row['price_ship_est'],
                                'order_item':[]
                            }
                            shop_order_info[order_shop_id] = tmp
                            arr_order_list['shop_order_info'].append(tmp)
                            arr_shop_order_info = arr_order_list['shop_order_info'][j]
                            order_item = {}
                            for row in result_order_item:
                                if order_shop_id == row['order_shop_id']:
                                    tmp = {
                                        'item_id':row['item_id'],
                                        'product_id':row['product_id'],
                                        'product_name':row['product_name'],
                                        'product_option':row['product_option'],
                                        'product_qty':row['product_qty'],
                                        'product_price':"%.2f" % row['product_price'],
                                        'product_url':row['product_url'],
                                        'image_url':row['image_url']
                                    }
                                    order_item[row['item_id']] = tmp
                                    arr_shop_order_info['order_item'].append(tmp)
                                    arr_order_list['item_images'].append(row['image_url'])
                            j = j+1
            i = i+1
        return jsonify({'result':1,'result_set':result_set})
    except Exception:
        con.rollback()
        con.close()
        logger.debug(traceback.format_exc())
        result = 0
        return jsonify({'result':0,'result_set':{}})

#장바구니 이탈 & 결제 취소시
@app.route('/api/v0/user/cart_back_event', methods=['POST'])
def cart_back_event():
    json_dict = json.loads(request.data)
    order_id = json_dict['order_id']
    con = mysql.connect()
    cursor = con.cursor()
    try:
        query = """
            UPDATE
                SERVICE.AB_order_shop
            SET
                price_est_done_flag = 0,
                price_total_est = null,
                price_discount_est = null,
                price_ship_est = 0,
                tax_est = null,
                update_date = NOW()
            WHERE
                order_id = %s
        """
        bind = (order_id,)
        cursor.execute(query, bind)
        if cursor.rowcount > 0:
            logger.debug("===== Success Update SERVICE.AB_order_shop =====")
            query = """
                UPDATE
                    SERVICE.AB_order
                SET
                    order_status = 0,
                    price_estimated = null,
                    price_ship = null,
                    tax = null,
                    update_date = NOW()
                WHERE
                    order_id = %s
            """
            cursor.execute(query, bind)
            if cursor.rowcount > 0:
                logger.debug("===== Success Update SERVICE.AB_order =====")
                query = """
                    UPDATE
                        QUEUE.q_process_list
                    SET
                        status = 4,
                        update_date = NOW()
                    WHERE
                        order_id = %s
                """
                cursor.execute(query, bind)
                if cursor.rowcount > 0:
                    logger.debug("===== Success Update QUEUE.q_process_list =====")
                    con.commit()
                    con.close()
                    result = {'result_code':1}
                else:
                    logger.debug("===== Nothing Update QUEUE.q_process_list =====")
                    result = {'result_code':0}
            else:
                logger.debug("===== Nothing Update SERVICE.AB_order =====")
                result = {'result_code':0}
        else:
            logger.debug("===== Nothing Update SERVICE.AB_order_shop =====")
            result = {'result_code':0}

        return jsonify(result)

    except Exception as e:
        logger.debug(e)
        return jsonify({'result_code':0})

#tpay 결제시스템 빌링키 발급
# @app.route('/api/v0/payment/tpay_payment',methods=['POST'])
# def tpay_payment():
#         json_dict = json.loads(request.data)
#         con = mysql.connect()
#         cursor = con.cursor()
#         curl = pycurl.Curl()
#         #parameters of AB_payment_info
#         e_id = json_dict['e_id']
#         order_id = json_dict['order_id']
#         amount_request = json_dict['amount_request']
#         #PG사 요구parameteres
#         api_key = json_dict['api_key']
#         mid = json_dict['mid']
#         card_num = json_dict['card_num']
#
#
#         cursor.execute("SELECT trans_id FROM BILLING.AB_payment_info WHERE e_id = '%s' AND order_id = '%s'"%(e_id,order_id))
#         card_token = cursor.fetchone()
#         print(card_token)
#         #결제 빌링키 발급
#         if card_token == None:
#             cursor.execute("INSERT INTO BILLING.AB_payment_info(e_id,order_id,payment_type,payment_status,amount_request,pg_type,reg_date) \
#                             VALUES('%s','%s',1,0,'%s',1,NOW())"%(e_id,order_id,amount_request))
#             url = "http://127.0.0.1:5001/test"  #PG사 api url : POST https://webtx.tpay.co.kr/api/v1/gen_billkey
#
#             buffer = StringIO()
#
#             curl.setopt(curl.URL, url)
#             postfields = urlencode({'api_key':api_key,'mid':mid,'card_num':card_num})
#             curl.setopt(curl.POSTFIELDS, postfields)
#             curl.setopt(curl.WRITEDATA, buffer)
#             curl.perform()
#
#             res = json.loads(buffer.getvalue())
#             result_cd = res['result_cd']
#             result_msg = res['result_msg']
#             card_token = res['card_token']
#
#             cursor.execute("UPDATE BILLING.AB_payment_info SET trans_id = '%s', result_code = '%s', result_message = '%s'\
#                             WHERE e_id = '%s' AND order_id = '%s'"%(card_token,result_cd,result_msg,e_id,order_id))
#             print("SUCCESS TO UPDATE card_token")
#             curl.close()
#             con.commit()
#             tpay_payment_billingkey()
#             return jsonify({"result_code":1})
#         #결제 요청
#         else:
#             tpay_payment_billingkey()
#             return jsonify({"result_code":1})
#
# #tpay 결제시스템 빌링키 결제
# def tpay_payment_billingkey():
#     json_dict = json.loads(request.data)
#     con = mysql.connect()
#     cursor = con.cursor()
#     curl = pycurl.Curl()
#     #parameters
#     e_id = json_dict['e_id']
#     order_id = json_dict['order_id']
#     amount_request = json_dict['amount_request']
#     api_key = json_dict['api_key']
#     mid = json_dict['mid']
#
#     card_num = json_dict['card_num']
#     cursor.execute("SELECT trans_id FROM BILLING.AB_payment_info WHERE e_id = '%s' AND order_id = '%s'"%(e_id,order_id))
#     card_token = cursor.fetchone()
#
#     url = "http://127.0.0.1:5001/tests" # PG사 api url : POST https://webtx.tpay.co.kr/api/v1/payments_token
#     buffer = StringIO()
#
#     curl.setopt(curl.URL, url)
#     postfields = urlencode({'api_key':api_key,'mid':mid,'paid_amt':amount_request,'card_token':card_token[0]})
#     curl.setopt(curl.POSTFIELDS, postfields)
#     curl.setopt(curl.WRITEDATA, buffer)
#     curl.perform()
#
#     res = json.loads(buffer.getvalue())
#     result_cd = res['result_cd']        #결제코드 성공인 경우 000을 리턴
#     result_msg = res['result_msg']
#     paid_amt = res['paid_amt']
#     if result_cd == "000":
#         cursor.execute("UPDATE BILLING.AB_payment_info SET payment_status = 1, amount_paid = '%s', result_code = '%s', result_message = '%s', update_date = NOW()\
#                         WHERE e_id = '%s' AND order_id = '%s'"%(paid_amt,result_cd,result_msg,e_id,order_id))
#         con.commit()
#         con.close()
#         print("SUCCESS")
#         return jsonify({"result_code":1})
#     else:
#         cursor.execute("UPDATE BILLING.AB_payment_info SET result_code = '%s', result_message = '%s',update_date = NOW()\
#                         WHERE e_id = '%s' AND order_id = '%s'"%(result_cd,result_msg,e_id,order_id))
#         print("FAIL")
#         return jsonify({"result_code":0})
#
# #tpay 결제시스템 배송비 결제
# @app.route('/api/v0/payment/tpay_payment/delivery_price', methods=['POST'])
# def tpay_delivery_payment():
#     json_dict = json.loads(request.data)
#     con = mysql.connect()
#     cursor = con.cursor()
#     curl = pycurl.Curl()
#     #parameters
#     e_id = json_dict['e_id']
#     order_id = json_dict['order_id']
#     #PG parameters
#     api_key = json_dict['api_key']
#     mid = json_dict['mid']
#     cursor.execute("SELECT delivery_price FROM SERVICE.AB_order WHERE e_id = '%s' AND order_id = '%s'"%(e_id,order_id))
#     paid_amt = cursor.fetchone()
#     cursor.execute("SELECT trans_id FROM BILLING.AB_payment_info WHERE e_id = '%s' AND order_id = '%s'"%(e_id,order_id))
#     card_token = cursor.fetchone()
#     url = "http://127.0.0.1:5001/test_delivery"
#     buffer = StringIO()
#
#     curl.setopt(curl.URL, url)
#     postfields = urlencode({'api_key':api_key,'mid':mid,'paid_amt':paid_amt[0],'card_token':card_token[0]})
#     curl.setopt(curl.POSTFIELDS, postfields)
#     curl.setopt(curl.WRITEDATA, buffer)
#     curl.perform()
#
#     res = json.loads(buffer.getvalue())
#     result_code = res['result_cd']
#     result_message = res['result_msg']
#     paid_amt = res['paid_amt']
#     if result_code == "000":
#         cursor.execute("UPDATE SERVICE.AB_order SET order_status = 7,payment_amount = '%s', payment_result = '%s', payment_msg = '%s', payment_date = NOW()\
#                         WHERE e_id = '%s', order_id = '%s'"%(paid_amt,result_code,result_message,e_id,order_id))
#         con.commit()
#         con.close()
#         print("SUCCESS")
#         return jsonify({'result_code':1})
#     else:
#         cursor.execute("UPDATE SERVICE.AB_order SET payment_amount = '%s', payment_result = '%s', payment_msg = '%s', payment_date = NOW()\
#                         WHERE e_id = '%s', order_id = '%s'"%(paid_amt,result_code,result_message,e_id,order_id))
#         con.commit()
#         con.close()
#         print("FAIL")
#         return jsonify({'result_code':0})

@app.route('/api/v0/payment/request_payment', methods=['POST'])
def request_payment():
    order_id = request.form.get('order_id')
    price_estimated = request.form.get('price_estimated')
    result_price = request.form.get('result_price') if 'result_price' in request.form else price_estimated
    name = request.form.get('name')
    cell_phone = request.form.get('cell_phone')
    email = request.form.get('email')

    logger.debug("order_id:" + str(order_id) + "/price_estimated: " + str(price_estimated) + "/result_price: " + str(result_price) +"/name: " + name +\
                 "/cell_phone: " + str(cell_phone) + "/email: " + email)

    try:
        if order_id is None or price_estimated is None or name is None or cell_phone is None or email is None:
            raise Exception('missing parameters')

        from models.payment import MPayment
        m_payment = MPayment(logger)

        order_info = m_payment.get_order_info(order_id)

        if order_info is False:
            raise Exception('invalid order_id')

        if int(order_info['price_estimated']) != int(result_price):
            raise Exception('invalid pay amount')

        billing_info_seq = m_payment.set_payment_info_init(order_info['e_id'], order_id, '1', int(price_estimated), '1', 1)
        if billing_info_seq is False:
            raise Exception('billing info init error')

        data = {
            'merchant_uid': 'afterbuy_' + str(billing_info_seq),
            'order_id': order_id,
            'order_id_alias': order_info['order_id_alias'],
            'e_id': order_info['e_id'],
            'price_estimated': int(result_price),
            'name': name,
            'cell_phone': cell_phone,
            'email': email,
            'billing_info_seq': billing_info_seq
        }

        logger.debug("ORDER_DATA: " + json.dumps(data))

        return render_template('request_payment.html', data=data)
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return jsonify({'result_code': 0})

@app.route('/api/v0/payment/get_payment_result', methods=['GET'])
def get_payment_result():
    try:
        from urllib import urlencode
        from models.payment import MPayment
        from util.slack import report_order_slack

        imp_success = request.args.get('imp_success')
        imp_uid = request.args.get('imp_uid')

        if imp_success is None or imp_uid is None:
            raise Exception("잘못된 접근입니다.")

        m_payment = MPayment(logger)
        buffer = StringIO()

        # get iamport token
        c = pycurl.Curl()
        data = {
            'imp_key': '6904226663122107',
            'imp_secret': 'R7coCaYe73Hmmk02FdhSmnFKUu6dOsaGAm4cx2qE581rs2u8fM0B9Fm4athZWrFxOKJlMa0Si1kL3OTi'
        }
        c.setopt(c.URL, 'https://api.iamport.kr/users/getToken')
        c.setopt(c.POSTFIELDS, urlencode(data))
        c.setopt(c.WRITEFUNCTION, buffer.write)
        c.perform()
        c.close()

        res = json.loads(buffer.getvalue())
        buffer.truncate(0)
        if res['code'] != 0:
            raise Exception(res['message'])
        elif res['response']['access_token'] is None or res['response']['access_token'] == "":
            raise Exception()
        imp_access_token = res['response']['access_token']

        # get iamport payment result
        api_url = "https://api.iamport.kr/payments/%s?_token=%s" % (str(imp_uid), str(imp_access_token))
        c = pycurl.Curl()
        c.setopt(c.URL, api_url)
        c.setopt(c.WRITEFUNCTION, buffer.write)
        c.perform()
        c.close()

        res = json.loads(buffer.getvalue())
        buffer.truncate(0)

        if imp_success == "false":
            if res['response']['merchant_uid'] is not None or res['response']['merchant_uid'] != "":
                billing_info_seq = int(res['response']['merchant_uid'].split('_')[1])
                m_payment.update_billing_info_fail(billing_info_seq, res['response']['imp_uid'], res['message'], json.dumps(res))
            raise Exception("결제가 실패하였습니다.")

        if res['code'] != 0:
            raise Exception(res['message'])

        payment_result = res['response']
        custom_data = json.loads(payment_result['custom_data'])
        result = m_payment.update_billing_info_success(
            custom_data['order_id'],
            custom_data['billing_info_seq'],
            payment_result['imp_uid'],
            payment_result['pg_tid'],
            payment_result['apply_num'],
            payment_result['paid_at'],
            payment_result['amount'],
            payment_result['status'],
            '',
            json.dumps(payment_result)
        )

        if result is False:
            raise Exception('결제 정보 저장 중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요.')

        con = mysql.connect()
        cursor = con.cursor()

        query = """
            SELECT
                e_id,
                payment_mileage
            FROM
                SERVICE.AB_order
            WHERE
                order_id = %s
            AND
                order_status = 2
        """
        bind = (custom_data['order_id'],)
        cursor.execute(query, bind)
        service_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            service_info.append(dict(zip(columns, row)))
        for row in service_info:
            e_id = row['e_id']
            payment_mileage = row['payment_mileage']

        report_order_slack(
            order_type = "상품 결제",
            e_id = e_id,
            order_id = custom_data['order_id'] if 'order_id' in custom_data else "Not in custom_data",
            billing_info_seq = custom_data['billing_info_seq'] if 'billing_info_seq' in custom_data else "Not in custom_data",
            amount = payment_result['amount'] if 'amount' in payment_result else "Not in payment_result",
            paid_at = payment_result['paid_at'] if 'paid_at' in payment_result else "Not in payment_result"
        )


        #마일리지 사용하여 결제 하였을 시
        if int(payment_mileage) > 0:
            query = """
                UPDATE
                    BILLING.account_mileage
                SET
                    mileage = mileage - %s
                WHERE
                    e_id = %s
            """
            bind = (
                int(payment_mileage),
                e_id
            )
            cursor.execute(query, bind)
            con.commit()
            query = """
                SELECT
                    mileage
                FROM
                    BILLING.account_mileage
                WHERE
                    e_id = %s
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            mileage = cursor.fetchone()
            description = "상품 결제시 사용"
            use_type = 1
            result_history = m_payment.insert_account_mileage_history(
                e_id,
                payment_mileage,
                mileage[0],
                description,
                use_type,
                custom_data['order_id']
            )

            if result_history is False:
                raise Exception('마일리지 사용내역 저장 중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요.')

        return jsonify({
            'result_code': 1,
            'result_msg': "결제가 완료되었습니다."
        })
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return jsonify({
            'result_code': 0,
            'result_msg': e.message if e.message else "결제 도중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요."
        })


@app.route('/api/v0/payment/set_payment_result', methods=['POST'])
def set_payment_result():
    result = request.get_json()

    try:
        from models.payment import MPayment
        m_payment = MPayment(logger)

        if result['success'] is True:
            m_payment.update_billing_info_success(
                result['custom_data']['order_id'],
                result['custom_data']['billing_info_seq'],
                result['imp_uid'],
                result['pg_tid'],
                result['apply_num'],
                result['paid_at'],
                result['paid_amount'],
                result['status'],
                '',
                json.dumps(result)
            )
        else:
            billing_info_seq = int(result['merchant_uid'].split('_')[1])
            m_payment.update_billing_info_fail(billing_info_seq, result['imp_uid'], result['error_msg'], json.dumps(result))
            raise Exception('payment was not a success')

        return jsonify({'result_code': 1})
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return jsonify({'result_code': 0})


@app.route('/api/v0/create_amazon_cart/<order_id>', methods=['GET'])
def create_amazon_cart(order_id):
    from amazon.api import AmazonAPI, AmazonCart
    from lxml import objectify

    try:
        purchase_url = ""
        conn = mysql.connect()
        cursor = conn.cursor()
        query = """
            SELECT
                oi.product_id,
                oi.product_qty
            FROM
            (
                SELECT
                    order_shop_id,
                    order_id
                FROM SERVICE.AB_order_shop
                WHERE
                    shop_site_no = 1
                    AND order_id = %s
            )	as	os
            INNER JOIN
                SERVICE.AB_order_item oi
            ON
                os.order_shop_id = oi.order_shop_id
        """
        cursor.execute(query, (order_id,))
        items = cursor.fetchall()

        if len(items) > 0:
            AMAZON_SECRET_KEY = 'yArVCZzNSoOwae9cjOWFmzKLd3aBIqaz3iDQIVDs'
            AMAZON_ACCESS_KEY = 'AKIAJHGYIFG5PGVIKEBQ'
            AMAZON_ASSOC_TAG = 'straw0c3-20'

            amazon_aff_api = AmazonAPI(AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_ASSOC_TAG)

            offer_id_key_template = 'Item.%s.ASIN'
            quantity_key_template = 'Item.%s.Quantity'

            _items = dict()
            i = 1

            for item in items:
                _items[offer_id_key_template % (i,)] = item[0]
                _items[quantity_key_template % (i,)] = item[1]
                i += 1

            result = amazon_aff_api.api.CartCreate(**_items)
            root = objectify.fromstring(result)
            cart = AmazonCart(root)

            purchase_url = cart.purchase_url

        response = {
            'purchase_url': purchase_url
        }

        return jsonify(response)
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return traceback.format_exc()

@app.route('/api/slack', methods=['POST'])
def slack():
    from util.slack import report_order_slack

    report_order_slack(
    order_id=request.form.get('order_id'),
    billing_info_seq=request.form.get('billing_info_seq'),
    amount=request.form.get('amount') if 'amount' in request.form else "",
    paid_at=request.form.get('paid_at')
    )
    return "test"

@app.route('/api/v0/payment/request_delivery_payment', methods=['POST'])
def delivery_payment():
    con = mysql.connect()
    cursor = con.cursor()
    order_id = request.form.get('order_id')
    e_id = request.form.get('e_id')
    price_estimated = request.form.get('price_estimated')
    result_price = request.form.get('result_price')
    try:
        query = """
             SELECT
                AB_order.order_id_alias,
                AB_order.delivery_price,
                AB_order.delivery_real_weight,
                delivery_info.name,
                delivery_info.cell_phone,
                delivery_info.email
            FROM
            (
                SELECT
                    order_id_alias
                    ,	delivery_price
                    ,	delivery_real_weight
                    ,	delivery_seq
                FROM	SERVICE.AB_order
                WHERE	order_id = %s
            )	as	AB_order
            INNER	JOIN
                MEMBERSHIP.delivery_info
            ON AB_order.delivery_seq = delivery_info.delivery_seq
        """
        bind = ( order_id, )
        cursor.execute(query, bind)
        result_delivery_order_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            result_delivery_order_info.append(dict(zip(columns, row)))

        for row in result_delivery_order_info:
            logger.debug(
                "e_id: " + str(e_id) + "/order_id: " + str(order_id) + "/price_estimated: " + str(price_estimated) + "/result_price: " + str(result_price)\
                + "/name: " + str(row['name']) + "/cell_phone: " + str(row['cell_phone']) + "/email: " + str(row['email']))
            delivery_price = row['delivery_price']

            try:
                if order_id is None or row['delivery_price'] is None or row['name'] is None or row['cell_phone'] is None or row['email'] is None:
                    raise Exception('missing parameters')

                from models.payment import MPayment
                m_payment = MPayment(logger)

                if int(delivery_price) != int(result_price):
                    raise Exception("Does Not Match price_estimated AND Pay Amount")

                billing_info_seq = m_payment.set_payment_info_init(e_id, order_id, '1', int(price_estimated), '1', 2)
                if billing_info_seq is False:
                    raise Exception('billing info init error')
                data = {
                    'merchant_uid': 'afterbuy_' + str(billing_info_seq),
                    'order_id': order_id,
                    'order_id_alias': row['order_id_alias'],
                    'e_id': e_id,
                    'price_estimated': int(delivery_price),
                    'name': row['name'],
                    'cell_phone': row['cell_phone'],
                    'email': row['email'].replace(' ',''),
                    'billing_info_seq': billing_info_seq
                }
                return render_template('request_delivery_payment.html', data=data)
            except Exception as e:
                logger.debug(e)
                logger.debug(traceback.format_exc())
                return jsonify({'result_code': 0})
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return jsonify({'result_code': 0})

@app.route('/api/v0/payment/get_delivery_payment_result', methods=['GET'])
def get_delivery_payment_result():
    try:
        from urllib import urlencode
        from models.payment import MPayment
        from util.slack import report_order_slack

        imp_success = request.args.get('imp_success')
        imp_uid = request.args.get('imp_uid')

        if imp_success is None or imp_uid is None:
            raise Exception("잘못된 접근입니다.")

        m_payment = MPayment(logger)
        buffer = StringIO()

        # get iamport token
        c = pycurl.Curl()
        data = {
            'imp_key': '6904226663122107',
            'imp_secret': 'R7coCaYe73Hmmk02FdhSmnFKUu6dOsaGAm4cx2qE581rs2u8fM0B9Fm4athZWrFxOKJlMa0Si1kL3OTi'
        }
        c.setopt(c.URL, 'https://api.iamport.kr/users/getToken')
        c.setopt(c.POSTFIELDS, urlencode(data))
        c.setopt(c.WRITEFUNCTION, buffer.write)
        c.perform()
        c.close()

        res = json.loads(buffer.getvalue())
        buffer.truncate(0)
        if res['code'] != 0:
            raise Exception(res['message'])
        elif res['response']['access_token'] is None or res['response']['access_token'] == "":
            raise Exception()
        imp_access_token = res['response']['access_token']

        # get iamport payment result
        api_url = "https://api.iamport.kr/payments/%s?_token=%s" % (str(imp_uid), str(imp_access_token))
        c = pycurl.Curl()
        c.setopt(c.URL, api_url)
        c.setopt(c.WRITEFUNCTION, buffer.write)
        c.perform()
        c.close()

        res = json.loads(buffer.getvalue())
        buffer.truncate(0)

        if imp_success == "false":
            if res['response']['merchant_uid'] is not None or res['response']['merchant_uid'] != "":
                billing_info_seq = int(res['response']['merchant_uid'].split('_')[1])
                m_payment.update_billing_info_fail(billing_info_seq, res['response']['imp_uid'], res['message'],
                                                   json.dumps(res))
            raise Exception("배송비 결제가 실패하였습니다.")

        if res['code'] != 0:
            raise Exception(res['message'])

        payment_result = res['response']
        custom_data = json.loads(payment_result['custom_data'])
        result = m_payment.update_billing_delivery_info_success(
            custom_data['order_id'],
            custom_data['billing_info_seq'],
            payment_result['imp_uid'],
            payment_result['pg_tid'],
            payment_result['apply_num'],
            payment_result['paid_at'],
            payment_result['amount'],
            payment_result['status'],
            '',
            json.dumps(payment_result)
        )

        if result is False:
            raise Exception('배송비 결제 정보 저장 중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요.')

        con = mysql.connect()
        cursor = con.cursor()

        query = """
                SELECT
                    e_id,
                    delivery_mileage
                FROM
                    SERVICE.AB_order
                WHERE
                    order_id = %s
                AND
                    order_status = 7
            """
        bind = (custom_data['order_id'],)
        cursor.execute(query, bind)
        service_info = []
        columns = tuple([d[0] for d in cursor.description])
        for row in cursor:
            service_info.append(dict(zip(columns, row)))
        for row in service_info:
            e_id = row['e_id']
            delivery_mileage = row['delivery_mileage']

        report_order_slack(
            order_type="배송비 결제",
            e_id=e_id,
            order_id=custom_data['order_id'],
            billing_info_seq=custom_data['billing_info_seq'],
            amount=payment_result['amount'],
            paid_at=payment_result['paid_at']
        )


        # 마일리지 사용하여 결제 하였을 시
        if int(delivery_mileage) > 0:
            query = """
                UPDATE
                    BILLING.account_mileage
                SET
                    mileage = mileage - %s
                WHERE
                    e_id = %s
            """
            bind = (
                int(delivery_mileage),
                e_id
            )
            cursor.execute(query, bind)
            con.commit()
            query = """
                SELECT
                    mileage
                FROM
                    BILLING.account_mileage
                WHERE
                    e_id = %s
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            mileage = cursor.fetchone()
            description = "배송비 결제시 사용"
            use_type = 2
            result_history = m_payment.insert_account_mileage_history(
                e_id,
                delivery_mileage,
                mileage[0],
                description,
                use_type,
                custom_data['order_id']
            )

            if result_history is False:
                raise Exception('마일리지 사용내역 저장 중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요.')
        return jsonify({
            'result_code': 1,
            'result_msg': "결제가 완료되었습니다."
        })
    except Exception as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        return jsonify({
            'result_code': 0,
            'result_msg': e.message if e.message else "배송비 결제 도중 오류가 발생하였습니다.\n1:1 문의를 통해 문의해 주세요."
        })

#마일리지로 총 계산 했을 경우
@app.route('/api/v0/free_price_estimated', methods=['POST'])
def free_price_estimated():
    e_id = request.form.get('e_id')
    order_id = request.form.get('order_id')
    order_status = request.form.get('order_status') if 'order_status' in request.form else '1'
    price_estimated = request.form.get('price_estimated')
    mileage = request.form.get('mileage')
    total_price = request.form.get('total_price')
    logger.debug("e_id:" + str(e_id) + "/order_id:" + str(order_id))
    con = mysql.connect()
    cursor = con.cursor()

    try:
        from models.payment import MPayment
        from util.slack import report_order_slack

        m_payment = MPayment(logger)

        if order_status == '1':
            query = """
                INSERT INTO
                    BILLING.AB_payment_info
                    (
                        e_id,
                        order_id,
                        payment_type,
                        payment_status,
                        amount_request,
                        pg_type,
                        amount_paid,
                        reg_date,
                        service_type
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        4,
                        '1',
                        %s,
                        0,
                        %s,
                        NOW(),
                        1
                    )
            """
            bind = (
                e_id,
                order_id,
                int(price_estimated),
                int(total_price)
            )
            cursor.execute(query, bind)

            query = """
                UPDATE
                    BILLING.account_mileage
                SET
                    mileage = mileage - %s
                WHERE
                    e_id = %s
            """
            bind = (
                mileage,
                e_id
            )
            cursor.execute(query, bind)

            query = """
                UPDATE
                    SERVICE.AB_order
                SET
                    order_status = '2',
                    payment_mileage = %s,
                    payment_date = NOW(),
                    update_date = NOW()
                WHERE
                    order_id = %s
            """
            bind = (
                mileage,
                order_id
            )
            cursor.execute(query, bind)
            con.commit()
            report_order_slack(
                order_type="상품 결제",
                order_id= order_id,
                billing_info_seq= "마일리지 결제",
                amount=0,
                paid_at= int(time.time())
            )

            query = """
                SELECT
                    mileage
                FROM
                    BILLING.account_mileage
                WHERE
                    e_id = %s
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            cur_mileage = cursor.fetchone()
            description = "상품 총 결제금액 마일리지 사용"
            use_type = 1
            result_history = m_payment.insert_account_mileage_history(
                e_id,
                mileage,
                int(cur_mileage[0]),
                description,
                use_type,
                order_id
            )
            if result_history is False:
                raise Exception('Fail to left mileage history')

            return jsonify({'result_code':1})
        elif order_status == '6':
            query = """
                INSERT INTO
                    BILLING.AB_payment_info
                    (
                        e_id,
                        order_id,
                        payment_type,
                        payment_status,
                        amount_request,
                        pg_type,
                        amount_paid,
                        reg_date,
                        service_type
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        4,
                        '1',
                        %s,
                        0,
                        %s,
                        NOW(),
                        2
                    )
            """
            bind = (
                e_id,
                order_id,
                price_estimated,
                total_price
            )
            cursor.execute(query, bind)

            query = """
                UPDATE
                    BILLING.account_mileage
                SET
                    mileage = mileage - %s
                WHERE
                    e_id = %s
            """
            bind = (
                mileage,
                e_id
            )
            cursor.execute(query, bind)

            query = """
                UPDATE
                    SERVICE.AB_order
                SET
                    order_status = '7',
                    payment_date = NOW(),
                    update_date = NOW()
                WHERE
                    order_id = %s
            """
            bind = (order_id,)
            cursor.execute(query, bind)
            con.commit()
            report_order_slack(
                order_type="배송 결제",
                order_id=order_id,
                billing_info_seq="마일리지 결제",
                amount=0,
                paid_at=int(time.time())
            )


            query = """
                SELECT
                    mileage
                FROM
                    BILLING.account_milpayment_mileageeage
                WHERE
                    e_id = %s
            """
            bind = (e_id,)
            cursor.execute(query, bind)
            cur_mileage = cursor.fetchone()
            description = "배송비 총 결제금액 마일리지 사용"
            use_type = 2
            result_history = m_payment.insert_account_mileage_history(
                e_id,
                mileage,
                int(cur_mileage[0]),
                description,
                use_type,
                order_id
            )
            if result_history is False:
                raise Exception('Fail to left mileage history')
            return jsonify({'result_code':1})
        else:
            logger.debug("===== No match order_status To Payment =====")
            return jsonify({'result_code':0})

    except Exception as e:
        con.rollback()
        con.close()
        logger.debug(e)
        logger.debug("===== Free price_estimated Payment Failed =====")
        return jsonify({'result_code':0})



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
