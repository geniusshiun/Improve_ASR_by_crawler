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
from pymongo import MongoClient
import datetime
from difflib import SequenceMatcher
from joblib import Parallel, delayed
from firebase import firebase

class ASRdataFetcher(object):
    """Summary of class here.
    A class for get text from different source(such like text, databases, etc)
    """
    def get(self, textpath, score):
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
        fetcher: data input source
        textpath: data input path
        score: asr result confidence score
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
def reconstruct_search_words(textpath,score=0.845):
    """Reconstruct search words
    
    Based on the search limit, we reorganized the words from input file.
    
    Args:
        textpath: It is the file path of input words.
        score: asr result confidence score
    Returns:
        {Audio file name:keywordlist}
    """
    fetcher = ASRdataFetcher()
    keywordlist = short_word_less_32(fetcher,textpath,score)
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
class search(object):
    def google_get_url(self,keyword):
        """Get web url from google
        
        As title
        
        Args:
            keyword: query search words
        Returns:
            weburls: web url list
        """
        
        google_url = 'https://www.google.com.tw/search'
        my_params = {'q':keyword, 'start':0}
        r = rq.get(google_url,params=my_params,verify = False)
        if r.status_code == 200:
            #doc = html.fromstring(r.text)
            #url_title = doc.xpath('//*[@id="rso"]/div[3]/div/div/div/div/h3/a')
            soup = BeautifulSoup(r.text,'html.parser')
            items = soup.select('div.g > h3.r > a[href^="/url"]')
            #print([urlparse.parse_qs(urlparse.urlparse(i.get('href')).query)["q"][0] for i in items])
            weburls = [urlparse.parse_qs(urlparse.urlparse(i.get('href')).query)["q"][0] for i in items]
            weburls = [url for url in weburls if not '.pdf' in url and not '.PDF' in url and not '.doc' in url and not '.xls' in url]
        else: 
            print(r.status_code)
            if r.status_code == '503':
                print('googleban = True')
                sys.exit()
        return weburls
    def bing_get_url(self,keyword):
        bing_url = 'https://www.bing.com/'
        my_params = {'q':keyword, 'start':0}
        r = rq.get(bing_url,params=my_params)
        if r.status_code == 200:
            #doc = html.fromstring(r.text)
            #url_title = doc.xpath('//*[@id="rso"]/div[3]/div/div/div/div/h3/a')
            soup = BeautifulSoup(r.text,'html.parser')
            #for link in soup.find_all('a'):
            #    print(link.get('href'))
            items = [item['href'] for item in soup.select('li.b_algo > h2 > a')] #= [re.findall('href="(.+)">',item.text) for item in 
            weburls = [url for url in items if not '.pdf' in url and not '.PDF' in url and not '.doc' in url and not '.xls' in url]
        else: 
            print(r.status_code)
            if r.status_code == '503':
                print('bingban = True')
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
        # add some limit to those continues receive data but too long
        searchweb = rq.get(url,headers= headers,timeout=3)
        
        if searchweb.encoding == 'ISO-8859-1':
            encodings = re.findall('charset=\"?(\S.+)\"',searchweb.text)
            if encodings:
                searchweb.encoding = encodings[0]
            else:
                searchweb.encoding = 'utf8'
        # we could use other way to parser the words, faster
        searchwebsoup = BeautifulSoup(searchweb.text,"lxml")
        alldata = re.findall('[A-Za-z0-9().% ]*[一-龥]+[A-Za-z0-9().% ]*',str(searchwebsoup.text))
    except Exception as e:
        #print(e)
        logger.warning(str(e))
        alldata = ''
    return alldata
