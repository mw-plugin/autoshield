#!/www/server/mdserver-web/bin/python
# coding: utf-8

# @Descript cloudflare_autoshield <cloudflare自动开盾>
# @Version 2.0.1
# @Author xcsoft<contact@xcsoft.top>
# @Date 2021 11 23
# @Last Edit Date 2022 06 22

import os
import sys
import json
import requests
import psutil

sys.path.append("/www/server/mdserver-web/class/core")
import mw

PLUGIN_NAME = 'autoshield'
FIREWALL_SERVICE_NAME = 'autoshield.py'
PLUGIN_PATH = "/www/server/{}/".format(PLUGIN_NAME)
FIREWALL_SERVICE_PATH = PLUGIN_PATH + FIREWALL_SERVICE_NAME

SETTING_FILE_PATH = PLUGIN_PATH + 'config/setting.json'  # setting文件路径
SAFE_FILE_PATH = PLUGIN_PATH + 'config/safe.json'  # safe文件路径
DOMAIN_FILE_PATH = PLUGIN_PATH + 'config/domain.json'  # 用户域名temp文件路径
DOMAIN_DNS_BASE_PATH = PLUGIN_PATH + 'config/dns/'  # 用户域名temp文件路径

PER_PAGE = 200  # 获取的域名个数 值应该在1到1000之间

def status():
    data = mw.execShell("ps -ef | grep autoshield.py | grep -v grep | awk '{print $2}'")
    if data[0] == '':
        return 'stop'
    return 'start'


# 获取服务运行状态
def get_status():
    data = mw.execShell("ps -ef | grep autoshield.py | grep -v grep | awk '{print $2}'")
    runStatus = True
    if data[0] == '':
        runStatus = False
    return __out(data={'runStatus': runStatus})


# 获取 cloudflare key & email
def get_setting():
    default = {
        'email': "",
        'cfkey': "",
    }
    if not os.path.exists(SETTING_FILE_PATH):
        mw.writeFile(SETTING_FILE_PATH, json.dumps(default))
    try:
        data = json.loads(mw.readFile(SETTING_FILE_PATH))
        default = {
            'key': data['key'] if data['key'] else '',
            'email': data['email'] if data['email'] else '',
        }
    except:
        mw.writeFile(SETTING_FILE_PATH, json.dumps(default))

    return __out(data=default)


def get_domain():
    try:
        res = mw.readFile(DOMAIN_FILE_PATH)
        response = json.loads(res)
        data = {}
        for k, v in response['domains'].items():
            data[k] = {
                "id": v['id'],
                "security": __transform_mode(v['security']),
                "status": v['status']
            }
        return __out(data=data)
    except:
        return __out(False, "请先配置密钥信息")


# 获取防御等级
def get_safe():
    _safeLoad = __getSafeLoad()['safe_load']
    default = {
        "wait": 300,  # 负载恢复后的等待周期
        "sleep": 5,  # 检测周期
        "check": 30,  # 持续监测时间
        "load": _safeLoad,  # 安全负载
    }
    if not os.path.exists(SAFE_FILE_PATH):
        mw.writeFile(SAFE_FILE_PATH, json.dumps(default))

    try:
        data = json.loads(mw.readFile(SAFE_FILE_PATH))
        result = {
            "wait": data['wait'] if data['wait'] else 300,
            "sleep": data['sleep'] if data['sleep'] else 5,
            "check": data['check'] if data['check'] else 30,
            "load": data['load'] if data['load'] else _safeLoad,
        }
    except:
        mw.writeFile(SAFE_FILE_PATH, json.dumps(default))
        result = default

    return __out(data=result)


# 启动服务
def start():
    mw.execShell("systemctl start autoshield")
    return __out(True)


# 停止服务
def stop():
    mw.execShell("systemctl stop autoshield")
    return __out(True)


# 重启服务
def restart():
    mw.execShell("systemctl restart autoshield")
    return __out(True)


