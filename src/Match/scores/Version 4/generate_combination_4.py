import json
import os
import sys
from collections import OrderedDict
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
from zhuyin2hanyu.util import separate_zhuyin
from zhuyin2hanyu.util import score_data

'''
    GLOBAL VALUE INITIALIZATION
'''
DIFFERENCE_IN = '../Version 3/combination_zhuyin_3.txt'
DIFFERENCE_OUT = '_'.join(chars for chars in DIFFERENCE_IN.split('_')[:-1])
CONSONANT_FILE = 'consonant_difference_4.txt'
VOWEL_FILE = 'vowel_difference_4.txt'

if __name__ == '__main__':
    '''
        Generate zhuyin combination score
        Using the data of the current version consonant and vowel score
    '''
    source_file = os.path.join(os.path.dirname(__file__), DIFFERENCE_IN)
    consonant_file = os.path.join(os.path.dirname(__file__), CONSONANT_FILE)
    vowel_file = os.path.join(os.path.dirname(__file__), VOWEL_FILE)

    with open(source_file, 'r', encoding='utf8') as source_file, \
    open(consonant_file, 'r', encoding='utf8') as consonant_file, \
    open(vowel_file, 'r', encoding='utf8') as vowel_file:
        #Load respective json file
        source_dict = json.load(source_file, object_pairs_hook=OrderedDict)
        consonant_dict = json.load(consonant_file, object_pairs_hook=OrderedDict)
        vowel_dict = json.load(vowel_file, object_pairs_hook=OrderedDict)

        #Collect consonant and vowel
        consonant = [key for key, value in consonant_dict.items()]
        vowel = [key for key, value in vowel_dict.items()]
        vowel.sort(key=len, reverse=True)

        '''
            Collect all possible Zhuyin Key
            And the process it to the longest possible separation
        '''
        separated_zhuyin = OrderedDict()
        for key, value in source_dict.items():
            separated_zhuyin[key] = separate_zhuyin(key, consonant, vowel)

        '''
            Check consonant and vowel score
            Save resulting score in the source_dict
        '''
        score_data(separated_zhuyin, source_dict, consonant_dict, vowel_dict)

        #Preparation for result file
        result_filename, result_extension = os.path.splitext(DIFFERENCE_OUT)
        result_filename = os.path.basename(result_filename)
        result_file = os.path.join(os.path.dirname(__file__), result_filename + '_4.txt')
        with open(result_file, 'w', encoding='utf8') as write_file:
            json.dump(source_dict, write_file, indent = 4, ensure_ascii=False)
