import os
import json
from collections import OrderedDict

'''
    GLOBAL VALUE INITIALIZATION
'''
ZHUYIN2HANYU = 'zhuyin2hanyu.txt'
ZHUYIN_LEVENSHTEIN = 'zhuyin_levenshtein.txt'
HANYU_LEVENSHTEIN = 'hanyu_levenshtein.txt'

def levenshtein_dict(types):
    '''
        Return Levenshtein result correspond to the input types
    '''
    if types == 'zhuyin':
        input_file = ZHUYIN_LEVENSHTEIN
    elif types == 'pinyin':
        input_file = HANYU_LEVENSHTEIN
    else:
        return None

    source_file = os.path.join(os.path.dirname(__file__), input_file)
    with open(source_file, 'r', encoding='utf8') as source:
        result_dict = json.load(source, object_pairs_hook=OrderedDict)
        return result_dict

def hanyu2zhuyin_dict():
    '''
        Create a dictionary of zhuyin from possible HanYuPinYin
        Return example:
        {'zhi': 'ㄓ', 'chi': 'ㄔ'}
    '''
    read_file = os.path.join(os.path.dirname(__file__), ZHUYIN2HANYU)
    with open(read_file, 'r', encoding='utf8') as source:
        #Take out the first line
        source.readline()

        hanyu_dict = OrderedDict()
        for line in source:
            splitted_line = line.strip().split()
            if len(splitted_line) == 2:
                hanyu_dict[splitted_line[1]] = splitted_line[0]
        return hanyu_dict

def zhuyin2hanyu_dict():
    '''
        Create a dictionary of HanYuPinYin from possible zhuyin
        Return example:
        {'ㄓ': 'zhi', 'ㄔ': 'chi'}
    '''
    read_file = os.path.join(os.path.dirname(__file__), ZHUYIN2HANYU)
    with open(read_file, 'r', encoding='utf8') as source:
        #Take out the first line
        source.readline()

        zhuyin_dict = OrderedDict()
        for line in source:
            splitted_line = line.strip().split()
            if len(splitted_line) == 2:
                zhuyin_dict[splitted_line[0]] = splitted_line[1]
        return zhuyin_dict

def separate_zhuyin(key, consonant, vowel):
    '''
        Received an argument as string containing zhuyin
        Return value will be dictionary of consonant and vowel
        {
            "consonant": ['a']
            "vowel": ['a']
        }
    '''
    data = OrderedDict()
    data['consonant'] = []
    data['vowel'] = []
    if key[0] in consonant:
        data['consonant'] = [key[0]]
        if key[1:] in vowel:
            data['vowel'] = [key[1:]]
        else:
            data['vowel'] = [vowel_key for vowel_key in key[1:] if vowel_key in vowel]
    else:
        data['consonant'] = ['空聲']
        if key in vowel:
            data['vowel'] = [key]
        else:
            data['vowel'] = [vowel_key for vowel_key in key if vowel_key in vowel]
    
    if len(data['vowel']) == 0:
        data['vowel'] = ['空聲']
    return data

def cross_score_data(score_dict, first_list, second_list):
    '''
        Search score from dictionary and calculate score
    '''
    score = []
    if first_list == second_list:
        score.append(1)
    else:
        for word1 in first_list:
            for word2 in second_list:
                score.append(score_dict[word1][word2])
    return score

def score_data(separated_zhuyin, source_dict, consonant_dict, vowel_dict):
    '''
        Check consonant and vowel score
        Save resulting score in the source_dict
    '''
    for first_key, first_value in source_dict.items():
        for second_key, second_value in first_value.items():
            first = separated_zhuyin[first_key]
            second = separated_zhuyin[second_key]

            #Compare consonant and vowel if available
            score = []
            if first['consonant'] == second['consonant']:
                score.append(1)
            else:
                appropriate_score = cross_score_data(consonant_dict, first['consonant'], second['consonant'])
                score.extend(appropriate_score)
            if first['vowel'] == second['vowel']:
                score.extend([1, 1])
            else:
                appropriate_score = cross_score_data(vowel_dict, first['vowel'], second['vowel'])
                appropriate_score.extend(appropriate_score)
                score.extend(appropriate_score)

            #Save scores
            source_dict[first_key][second_key] = float(sum(score)) / max(len(score), 1)