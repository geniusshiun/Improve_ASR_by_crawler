# -*- coding: utf-8 -*-
# using Python 3
import os
import json
import sys
from collections import OrderedDict
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
import nltk.metrics.distance as nltk
from util import separate_zhuyin

SOURCE_FILE = 'zhuyin2hanyu.txt'
HANYU_OUTPUT_FILE = 'hanyu_levenshtein.txt'
ZHUYIN_OUTPUT_FILE = 'zhuyin_levenshtein.txt'

def similarity_dict(types):
    '''
        Create similarity dict correspons to the types
    '''
    if types == 'zhuyin':
        choices = 0
    elif types == 'pinyin':
        choices = 1
    else:
        return None

    read_file = os.path.join(os.path.dirname(__file__), SOURCE_FILE)
    with open(read_file, 'r', encoding='utf8') as source:
        #Take out the first line
        source.readline()

        #Get list of HanYu PinYin
        data = []
        for line in source:
            stripped_line = line.strip().split()
            if len(stripped_line) == 2:
                data.append(stripped_line[choices])
 
        #Create dictionary
        similarity_dict = OrderedDict()
        for words1 in data:
            similarity_dict[words1] = OrderedDict()
            for words2 in data:
                similarity_dict[words1][words2] = 0

        return similarity_dict

def create_hanyu_dict():
    '''
        Create a dictionary score between from possible HanYuPinYin
        Initial value created will be 0
        Return example:
        {'a':
          { 'a' : 0, 'b' : 0 },
         'b':
          { 'a' : 0, 'b' : 0 }
         }
    '''
    return similarity_dict('pinyin')

def create_zhuyin_dict():
    '''
        Create a dictionary score between from possible ZhuYin
        Initial value created will be 0
        Return example:
        {'ㄓ':
          { 'ㄓ' : 0, 'ㄔ' : 0 },
         'ㄔ':
          { 'ㄓ' : 0, 'ㄔ' : 0 }
         }
    '''
    return similarity_dict('zhuyin')

def calculate_levenshtein_distance(dictionary):
    '''
        Calculate Levenshtein Distance between two pairs of 2-dimensional dictionary key.
        The resulting value will be stored in the value of the dictionary
    '''
    for key1, value1 in dictionary.items():
        for key2, value2 in value1.items():
            dictionary[key1][key2] =  nltk.edit_distance(key1, key2)

def similarity_score():
    '''
        Write the value of Levenshtein distance into file
        The data is written in json format to represent 2D dictionary in Python
    '''
    hanyu_dict = create_hanyu_dict()
    calculate_levenshtein_distance(hanyu_dict)
    result =  os.path.join(os.path.dirname(__file__), HANYU_OUTPUT_FILE)
    with open(result, 'w', encoding='utf8') as write_file:
        json.dump(hanyu_dict, write_file, indent = 4, ensure_ascii=False)

    zhuyin_dict = create_zhuyin_dict()
    calculate_levenshtein_distance(zhuyin_dict)
    result =  os.path.join(os.path.dirname(__file__), ZHUYIN_OUTPUT_FILE)
    with open(result, 'w', encoding='utf8') as write_file:
        json.dump(zhuyin_dict, write_file, indent = 4, ensure_ascii=False)

if __name__ == '__main__':
    similarity_score()
