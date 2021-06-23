import base64
import json as JSON
import logging
import os
import re
import sys
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (QWidget, QLabel, QGridLayout, QLineEdit, QPushButton)

from logger import Logger


class GridLayout(QWidget):

    #日志文件
    __log = Logger("log.txt")

    #备份目录名称
    __backup = "backup"

    #配置文件名称
    __conf = "conf.txt"

    def __init__(self):
        super().__init__()

        #初始化界面
        self.initUI()

        #加载配置文件
        if os.path.exists(self.__conf) or os.path.isfile(self.__conf):
            f = open(self.__conf,mode="r")
            line = f.readline()
            if(len(line.strip()) != 0):
                #解码
                de = line.encode()
                de = base64.b16decode(de)
                de = base64.b64decode(de)
                de = bytes.decode(de,encoding='unicode-escape')

                list = de.split("|")
                self.joplinPort.setText(list[0])
                self.joplinToken.setText(list[1])
                self.giteeToken.setText(list[2])
                self.giteeOwner.setText(list[3])
                self.giteePath.setText(list[4])
                self.giteeRepo.setText(list[5])

                f.close()

    def initUI(self):

        #resize()方法调整窗口的大小。这离是250px宽150px高
        self.resize(500, 300)
        #move()方法移动窗口在屏幕上的位置到x = 300，y = 300坐标。
        self.move(300, 300)
        #设置窗口的标题
        self.setWindowTitle('Joplin更改gitee图床')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint|QtCore.Qt.WindowMinimizeButtonHint)

        layout = QGridLayout()
        #layout.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        layout.setSpacing(10)

        qLabel0 = QLabel("Joplin")
        layout.addWidget(qLabel0);

        qLabel1 = QLabel("Joplin 端口 (port):")
        layout.addWidget(qLabel1,1,0);

        self.joplinPort = QLineEdit();
        layout.addWidget(self.joplinPort,1,1);

        qLabel2 = QLabel("Joplin 令牌 (token):")
        layout.addWidget(qLabel2,2,0);

        self.joplinToken = QLineEdit();
        layout.addWidget(self.joplinToken,2,1);

        qLabel7 = QLabel("Gitee")
        layout.addWidget(qLabel7);

        qLabel3 = QLabel("Gitee 令牌 (token):")
        layout.addWidget(qLabel3,4,0);

        self.giteeToken = QLineEdit();
        layout.addWidget(self.giteeToken,4,1);

        qLabel4 = QLabel("Gitee 所有者 (owner):")
        layout.addWidget(qLabel4,5,0);

        self.giteeOwner = QLineEdit();
        layout.addWidget(self.giteeOwner,5,1);

        qLabel5 = QLabel("Gitee 仓库名称 (repo):")
        layout.addWidget(qLabel5,6,0);

        self.giteeRepo = QLineEdit();
        layout.addWidget(self.giteeRepo,6,1);

        qLabel6 = QLabel("Gitee 文件夹路径 (path):")
        layout.addWidget(qLabel6,7,0);

        self.giteePath = QLineEdit();
        layout.addWidget(self.giteePath,7,1);

        self.button = QPushButton("确认");
        self.button.clicked.connect(self.buttonClick);
        layout.addWidget(self.button);

        self.setLayout(layout);
        #显示在屏幕上
        self.show()

    def run(self, value):
        try:
            id = value.get("id");
            title = value.get("title");

            #根据id 查询笔记内容
            joplinUpdate = "http://127.0.0.1:{}/notes/{}?token={}".format(self.joplinPort.text(),id,self.joplinToken.text())
            joplinBody = joplinUpdate + "&fields=body"
            resp = requests.get(joplinBody,timeout=5)
            body = str(resp.json().get("body"))

            gitee = "https://gitee.com/" + self.list[3]
            #只匹配地址不为gitee的图片链接
            data = re.findall(r'!\[(.*)\]\(((?!' + gitee + ').*)\)',body)
            if(len(data) <= 0):
                return (0,title)

            #备份笔记 防止修改出错
            date = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            f = open(self.__backup + os.sep +title + "_" + date + ".md","w+")
            f.write(body)
            f.close();

            files = []
            for v in data:
                try:
                    #使用正则表达式查询 笔记内容中的 图片链接
                    addr = v[1];

                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"}

                    #获取网络图片并转为base64
                    picData = requests.get(addr,timeout=20,headers=headers)
                    if(picData.status_code != 200):
                        self.__log.logger.error(picData.content)
                        raise Exception("图片下载失败")

                    base = base64.b64encode(picData.content)
                    time_tup = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]

                    path = self.list[4] + "/" + time_tup + ".png"
                    files.append(path)

                    url = "https://gitee.com/api/v5/repos/{}/{}/contents/{}"
                    postUrl = url.format(self.list[3],self.list[5],path)
                    params = {"access_token": self.list[2], "owner": self.list[3], "repo": self.list[5], "path": path, "content": base, "message": "上传图片"}

                    #上传图片到Gitee 并返回图片地址
                    resp = requests.post(postUrl,data=params,timeout=20)
                    pic = resp.json().get("content").get("download_url")
                except Exception as e:
                    if len(files) != 0:
                        #如果请求失败 或者 获取不到数据 删除之前上传的文件
                        getUrl = url.format(self.list[3],self.list[5],self.list[4]) + "?access_token=" + self.list[2]
                        sha = requests.get(getUrl,timeout=20).json().get("sha")

                        params["sha"] = sha
                        for file in files:
                            params["path"] = file
                            requests.delete(postUrl,data=params,timeout=20)

                    raise Exception(e)
                else:
                    #把笔记中的图片链接替换为Gitee的图片链接
                    body = body.replace(addr, pic)


            params = {"body": body}
            #更新笔记
            resp = requests.put(joplinUpdate,data=JSON.dumps(params),timeout=5)

            return (1,title)
        except Exception as e:
            logging.exception(e)
            self.__log.logger.error(e)
            return (-1,title)

    def buttonClick(self):
        joplinPort = self.joplinPort.text().strip();
        joplinToken = self.joplinToken.text().strip();
        giteeToken = self.giteeToken.text().strip();
        giteeRepo = self.giteeRepo.text().strip();
        giteePath = self.giteePath.text().strip();
        giteeOwner = self.giteeOwner.text().strip();

        self.list = [joplinPort,joplinToken,giteeToken,giteeOwner,giteePath,giteeRepo]
        if(len(self.list[5]) == 0 or len(self.list[0]) == 0 or
                len(self.list[1]) == 0 or len(self.list[2]) == 0 or
                len(self.list[3]) == 0 or len(self.list[4]) == 0):
            QtWidgets.QMessageBox.warning(self, "警告", "数据不能为空", QtWidgets.QMessageBox.Cancel)
            return

        b = False
        try:
            #创建备份目录
            if not os.path.exists(self.__backup) or not os.path.isdir(self.__backup):
                os.mkdir(self.__backup)

            #用户数据写入配置文件
            f = open(self.__conf,mode="w+")
            en = self.list[0] + "|" + self.list[1] + "|" + self.list[2] + "|" + self.list[3] + "|" + self.list[4] + "|" + self.list[5]
            en = en.encode(encoding='unicode-escape')
            en = base64.b64encode(en)
            en = base64.b16encode(en)
            en = bytes.decode(en)
            f.write(en);
            f.close()

            self.__log.logger.info("----------------------------------------")

            #查询包含 /![] 的笔记
            joplinSearch = "http://127.0.0.1:{}//search?query=/![]&type=note&token={}".format(self.list[0],self.list[1])
            resp = requests.get(joplinSearch,timeout=5)

            #返回多个笔记的id
            data = resp.json().get("items")
            #使用线程池
            with ThreadPoolExecutor(max_workers=5) as executor:
                all_task = [executor.submit(self.run, (value)) for value in data]
                done_iter = futures.as_completed(all_task)

                for done in done_iter:
                    (code,title) = done.result();
                    if(code == 0):
                        self.__log.logger.info("笔记标题: " + title +  " 【忽略】")
                    if(code == 1):
                        self.__log.logger.info("笔记标题: " + title +  " 【完成】")
                    if(code == -1):
                        self.__log.logger.error("笔记标题: " + title +  " 【错误】")
                        b = True

        except Exception as e:
            logging.exception(e)
            self.__log.logger.error(e)
            QtWidgets.QMessageBox.warning(self, "警告", "处理出现异常，请查看日志！！", QtWidgets.QMessageBox.Cancel)
        else:
            if(b):
                QtWidgets.QMessageBox.warning(self, "警告", "处理出现异常，请查看日志！！", QtWidgets.QMessageBox.Cancel)
            else:
                QtWidgets.QMessageBox.warning(self, "提示", "处理完毕！！", QtWidgets.QMessageBox.Cancel)

if __name__ == '__main__':
    #每一pyqt5应用程序必须创建一个应用程序对象。sys.argv参数是一个列表，从命令行输入参数。
    app = QApplication(sys.argv)
    #QWidget部件是pyqt5所有用户界面对象的基类。他为QWidget提供默认构造函数。默认构造函数没有父类。
    w = GridLayout()
    sys.exit(app.exec_())