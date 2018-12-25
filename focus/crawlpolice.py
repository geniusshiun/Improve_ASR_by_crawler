
import requests as rq
from bs4 import BeautifulSoup
import re
from os.path import join
import glob

def getallPagelink():
    rooturl = 'https://www.pbs.gov.tw/cht/'
    url = 'https://www.pbs.gov.tw/cht/index.php?code=list&ids=46&start_time=106-01-01&expire_time=107-12-20&group_ID=&keyword=&search=%E9%80%81%E5%87%BA'
    url = 'https://www.pbs.gov.tw/cht/index.php?code=list&ids=46&start_time=106-01-01&expire_time=107-12-20&group_ID=&keyword=&search=%E9%80%81%E5%87%BA&page=170'
    header = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
        }
    
    with open('alllink','a',encoding='utf8') as f:
        while True:
            res = rq.get(url,headers=header)
            if not res.status_code == rq.codes.ok:
                print(res.status_code)
                break
            #res.encoding='ISO-8859-1'
            #print(res.request.headers) 
            
            soup = BeautifulSoup(res.text, 'lxml')
            hotnews_icon = soup.find_all("div", {"class": "hotnews_icon"})
            pagination = soup.find_all("ul", {"class": "pagination"})[0]

        # for eachpageurl in pagination:
            if re.findall('href="#" tabindex="142"',str(pagination)):
                print('finish')
                break
            else:
                nexturl = re.findall('href="(.+)" tabindex="142',str(pagination))[0].replace('amp;','')

                #crawl this page all data
                title_link = {}
                for eachnews in hotnews_icon:
                #    print(eachnews)
                    try:
                        title = re.findall('title="(.+)\(',str(eachnews).replace("'",'"'))[0].replace('.mp3.mp3','.mp3').replace('.MP3.MP3','.mp3')
                        link = rooturl+re.findall('href="(.+)" tabindex',str(eachnews))[0].replace('amp;','')
                        title_link[title] = link
                    except:
                        
                        print(str(eachnews))
                        break
                for title,link in title_link.items():
                    f.write(title+'\t'+link+'\n')
                    #print(title,link)

                print('go next',nexturl)
                url = nexturl
def crawlfunc(url):
    print(url)
    header = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
        }
    try:
        res = rq.get(url,headers=header)
    except Exception as e:
        print('ban!!',e)
        raise
        return ('','','','')
    soup = BeautifulSoup(res.text, 'lxml')
    
    try:
        title = soup.find_all('h3')[0].text
        articleId = re.findall('id=(\d+)',url)[0]
        pagedata = soup.find_all("div", {"class": "pageinside"})[0].text.replace('新聞科','')
        date = re.findall('\d+-\d+-\d+',pagedata)[0]
        pagedata = pagedata.replace(date,'').replace(title,'').strip().replace('\n','')
        
    except:
        pagedata = ''
    try:
        mp3link = re.findall('src="(.+)" tabindex',str(soup.find_all('audio')[0]))[0]
    except:
        mp3link = ''
    with open(join('allActicle',articleId),'w',encoding='utf8') as f:
        f.write(url+'\t'+title+'\t'+pagedata+'\t'+mp3link+'\n')
    return (url,title,pagedata,mp3link)
   
def crawlEachpage():
    import multiprocessing as mp
    rooturl = 'https://www.pbs.gov.tw/cht/'
    title_link = {}
    linklist = []
    errortitle = []
    existArticleID = []
    with open('alllink','r',encoding='utf8') as f:
        for line in f.readlines():
            title = line.strip().split('\t')[0]
            link = line.strip().split('\t')[1]
            if 'https://' in link:
                linklist.append(link)
    for filepath in glob.glob(join('allActicle','*')):
        existArticleID.append(re.findall('\d+',filepath)[0])
    #print(len(existArticleID))
    #print(len(linklist))
    
    notIn = []
    for link in linklist:
        articleID = re.findall('id=(\d+)',link)[0]
        #print(articleID)
        if not articleID in existArticleID:    
            notIn.append(link)
    
    if notIn:
        try:
            pool = mp.Pool()
            res = pool.map(crawlfunc, notIn)
            pool.close()
            pool.join()
        except Exception as e:
            pool.terminate()
            print(e)
        except KeyboardInterrupt:
            pool.terminate()
            print('keyboard stop')
    else:
        print('all finish!!')
    
    # finishUrl = []
    # with open('allreferenceText','a',encoding='utf8') as f:
    #     for index in range(len(res)):
    #         if not res[index][0] == '':
    #             f.write(res[index][0]+'\t'+res[index][1]+'\t'+res[index][2]+'\t'+res[index][3]+'\n')
    #             finishUrl.append(res[index][0])
    # with open('finishUrl','a',encoding='utf8') as f:
    #     for url in finishUrl:
    #         f.write(url+'\n')
    
    #print(res[0][0],res[0][1])
    
    #return title+'\n'+
    
   # print(errortitle)
    #for item in list(enumerate(title_link.items())):
    #    print(item)

def main():
    #getallPagelink()
    crawlEachpage()
    

if __name__ == "__main__":
    main()