# 设置cloudflare key & email
def set_setting():
    args = __getArgs()
    email = args['email']
    key = args['key']
    if not email or not key:
        return __out(False, "", {'success': False, 'msg': '必填项不能为空'})

    mw.writeFile(SETTING_FILE_PATH, json.dumps({
        'email': email,
        'key': key
    }))
    return __out(True)


# 设置 防护属性
def set_safe():
    args = __getArgs()
    check = args['check']
    wait = args['wait']
    sleep = args['sleep']
    load = args['load']
    if not check or not wait or not sleep or not load:
        return __out(False, "必填项不能为空")
    if int(check) <= 0 or int(wait) <= 0 or int(sleep) <= 0 or float(load) <= 0:
        return __out(False, "数值必须为大于0的整数")
    mw.writeFile(SAFE_FILE_PATH, json.dumps({
        "wait": int(wait),  # 负载恢复后的等待周期
        "sleep": int(sleep),  # 检测周期
        "check": int(check),  # 持续监测时间
        "load": round(float(load), 2),
    }))
    return __out()


# 设置域名security mode
def set_domain_security():
    args = __getArgs()
    id = args['id']
    mode = args['mode']
    domainName = __getDomainNameById(id)
    response = Cloudflare().setDomainMode(domainId=id, mode=mode)
    if response['success']:
        data = json.loads(mw.readFile(DOMAIN_FILE_PATH))
        data['domains'][domainName]['security'] = mode
        mw.writeFile(
            DOMAIN_FILE_PATH,
            json.dumps(data)
        )
        mw.writeLog(
            PLUGIN_NAME,
            '设置域名[{}]的防御等级为[{}]'.format(
                domainName, __transform_mode(mode))
        )
        return __out(data = {
            "mode_name": __transform_mode(mode)
        })
    else:
        mw.writeLog(
            PLUGIN_NAME,
            '设置域名[{}]的防御等级为[{}]时出错: {}'.format(
                domainName, mode, response['errors'])
        )
    return __out(False)


# 设置域名是否自动开盾
def set_domain_status():
    args = __getArgs()
    domainName = args['domainName']
    res = json.loads(mw.readFile(DOMAIN_FILE_PATH))
    res['domains'][domainName]['status'] = not res['domains'][domainName]['status']
    mw.writeFile(DOMAIN_FILE_PATH, json.dumps(res))
    return __out()


# 刷新域名列表
def refresh_domain():
    response = Cloudflare().getDomain()
    if response['success']:
        # 获取成功
        count = response['result_info']['count']  # 域名数量
        result = response['result']  # 域名信息

        data = {}  # 初始化data
        index = []  # 域名索引
        for v in result:
            data[v['name']] = {
                'id': v['id'],
                'security': "unknow",
                'status': True
            }
            mw.writeFile(DOMAIN_DNS_BASE_PATH + v['name'] + '.json',"{}")
            index.append(v['name'])
        res = {
            'count': count,
            'domains': data,
            'index': index
        }
        mw.writeFile(DOMAIN_FILE_PATH, json.dumps(res))
        return __out(data = {"count": count})
    # 获取失败
    mw.writeLog(
        PLUGIN_NAME,
        "登录时遇到错误 > " + json.dumps(response['errors'])
    )
    return __out(False, "邮箱或密钥错误")


# 刷新所有域名的防护等级
def refresh_domain_security():
    domainList = json.loads(mw.readFile(DOMAIN_FILE_PATH))
    for domainName, v in domainList['domains'].items():
        domainId = v['id']  # 域名信息
        domainInfo = Cloudflare().getSecurity(domainId)
        if domainInfo['success']:  # 获取成功
            domainList['domains'][domainName]['security'] = domainInfo['result']['value']
        else:
            mw.writeLog(
                PLUGIN_NAME,
                '获取域名{}防御等级时出现错误 > {}'.format(
                    domainName, json.dumps(domainInfo['errors']))
            )
    mw.writeFile(DOMAIN_FILE_PATH, json.dumps(domainList))
    return __out()


