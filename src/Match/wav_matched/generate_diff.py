import re
import sys
import os
import json
import time
import multiprocessing
import itertools
from collections import OrderedDict
import unicodedata
import string
import datetime
import argparse

import util

'''
    GLOBAL VALUE INITIALIZATION
'''
FILE_IO = ()

#A dictionary but only for checking
PINYIN = util.hanyu2zhuyin

COLUMN_INFO = ('File Path', 'Full String', 'ASR Result', 'Full String Pinyin', 'ASR Result Pinyin',# 'Regex Used',
    'Matched String', 'PinYin Start', 'PinYin Length', 'Actual Start', 'Actual Length', 'Actual Matched String',
    'Actual String Word Count', 'Regex Word Count', 'Matched String Word Count', 'Word Count Ratio (Matched/Regex)',
    'Matching Time', 'Score')

MIN_LENGTH_MULTIPLIER = 0.5
MAX_LENGTH_MULTIPLIER = 10
MIN_GRAM_SCORE = 0.3
CONFUSION_LIST_LENGTH_LIMIT = 10
GROUP_MAX_DELETION = 9 #Max deletion represent index, therefore for value 2, 3 group is deleted
WINDOW_VIEW_MULTIPLIER = 3
GROUPING_MIN = 3 #Represent index, therefore for value 2, 3 group is used
GROUPING_MAX = 6

REGEX_CACHE = util.DICT_CACHE(1000)
CONFUSION_CACHE = util.DICT_CACHE(1000)


def retrieve_regex_group(input_string):
    '''
        Return the string that is separated by punctuation
        The input string should be in the regex format
        and should have .+ or .* between grouped words
        Example: (anything).+(is)?.+(possible)?.*(as)?.+(we)?.+(are)
        This function is to preprocess string from fcr matching
    '''
    exclusion_words = {'', ' ', '\n'}    
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

def possible_confusion(word_group):
    '''
        This function will return the possible confusion of pinyin sentence
        The returned result will be ordered from the highest score
        Returned the highest possible confusion including the input
        Confusion score threshold is set within global variable
    '''
    max_confusion = int(CONFUSION_LIST_LENGTH_LIMIT**(1/float(len(word_group)))) + 1
    max_confusion = max(3, max_confusion)

    confusion_list = list(util.possible_confusion(util.hanyu2zhuyin[entry])[:max_confusion]
        if entry in PINYIN else [entry] for entry in word_group)
    return confusion_list

def get_begin_end_regex(beginning_list, ending_list):
    '''
        Get the unique 'or' regex from a list of word
        the list of word should have the same word length for each element
        Example:
            ['an xin', 'ang xing']
        Result:
            ((an|ang)( (xin|xing)))
    '''
    begin_el_len = len(beginning_list[0].split())
    end_el_len = len(ending_list[0].split())

    begin_dict = list(OrderedDict( (phrase.split()[index], None) for phrase in beginning_list) for index in range(begin_el_len))
    begin = '([^a-zA-Z0-9]*?'.join(('('+ '|'.join(key for key in begin_el) + '))') for begin_el in begin_dict)
    begin = ''.join(('((', begin, ')'))

    end_dict = list(OrderedDict( (phrase.split()[index], None) for phrase in ending_list) for index in range(end_el_len))
    end = '([^a-zA-Z0-9]*?'.join(('('+ '|'.join(key for key in end_el) + '))') for end_el in end_dict)
    end = ''.join(('((', end, ')'))

    return begin, end

