import re 
import json
import os 
import time

import requests
import execjs
import logging
import base64
from threading import Thread
from queue import Queue

from settings import url_list

class ManHua:
	def __init__(self):
		self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"}
		self.queue = Queue()
		self.path = os.getcwd()
		logging.basicConfig(filename='TencentManHua.log',filemode='w',level=logging.DEBUG,
							format='%(levelname)s:%(asctime)s:%(message)s',datefmt='%Y-%m-%d:%H:%M:%S')

	def __get_data_noce(self,url):
		"""获取网页中返回的data以及nonce参数
			url:网址
		"""
		try:
			res = requests.get(url,headers=self.headers).text
			nonce = re.findall('window\["n.*?e"\]\s=\s(.*?);',res)[0]
			data = re.findall('var DATA.*?\'(.*?)\'',res)[0]
			title = re.findall('title-comicHeading\">(.*?)<',res)[0].replace(' ','')
			name = re.findall('<title>《(.*?)》',res)[0]
			return nonce,data,title,name
		except Exception as er:
			print(url,er)

	def __parse_img(self,nonce,data):
		T = [i for i in data]
		N = re.findall('\d+[a-zA-Z]+',nonce)
		length = len(N)
		while length:
		    locate = int(re.findall('\d+',N[length-1])[0]) & 255 
		    string = re.sub('\d+','',N[length-1])
		    del T[locate:locate+len(string)]
		    length -= 1
		T = ''.join(T)
		return base64.b64decode(T.encode()).decode()

	def __get_pic(self,nonce,data,title,name):
		"""利用js解密出图片地址
			nonce,data:网页返回的参数
		"""
		if "!!document.children" in nonce:
			nonce = nonce.replace("!!document.children",'1')
		elif "!!document.getElementsByTagName('html')" in nonce:
			nonce = nonce.replace("!!document.getElementsByTagName('html')",'1')
		elif "window.Array" in nonce:
			nonce = nonce.replace('window.Array','1')
		nonce_code = "function t(){ return " + nonce + "}"
		try:
			n = execjs.compile(nonce_code).call('t')
			a = json.loads(self.__parse_img(n,data))
			for i in a['picture']:
				self.queue.put((name,title,i['url']),block=False)
		except:
			pass

	def downloads_img(self):
		"""下载图片,对每个章节建立一个文件夹存放"""
		while True:
			try:
				name,title,pic_link = self.queue.get()
				os.chdir(self.path)
				if not os.path.exists(self.path+os.sep+name):
					os.mkdir(self.path+os.sep+name)
				os.chdir(self.path+os.sep+name)
				if not os.path.exists(self.path+os.sep+name+os.sep+title):
					os.mkdir(self.path+os.sep+name+os.sep+title)
				os.chdir(self.path+os.sep+name+os.sep+title)
				with open(pic_link.split('_')[-1].split('/')[0],'wb') as f:
					print('正在下载：',title,pic_link)
					f.write(requests.get(pic_link).content)
			except Exception as er:
				logging.error(er)
			self.queue.task_done()
				
	def getAllPic(self,uid):
		"""获取所有图片的函数"""
		n = 1
		sign = 0
		while True:
			url = 'https://ac.qq.com/ComicView/index/id/%s/cid/%d' % (uid,n)
			result = self.__get_data_noce(url)
			if result:
				self.__get_pic(*result)
				sign = 0
			else:
				if sign > 2:
					break
				sign += 1
			n += 1

	def main(self):
		"""主函数，开启5个线程下载"""
		threads2 = [Thread(target=self.getAllPic,args=(uid,)) for uid in [i.split('/')[-1] for i in url_list]]
		for j in threads2:
			j.setDaemon(True)
			j.start()
		time.sleep(5)  #等待几秒，让队列中先有数据
		threads1 = [Thread(target=self.downloads_img) for i in range(5)]
		for i in threads1:
			i.setDaemon(True)
			i.start()
		self.queue.join()		

if __name__ == '__main__':
	ManHua().main()
