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
from os.path import join
from time import sleep
from urllib import parse as urlparse
import functools
import unittest

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
                except Exception as e:
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
    googletopN = '10'
    outputpath = 'crawlresult'

    # load from input text path
    input_text_path = [join(input_text_folder,os.path.basename(x)) for x in glob.glob(join(input_text_folder,('*'))) 
                    if '.cm' in x and '.cm2' not in x and '.syl' not in x]
    #print(input_text_path)
    print([reconstruct_search_words(eachpath) for eachpath in input_text_path])
if __name__ == "__main__":
    main()
    #unittest.main()
    