def consider_confusion(word_group, group_needed):
    '''
        Trying to get more answer by adding possible confusion inside
        The confusion that is considered in this step is for the beginning and end
        Therefore confusion will be added by adding'or'(|) into the regex string result
    '''
    #(I).*?(.*?(to).*?)?(.*?(to).*?)?(eat)
    if len(word_group) < 2*group_needed:
        return '', '', None

    #If possible, check cache
    cache_key = '-'.join( ('_'.join(word_group), str(group_needed)) )
    answer = CONFUSION_CACHE.get(cache_key)
    if answer is not None:
        return answer['begin'], answer['end'], answer['word group']
    else:
        #Adding possible non alphanumeric appearance between words
        beginning_list = possible_confusion(word_group[0].split())
        beginning_list.extend( list([words] for words in word_group[1:group_needed]) )
        end_list = list([words] for words in word_group[-1*group_needed:-1])
        end_list.extend( possible_confusion(word_group[-1].split()) )

        beginning_list = itertools.product(*beginning_list)
        end_list = itertools.product(*end_list)

        beginning_list = list(' '.join(word) for word in beginning_list)
        end_list = list(' '.join(word) for word in end_list)

        #Scoring needspace to be used
        score_key_sorter = util.STRING_SCORE(' '.join(word_group[:group_needed]))
        beginning_list.sort(key = score_key_sorter.string_similarity_score, reverse=True)
        beginning_list = beginning_list[:CONFUSION_LIST_LENGTH_LIMIT]
        score_key_sorter = util.STRING_SCORE(' '.join(word_group[-1*group_needed:]))
        end_list.sort(key = score_key_sorter.string_similarity_score, reverse=True)
        end_list = end_list[:CONFUSION_LIST_LENGTH_LIMIT]

        begin, end = get_begin_end_regex(beginning_list, end_list)

        middle_word_group = '\\b.*?)?(.*?\\b'.join(word_group[group_needed:-1*group_needed])
        word_group = ''.join(('.*?(.*?\\b', middle_word_group, '\\b.*?)?'))

        CONFUSION_CACHE.push_cache(cache_key, OrderedDict( (
            ('begin', begin), ('end', end), ('word group', word_group)
            ) ))
        return begin, end, word_group

def preprocess_regex(word_group):
    '''
        Changing groups of words into regex
        word_group should be in a regex
        This regex formula is to match the most possible hit between start and end words
        While still choosing the shortest possible answer to return
    '''
    result_string = word_group.replace('(', '(?:')
    return ''.join(('(?=(', result_string, '))'))

def reference_data_to_generator(file_in):
    '''
        Create a generator that return list of item for each column in data
        Return example:
        ['我們', '(我們)', 'wo men', '(wo men).?'], 0, -1, '', '']
    '''
    column_represent = ('file_path', 'google_result', 'asr_result', 'google_result_pinyin', 'asr_result_pinyin', 
        'match_string_pinyin', 'match_start_pinyin', 'match_length_pinyin', 'match_start', 'match_length', 'match_string',
        'asr_word_length_pinyin', 'match_word_length_pinyin', 'match_word_ratio_pinyin')
    read_file = os.path.join(os.path.dirname(__file__), file_in)
    with open(read_file, 'r', encoding='utf8') as source:
        for line in source:
            if line != '\n':
                splitted_line = line.split('\t')
                yield OrderedDict( (column_represent[i], splitted_line[i].strip()) for i in range(min(len(column_represent), len(splitted_line))) )

def match_regex(full_string, word_group_list, anchor_regex_length, phrase_grouping):
    '''
        This function is trying to match the string using word group
        Word group is presented in a list and Order matters in this matching
    '''
    #Group the first and end n groups to reduce possible match
    #Higher number result in higher precision but with a lower match rate
    #Try to lower it to the point where it at least match something with at least 1 start and end group
    start_available = False
    end_available = False
    regex_needed = ''
    begin, end, word_group = consider_confusion(word_group_list, phrase_grouping)
    if word_group is not None:
        regex_needed = preprocess_regex(''.join( ('(\\b', begin, '\\b)', '.*?', '(\\b', end, '\\b)') ))
        beginning_regex = preprocess_regex(''.join( ('(\\b', begin, '\\b)') ))
        #Search from cache if possible
        p = REGEX_CACHE.get(beginning_regex)
        if p is None:
            p = re.compile(beginning_regex)
            REGEX_CACHE.push_cache(beginning_regex, p)
        begin_loc = list((entry.span(1)[0], entry.span(1)[1]) for entry in p.finditer(full_string))
        if len(begin_loc) != 0:
            start_available = True

        end_regex = preprocess_regex(''.join( ('(\\b', end, '\\b)') ))
        #Search from cache if possible
        p = REGEX_CACHE.get(end_regex)
        if p is None:
            p = re.compile(end_regex)
            REGEX_CACHE.push_cache(end_regex, p)
        end_loc = list((entry.span(1)[0], entry.span(1)[1]) for entry in p.finditer(full_string))
        if len(end_loc) != 0:
            end_available = True

        match_group = list((b[0], e[1]) 
            for b in begin_loc for e in end_loc 
            if e[1] > b[0] and MIN_LENGTH_MULTIPLIER*anchor_regex_length*3 < e[1] - b[0] < MAX_LENGTH_MULTIPLIER*anchor_regex_length*3 and
            util.calculate_score(word_group_list, full_string[b[0]:e[1]]) > MIN_GRAM_SCORE)

        if len(match_group) != 0:
            #print('z')
            ans = min(match_group, key= lambda x: abs( anchor_regex_length - len(util.strip_punctuation(full_string[x[0]:x[1]]).strip().split()) ) )
            #ans = max(match_group, key= lambda x: x[2] )
            return OrderedDict( (
                ('regex', regex_needed), 
                ('match_string', full_string[ans[0]:ans[1]]), 
                ('start', ans[0]), ('length', ans[1] - ans[0]), 
                ('word_length', len(util.strip_punctuation(full_string[ans[0]:ans[1]]).strip().split())),
                ('start_available', start_available), ('end_available', end_available),
                ('score', util.calculate_hit_rate_without_order(word_group_list, full_string[ans[0]:ans[1]]))
                ) )

    return OrderedDict( (
        ('regex', regex_needed), 
        ('match_string', ''), 
        ('start', 0), ('length', -1), 
        ('word_length', 0),
        ('start_available', start_available), ('end_available', end_available),
        ('score', 0)
        ) )

