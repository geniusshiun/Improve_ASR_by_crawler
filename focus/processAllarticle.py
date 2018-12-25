import glob
from os.path import join
import re
import wget
import subprocess
import multiprocessing as mp
def main():
    alldata = []
    downloadMP3 = {}
    id_data = {}
    symbolchange = {}
    for filepath in glob.glob(join('allArcticle','*')):
        with open(filepath,'r',encoding='utf8') as f:  
            
            articleID = re.findall('\d+',filepath)[0]
            id_data[articleID] =[]
            allline = []
            for line in f.readlines():
                line = line.strip()
                allline.append(line)
            if len(allline) > 1:    
                content = ''.join(allline)
            else:
                content = line
            if len(content.split('\n'))>1:
                print(content)
            #print(''.join(allline).split('\t')[2])
            alldata.append(content.split('\t')[2])
            downloadMP3[articleID] = content.split('\t')[-1]
            id_data[articleID].append(content.split('\t')[0]) # url
            id_data[articleID].append(content.split('\t')[1]) # title
            id_data[articleID].append(content.split('\t')[2]) # content
            
            id_data[articleID].append(articleID+'.pcm') # mp3 file name
            id_data[articleID].append(content.split('\t')[-1]) # mp3 url
            
    with open('symbol_nonchange','w',encoding='utf8') as f:
        for articleID, symbol_non_list in symbolchange.items():
            f.write(articleID+'\t'+symbol_non_list+'\n')
    with open('police1060101_1071220data','w',encoding='utf8') as f:
        for data in alldata:
            f.write(data+'\n')
    with open('police1060101_1071220','w',encoding='utf8') as f:
        for articleID, datalist in id_data.items():
            f.write(articleID+'\t'+'\t'.join(datalist)+'\n')
    with open('1060101_1071220mp3URL','w',encoding='utf8') as f:
        for ID,url in downloadMP3.items():
            f.write(ID+'\t'+url+'\n')
def downloadfun(articleid,url):
    print(url,articleid)
    wget.download(url, join('mp3download',articleid+'.mp3'))  
def downloadmp3():
    
    idUrlList = {}
    with open('1060101_1071220mp3URL','r',encoding='utf8') as f:
        for line in f.readlines():
            articleID = line.strip().split('\t')[0]
            idUrlList[articleID] = line.strip().split('\t')[1]
    print(len(idUrlList))
    for filepath in glob.glob(join('mp3download','*')):
        fileID = re.findall('(\d+).mp3',filepath)[0]
        del idUrlList[fileID]
        #print(fileID)
    print(len(idUrlList))
    pool = mp.Pool()
    
    for articleID, url in idUrlList.items():   
        res = pool.apply_async(func=downloadfun, args=[articleID,url])
    
    pool.close()
    pool.join()
def mp3ToPCMfunc(filepath):
    articleID = re.findall('\d+',filepath)[1]
    cmd = ['ffmpeg', '-y', '-i', filepath, '-acodec', 'pcm_s16le', '-f', 's16le',
        '-ac', '1', '-ar', '16000', join(r'D:\policePCM',articleID+'.pcm')]
    subprocess.call(cmd)
def mp3ToPCM():
    pool = mp.Pool()
    pool.map(mp3ToPCMfunc,glob.glob(join('mp3download','*')))
    pool.close()
    pool.join()
if __name__ == '__main__':
    main()
    #downloadmp3()
    #mp3ToPCM()
    