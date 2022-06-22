import os
import sys

sys.path.append("/www/server/mdserver-web/class/core")
import mw

def getPluginName():
    return 'autoshield'

def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()

def getInitdConfTpl():
    path = getPluginDir() + "/init.d/autoshield.tpl"
    return path

def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()

def contentReplace(content):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    return content

if __name__ == "__main__":    
    file_tpl = getInitdConfTpl()
    service_path = mw.getServerDir()

    initD_path = getServerDir() + '/init.d'
    if not os.path.exists(initD_path):
        os.mkdir(initD_path)
    file_bin = initD_path + '/' + getPluginName()

    if not os.path.exists(file_bin):
        content = mw.readFile(file_tpl)
        content = contentReplace(content)
        mw.writeFile(file_bin, content)
        mw.execShell('chmod +x ' + file_bin)

    # conf_bin = getConf()
    # if not os.path.exists(conf_bin):
    #     mw.execShell('mkdir -p ' + getServerDir() + '/custom/conf')
    #     conf_tpl = getConfTpl()
    #     content = mw.readFile(conf_tpl)
    #     content = contentReplace(content)
    #     mw.writeFile(conf_bin, content)

    # systemd
    systemDir = '/lib/systemd/system'
    systemService = systemDir + '/autoshield.service'
    systemServiceTpl = getPluginDir() + '/init.d/autoshield.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        service_path = mw.getServerDir()
        se_content = mw.readFile(systemServiceTpl)
        se_content = se_content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, se_content)

    log_path = getServerDir() + '/log'
    if not os.path.exists(log_path):
        os.mkdir(log_path)