# 获取安全负载
def get_safe_load():
    return __out(True, "", __getSafeLoad())

# 转换mode 名称
def __transform_mode(mode):
    if mode == 'low':
        return '低'
    elif mode == 'medium':
        return '中'
    elif mode == 'high':
        return '高'
    elif mode == 'under_attack':
        return '开盾'
    elif mode == 'essentially_off':
        return '本质上为关'
    else:
        return '未知'


# 通过域名ID获取域名名称
def __getDomainNameById(id):
    res = json.loads(mw.readFile(DOMAIN_FILE_PATH))
    for k, v in res['domains'].items():
        if v['id'] == id:
            return k


def __getSafeLoad():
    cpuCount = psutil.cpu_count()
    safe_load = cpuCount * 1.75
    return {'cpu_count': cpuCount, 'safe_load': safe_load}

def __out(success: bool = True, msg: str = "ok", data: dict = {}):
    return json.dumps({
        "success": success,
        "msg": msg,
        "data": data
    })


def __getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


class Cloudflare:
    __base_url = "https://api.cloudflare.com/client/v4/"

    def __init__(self):
        data = json.loads(mw.readFile(SETTING_FILE_PATH))
        self.key = data['key'] if data['key'] else ''
        self.email = data['email'] if data['email'] else ''

    def getDomainDns(self, domainId):
        response = self.__get('zones/{}/dns_records'.format(domainId), {})
        return response

    # 获取用户域名
    def getDomain(self):
        response = self.__get('zones', {
            'per_page': PER_PAGE  # 拉满
        })
        return response

    # 获取域名防御等级
    def getSecurity(self, domainId):
        response = self.__get(
            'zones/{}/settings/security_level'.format(domainId),
            {}
        )
        return response

    def setDomainMode(self, domainId, mode):
        response = self.__patch(
            'zones/{}/settings/security_level'.format(domainId),
            {'value': mode}
        )
        return response

    def __patch(self, url, data):
        response = requests.patch(
            self.__base_url + url,
            data=json.dumps(data),
            headers={
                "Content-Type": "application/json",
                "X-Auth-Key": self.key,
                "X-Auth-Email": self.email,
            }
        )
        return response.json()

    def __post(self, url, data):
        response = requests.post(
            self.__base_url + url,
            data=json.dumps(data),
            headers={
                "Content-Type": "application/json",
                "X-Auth-Key": self.key,
                "X-Auth-Email": self.email,
            }
        )
        return response.json()

    def __get(self, url, param):
        response = requests.get(
            self.__base_url + url,
            params=param,
            headers={
                "X-Auth-Key": self.key,
                "X-Auth-Email": self.email,
            }
        )
        return response.json()


if __name__ == "__main__":
    config_path = PLUGIN_PATH + 'config/'
    dns_path = PLUGIN_PATH + 'config/dns/'
    if not os.path.isdir(config_path):
        os.makedirs(config_path, 755)
    if not os.path.isdir(dns_path):
        os.makedirs(dns_path, 755)
    pass

    func = sys.argv[1]
    if func == "start":
        print(start())
    elif func == "stop":
        print(stop())
    elif func == "restart":
        print(restart())

    elif func == 'status':
        print(status())
    elif func == 'get_status':
        print(get_status())
    elif func == "get_setting":
        print(get_setting())
    elif func == 'get_domain':
        print(get_domain())
    elif func == 'get_safe':
        print(get_safe())

    elif func == "set_setting":
        print(set_setting())
    elif func == "set_safe":
        print(set_safe())
    elif func == "set_domain_security":
        print(set_domain_security())
    elif func == "set_domain_status":
        print(set_domain_status())

    elif func == "refresh_domain":
        print(refresh_domain())
    elif func == "refresh_domain_security":
        print(refresh_domain_security())
    elif func == "get_safe_load":
        print(get_safe_load())

    else:
        print("unknown func")
