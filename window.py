import requests
import base64
import time
import json as JSON
import re;
import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (QWidget, QLabel, QGridLayout, QLineEdit, QPushButton)
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

from logger import Logger


class GridLayout(QWidget):

    def __init__(self):
        super().__init__()

        self.initUI()
        self.log = Logger("log.txt")

    def initUI(self):

        #resize()方法调整窗口的大小。这离是250px宽150px高
        self.resize(500, 300)
        #move()方法移动窗口在屏幕上的位置到x = 300，y = 300坐标。
        self.move(300, 300)
        #设置窗口的标题
        self.setWindowTitle('Joplin更改gitee图床')

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
            resp = requests.get(joplinBody)
            body = str(resp.json().get("body"))

            #只匹配地址不为gitee的图片链接
            data = re.findall(r'!\[(.*)\]\(((?!https://gitee.com).*)\)',body)
            if(len(data) <= 0):
                return (0,title)

            for v in data:
                #使用正则表达式查询 笔记内容中的 图片链接
                addr = v[1];

                #获取网络图片并转为base64
                base = base64.b64encode(requests.get(addr).content)
                time_tup = str(round(time.time() * 1000))

                path = self.giteePath.text() + "/" + time_tup + ".png"

                url = "https://gitee.com/api/v5/repos/{}/{}/contents/{}".format(self.giteeOwner.text(),self.giteeRepo.text(),path)
                params = {"access_token": self.giteeToken.text(), "owner": self.giteeOwner.text(), "repo": self.giteeRepo.text(), "path": path, "content": base, "message": "上传图片"}

                #上传图片到Gitee 并返回图片地址
                resp = requests.post(url,data=params)
                pic = resp.json().get("content").get("download_url")

                #把笔记中的图片链接替换为Gitee的图片链接
                body = body.replace(addr, pic)

            params = {"body": body}
            #更新笔记
            resp = requests.put(joplinUpdate,data=JSON.dumps(params))

            return (1,title)
        except Exception as e:
            logging.exception(e)
            self.log.logger.error(e)
            return (-1,title)

    def buttonClick(self):
        if(len(self.joplinToken.text().strip()) == 0 or len(self.joplinPort.text().strip()) == 0 or
                len(self.giteeToken.text().strip()) == 0 or len(self.giteeRepo.text().strip()) == 0 or
                len(self.giteePath.text().strip()) == 0 or len(self.giteeOwner.text().strip()) == 0):
            QtWidgets.QMessageBox.warning(self, "警告", "数据不能为空", QtWidgets.QMessageBox.Cancel)
            return

        b = False
        try:
            #查询包含 /![] 的笔记
            joplinSearch = "http://127.0.0.1:{}//search?query=/![]&type=note&token={}".format(self.joplinPort.text(),self.joplinToken.text())
            resp = requests.get(joplinSearch)

            #返回多个笔记的id
            data = resp.json().get("items")
            #使用线程池
            with ThreadPoolExecutor(max_workers=5) as executor:
                all_task = [executor.submit(self.run, (value)) for value in data]
                done_iter = futures.as_completed(all_task)

                for done in done_iter:
                    (code,title) = done.result();
                    if(code == 0):
                        self.log.logger.info("笔记标题: " + title +  " 【忽略】")
                    if(code == 1):
                        self.log.logger.info("笔记标题: " + title +  " 【完成】")
                    if(code == -1):
                        self.log.logger.error("笔记标题: " + title +  " 【错误】")
                        b = True

        except Exception as e:
            logging.exception(e)
            self.log.logger.error(e)
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