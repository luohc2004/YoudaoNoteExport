#!/usr/bin/python
# -*- coding:utf-8 -*-
import re

defaultencoding = 'utf-8'

import requests
import sys

reload(sys)
sys.setdefaultencoding('utf8')
import time
import hashlib
import os
from requests.cookies import create_cookie
import json


def timestamp():
    return str(int(time.time() * 1000))


class YoudaoNoteSession(requests.Session):
    def __init__(self):
        requests.Session.__init__(self)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

    def login(self, username, password):
        self.get('https://note.youdao.com/web/')

        self.headers['Referer'] = 'https://note.youdao.com/web/'
        self.get('https://note.youdao.com/signIn/index.html?&callback=https%3A%2F%2Fnote.youdao.com%2Fweb%2F&from=web')

        self.headers[
            'Referer'] = 'https://note.youdao.com/signIn/index.html?&callback=https%3A%2F%2Fnote.youdao.com%2Fweb%2F&from=web'
        self.get('https://note.youdao.com/login/acc/pe/getsess?product=YNOTE&_=' + timestamp())
        self.get('https://note.youdao.com/auth/cq.json?app=web&_=' + timestamp())
        self.get('https://note.youdao.com/auth/urs/login.json?app=web&_=' + timestamp())
        data = {
            "username": username,
            "password": hashlib.md5(password).hexdigest()
        }
        self.post(
            'https://note.youdao.com/login/acc/urs/verify/check?app=web&product=YNOTE&tp=urstoken&cf=6&fr=1&systemName=&deviceType=&ru=https%3A%2F%2Fnote.youdao.com%2FsignIn%2F%2FloginCallback.html&er=https%3A%2F%2Fnote.youdao.com%2FsignIn%2F%2FloginCallback.html&vcode=&systemName=&deviceType=&timestamp=' + timestamp(),
            data=data, allow_redirects=True)
        self.get('https://note.youdao.com/yws/mapi/user?method=get&multilevelEnable=true&_=' + timestamp())
        print(self.cookies)
        self.cstk = self.cookies.get('YNOTE_CSTK')

    def getRoot(self):
        data = {
            'path': '/',
            'entire': 'true',
            'purge': 'false',
            'cstk': self.cstk
        }
        response = self.post(
            'https://note.youdao.com/yws/api/personal/file?method=getByPath&keyfrom=web&cstk=%s' % self.cstk, data=data)
        print('getRoot:' + response.content)
        jsonObj = json.loads(response.content)
        return jsonObj['fileEntry']['id']

    def getNote(self, id, saveDir, name):
        data = {
            'fileId': id,
            'version': -1,
            'convert': 'true',
            'editorType': 1,
            'cstk': self.cstk
        }
        url = 'https://note.youdao.com/yws/api/personal/sync?method=download&keyfrom=web&cstk=%s' % self.cstk
        response = self.post(url, data=data)
        with open('%s/%s' % (saveDir, name), 'w') as fp:
            fp.write(response.content)

    def getNoteDocx(self, id, saveDir, name):
        url = 'https://note.youdao.com/ydoc/api/personal/doc?method=download-docx&fileId=%s&cstk=%s&keyfrom=web' % (
            id, self.cstk)
        response = self.get(url)
        if response.headers.get('Content-Disposition'): # 老的note导出的word的response还不一样...
            h = response.headers['Content-Disposition']
            h = h.split('\"')
            name = h[1]
        rstr = r"[\/\\\:\*\?\"\<\>\|]|\r|\n|\t"  # '/ \ : * ? " < > |'
        name = re.sub(rstr, "_", name)  # 替换非法文件名为下划线
        with open('%s/%s' % (saveDir, name), 'wb') as fp:
            fp.write(response.content)

    def getFileRecursively(self, id, saveDir):
        data = {
            'path': '/',
            'dirOnly': 'false',
            'f': 'false',
            'cstk': self.cstk
        }
        url = 'https://note.youdao.com/yws/api/personal/file/%s?all=true&f=true&len=30&sort=1&isReverse=false&method=listPageByParentId&keyfrom=web&cstk=%s' % (
            id, self.cstk)
        lastId = None
        count = 0
        total = 1
        while count < total:
            if lastId == None:
                response = self.get(url)
            else:
                response = self.get(url + '&lastId=%s' % lastId)
            print('getFileRecursively:' + response.content)
            jsonObj = json.loads(response.content)
            total = jsonObj['count']
            for entry in jsonObj['entries']:
                fileEntry = entry['fileEntry']
                id = fileEntry['id']
                name = fileEntry['name']
                print('%s %s' % (id, name))
                if fileEntry['dir']:
                    subDir = saveDir + '/' + name
                    try:
                        os.lstat(subDir)
                    except OSError:
                        os.mkdir(subDir)
                    self.getFileRecursively(id, subDir)
                else:
                    # with open('%s/%s.json' % (saveDir, id), 'w') as fp:
                    #     fp.write(json.dumps(entry, ensure_ascii=False).encode('utf-8'))
                    if name.endswith('.md'):
                        self.getNote(id, saveDir, name)
                    else:  # docx
                        self.getNoteDocx(id, saveDir, name)
                count = count + 1
                lastId = id

    def getAll(self, saveDir):
        rootId = self.getRoot()
        self.getFileRecursively(rootId, saveDir)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('args: <username> <password>')
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    sess = YoudaoNoteSession()
    sess.login(username, password)
    if sess.cstk:
        sess.getAll(".")
    else:
        print('login failed')
