import json
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import unquote
from PIL import Image
import datetime
import time
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from pypinyin import lazy_pinyin
import stations_info


class GrabTicket(object):
    """12306抢票系统"""

    # 禁用安全请求警告
    urllib3.disable_warnings(InsecureRequestWarning)

    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko)\
         Chrome/62.0.3202.89 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept-Language": "zh-CN, zh; q=0.9",
    }

    session = requests.session()
    session.headers = headers

    def __init__(self):
        self.D = None
        self.M = []
        self.ay = []
        self.id_type_code = ''
        self.ticket_submit_order = self.ticket_submit_order()
        self.init_seatTypes = {}
        self.defaultTicketTypes = {}
        self.init_cardTypes = {}
        self.ticket_seat_codeMap = {}
        self.ticketInfoForPassengerForm = {}
        self.orderRequestDTO = {}
        self.limit_tickets = []
        self.current_train = {}  # 当前选择的车次

    def get_captcha(self):
        """获取验证码图片,并保存到本地"""
        print("进入get_captcha，获取并保存验证码图片\n")
        r = str(random.random())
        url = 'https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&' + r
        res = self.session.get(url, verify=False)
        with open('static/captcha.png', 'wb') as fo:
            fo.write(res.content)
        self.check_captcha()

    def check_captcha(self):
        """校验验证码"""
        print("进入check_acotcha，校验验证码\n")
        img = Image.open('static/captcha.png')
        img.show()

        code = input("请输入验证码,从左至右从上至下为1到8，用英文逗号隔开：")

        captcha_coordinate = ['35,35', '105,35', '175,35', '245,35', '35,105', '105,105', '175,105', '245,105']
        # 取每个验证码中点的坐标,12306是通过坐标验证的
        solution_list = code.split(',')
        print('用户输入验证码位置：', solution_list)
        solution_coordinate_list = []
        for item in solution_list:
            solution_coordinate_list.append(captcha_coordinate[int(item) - 1])
        solution_coordinate_str = ','.join(solution_coordinate_list)

        url = 'https://kyfw.12306.cn/passport/captcha/captcha-check'
        data = {
            'answer': solution_coordinate_str,
            'login_site': 'E',
            'rand': 'sjrand'
        }
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        # print(msg['result_message'])

        if msg['result_code'] == '4':
            self.start_login()
        else:
            self.get_captcha()

    def start_login(self):
        """开始登录"""
        print("进入start_login，开始登录\n")
        url = 'https://kyfw.12306.cn/passport/web/login'
        # username = input("请输入用户名：")
        # password = input("请输入密码：")
        username = input("请输入用户名")
        password = input("请输入密码")

        data = {
            "username": username,
            "password": password,
            "appid": 'otn'
        }

        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        # print('开始登录',msg)

        if msg['result_code'] == 0:
            self.check_login()
        else:
            print("用户名或密码错误，请重新登录")

    def check_login(self):
        """验证是否已经登录"""
        print("进入check_login，验证登录状态\n")
        url = 'https://kyfw.12306.cn/passport/web/auth/uamtk'
        data = {
            'appid': 'otn',
            'withCredentials': True
        }
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        if msg['result_code'] == 0:  # 已经登录
            if msg['apptk']:
                tk = msg['apptk']
            else:
                tk = msg['newapptk']
            if tk:
                self.uam_pass_wort(tk)
            else:
                print('token验证失败')
        else:
            print(msg['result_message'])

    def uam_pass_wort(self, tk):
        """ 验证token，获取用户名 """
        print("进入uam_pass_wort，验证token并获取用户名")
        url = 'https://kyfw.12306.cn/otn/uamauthclient'
        data = {
            'tk': tk
        }
        res = self.session.post(url, data=data, verify=False)
        # print(res.text)
        msg = res.json()
        if msg['result_code'] == 0:  # 验证通过
            self.get_left_ticket()
        else:
            print(msg['result_message'])

    def get_left_ticket(self):
        """获取余票"""
        print("进入get_left_ticket，获取余票")
        d = input('请输入出发日(如:2017-11-07):')

        if not re.match(r'\d{4}(-\d{2}){2}', d):
            print('日期格式错误')
            self.get_left_ticket()

        f = input('请输入出发地（汉字）:')
        t = input('请输入目的地（汉字）:')

        from_station = stations_info.stations_info.get(self.get_pinyin(f))
        to_station = stations_info.stations_info.get(self.get_pinyin(t))
        print(from_station, to_station)

        cookies = {
            "_jc_save_fromDate": d,
            "_jc_save_fromStation": from_station,
            "_jc_save_toDate": d,
            "_jc_save_toStation": to_station,
            "_jc_save_wfdc_flag": "dc",
        }

        requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)

        url = 'https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date=' + d + '&leftTicketDTO.from_station=' \
              + from_station + '&leftTicketDTO.to_station=' + to_station + '&purpose_codes=ADULT'
        res = self.session.get(url, verify=False)
        msg = res.json()
        print(1111111111, json.dumps(msg, sort_keys=True, indent=2, ensure_ascii=False))
        results = msg['data']['result']

        info = []
        for result in results:
            cols = result.split('|')
            if cols[0]:
                train = {}
                train['车次'] = cols[3]
                train['出发站'] = f
                train['到达站'] = t
                train['出发时间'] = cols[8]
                train['到达时间'] = cols[9]
                train['历时'] = cols[10]
                train['当日到达'] = cols[11]
                train['出发日'] = cols[13]
                train['商务座特等座'] = cols[32]
                train['一等座'] = cols[31]
                train['二等座'] = cols[30]
                train['高级软卧'] = cols[21]
                train['软卧'] = cols[23]
                train['动卧'] = cols[33]
                train['硬卧'] = cols[28]
                train['软座'] = cols[24]
                train['硬座'] = cols[29]
                train['无座'] = cols[26]
                train['其它'] = cols[22]
                train['secretStr'] = cols[0]
                info.append(train)

            for i, c in enumerate(cols):
                if i == 0 or i == 12:
                    continue
                print('%s:\t%s' % (i + 1, c))
                if (i + 1) % 9 == 0:
                    print('')
            print('')

        k = input('开始预订，请输入%d - %d之间的数字来选择车次：' % (1, len(info)))
        if not k.isdigit():
            print('请输入数值类型！')
        k = int(k)
        if k < 1 or k > len(info):
            print('输入有误!请重新输入')
        self.current_train = info[k - 1]
        self.submit_order(from_station, to_station)

    def submit_order(self, _f, _t):
        """提交预订单"""
        print("进入submit_order，提交预订单")
        url = 'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
        date_str = str(self.current_train["出发日"])
        print("出发日", date_str)
        train_date = self.str2date_format1(date_str)
        back_date = train_date
        data = {
            "secretStr": unquote(self.current_train['secretStr']),
            "train_date": train_date,
            "back_train_date": back_date,
            "tour_flag": "dc",
            "purpose_codes": "ADULT",
            "query_from_station_name": _f,
            "query_to_station_name": _t,
            "undefined": None
        }

        if not self.check_user():
            return False

        res = self.session.post(url,
                                data=data,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                verify=False)

        msg = res.json()
        print('预订单', msg)
        if msg['status']:
            if msg['data'] == 'Y':
                print('您选择的列车距开车时间很近了，\n请确保有足够的时间抵达车站，\n并办理换取纸质车票、安全检查、\
                实名制验证及检票等手续，以免耽误您的旅行。')
            # 跳转到确认乘客页面
            return self.confirm_passenger()
        else:
            # print(msg['messages'])
            return False

    def check_user(self):
        """验证用户登录状态"""
        print("进入check_user，验证用户登录状态")
        url = 'https://kyfw.12306.cn/otn/login/checkUser'
        data = {'_json_att': ''}
        res = self.session.post(url,
                                data=data,
                                verify=False,
                                headers={'If-Modified-Since': '0',
                                         'Cache-Control': 'no-cache',
                                         'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
        msg = res.json()
        print('验证用户', msg)
        if msg['status']:
            if msg['data']['flag']:
                return True
        else:
            print(msg['messages'])
            return False

    def confirm_passenger(self):
        """确认坐席和乘客信息"""
        print("进入confirm_passenger，确认坐席和乘客信息")
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
        res = self.session.get(url, verify=False)
        # print(res.text)
        token_pattern = r'var globalRepeatSubmitToken = \'(.*?)\';'
        token = re.findall(token_pattern, res.text)[0]
        print("这是token", token)
        self.get_common_data(res.text)

        train_info = self.ticketInfoForPassengerForm['queryLeftTicketRequestDTO']
        # left_ticket_str = self.ticketInfoForPassengerForm['leftTicketStr']
        train_date = train_info['train_date']

        # 得到星期几
        weekday = self.get_week(
            datetime.date(int(train_date[:4]), int(train_date[4:6]), int(train_date[6:8])))

        print("列车信息(以下余票信息仅供参考)：\n")
        print(self.str2date_format1(train_date)
              + '（' + weekday + '） '
              + train_info['station_train_code']
              + '次 '
              + train_info['from_station_name']
              + '站（'
              + train_info['start_time']
              + '开）'
              + "--"
              + train_info['to_station_name']
              + '站（'
              + train_info['arrive_time'] + '到）')
        print('-----------------------------------------------------------------')
        left_details = self.ticketInfoForPassengerForm['leftDetails']

        seat_map = {}
        seat_index = 0
        for det in left_details:
            seat_index = seat_index + 1
            print(seat_index, ':', det, '\n')
            seat_map[str(seat_index)] = det
        seat_info = input('选择坐席，请输入%d - %d之间的数字来选择座位：' % (1, seat_index))
        user_select_seat = seat_map[seat_info]
        print("用户选择的坐席", user_select_seat)
        user_select_seat = user_select_seat.replace("有票", "")
        print("这是confirm_passenger的left_details", left_details)
        # 获取乘客信息
        normal_passengers = self.get_passengers(token)
        if normal_passengers:
            print("乘客信息：\n")
            for i, passenger in enumerate(normal_passengers):
                print(str(i + 1) + '. ' + passenger['passenger_name'])

        k = input('选择乘客，请输入%d - %d之间的数字来选择乘车人：' % (1, len(normal_passengers)))
        if not k.isdigit():
            print('请输入数值类型！')
        k = int(k)
        if k < 1 or k > len(normal_passengers):
            print('输入有误!请重新输入')
        person = normal_passengers[k - 1]

        af = 'normalPassenger_0'
        args = [af, '0', user_select_seat, '1', '成人票', person['passenger_name'], person['passenger_id_type_code'],
                person['passenger_id_type_name'], person['passenger_id_no'], person['mobile_no'], '',
                self.ticketInfoForPassengerForm['tour_flag'], True, person['passenger_type'], False, None]

        self.add_limit_tickets(*args)

        # self.update_save_passenger_info(res.text)
        flag = self.check_order_info(token)  # 验证订单

        if flag:  # 验证成功
            print("验证成功")
            return self.get_queue_count(token)  # 获取队列计数
        else:
            return False

    def get_common_data(self, text_str):
        """获取订单确认页面里面的通用数据,初始化信息"""
        print("进入get_common_data，获取通用数据")
        self.ticketInfoForPassengerForm = self.get_dict(r'var ticketInfoForPassengerForm=(.*?);', text_str)  # 车票信息
        self.init_seatTypes = self.get_dict(r'var init_seatTypes=(.*?);', text_str)  # 初始所有座位类型
        self.defaultTicketTypes = self.get_dict(r'var defaultTicketTypes=(.*?);', text_str)  # 默认车票类型
        self.init_cardTypes = self.get_dict(r'var init_cardTypes=(.*?);', text_str)  # 初始证件类型
        self.ticket_seat_codeMap = self.get_dict(r'var ticket_seat_codeMap=(.*?);', text_str)  # 车票座位代码地图
        self.orderRequestDTO = self.get_dict(r'var orderRequestDTO=(.*?);', text_str)  # 订单请求DTO
        self.id_type_code = re.findall(r'var id_type_code = \'(.*?)\'', text_str)[0]
        # print(json.dumps(self.ticketInfoForPassengerForm, sort_keys=True, indent=2, ensure_ascii=False))
        self.ticketType = self.get_position(self.ticket_seat_codeMap, self.defaultTicketTypes)

    @staticmethod
    def get_position(ticket_seat_codeMap, defaultTicketTypes):
        """获取所选座位"""
        print("进入position，获取所选座位")
        array = []
        for m in ticket_seat_codeMap:
            for t in defaultTicketTypes:
                if t['id'] == m:
                    array.append(t)
                    break
        return sorted(array, key=lambda k: t['id'])

    def get_passengers(self, token):
        """获取乘客信息"""
        print("进入get_passengers，获取乘客信息")
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
        data = {
            '_json_att': '',
            'REPEAT_SUBMIT_OKEN': token
        }
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        if msg['status'] and msg['data']['isExist']:
            self.M = msg['data']['dj_passengers']
            self.ay = msg['data']['normal_passengers']
            return msg['data']['normal_passengers']
        else:
            print("没有获取到乘客信息")
            return None

    def add_limit_tickets(self, *args):
        """获取限购车票的列表"""
        print("进入add_limit_tickets，获取限购信息")
        if len(self.limit_tickets) >= 5:
            print("最多只能购买 5 张车票")
        ticket_type = self.get_ticket_type(args[13], args[6], args[3])
        print("座位类型========", args[1])
        d = {
            'only_id': args[0],
            # 'seat_type': args[1],  # 座位类型
            'seat_type': "O",  # 座位类型   todo: seat_type对应
            'seat_type_name': args[2],  # 座位类型名称
            'ticket_type': args[3],  # 车票类型
            'ticket_type_name': args[4],  # 车票类型名称
            'name': args[5],  # 乘客名字
            'id_type': args[6],  # 证件类型
            'id_type_name': args[7],  # 证件类型名称
            'id_no': args[8],  # 证件编号
            'phone_no': args[9],  # 手机号
            'passenger_type': args[13],  # 乘客类型
            'seatTypes': self.ticket_seat_codeMap[self.ticket_submit_order['ticket_type']['adult'] \
                if ticket_type == '' else ticket_type],  # 座位所有类型
            'ticketTypes': self.ticketType,
            'cardTypes': self.init_cardTypes,  # 初始所有证件类型
            'save_status': args[10],  # 保存状态
            'tour_flag': args[11],  # 旅行标识 单程或返程
            'isDisabled': True if args[13] == self.ticket_submit_order['ticket_type']['student'] else args[12],  #
            'isDefaultUsed': False,
            'checkboxStatus': args[14],
            'isAccompanyChild': args[15] if args[15] else None
        }
        print("这是add_limit_tickets-----------，", d)
        self.limit_tickets.append(d)

    def check_order_info(self, token):
        """验证订单信息"""
        print("进入check_order_info，验证订单信息")
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
        data = {
            'cancel_flag': '2',
            'bed_level_order_num': '000000000000000000000000000000',
            'passengerTicketStr': self.get_passenger_tickets(),
            'oldPassengerStr': self.get_old_passengers(),
            'tour_flag': self.ticketInfoForPassengerForm['tour_flag'],
            'randCode': '',
            'whatsSelect': '1',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }
        print("这就是验证的data：\n", data)
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        print('check_order_info:', msg)

        if msg['status']:
            if msg['data']['submitStatus']:
                if 'get608Msg' not in msg['data'] or not msg['data']['get608Msg']:
                    return True
        else:
            print(msg['messages'])
            return False

    def get_queue_count(self, token):
        """获取队列计数"""
        print("进入get_queue_count，获取队列计数")
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'

        data = {
            'train_date': self.get_standard_time(
                datetime.datetime.fromtimestamp(int(self.orderRequestDTO['train_date']['time']) / 1000)),
            'train_no': self.orderRequestDTO['train_no'],
            'stationTrainCode': self.orderRequestDTO['station_train_code'],
            'seatType': self.limit_tickets[0]['seat_type'],
            'fromStationTelecode': self.orderRequestDTO['from_station_telecode'],
            'toStationTelecoe': self.orderRequestDTO['to_station_telecode'],
            'leftTicket': self.ticketInfoForPassengerForm['queryLeftTicketRequestDTO']['ypInfoDetail'],
            'purpose_codes': self.ticketInfoForPassengerForm['purpose_codes'],
            'train_location': self.ticketInfoForPassengerForm['train_location'],
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }
        print("get_queue_count的data--------", data)
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        print("获取队列计数的msg", msg)
        if msg['status']:
            return self.confirm_single_for_queue(token)
        else:
            print(msg['messages'])
            return False

    def confirm_single_for_queue(self, token):
        """确认队列单"""
        print("进入confirm_single_for_queue，确认队列")
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
        data = {
            'passengerTicketStr': self.get_passenger_tickets(),
            'oldPassengerStr': self.get_old_passengers(),
            'randCode': '',
            'purpose_codes': self.ticketInfoForPassengerForm['purpose_codes'],
            'key_check_isChange': self.ticketInfoForPassengerForm['key_check_isChange'],
            'leftTicketStr': self.ticketInfoForPassengerForm['leftTicketStr'],
            'train_location': self.ticketInfoForPassengerForm['train_location'],
            'choose_seats': '',
            'seatDetailType': '000',
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }
        res = self.session.post(url, data=data, verify=False)
        msg = json.loads(res.text)
        print("确认队列confirm_single_for_queue的msg", res.text)
        flag = False

        if msg['status']:
            if msg['data']['submitStatus']:
                time.sleep(2)
                flag = self.query_order_wait_time(token)
            else:
                print('出票失败！原因：' + msg['data']['errMsg'])

        else:
            print('订票失败！很抱歉！请重新订票')
        return flag

    def query_order_wait_time(self, token):
        """购票排队"""
        print("进入query_order_wait_time，购票排队")
        t = str(int(time.time() * 1000))
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=' + t \
              + '&tourFlag=' + self.ticketInfoForPassengerForm[
                  'tour_flag'] + '&_json_att=&REPEAT_SUBMIT_TOKEN=' + token
        res = self.session.get(url, verify=False)
        msg = res.json()
        print("query_order_wait_time的msg，", msg)

        if msg['data'] and msg['data']['queryOrderWaitTimeStatus']:
            waitObj = msg['data']
            if waitObj['waitTime'] != -100 and waitObj['waitTime'] != -1:
                if waitObj['waitTime'] == -2:
                    print("在排队")
                    print(waitObj['msg'])
                    return False
                else:
                    print("开始休眠三秒")
                    time.sleep(3)
                    self.query_order_wait_time(token)
            else:
                return self.finish_method(waitObj['tourFlag'], waitObj['waitTime'], waitObj, token)
        else:
            return False

    def finish_method(self, tour_flag, wait_time, wait_obj, token):
        """订单完成"""
        print("进入finish_method，完成订单")
        url = ''
        if wait_time == -1 or wait_time == -100:
            if tour_flag == self.ticket_submit_order['tour_flag']['dc']:
                url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
            elif tour_flag == self.ticket_submit_order['tour_flag']['wc']:
                url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForWcQueue'
            elif tour_flag == self.ticket_submit_order['tour_flag']['fc']:
                url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForFcQueue'
            elif tour_flag == self.ticket_submit_order['tour_flag']['gc']:
                url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForGcQueue'
            data = {
                'orderSequence_no': wait_obj['orderId'],
                '_json_att': '',
                'REPEAT_SUBMIT_TOKEN': token
            }
            res = self.session.post(url, data=data, verify=False)
            msg = res.json()
            if msg['status']:
                if msg['data']['submitStatus']:
                    self.ots_redirect()
                    return True
                else:
                    print(msg['data']['errMsg'])
                    return False

    def ots_redirect(self):
        """车票信息"""
        print("进入ots_redirect，获取车票信息")
        t = str(int(time.time() * 1000))
        url = 'https://kyfw.12306.cn/otn//payOrder/init?random=' + t
        res = self.session.post(url, verify=False)
        pattern = r'var parOrderDTOJson = \'(.*?)\';'
        parOrderDTOStr = re.findall(pattern, res.text)[0].replace(r'\"', '"')
        parOrderDTOJson = json.loads(parOrderDTOStr)
        pattern2 = r'var passangerTicketList = (.*?);'
        passangerTicketListStr = re.findall(pattern2, res.text)[0].replace(r'null', "''").replace(r"'", '"')
        passangerTicketListJson = json.loads(passangerTicketListStr)
        pattern3 = r'var insInfos = (.*?);'
        insInfosStr = re.findall(pattern3, res.text)[0].replace(r'null', "''").replace(r"'", '"')
        insInfosJson = json.loads(insInfosStr)
        print("车票信息：\n")
        print(json.dumps(parOrderDTOJson, sort_keys=True, indent=2, ensure_ascii=False))
        print(json.dumps(passangerTicketListJson, sort_keys=True, indent=2, ensure_ascii=False))
        print(json.dumps(insInfosJson, sort_keys=True, indent=2, ensure_ascii=False))

    @staticmethod
    def get_dict(pattern, text):
        """匹配字符串"""
        print("进入get_dict，正则匹配字符串")
        _str = re.findall(pattern, text)[0]
        _str = _str.replace('\'', '"')
        return json.loads(_str)

    def update_save_passenger_info(self, html):
        """更新乘客信息"""
        print("进入update_save_passenger_info，更新乘客信息")
        bs = BeautifulSoup(html, features='lxml')
        del_id = 'del_1_normalPassenger_0'
        for lt in self.limit_tickets:
            if lt['only_id'] == (del_id.split('_')[2] + '_' + del_id.split('_')[3]):
                ac = del_id.split('_')[1]
                print("更新乘客信息", ac)
                seat_type_obj = bs.find('select', id='seatType_' + ac)  # todo：None
                print("座位信息，初：", seat_type_obj)
                seat_type = seat_type_obj.select('option[selected="selected"]')
                print("--------------------------------------------------------")
                print(seat_type)
                break

    # def Y(self):
    #     if len(self.limit_tickets) < 1:
    #         return len(self.limit_tickets)
    #     else:
    #         b = 0
    #         for a in self.limit_tickets:
    #             z = int(a['only_id'].split('_')[1])
    #             if z > b:
    #                 b = z
    #         return b + 1

    @staticmethod
    def get_week(date):
        """根据日期获取当前是星期几"""
        weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return weekday[date.weekday()]

    @staticmethod
    def get_standard_time(date):
        """获取标准时间"""
        return date.strftime('%a %b %d %Y %H:%M:%S ') + 'GMT+0800 (中国标准时间)'

    def get_passenger_tickets(self):
        _str = ''
        for v in self.limit_tickets:
            av = v['seat_type'] + ',0,' + v['ticket_type'] + ',' + v['name'] + ',' \
                 + v['id_type'] + ',' + v['id_no'] + ',' + v['phone_no'] + ',' \
                 + 'N' if v['save_status'] == '' else 'Y'
            _str += av + '_'
            return _str[:len(_str) - 1]

    def get_old_passengers(self):
        _str = ''
        for d in self.limit_tickets:
            if self.ticketInfoForPassengerForm['tour_flag'] == self.ticket_submit_order['tour_flag']['fc'] \
                    or self.ticketInfoForPassengerForm['tour_flag'] == self.ticket_submit_order['tour_flag']['gc']:
                a = d['name'] + ',' + a['id_type'] + ',' + a['id_no'] + ',' + a['passenger_type']
                _str += a + '_'
            else:
                if 'djPassenger_' in d['only_id']:
                    b = d['only_id'].split('_')[1]
                    a = self.M[b]['passenger_name'] + ',' + self.M[b]['passenger_id_type_code'] + ',' + \
                        self.M[b]['passenger_id_no'] + ',' + self.M[b]['passenger_type']
                    _str += a + '_'
                else:
                    if 'normalPassenger' in d['only_id']:
                        b = int(d['only_id'].split('_')[1])
                        a = self.ay[b]['passenger_name'] + ',' + self.ay[b]['passenger_id_type_code'] + ',' + \
                            self.ay[b]['passenger_id_no'] + ',' + self.ay[b]['passenger_type']
                        _str += a + '_'
                    else:
                        _str += '_ '
        return _str

    def get_ticket_type(self, t1, t2, t3):
        print("进入get_ticket_type，获取车票类型")
        for v in self.ticket_submit_order['passenger_type'].values():
            if t1 == v:
                t0 = v
            else:
                t0 = ""
        if self.ticketInfoForPassengerForm['purpose_codes'] == self.ticket_submit_order['ticket_query_flag'] \
                ['query_student']:
            return self.ticket_submit_order['ticket_type']['student']
        else:
            if t1 == self.ticket_submit_order['passenger_type']['disability']:
                t4 = self.id_type_code
                if t4 != self.ticket_submit_order['passenger_card_type']['two'] or \
                        t2 != self.ticket_submit_order['passenger_card_type']['two']:
                    return self.ticket_submit_order['ticket_type']['adult']
                else:
                    return t0
            else:
                return (self.ticket_submit_order['ticket_type']['adult'] if t3 == '' else t3) if t0 == '' else t0

    @staticmethod
    def ticket_submit_order():
        """获取车票提交订单信息"""
        print("进入ticket_submit_order，获取车票提交订单信息")
        tso = json.load(open('ticket_submit_order.json', 'r'), encoding='utf-8')
        return tso

    @staticmethod
    def str2date_format1(date_str):
        """字符串转日期格式 yyyy-MM-dd"""
        l = list(date_str)
        l.insert(4, '-')
        l.insert(-2, '-')
        return ''.join(l)

    # def get_pass_code(self):
    #     r = str(random.random())
    #     url = 'https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=passenger&rand=randp&' + r
    #     res = self.session.get(url, verify=False)
    #     print(res.text)
    #     return True

    def get_left_ticket_log(self, d, f, t):
        print("进入get_left_ticket_log")
        url = 'https://kyfw.12306.cn/otn/leftTicket/log?leftTicketDTO.train_date=' + d + \
              '&leftTicketDTO.from_station=' + f + '&leftTicketDTO.to_station=' + t + '&purpose_codes=ADULT'
        res = self.session.get(url, verify=False)
        msg = res.json()
        print(msg)
        if msg['status'] and msg['validateMessagesShowId'] == '_validatorMessage':
            return True
        else:
            print(msg)
        return False

    @staticmethod
    def get_pinyin(arg):
        """将汉字变为拼音"""
        str = ''
        for item in lazy_pinyin(arg):
            str += item
        return str

    def cancel_no_complete_order(self, sequence_no):
        """取消未完成的订单"""
        print("进入cancel_no_complete_order，取消未完成的订单")
        url = 'https://kyfw.12306.cn/otn/queryOrder/cancelNoCompleteMyOrder'
        data = {
            'sequence_no': sequence_no,
            'cancel_flag': '',
            '_json_att': ''
        }
        res = self.session.post(url, data=data, verify=False)
        msg = res.json()
        print(msg)
        if msg['status'] and msg['data']['existError'] == 'N':
            print("取消订单成功！")

    def index(self):
        """ 入口 """
        url = 'https://kyfw.12306.cn/otn/login/init'  # 验证码页面
        self.session.get(url, verify=False)
        self.get_captcha()


if __name__ == '__main__':
    g = GrabTicket()
    g.index()
    # g.get_left_ticket()
