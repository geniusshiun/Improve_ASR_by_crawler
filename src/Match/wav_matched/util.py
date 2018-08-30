import os
import re
import json
import sys
import string
import difflib

import unicodedata
from collections import OrderedDict
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
from scores.config import COMBINATION_DIFFERENCE_FILE
from scores.zhuyin2hanyu.util import hanyu2zhuyin_dict
from scores.zhuyin2hanyu.util import zhuyin2hanyu_dict

'''
    GLOBAL VALUE INITIALIZATION
'''
UNIGRAM_WEIGHT = 1
BIGRAM_WEIGHT = 4
TRIGRAM_WEIGHT = 14
CHINESE_PUNCTUATION = dict.fromkeys(i for i in range(sys.maxunicode) \
                      if unicodedata.category(chr(i)).startswith('P'))
ENGLISH_PUNCTUATION = str.maketrans(dict.fromkeys(string.punctuation.encode('utf8'), ' '))
SCORES_THRESHOLD = 0.7

hanyu2zhuyin = hanyu2zhuyin_dict()
zhuyin2hanyu = zhuyin2hanyu_dict()

#Getting scores from the scores folder with the newest config version
SCORES_JSON = ''.join(('../scores/', COMBINATION_DIFFERENCE_FILE))
combination_difference = os.path.join(os.path.dirname(__file__), SCORES_JSON)
with open(combination_difference, 'r', encoding='utf8') as difference_file:
    COMBINATION_SCORE = json.load(difference_file, object_pairs_hook=OrderedDict)

class DICT_CACHE:
    def __init__(self, max_key_number):
        self._max_key_number = max_key_number
        self._cache = OrderedDict()

    def get(self, key):
        popped = self._cache.pop(key, None)
        if popped is not None:
            self._cache[key] = popped
            return self._cache[key]
        else:
            return None

    def push_cache(self, key, data):
        if key not in self._cache and len(self._cache) > self._max_key_number:
            for keyword in self._cache:
                self._cache.pop(keyword, None)
                break
        self._cache[key] = data

    def clear_cache(self):
        self._cache.clear()

class STRING_SCORE:
    def __init__(self, actual_string):
        self._actual_string = actual_string

    def string_similarity_score(self, computed_string):
        '''
            Calculating the score of similarity between two string
            The first argument is the actual string and the second is the one wanted to be compared
            The length of the string should be equal, in the condition where it is not, the shortest length will be used
        '''
        entry = [self._actual_string.strip().split(), computed_string.strip().split()]
        scores = []
        try:
            scores = list(COMBINATION_SCORE[hanyu2zhuyin[entry[0][index]]][hanyu2zhuyin[entry[1][index]]] for index in range(min(len(entry[0]), len(entry[1]))))
        except:
            if self._actual_string == computed_string:
                return 1
            else:
                return 0
        else:
            scores = float(sum(scores)) / max(len(scores), 1)
            return scores

REGEX_CACHE = DICT_CACHE(1000)

def strip_punctuation(input_string):
    '''
        Return back string without any punctuation of the list below
        List is provided in string.punctuation  
    '''
    istring = input_string.translate(CHINESE_PUNCTUATION)
    return istring.translate(ENGLISH_PUNCTUATION)

def possible_confusion(key):
    '''
        This function will return the possible confusion of zhuyin word
        The returned result will be ordered from the highest score
        Returned the highest possible confusion including the input
        Confusion score threshold is set within global variable
    '''
    confusion_result = list( (wanted_keyword, COMBINATION_SCORE[key][wanted_keyword]) for wanted_keyword in COMBINATION_SCORE[key] if COMBINATION_SCORE[key][wanted_keyword] > SCORES_THRESHOLD)
    confusion_result.sort(key=lambda tup: tup[1], reverse=True)
    return [zhuyin2hanyu[confusion[0]] for confusion in confusion_result]

def reflect_pinyin_to_result(actual_string, converted_string):
    '''
        Trying to match actual Chinese String into Converted Pinyin String
        Assume that all that is not considede correct pinyin should have its own chinese character in actual string
        Actual string could contain 'space', which is not correctly represented in converted string
        English word in actual string could be separated by space in the converted string, which
            let the possibility of the separated word to be interpreted as correct pinyin
    '''

    '''
        0x3000 is ideographic space (i.e. double-byte space)
        Anything over is an Asian character
    '''
    actual_string_lower = actual_string.lower().strip()
    converted_string_lower = converted_string.lower().strip()

    token = ()
    #Start index from zero, for converted string
    converted_index = 0
    for actual_index, actual_char in enumerate(actual_string_lower):
        token += ((actual_index, converted_index), )
        #Special maintenance if space is in actual string
        if actual_char == ' ':
            #Increase index until the next valid character is found
            for converted_char in converted_string_lower[converted_index:]:
                if converted_char == ' ':
                    converted_index += 1
                else:
                    break
        elif not ord(actual_char) > 0x3000 or actual_char in ENGLISH_PUNCTUATION or actual_char in CHINESE_PUNCTUATION:
            converted_index += 1
            #Increase index until the next valid character is found
            for converted_char in converted_string_lower[converted_index:]:
                if converted_char == ' ':
                    converted_index += 1
                else:
                    break
        else:
            converted_index += 1
            for converted_char in converted_string_lower[converted_index:]:
                #Special condition for e#
                if not ord(converted_char) > 0x3000 and (converted_char.isalpha() or converted_char == '#'):
                    converted_index += 1
                else:
                    #Increase index until the next valid character is found
                    for converted_char in converted_string_lower[converted_index:]:
                        if converted_char == ' ':
                            converted_index += 1
                        else:
                            break
                    break
    return token

