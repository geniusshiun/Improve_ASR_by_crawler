
import requests as rq
from bs4 import BeautifulSoup
import re


def getallPagelink():
    rooturl = 'https://www.pbs.gov.tw/cht/'
    url = 'https://www.pbs.gov.tw/cht/index.php?code=list&ids=46&start_time=106-03-16&expire_time=106-07-30&group_ID=&keyword=&search=%E9%80%81%E5%87%BA'
    #url = 'https://www.pbs.gov.tw/cht/index.php?code=list&ids=46&start_time=106-03-16&expire_time=106-03-29&group_ID=&keyword=&search=%E9%80%81%E5%87%BA%27,&page=2'
    header = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
        }
    with open('alllink','w',encoding='utf8') as f:
        while True:
            res = rq.get(url,headers=header)

            #res.encoding='ISO-8859-1'
            #print(res.request.headers) 
            soup = BeautifulSoup(res.text, 'lxml')
            #print(soup.prettify())
            hotnews_icon = soup.find_all("div", {"class": "hotnews_icon"})
            pagination = soup.find_all("ul", {"class": "pagination"})[0]
        # #print(pagination)

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
                    title = re.findall('title="(.+)\(',str(eachnews))[0]
                    link = rooturl+re.findall('href="(.+)" tabindex',str(eachnews))[0].replace('amp;','')
                    title_link[title] = link
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
    
    res = rq.get(url,headers=header)
    soup = BeautifulSoup(res.text, 'lxml')
    
    try:
        title = soup.find_all('h3')[0].text
        pagedata = soup.find_all("div", {"class": "pageinside"})[0].text.replace('新聞科','')
        date = re.findall('\d+-\d+-\d+',pagedata)[0]
        pagedata = pagedata.replace(date,'').replace(title,'').strip().replace('\n','')
        
    except:
        pagedata = ''
    try:

        mp3link = re.findall('src="(.+)" tabindex',str(soup.find_all('audio')[0]))[0]
    except:
        mp3link = ''
    return (url,title,pagedata,mp3link)
   
def crawlEachpage():
    import multiprocessing as mp
    rooturl = 'https://www.pbs.gov.tw/cht/'
    
    title_link = {}
    linklist = []
    errortitle = []
    with open('alllink','r',encoding='utf8') as f:
        for line in f.readlines():
            title = line.strip().split('\t')[0]
            link = line.strip().split('\t')[1]
            if 'https://' in link:
                linklist.append(link)
    
    pool = mp.Pool()
    res = pool.map(crawlfunc, linklist  )
    pool.close()
    pool.join()

    with open('allreferenceText','w',encoding='utf8') as f:
        for index in range(len(res)):
            f.write(res[index][0]+'\t'+res[index][1]+'\t'+res[index][2]+'\t'+res[index][3]+'\n')
    
    #print(res[0][0],res[0][1])
    
    #return title+'\n'+
    
   # print(errortitle)
    #for item in list(enumerate(title_link.items())):
    #    print(item)

def main():
    crawlEachpage()
if __name__ == "__main__":
    main()
