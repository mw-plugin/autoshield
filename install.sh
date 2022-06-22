#!/bin/bash
PATH=/www/server/panel/pyenv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

#配置插件安装目录
curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

install_tmp=${rootPath}/tmp/mw_install.pl

#安装
Install()
{
	
	echo '正在安装...'
	#==================================================================

	python3 -m pip install requests
	python3 -m pip install psutil

	#创建初始文件
	mkdir -p $serverPath/autoshield
	echo '2.0.1' > $serverPath/autoshield/version.pl
	ln -s $serverPath/mdserver-web/plugins/autoshield/autoshield.py $serverPath/autoshield/autoshield.py
	ln -s $serverPath/mdserver-web/plugins/autoshield/serviced.py $serverPath/autoshield/serviced.py

	mkdir $serverPath/autoshield/config
	mkdir $serverPath/autoshield/config/dns
	mkdir $serverPath/autoshield/log
	
	python3 $serverPath/autoshield/serviced.py
	systemctl daemon-reload
	systemctl enable autoshield
	#依赖安装结束
	#==================================================================

	echo '================================================'
	echo '安装完成'
}

#卸载
Uninstall()
{
	rm -rf $serverPath/autoshield
	rm -rf /lib/systemd/system/autoshield.service
	systemctl daemon-reload
	echo "Uninstall completed" > $install_tmp
}

#操作判断
if [ "${1}" == 'install' ];then
	Install
else
	Uninstall
fi