def analyze(filename,outputpath,finishpath,threshold,thisTurnData,input_text_path,crawlflow):
    """Analyze match result; report whether re-crawl or not
    
    Open match file and consider the score of match result.
    Copy processed file and generate some tracking files.
    
    Args:
        filename: asr file name
        outputpath: the location of match file
        finishpath: finish file copy to this location
        threshold: besed on this threshold to decide re-crawl or not
        thisTurnData: the web contents lists from extended function crawlpage output
        input_text_path: loading folder
        crawlflow: the dict to store in database
    Returns:
        State,crawlflow:
            ex:
            'Get paragraph',crawlflow
            'Crawl Again',crawlflow
    """
    with open(join(outputpath,'fcr23.ws.re.wav.all2.match'),'r',encoding='utf8') as f:
        next(f)
        data = f.readline().strip()
        assert len(data.split('\t')) == 17
        score = data.split('\t')[16]
        filepath = data.split('\t')[0]
        #print('crawl '+str(len(thisTurnData))+' pages, spend '+
        #'crawlPagetime:{}\ttranfPinYintime:{}\tmatchFunctiontime:{}'
        #.format(crawlPagetime,tranfPinYintime,matchFunctiontime))
        if float(score) > float(threshold):
            paragraph = data.split('\t')[10]
            crawlflow['filepath'] = filepath
            crawlflow['score'] = score
            crawlflow['paragraph'] = data.split('\t')[10]
            print(paragraph)    
            #write ASR result and web data
            with open('final','a',encoding='utf8') as f:
                thispath = [path for path in input_text_path if filename in path][0]
                fetch = ASRdataFetcher()
                crawlflow['oriASRresult'] =''.join(fetch.get(thispath,0))
                f.write(crawlflow['oriASRresult']+'\t'+paragraph+'\n')
            [shutil.copy(fname, join(finishpath,'finish')) for fname in glob.glob(join(outputpath,('*.txt')))]    
            shutil.copy(join(outputpath,'fcr23.ws.re.wav.all2.match'), join(join(finishpath,'finish'),filename+'match'))
            return 'Get paragraph',crawlflow
        else:
            
            print('not found')
            [shutil.copy(filename, join(finishpath,'finish')) for filename in glob.glob(join(outputpath,('*.txt')))]   
            return 'Crawl Again',crawlflow