def match(full_string, word_group, word_group_regex_length):
    '''
        Trying to group the most possible combination of start and end as fixed to increase accuracy
    '''
    result_data = OrderedDict( (
        ('regex', ''), 
        ('match_string', ''), 
        ('start', 0), ('length', -1), 
        ('word_length', 0),
        ('start_available', False), ('end_available', False),
        ('score', 0)
        ) )

    for phrase_grouping in reversed(range(GROUPING_MIN, GROUPING_MAX)):
        #Consideration to cut the beginning or ending of word group to further loosen the requirements
        #Using bracket to encapsulate the chosen string
        bracket = [ (0, len(word_group)) ]
        used_bracket = []
        while len(bracket) > 0:
            data = bracket[0]
            bracket = bracket[1:]
            if data not in used_bracket:
                used_bracket.append(data)
            bracket_start = data[0]
            bracket_end = data[1]
            if bracket_start >= bracket_end:
                continue

            chosen_word_group = word_group[bracket_start:bracket_end]
            answer = match_regex(full_string, chosen_word_group, word_group_regex_length, phrase_grouping)

            result_data = answer
            if answer['length'] != -1:
                word_group = chosen_word_group
                return result_data

            if answer['start_available'] is False and bracket_start < GROUP_MAX_DELETION:
                data = (bracket_start+1, bracket_end-1)
                if data not in used_bracket and data not in bracket:
                    bracket.append(data)
            if answer['end_available'] is False and len(word_group) - bracket_end < GROUP_MAX_DELETION:
                data = (bracket_start, bracket_end-1)
                if data not in used_bracket and data not in bracket:
                    bracket.append(data)
            if answer['start_available'] and answer['end_available'] and answer['length'] == -1:
                if bracket_start < GROUP_MAX_DELETION:
                    data = (bracket_start+1, bracket_end)
                    if data not in used_bracket and data not in bracket:
                        bracket.append(data)
                if len(word_group) - bracket_end < GROUP_MAX_DELETION:
                    data = (bracket_start, bracket_end-1)
                    if data not in used_bracket and data not in bracket:
                        bracket.append(data)
    return result_data

####################################################################################################################################

def write_descriptions():
    desc_string = '\t'.join(description for description in COLUMN_INFO)
    return desc_string + '\n'

def default_answer(entry):
    '''
        Return a dict which contains default answer for each entry
    '''
    default_answer_pair = (entry['file_path'], entry['google_result'], entry['asr_result'], entry['google_result_pinyin'], entry['asr_result_pinyin'],# '',
        '', 0, -1, 0, 0, '', 0, 0, 0, 0, 0, 0)
    return OrderedDict( (info, default_answer_pair[index]) for index, info in enumerate(COLUMN_INFO) )

def write_answer(write_file, answer):
    write_file.write(''.join(('\t'.join(str(answer[key]) for key in answer), '\n')))

####################################################################################################################################

