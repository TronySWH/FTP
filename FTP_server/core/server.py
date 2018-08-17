#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: Trony

import socketserver
import json
import configparser
import os
from conf import settings

STATUS_CODE = {
    250: "Invalid cmd format, e.g:{'action':'get', 'filename':'test.py', 'size':344}",
    251: "Invalid cmd",
    252: "Invalid auth data",
    253: "Wrong username or password",
    254: "Passed authentication",
    255: "Filename doesn't exist provided",
    256: "File deson,t exist on server",
    257: "ready to send file",
    258: "md5 verification",

    800: "the file exist, but no enough, is continue",
    801: "the file exist !",
    802: "ready to receive datas",

    900: "md5 valdata success"
}


class ServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        while 1:
            data = self.request.recv(1024).strip()  # self.request相当于conn
            data = json.loads(data.decode('utf-8'))
            """
            {
                "action":"auth",
                "username":"yuan",
                "pwd":123
            }
            """
            if data.get("action"):
                if hasattr(self, data.get("action")):
                    func = getattr(self, data.get("action"))
                    func(**data)
                else:
                    print("Invalid cmd")
            else:
                print("Invalid cmd")

    def send_response(self, state_code):
        response = {'status_code': state_code}
        self.request.sendall(json.dumps(response).encode('utf-8'))

    def auth(self, **data):
        username = data['username']
        password = data['password']
        user = self.authenticate(username, password)
        if user:
            self.send_response(254)
        else:
            self.send_response(253)

    def authenticate(self, user, pwd):
        cfg = configparser.ConfigParser()
        cfg.read(settings.ACCOUNT_PATH)
        if user in cfg.sections():
            if cfg[user]['Password'] == pwd:
                self.user = user
                self.mainPath = os.path.join(settings.BASE_DIR, "home", self.user)
                return user

    def put(self, **data):
        print("data", data)
        file_name = data.get("file_name")
        file_size = data.get("file_size")
        target_path = data.get("target_path")
        abs_path = os.path.join(self.mainPath, target_path, file_name)

        ###############################################################
        has_received = 0
        if os.path.exists(abs_path):  # 判断是否有文件
            file_has_size = os.stat(abs_path).st_size
            if file_has_size <= file_size:
                # 断点续传
                self.request.sendall("800".encode('utf-8'))
                choice = self.request.recv(1024).decode("utf-8")
                if choice == "Y":
                    self.request.sendall(str(file_has_size).encode('utf-8'))
                    f = open(abs_path, 'ab')
                    has_received = file_has_size
                else:
                    f = open(abs_path, 'wb')
            else:
                # 文件完全存在
                self.request.sendall("801".encode('utf-8'))
                return
        else:
            self.request.sendall("802".encode('utf-8'))
            f = open(abs_path, 'wb')
        while has_received < file_size:
            try:
                data = self.request.recv(1024)
            except Exception as e:
                break
            f.write(data)
            has_received += len(data)
        f.close()

    def ls(self, **data):
        file_list = os.listdir(self.mainPath)
        file_str = "\n".join(file_list)
        if not len(file_list):
            file_str = "《empty dir!》"
        self.request.sendall(file_str.encode('utf-8'))

    def cd(self, **data):
        dirname = data.get('dirname')
        if dirname == "..":
            self.mainPath = os.path.dirname(self.mainPath)
        else:
            self.mainPath = os.path.join(self.mainPath, dirname)
        self.request.sendall(self.mainPath.encode("utf-8"))

    def mkdir(self, **data):
        dirname = data.get("dirname")
        path = os.path.join(self.mainPath, dirname)
        if not os.path.exists(path):
            if "/" in dirname:
                os.makedirs(path)
            else:
                os.mkdir(path)
            self.request.sendall("create success!".encode("utf-8"))
        else:
            self.request.sendall("dirname exist!".encode("utf-8"))
