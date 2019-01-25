import re
import glob
import sys
import os
from os.path import join
def strQ2B(ustring):
    """把字串全形轉半形"""
    rstring = []
    for uchar in ustring:
        inside_code=ord(uchar)
        if inside_code==0x3000:
            inside_code=0x0020
        else:
            if (inside_code-0xfee0 > 0):
                inside_code-=0xfee0

        if inside_code<0x0020 or inside_code>0x7e:   #轉完之後不是半形字元返回原來的字元
            rstring.append(uchar)
        else:
            rstring.append(chr(inside_code))

    return ''.join(rstring)
    
def loadreference(filepath):
    data = []
    with open(filepath,'r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip()
            data.append(line)
    #print(data)
    strdata = '\n'.join(data)
    maintainsymbol = ['！',':','？','；','，','：','。',';',',','!']
    for symbol in list(enumerate(set(re.findall('[^一-龥]',''.join(data))))):
        
        if not symbol[1] in maintainsymbol:
            strdata = strdata.replace(symbol[1],'')
    newdata = re.sub('[！:？；，：。;,]','\n',strdata)
    
    return [line for line in newdata.split('\n') if len(line) > 1]
def stonereader(filepath):
    stone = []
    with open(filepath,'r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip().replace(' ','')
            
            oriline = line
            if not line == '':
            #m = re.search("【", String)
                startlist = [m.start() for m in re.finditer('([【])',line)]
                endlist = [m.start() for m in re.finditer('([】])',line)]
                if len(startlist) - len(endlist) == 1:
                    endlist.append(len(oriline)-1)
               
                for index in reversed(range(len(startlist))):
                    line = line.replace(line[startlist[index]:endlist[index]+1],'')
                stone.append(line)
    strdata = '\n'.join(stone)
    maintainsymbol = ['！',':','？','；','，','：','。',';',',','!']
    for symbol in list(enumerate(set(re.findall('[^一-龥]',''.join(stone))))):
        
        if not symbol[1] in maintainsymbol:
            strdata = strdata.replace(symbol[1],'')
    newdata = re.sub('[！:？；，：。;,]','\n',strdata)
    
    return [line for line in newdata.split('\n') if len(line) > 1]
def policereader(filepath):
    data = []
    with open(filepath,'r',encoding='utf8') as f:
        for line in f.readlines():
            line = line.strip().split('\t')[2]
            data.append(line)
            
    strdata = '\n'.join(data)
    maintainsymbol = ['！',':','？','；','，','：','。',';',',','!','.']
    for symbol in list(enumerate(set(re.findall('[^A-Za-z0-9０-９Ａ-Ｚａ-ｚ一-龥％]',''.join(data))))):
        if not symbol[1] in maintainsymbol:
            print(symbol[1])
            strdata = strdata.replace(symbol[1],'')
    newdata = re.sub('[！:？；，：。;,!]','\n',strdata)
    
    return [line for line in newdata.split('\n') if len(line) > 1]
    

def main():
    outputfolder = sys.argv[1]
    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)
    for filepath in glob.glob('*.txt'):
        if 'removeMapping.txt' in filepath:
            continue
        if 'stone' == filepath:
            data = stonereader(filepath)
        else:
            data = loadreference(filepath)

    #for filename in ['吶喊.txt','石頭記.txt','美人恩.txt','老殘遊記.txt','西遊記.txt','allreferenceText','三國演義.txt']:
        newdata = data.copy()
        data = []
        for line in newdata:
            data.append(strQ2B(line))
        with open(join(outputfolder,filepath.replace('.txt','')+'line.txt'),'w',encoding='utf8') as f:
            for line in data:
                f.write(line+'\n')
if __name__=='__main__':
    main()