def pinyin_to_actual_result(pinyin_mapping, pinyin_start, pinyin_length):
    '''
        Given the mapping result from the actual to converted
        Then the actual pinyin start and length
        This function is used to mapped those start and length into actual result index
    '''
    answer = {}
    answer['start'] = pinyin_mapping[0][0]
    pinyin_end = pinyin_start + pinyin_length + 1
    for pinyin_mapping_index, pinyin_map in enumerate(pinyin_mapping):
        if pinyin_start < pinyin_map[1]:
            if pinyin_mapping_index == 0:
                answer['start'] = pinyin_mapping[pinyin_mapping_index][0]
                break
            else:
                answer['start'] = pinyin_mapping[pinyin_mapping_index-1][0]
                break

    answer['end'] = pinyin_mapping[-1][0]
    for pinyin_mapping_index, pinyin_map in enumerate(pinyin_mapping):
        if pinyin_end < pinyin_map[1]:
            if pinyin_mapping_index == 0:
                answer['end'] = pinyin_mapping[pinyin_mapping_index][0]
                break
            else:
                answer['end'] = pinyin_mapping[pinyin_mapping_index-1][0]
                break
    return answer

def calculate_hit_rate_without_order(word_group, match_string):
    '''
        Calculate the percentage of hit from the regex
        Create list of word from the regex
        and try to find the word in the string without considering order
    '''
    score = []

    score = sum(1 for sentence in word_group if re.search(''.join(('\\b', sentence, '\\b')), match_string) is not None)
    return float(score) / max(len(word_group), 1)

def calculate_unigram(word_group, full_string):
    '''
        Adding 4 for each found words in the full string
        This function is used to calculate the resemblance of word in the string
    '''
    unigram_list = word_group
    unigram_words = '|'.join(word for word in unigram_list)
    #Search from cache if possible
    regex = ''.join(('(?=((?:\\b(?:', unigram_words, ')\\b)))'))
    p = REGEX_CACHE.get(regex)
    if p is None:
        p = re.compile(regex)
        REGEX_CACHE.push_cache(regex, p)
    score = sum(UNIGRAM_WEIGHT for match in p.finditer(full_string))
    return score

def calculate_bigram(word_group, full_string):
    '''
        Adding 4 for each found words in the full string
        This function is used to calculate the resemblance of word in the string
    '''
    bigram_list = ['[^a-zA-Z0-9]+?'.join((word_group[index], word_group[index+1])) for index in range(len(word_group)-1)]
    bigram_words = '|'.join(word for word in bigram_list)
    #Search from cache if possible
    regex = ''.join(('(?=((?:\\b(?:', bigram_words, ')\\b)))'))
    p = REGEX_CACHE.get(regex)
    if p is None:
        p = re.compile(regex)
        REGEX_CACHE.push_cache(regex, p)
    score = sum(BIGRAM_WEIGHT for match in p.finditer(full_string))
    return score

def calculate_trigram(word_group, full_string):
    '''
        Adding 14 for each found words in the full string
        This function is used to calculate the resemblance of word in the string
    '''
    trigram_list = ['[^a-zA-Z0-9]+?'.join((word_group[index], word_group[index+1], word_group[index+2])) for index in range(len(word_group)-2)]
    trigram_words = '|'.join(word for word in trigram_list)
    #Search from cache if possible
    regex = ''.join(('(?=((?:\\b(?:', trigram_words, ')\\b)))'))
    p = REGEX_CACHE.get(regex)
    if p is None:
        p = re.compile(regex)
        REGEX_CACHE.push_cache(regex, p)
    score = sum(TRIGRAM_WEIGHT for match in p.finditer(full_string))
    return score

def calculate_score(word_group, full_string):
    '''
        Combine bigram and trigram method to calculate score
    '''
    tri_score = calculate_trigram(word_group, full_string)
    bi_score = calculate_bigram(word_group, full_string)
    score = tri_score + bi_score
    max_bi_score = (len(word_group) - 1) * BIGRAM_WEIGHT
    max_tri_score = (len(word_group) - 2) * TRIGRAM_WEIGHT
    max_score = max_bi_score + max_tri_score
    return score / max_score

def substitute_error(str1, str2):
    '''
        Return string of substitution error
        Using difflib
    '''
    s1 = str1.strip().split()
    s2 = str2.strip().split()
    difference = difflib.SequenceMatcher (None, s1, s2)

    result_string = '; '.join( ''.join((' '.join(entry for entry in s1[blocks[1]:blocks[2]]), '/', ' '.join(entry for entry in s2[blocks[3]:blocks[4]])))
        for blocks in difference.get_opcodes() if blocks[0] == 'replace')
    return result_string