def diff_word_reconstruct(hint_dict,jiebacut_result,crawlflow):
    newhintlist = []
    last_position = 0
    new_left = 0
    firstTimeOverLeft = False
    for position,word in hint_dict.items():
        now_length = 0
        for jieba_word in jiebacut_result:
            now_length += len(jieba_word)
            if now_length <= position[0]:
                last_position = now_length
                continue
            elif now_length > position[0]:
                if not firstTimeOverLeft:
                    new_left = last_position
                    firstTimeOverLeft = True
            if now_length > position[1]:
                if now_length - len(jieba_word) <= position[0]:
                    new = crawlflow['paragraph'][now_length - len(jieba_word):now_length]
                else:
                    new = crawlflow['paragraph'][new_left:now_length]
                newhintlist.append(new)
                firstTimeOverLeft = False
                break
            elif now_length == position[1]:
                newhintlist.append(crawlflow['paragraph'][new_left:position[1]])
                firstTimeOverLeft = False
                break
    newhintlist = [hint for hint in newhintlist if len(hint) > 1]
    return newhintlist

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
    
    conn = MongoClient('localhost',27017)
    db = conn.googlecrawlstream
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    matchfile_pre = 'fcr23.ws.re.wav.all2'
    matchfile_tmp = 'fcr23.ws.re.wav.all2.res'
    matchfile_result = 'fcr23.ws.re.wav.all2.match'

    #load config
    with open('config','r',encoding='utf8') as f:
        config = json.loads(f.readlines()[0].strip())
    outputpath = config['outputpath']
    Nasgoogle_crawl_dir = config['Nasgoogle_crawl_dir']
    ASR_result = config['ASR_result']
    bashfilepath =config['bashfilepath']
    input_text_folder = config['input_text_folder']
    finishpath = config['finishpath']

    # firebaseurl = config['firebaseurl']
    # fb = firebase.FirebaseApplication(firebaseurl,None)

    jieba.set_dictionary('dict.txt.big')
    jieba.initialize()
    
    # load from input text path
    input_text_path = [join(input_text_folder,os.path.basename(x)) for x in glob.glob(join(input_text_folder,('*'))) 
                    if '.cm' in x and '.cm2' not in x and '.syl' not in x]
    #print(input_text_path)
    input_text_path = sorted(input_text_path, key=functools.cmp_to_key(myCompare))
    search_enging = search()
    searchEngine = 'Google'
    for eachTarget in [reconstruct_search_words(eachpath,0.845) for eachpath in input_text_path]:
        for filename, keywordlist in eachTarget.items():
            crawlflow = {}
            # get web urls from google each 15 seconds
            
            logger.info('Start: '+filename)
            n_segment_urls = {}                 # is there a repetition in urls
            alldata = []
            print(filename,keywordlist)
            #if not filename == 'A0001038':
            #   continue
            thisTurnData = []
            crawlflow['keywordlist'] = keywordlist
            
            for keyword in keywordlist:
                crawlflow['filename'] = filename
                crawlflow['keyword'] = keyword
                [os.remove(filename) for filename in glob.glob(join(outputpath,('fcr23.ws.re.wav*')))]
                [os.remove(filename) for filename in glob.glob(join(outputpath,('*.txt')))]
                [os.remove(filename) for filename in glob.glob(join(outputpath,('*.line')))]
                tFirstStart = time.time()
                webUrls = search_enging.google_get_url(keyword)  # crawl google
                crawlflow['searchEngine'] = searchEngine
                crawlflow['webUrls'] = webUrls
                crawlflow['round'] = keywordlist.index(keyword)
                for url in webUrls:
                    if url in n_segment_urls:
                        n_segment_urls[url] += 1
                        webUrls.remove(url)
                    else:
                        n_segment_urls[url] = 1
                #pool = mp.Pool()
                #thisTurnData = pool.map(crawlpage,webUrls)
                thisTurnData = Parallel(n_jobs=-1, backend="threading")(delayed(crawlpage)(url) for url in webUrls)
                alldata.extend(thisTurnData)
                
                #pool.close()
                #pool.join()
                
                crawlPagetime = str(int(time.time()-tFirstStart))
                crawlflow['crawlPagetime'] = crawlPagetime
                thisTurnData = [data for data in thisTurnData if len(''.join(data)) < 30000 and not data == '' and not data == []]
                after_filter_page_num = len(thisTurnData)
                crawlflow['afterFilterPageNum'] = after_filter_page_num
                if not thisTurnData:
                    crawlflow['filename'] = filename+'-'+str(keywordlist.index(keyword))
                    db[timestamp+'fail'].insert_one(crawlflow.copy())
                    #fb.post('/'+timestamp+'fail', crawlflow)
                    # crawlflow = {}
                    # crawlflow['filename'] = filename
                    # crawlflow['keywordlist'] = keywordlist
                    continue
                # write down those data from web page
                for data in thisTurnData:
                    webcontent = ''.join(data)
                    if len(webcontent) > 0:
                        with open(join(outputpath,filename+'-'+str(alldata.index(data))+'.txt'),'w',encoding='utf8') as f:
                            f.write(''.join(data))
                # use pin yin to transfer data
                tStart = time.time()
                rq.get(bashfilepath+'?text={}&asr={}'.format(Nasgoogle_crawl_dir,ASR_result))
                tranfPinYintime = str(int(time.time()-tStart))
                crawlflow['tranfPinYintime'] = tranfPinYintime
                tStart = time.time()
                # use match method to find paragraph
                
                p1 = subprocess.Popen(['python3','generate_diff.py',join(outputpath,matchfile_pre),
                    join(outputpath,matchfile_tmp)],cwd="Match/wav_matched/",stdout=subprocess.PIPE,shell=True)
                p1.wait()
                p2 = subprocess.Popen(['python3','filter_crawl_result.py',join(outputpath,matchfile_tmp),
                    join(outputpath,matchfile_result)],cwd="Match/wav_matched/",stdout=subprocess.PIPE,shell=True)
                p2.wait()
                matchFunctiontime = str(int(time.time()-tStart))
                crawlflow['matchFunctiontime'] = matchFunctiontime
                # Analyze - read match file and decide to query this file or not
                if analyze(filename, outputpath,finishpath, 0.9, thisTurnData, input_text_path,crawlflow)[0] == 'Get paragraph':
                    # from crawlflow['oriASRresult'] to compare with crawlflow['paragraph']
                    crawl_compare_match = SequenceMatcher(None, crawlflow['oriASRresult'], crawlflow['paragraph']).get_matching_blocks()
                    same_sents = [crawlflow['oriASRresult'][m[0]:m[0]+m[2]] for m in crawl_compare_match]
                    same_sents = [sentence for sentence in same_sents if len(sentence) > 1]
                    crawlflow['oriASRresult'] = crawlflow['oriASRresult'].replace(' ','')
                    crawlflow['paragraph'] = crawlflow['paragraph'].replace(' ','')
                    opc1=SequenceMatcher(None, crawlflow['oriASRresult'], crawlflow['paragraph']).get_opcodes()    
                    hint_dict = {}
                    for tag, i1, i2, j1, j2 in  opc1:
                        if tag == 'replace':
                            hint_dict[(j1,j2)] = crawlflow['paragraph'][j1:j2]
                    jiebacut_result = [w for w in jieba.cut(crawlflow['paragraph'])]
                    orihints = [crawlflow['paragraph'][j1:j2] for tag, i1, i2, j1, j2 in  opc1 if tag == 'replace']
                    # hints.extend(same_sents)
                    crawlflow['orihints'] = orihints
                    reconstruct_hints = diff_word_reconstruct(hint_dict,jiebacut_result,crawlflow)
                    hints = reconstruct_hints.copy()
                    crawlflow['reconstruct_hints'] = reconstruct_hints
                    tmpparagraph = crawlflow['paragraph']
                    for hint in hints:
                        tmpparagraph = tmpparagraph.replace(hint,' ')
                    hints.extend([sent for sent in ''.join(tmpparagraph).split(' ') if len(sent) > 1])
                    hintlength = 0
                    for hint in hints:
                        hintlength+=len(hint)
                        if hintlength >= 5000:
                            hints.remove(hint)
                            break
                        if len(hint) > 100:
                            hints.remove(hint)
                    crawlflow['hints'] = hints
                    db[timestamp].insert_one(crawlflow.copy())
                    #fb.post('/'+timestamp, crawlflow)
                    break
                else:
                    thisTurnData = []
                    crawlflow['filename'] = filename+'-'+str(keywordlist.index(keyword))
                    db[timestamp+'fail'].insert_one(crawlflow.copy())
                    #fb.post('/'+timestamp+'fail', crawlflow)
                    # crawlflow.clear()
                    # crawlflow['filename'] = filename
                    # crawlflow['keywordlist'] = keywordlist

                    #x = input('wait here')    
                tEnd = time.time()
                sleeptime = 15 -int(tEnd-tFirstStart) 
                if sleeptime > 0 and searchEngine == 'Google':
                    print('sleep',sleeptime)
                    time.sleep(sleeptime)
            
            #print(eachTarget.keys(),eachTarget.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Script for web crawler")
    parser.add_argument("--thread_count", type=int, default=50)
    parser.add_argument("--drama_file", type=str, required=True)
    parser.add_argument('file_in', type=str,help='string with absolute path or relative path to the input')
    args = parser.parse_args()
    main()
    #unittest.main()
    