def main_worker(file_io):
    file_in = file_io[0]
    file_out = file_io[1]

    result = os.path.join(os.path.dirname(__file__), file_out)
    print(result)
    with open(result, 'w', encoding='utf8') as write_file:
        #Writing info on top of the file
        write_file.write(write_descriptions())

        for entry in reference_data_to_generator(file_in):
            print('Processing', entry['file_path'], ' in ', file_in)
            answer = default_answer(entry)
            
            #Initializes starting time
            answer['Actual String Word Count'] = len(entry['google_result'])
            answer['Matching Time'] = time.time()

            word_group = entry['asr_result_pinyin']
            word_group = retrieve_regex_group(word_group)
            word_group = preprocess_word_group(word_group)
            word_group_regex_length = sum(len(word.strip().split()) for word in word_group)

            ################################################
            result_data = match(entry['google_result_pinyin'], word_group, word_group_regex_length)
            ################################################

            #Store answer from matching result
            #answer['Regex Used'] = result_data['regex']
            answer['Matched String'] = result_data['match_string']
            answer['PinYin Start'] = result_data['start']
            answer['PinYin Length'] = result_data['length']
            answer['Regex Word Count'] = word_group_regex_length
            answer['Matched String Word Count'] = result_data['word_length']
            if word_group_regex_length != 0:
                answer['Word Count Ratio (Matched/Regex)'] = result_data['word_length'] / word_group_regex_length
            answer['Score'] = result_data['score']

            #Answer is found
            if result_data['length'] != -1:
                pinyin_mapping = util.reflect_pinyin_to_result(entry['google_result'], entry['google_result_pinyin'])
                google_result_index = util.pinyin_to_actual_result(pinyin_mapping, result_data['start'], result_data['length'])
            ################################################
                
                answer['Actual Start'] = google_result_index['start']
                answer['Actual Length'] = google_result_index['end'] - google_result_index['start']
                answer['Actual Matched String'] = entry['google_result'][google_result_index['start']:google_result_index['end']]
            answer['Matching Time'] = time.time() - answer['Matching Time']
            write_answer(write_file, answer)

##################################################################################################
import textwrap as _textwrap

class LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
    '''
    Process string searching.
    Format for the input file:
    - Each column must be separated by a tab
    - Total column is 5, with order: FileName, CrawledString, ASR Result, CrawledString in PinYin, ASR Result in PinYin
    ''', formatter_class=LineWrapRawTextHelpFormatter)

    parser.add_argument('file_in', type=str,
                    help='string with absolute path or relative path to the input')
    parser.add_argument('file_out', type=str,
                    help='string with absolute path or relative path to the output')
    parser.add_argument('--minlen', type=float, default=MIN_LENGTH_MULTIPLIER,
                    help='specify multiplier for min length of matched result (multiplied by ASR result word length)\
                    DEFAULT={0} RANGE={1}'.format(MIN_LENGTH_MULTIPLIER, '">=0"'))
    parser.add_argument('--maxlen', type=float, default=MAX_LENGTH_MULTIPLIER,
                    help='specify multiplier for max length of matched result (multiplied by ASR result word length)\
                    DEFAULT={0} RANGE={1}'.format(MAX_LENGTH_MULTIPLIER, '">minlen"'))
    parser.add_argument('--minscore', type=float, default=MIN_GRAM_SCORE,
                    help='specify the minimal score of bigram and trigram combination to be considered an answer\
                    DEFAULT={0} RANGE={1}'.format(MIN_GRAM_SCORE, '">=0"'))
    parser.add_argument('--confusion', type=int, default=CONFUSION_LIST_LENGTH_LIMIT,
                    help='specify number of different confusion possibility to be tested (impact performance if too high)\
                    DEFAULT={0} RANGE={1}'.format(CONFUSION_LIST_LENGTH_LIMIT, '">1"'))
    parser.add_argument('--ignore', type=int, default=GROUP_MAX_DELETION,
                    help='specify the max number of ASR phrase that can be ingnored from the front and end (impact performance if too high)\
                    DEFAULT={0} RANGE={1}'.format(GROUP_MAX_DELETION, '">1"'))
    parser.add_argument('--mingroup', type=int, default=GROUPING_MIN,
                    help='specify min groups of phrase that must be in a successive pattern (impact performance if too low)\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MIN, '">=1"'))
    parser.add_argument('--maxgroup', type=int, default=GROUPING_MAX,
                    help='specify max groups of phrase that must be in a successive pattern (impact performance if range of --maxgroup and --mingroup is too large_\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MAX, '">mingroup"'))

    args = parser.parse_args()
    FILE_IO = (args.file_in, args.file_out)
    MIN_LENGTH_MULTIPLIER = args.minlen
    MAX_LENGTH_MULTIPLIER = args.maxlen
    MIN_GRAM_SCORE = args.minscore
    CONFUSION_LIST_LENGTH_LIMIT = args.confusion
    GROUP_MAX_DELETION = args.ignore
    GROUPING_MIN = args.mingroup
    GROUPING_MAX = args.maxgroup

    main_worker(FILE_IO)

    #main()
