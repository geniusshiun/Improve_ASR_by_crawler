import json
import re
import os
import sys
import random
from collections import OrderedDict
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
from zhuyin2hanyu.util import levenshtein_dict
from zhuyin2hanyu.util import hanyu2zhuyin_dict
from zhuyin2hanyu.util import separate_zhuyin

'''
    GLOBAL VALUE INITIALIZATION
'''
CONSONANT_FILE_PREPROCESS = '../Version 3/consonant_difference_3.txt'
VOWEL_FILE_PREPROCESS = '../Version 3/vowel_difference_3.txt'
COMBINATION_FILE_PREPROCESS = '../Version 3/combination_zhuyin_3.txt'
CONSONANT_RESULT = 'consonant_difference_4.txt'
VOWEL_RESULT = 'vowel_difference_4.txt'
SIMILARITY_THRESHOLD = 0.5
LEARNING_RATE = 0.005

def create_json_dict(filename):
    '''
        Return a dictionary of from the filename
        Data from the reag target file should be using json format
    '''
    read_file = os.path.join(os.path.dirname(__file__), filename)
    with open(read_file, 'r', encoding='utf8') as source:
        result_dict = json.load(source, object_pairs_hook=OrderedDict)
        return result_dict

def consonant_dict():
    '''
        Return a dictinary of consonant difference from preprocessed
        Data from the read target file should be using json format
    '''
    return create_json_dict(CONSONANT_FILE_PREPROCESS)

def vowel_dict():
    '''
        Return a dictinary of consonant difference from preprocessed
        Data from the read target file should be using json format
    '''
    return create_json_dict(VOWEL_FILE_PREPROCESS)

def combination_dict():
    '''
        Return a dictinary of consonant difference from preprocessed
        Data from the read target file should be using json format
    '''
    return create_json_dict(COMBINATION_FILE_PREPROCESS)

def adjust_dict_score(ratio_estimation, entryA, entryB, dictionary):
    '''
        Adjusting the score that is below estimation
        By adjusting the score of the pairs of entry
        Towards the dictionary
    '''
    for word1 in entryA:
        for word2 in entryB:
            if word1 != word2:
                upper_bound = (ratio_estimation-dictionary[word1][word2])*LEARNING_RATE
                dictionary[word1][word2] += random.uniform(upper_bound/2, upper_bound)

def levenshtein_adjust_dict(levenshtein, convert_function, combination, consonant, vowel):
    '''
        This function is used to adjust the score by referencing levenshtein value
        Key in the levenshtein key might be incompatible with the combination dictionary
        Therefore, the convert function is used to change it
        In the default case, zhuyin is used, therefore, pinyin value should be converted to zhuyin by the function
    '''
    for entryA in levenshtein:
        for entryB in levenshtein[entryA]:
            ratio = 1 - (levenshtein[entryA][entryB] / max(len(entryA), len(entryB)))

            first_key = convert_function(entryA)
            second_key = convert_function(entryB)
            if ratio > combination[first_key][second_key]:
                
                decomposed_entryA = separate_zhuyin(first_key, consonant, vowel)
                decomposed_entryB = separate_zhuyin(second_key, consonant, vowel)

                adjust_dict_score(ratio, decomposed_entryA['consonant'], decomposed_entryB['consonant'], consonant)
                adjust_dict_score(ratio, decomposed_entryA['vowel'], decomposed_entryB['vowel'], vowel)

def improve_score():
    '''
        Increase and decrease score appropriately
        By using data of levenshtein distance for zhuyin
        If ratio of distance is higher than available combination score
        Then increase the each component score
    '''
    zhuyin_levenshtein = levenshtein_dict('zhuyin')
    hanyu_levenshtein = levenshtein_dict('pinyin')
    hanyu2zhuyin = hanyu2zhuyin_dict()
    combination = combination_dict()
    consonant = consonant_dict()
    vowel = vowel_dict()

    levenshtein_adjust_dict(zhuyin_levenshtein, lambda x: x, combination, consonant, vowel)
    levenshtein_adjust_dict(hanyu_levenshtein, lambda x: hanyu2zhuyin[x], combination, consonant, vowel)

    return consonant, vowel

if __name__ == '__main__':
    '''
        Improve score using levenshtein value
        This method is used to prevent score from missing data to become too low
        Trying to add some small variability in the increase of score
        by using the pseudo random value
    '''

    consonant, vowel = improve_score()
    
    consonant_result = os.path.join(os.path.dirname(__file__), CONSONANT_RESULT)
    vowel_result = os.path.join(os.path.dirname(__file__), VOWEL_RESULT)
    with open(consonant_result, 'w', encoding='utf8') as consonant_result_file, \
    open(vowel_result, 'w', encoding='utf8') as vowel_result_file:
        json.dump(consonant, consonant_result_file, indent = 4, ensure_ascii=False)
        json.dump(vowel, vowel_result_file, indent = 4, ensure_ascii=False)