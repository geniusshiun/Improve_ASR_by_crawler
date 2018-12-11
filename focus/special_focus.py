"""
Loads from input text path.
Loads reference data.
Compare Levenshtein ratio.
Author: YEN-HSUN, CHEN, 2018
"""
import glob
import requests
from os.path import join
import re
import jieba, jieba.analyse
import jieba.posseg as pseg
import Levenshtein as lev
import multiprocessing as mp
import functools


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
def createNewA(filepath,article,articleID,beautiful,stone,monkey,oldman,lu_1):
    """Write the new file A based on Levenshtein ratio
    
    Computer the highest Levenshtein ratio between different reference data.
    Number > 10000, compare with article
    Number < 10000, compare with beautiful and stone
    
    Args:
        filepath: ASR result file path
        article: Radio data(list)
        articleID: Radio data dict. articleID[data] = article_id
        beautiful: Reference data 1.(list)
        stone: Reference data 2.(list)
    Returns:
        None
    Raises:
        pass
    """
    #load .cm files   
    inwhichReference = {0:'null',1:'警廣',2:'美人恩',3:'石頭記',4:'西遊記',5:'老殘遊記',6:'魯迅吶喊'}
    number = int(re.findall('A(\d+)',filepath)[0])
    filename = re.findall('(A\d+)',filepath)[0]
    oridata = []
    inputlist = []
    #if number > 10000:
    #    return False
    with open(filepath,'r',encoding = 'utf8') as f:
        for line in f.readlines():
            
            if line == '\n' or len(re.findall('[一-龥]',line))==0: continue
            try:
                oridata.append(line)
                cmnum = round(float(line.strip().split('\t')[-1]),3)
                if cmnum < 0.7: continue
                else: inputlist.append(line.strip().split('	')[1])    
            except: #Exception as e:
                pass
    data = ''.join(inputlist)
    if len(data) < 20:
        print('ASR bad')
        return number,'0','ASR length < 20'
    maxratio = 0
    referenceCandidata = ''
    if number > 10000:
        computerArticle = article
    else:
        computerArticle = []
        computerArticle.extend(beautiful)
        computerArticle.extend(stone)
        computerArticle.extend(monkey)
        computerArticle.extend(oldman)
        computerArticle.extend(lu_1)
    for reference in computerArticle:
        ratio = lev.ratio(data,reference)
        if ratio > maxratio:
            maxratio = ratio
            referenceCandidata = reference
    referenceIndex = 0
    if maxratio > 0.3:
        if number > 10000:
            print(number,maxratio,referenceCandidata[:10],articleID[referenceCandidata])
            referenceIndex = 1
        else:
            print(number,maxratio,referenceCandidata[:10])
            if referenceCandidata in beautiful: 
                referenceIndex = 2
            elif referenceCandidata in stone: 
                referenceIndex = 3
            elif referenceCandidata in monkey: 
                referenceIndex = 4
            elif referenceCandidata in oldman: 
                referenceIndex = 5
            elif referenceCandidata in lu_1: 
                referenceIndex = 6
        
        #writ new A
        with open(join('kaggle7',filename+'.cm'),'w',encoding = 'utf8') as f:
            for line in oridata:
                f.write(line)
            f.write('1\t'+referenceCandidata+'\t0.99')
        return filename,maxratio,inwhichReference[referenceIndex]
    return filename,maxratio,inwhichReference[referenceIndex]
def loadreference(filepath):
    data = []
    with open(filepath,'r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip()
            if len(line) > 20:
                data.append(line)
    return data
def main():
    
    articleID = {}
    article = []
    beautiful = []
    stone = []
    monkey = []
    oldman = []
    lu_1 = []#吶喊
    beautiful = loadreference('美人恩.txt')
    monkey = loadreference('西遊記.txt')
    oldman = loadreference('老殘遊記.txt')
    lu_1 = loadreference('吶喊.txt')
    with open('石頭記.txt','r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip().replace(' ','')
            
            oriline = line
            if not line == '':
            #m = re.search("【", String)
                startlist = [m.start() for m in re.finditer('([【])',line)]
                endlist = [m.start() for m in re.finditer('([】])',line)]
                if len(startlist) - len(endlist) == 1:
                    endlist.append(len(oriline)-1)
                try:
                    for index in reversed(range(len(startlist))):
                        line = line.replace(line[startlist[index]:endlist[index]+1],'')
                    if len(line) > 5:
                        stone.append(line)
                        #print(oriline,line)
                except:
                    print(oriline)
                    print(startlist)
                    print(endlist)
            #print(re.finditer('([【])',line))
    
    with open('allreferenceText','r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip()
            try:
                data = line.split('\t')[2]
                article_id = re.findall('article_id=(\d+)',line.split('\t')[0])[0]
                articleID[data] = article_id
                article.append(data)
            except:
                print(line)
    
    input_text_path = sorted(glob.glob(join('A','*.cm')), key=functools.cmp_to_key(myCompare))
    pool = mp.Pool()
    reslist = []
    for filepath in input_text_path:
        args = [filepath,article,articleID,beautiful,stone,monkey,oldman,lu_1]
        res = pool.apply_async(func=createNewA, args=args)
        reslist.append(res)
    pool.close()
    pool.join()
    f = open('result.log','w',encoding='utf8')
    for res in reslist:
        #filename,maxratio,inwhichReference[referenceIndex]
        result = res.get()
        print(result)
        filename = str(result[0])
        maxratio = str(result[1])[:5]
        comment = result[2]
        f.write(filename+'\t'+maxratio+'\t'+comment+'\n')
    f.close()

if __name__ == '__main__':
    main()
