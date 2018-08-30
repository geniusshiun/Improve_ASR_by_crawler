"""
Loads from input text path and reconstructs the input words.
Set a timer to query search enging by input words.
Get urls and save in database.
Author: YEN-HSUN, CHEN, 2018
"""
from bs4 import BeautifulSoup
import requests as rq
import re
import logging
import sys
import os
import glob
import random
import json
from os.path import join
from time import sleep
from urllib import parse as urlparse
import functools
import unittest
import time
from lxml import html
import multiprocessing as mp
import subprocess
import jieba, jieba.analyse
import shutil

class ASRdataFetcher(object):
    """Summary of class here.
    A class for get text from different source(such like text, databases, etc)
    """
    def get(self, textpath, score=0.845):
        """get text and cm score from textpath
    
        Return contain chinese characters and score > threshold.
        
        Args:
            textpath: file path
            score: asr result confidence score
        Returns:
            inputlist: as describe above
        """
        inputlist = []
        with open(textpath,'r',encoding = 'utf8') as f:
            for line in f.readlines():
                if line == '\n' or len(re.findall('[一-龥]',line))==0: continue
                try:
                    cmnum = round(float(line.strip().split('\t')[-1]),3)
                    if cmnum < score: continue
                    else: inputlist.append(line.strip().split('	')[1])    
                except: #Exception as e:
                    pass
        return inputlist
def myCompare(a,b):
    """my own compare function based on the file list format
    
    Sort the files such like A0000006.cm and A0000007.cm.
    
    Args:
        a: the first inpu file name
        b: the second input file name
    Returns:
        None
    Raises:
        pass
    """
    try:
        if( int(a[-10:-3]) > int(b[-10:-3]) ):
            return 1
        elif(int(a[-10:-3]) < int(b[-10:-3]) ):
            return -1
        else:
            return 0
    except:
        pass
        return 0
def short_word_less_32(fetcher,textpath,score):
    """Let all the words of the list short than 32 characters.
    
    Reorganized the words from input list.
    
    Args:
        inputlist: Remain those higher than cofidence score.
    Returns:
        keywordlist: All words short than 32 characters.
    """
    inputlist = fetcher.get(textpath,score)
    keywordlist = []
    keywordlens = 0
    tmpkeywords =''
    laststartindex = 0
            
    #make keywordlist
    for index in range(len(inputlist)):
        if (keywordlens + len(inputlist[index])) > 32:
            laststartindex = index
            if len(inputlist[index]) >32:       
                keywordlist.append(inputlist[index][:32])
                keywordlens = 0
            else:
                keywordlist.append(tmpkeywords)
                keywordlens = len(inputlist[index])
                tmpkeywords = inputlist[index]
            
        else:
            keywordlens += len(inputlist[index])
            tmpkeywords+=inputlist[index]
            if index == len(inputlist)-1:
                nowindex = int(laststartindex)-1
                while True:
                    if len(tmpkeywords) + len(inputlist[nowindex]) <= 32:
                        tmpkeywords = inputlist[nowindex]+tmpkeywords
                        nowindex-=1
                        if nowindex < 0: break
                    else: break
                keywordlist.append(tmpkeywords)
                break
    #for item in keywordlist:
    #    if item == '':
    #        keywordlist.remove(item)
    return keywordlist
def reconstruct_search_words(textpath):
    """Reconstruct search words
    
    Based on the search limit, we reorganized the words from input file.
    
    Args:
        textpath: It is the file path of input words.
    Returns:
        {Audio file name:keywordlist}
    """
    fetcher = ASRdataFetcher()
    keywordlist = short_word_less_32(fetcher,textpath,0.845)
    return {textpath[-11:-3]:keywordlist}
class test_myCompare(unittest.TestCase):
    """ 
	test myCompare function
	"""
    def test_inputs(self):
        self.assertEqual(myCompare('A0000525.cm','A0000532.cm'), -1)
        self.assertEqual(myCompare('A0000546.cm','A0000532.cm'), 1)
        self.assertEqual(myCompare('A0000546.cm','A0000546.cm'), 0)
        self.assertEqual(myCompare('',''), 0)
class test_short_word_less_32(unittest.TestCase):
    """ 
	test myCompare function
	"""
    def test_inputs(self):
        fetcher = ASRdataFetcher()
        textpath = join(join('..','input_ASR_results'),'A0000525.cm')
        self.assertEqual([text for text in short_word_less_32(fetcher,textpath,0.845) if len(text) > 32], [])
def get_web_url(keyword):
    """Get web url from google
    
    As title
    
    Args:
        keyword: query search words
    Returns:
        weburls: web url list
    """
    
    google_url = 'https://www.google.com.tw/search'
    my_params = {'q':keyword, 'start':0}
    r = rq.get(google_url,params=my_params)
    if r.status_code == 200:
        doc = html.fromstring(r.text)
        #url_title = doc.xpath('//*[@id="rso"]/div[3]/div/div/div/div/h3/a')
        soup = BeautifulSoup(r.text,'html.parser')
        items = soup.select('div.g > h3.r > a[href^="/url"]')
        #print([urlparse.parse_qs(urlparse.urlparse(i.get('href')).query)["q"][0] for i in items])
        weburls = [urlparse.parse_qs(urlparse.urlparse(i.get('href')).query)["q"][0] for i in items]
        weburls = [url for url in weburls if not '.pdf' in url and not '.PDF' in url and not '.doc' in url]
    else: 
        print(r.status_code)
        if r.status_code == '503':
            print('googleban = True')
            sys.exit()
    return weburls
