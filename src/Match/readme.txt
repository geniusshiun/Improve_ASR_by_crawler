新增可調參數版本: (詳閱 generate_diff.py -h)
 簡單說明幾個參數
   parser.add_argument('--ignore', type=int, default=GROUP_MAX_DELETION,
                    help='specify the max number of ASR phrase that can be ingnored from the front and end (impact performance if too high)\
                    DEFAULT={0} RANGE={1}'.format(GROUP_MAX_DELETION, '">1"'))
    parser.add_argument('--mingroup', type=int, default=GROUPING_MIN,
                    help='specify min groups of phrase that must be in a successive pattern (impact performance if too low)\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MIN, '">=1"'))
    parser.add_argument('--maxgroup', type=int, default=GROUPING_MAX,
                    help='specify max groups of phrase that must be in a successive pattern (impact performance if range of --maxgroup and --mingroup is too large_\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MAX, '">mingroup"'))

mingroup代表最小檢查group數 (範圍: 0~n,  0代表index=0 亦即一個group)
maxgroup代表最大檢查group數 (範圍: mingroup~n)
ignore(default=GROUP_MAX_DELETION) 代表檢查時可以跳過的group數 

這三個值可視為一組同時調整  預設為 GROUP_MAX_DELETION 9 ; mingroup: 3 maxgroup: 6
這比較適合用在自動收集下來的網頁 做快速的大概抓取範圍

若改為  GROUP_MAX_DELETION 2 ; mingroup: 1 maxgroup: 2
比較適合用在人工確認已經找到最正確的網頁  抓取比較準確的範圍  要花比較多的時間比對 但找出來的範圍會很準確