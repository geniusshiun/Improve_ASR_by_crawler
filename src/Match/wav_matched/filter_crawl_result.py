import os
import sys
import re
import string
import time
import multiprocessing
import datetime
import argparse
from collections import OrderedDict

import util

'''
    GLOBAL VALUE INITIALIZATION
'''
ENGLISH_PUNCTUATION = str.maketrans(dict.fromkeys(string.punctuation.encode('utf8'), ' '))
FILE_IO = ()
RATIO_THRESHOLD = 2

PINYIN = tuple(key for key in util.hanyu2zhuyin)

def retrieve_regex_group(input_string):
    '''
        Return the string that is separated by punctuation
        The input string should be in the regex format
        and should have .+ or .* between grouped words
        Example: (anything).+(is)?.+(possible)?.*(as)?.+(we)?.+(are)
        This function is to preprocess string from fcr matching
    '''
    exclusion_words = ['', ' ', '\n']    
    splitter_key = '|'.join(re.escape(chr(key)) for key in util.ENGLISH_PUNCTUATION)
    preprocess_words = re.split(splitter_key, input_string)
    return [words.strip() for words in preprocess_words if words not in exclusion_words]

def preprocess_word_group(word_group):
    '''
        Trying to combine non PINYIN word group into 1
        To speed up the process by eliminating possible random search
    '''
    result = []
    temporary = []
    for words in word_group:
        splitted_words = words.split()
        if len(splitted_words) == 1:
            if splitted_words[0] not in PINYIN:
                temporary.append(splitted_words[0])
                continue
        if len(temporary) != 0:
            result.append('[^a-zA-Z0-9]*?'.join(temporary))
            temporary = []
        result.append(words)

    return result

def reference_data_to_generator(file_in):
    '''
        Create a generator that return list of item for each column in data
        Return example:
        ['我們', '(我們)', 'wo men', '(wo men).?'], 0, -1, '', '']
    '''
    column_represent = ('file_path', 'google_result', 'asr_result', 'google_result_pinyin', 'asr_result_pinyin',
        'match_string_pinyin', 'match_start_pinyin', 'match_length_pinyin', 'match_start', 'match_length', 'match_string',
        'google_result_word_length', 'asr_word_length_pinyin', 'match_word_length_pinyin', 'match_word_ratio_pinyin',
        'matching_time', 'score')
    read_file = os.path.join(os.path.dirname(__file__), file_in)
    with open(read_file, 'r', encoding='utf8') as source:
        next(source)
        for line in source:
            if line != '\n':
                splitted_line = line.split('\t')
                yield OrderedDict( (column_represent[i], splitted_line[i]) for i in range(min(len(column_represent), len(splitted_line))) )

def write_descriptions():
    column_info = ('File Path', 'Full String', 'ASR Result', 'Full String Pinyin', 'ASR Result Pinyin', #'Regex Used',
        'Matched String', 'PinYin Start', 'PinYin Length', 'Actual Start', 'Actual Length', 'Actual Matched String',
        'Actual String Word Count', 'Regex Word Count', 'Matched String Word Count', 'Word Count Ratio (Matched/Regex)',# 'Confusion Pairs', 
        'Matching Time', 'Score')

    desc_string = '\t'.join(description for description in column_info)
    return ''.join((desc_string, '\n'))

def main_worker(file_io):
    file_in = file_io[0]
    file_out = file_io[1]
    filtered_result = OrderedDict()

    result = os.path.join(os.path.dirname(__file__), file_out)
    with open(result, 'w', encoding='utf8') as write_file:
        write_file.write(write_descriptions())

        for entry in reference_data_to_generator(file_in):
            print('Processing', entry['file_path'], ' in ', file_in)
            if 'asr_result_pinyin' not in entry:
                continue

            #Check in the dictionary of result
            if entry['asr_result_pinyin'] in filtered_result:
                word_group = entry['asr_result_pinyin']
                word_group = retrieve_regex_group(word_group)
                word_group = preprocess_word_group(word_group)
                entry_score = util.calculate_score(word_group, entry['match_string_pinyin'])
                possible_result_score = util.calculate_score(word_group, filtered_result[entry['asr_result_pinyin']]['match_string_pinyin'])
                choice = [(entry, entry_score), (filtered_result[entry['asr_result_pinyin']], possible_result_score)]
                chosen = max(choice, key = lambda x: x[1])
                filtered_result[entry['asr_result_pinyin']] = chosen[0]
            #If entry is not found, then put it inside
            else:
                filtered_result[entry['asr_result_pinyin']] = entry

        #Write into file
        for key in filtered_result:
            result_string = '\t'.join(str(filtered_result[key][entry]).strip() for entry in filtered_result[key])
            write_file.write(''.join((result_string, '\n')))

##################################################################################################
import textwrap as _textwrap

class LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
    '''
    Filter diff file produced by generate_diff.
    Format for the input file:
    - Each column must be separated by a tab
    - Total input column is 14
    ''', formatter_class=LineWrapRawTextHelpFormatter)

    parser.add_argument('file_in', type=str,
                    help='string with absolute path or relative path to the input')
    parser.add_argument('file_out', type=str,
                    help='string with absolute path or relative path to the output')
    args = parser.parse_args()
    FILE_IO = (args.file_in, args.file_out)

    main_worker(FILE_IO)
    
    #main()