def crawlpage(url):
    """Get web data by url
    
    Consider the encode and get all data from web page by lxml or beautifulSoup.
    Parser all text by regular expression match.
    
    Args:
        url: web url
    Returns:
        data: web data
    """
    #print(url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'}
    try:
        searchweb = rq.get(url,headers= headers,timeout=5)
        if searchweb.encoding == 'ISO-8859-1':
            encodings = re.findall('<meta.*content=.*charset=(?P<charset>[^;\s]+)',searchweb.text)
            if encodings:
                searchweb.encoding = encodings[0]
        searchwebsoup = BeautifulSoup(searchweb.text,"lxml")
        alldata = re.findall('[A-Za-z0-9().% ]*[一-龥]+[A-Za-z0-9().% ]*',str(searchwebsoup.text))
    except:
        alldata = ''
    return alldata
logger = logging.getLogger('google_crawler')
logger.setLevel(logging.DEBUG)
formatter=logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
fh = logging.FileHandler('google_crawler.log', mode='a',encoding='utf8')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

def main():
    # varibales
    input_text_folder = join('..','input_ASR_results')
    #googletopN = '10'
    #outputpath = join('..','crawlresult')
    with open('config','r',encoding='utf8') as f:
        config = json.loads(f.readlines()[0].strip())
    outputpath = config['outputpath']
    Nasgoogle_crawl_dir = config['Nasgoogle_crawl_dir']
    ASR_result = config['ASR_result']
    bashfilepath =config['bashfilepath']
    # outputpath = join('\\\\140.96.186.23\計畫管理\FY107_E100計畫管理\科技大擂台\大擂台語料\題目試聽抓文字語料','all2')
    # Nasgoogle_crawl_dir = '/home/openstack/mnt/nas/FY107_E100計畫管理/科技大擂台/大擂台語料/題目試聽抓文字語料/all2'
    # ASR_result = '/mnt/nas/FY107_E100計畫管理/科技大擂台/大擂台語料/dry_run/kaggle1_cm/data/wav/A'
    # bashfilepath = 'http://140.96.178.204:8000/cgi-bin/re2google.sh'

    # load from input text path
    input_text_path = [join(input_text_folder,os.path.basename(x)) for x in glob.glob(join(input_text_folder,('*'))) 
                    if '.cm' in x and '.cm2' not in x and '.syl' not in x]
    #print(input_text_path)
    
    filetoUrls = {}
    
    for eachTarget in [reconstruct_search_words(eachpath) for eachpath in input_text_path]:
        for filename, keywordlist in eachTarget.items():
            #get web urls from google each 15 seconds
            n_segment_urls = {}
            alldata = []
            print(filename,keywordlist)
            [os.remove(filename) for filename in glob.glob(join(outputpath,('fcr23.ws.re.wav*')))]
            for keyword in keywordlist:
                tStart = time.time()
                webUrls = get_web_url(keyword) 
                for url in webUrls:
                    if url in n_segment_urls:
                        n_segment_urls[url] += 1
                        webUrls.remove(url)
                    else:
                        n_segment_urls[url] = 1
                pool = mp.Pool()
                alldata.extend(pool.map(crawlpage,webUrls))
                pool.close()
                pool.join()
                
                for data in alldata:
                    if len(data) > 0:
                        with open(join(outputpath,filename+'-'+str(alldata.index(data))+'.txt' ),'w',encoding='utf8') as f:
                            f.write(''.join(data))
                #use pin yin to transfer data
                
                res = rq.get(bashfilepath+'?text={}&asr={}'.format
                                                                    (Nasgoogle_crawl_dir,ASR_result))
                # use match method to find paragraph
                matchfile_pre = 'fcr23.ws.re.wav.all2'
                matchfile_tmp = 'fcr23.ws.re.wav.all2.res'
                matchfile_result = 'fcr23.ws.re.wav.all2.match'
                p1 = subprocess.Popen(['python3','generate_diff.py',join(outputpath,matchfile_pre),
                    join(outputpath,matchfile_tmp)],cwd="Match/wav_matched/",stdout=subprocess.PIPE,shell=True)
                p1.wait()
                p2 = subprocess.Popen(['python3','filter_crawl_result.py',join(outputpath,matchfile_tmp),
                    join(outputpath,matchfile_result)],cwd="Match/wav_matched/",stdout=subprocess.PIPE,shell=True)
                p2.wait()
                #read match file and decide to query this file or not
                threshold = 0.9
                with open(join(outputpath,'fcr23.ws.re.wav.all2.match'),'r',encoding='utf8') as f:
                    next(f)
                    data = f.readline().strip()
                    
                    print(len(data.split('\t')))
                    score = data.split('\t')[16]
                    if float(score) > float(threshold):
                        print(data.split('\t')[10])    
                        x = input('wait here')                    
                        [shutil.copy(filename, join(outputpath,'finish')) for filename in glob.glob(join(outputpath,('*.txt')))]
                        [os.remove(filename) for filename in glob.glob(join(outputpath,('*.txt')))]
                        break
                    else:
                        print('not found')
                    
                    
                        
                
                tEnd = time.time()
                
                    
                        
                sleeptime = 15 -int(tEnd-tStart) 
                if sleeptime > 0:
                    print('sleep',sleeptime)
                    time.sleep(sleeptime)
            
            #print(eachTarget.keys(),eachTarget.values())


if __name__ == "__main__":
    main()
    #unittest.main()
    
