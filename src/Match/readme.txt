�s�W�i�հѼƪ���: (�Ծ\ generate_diff.py -h)
 ²�满���X�ӰѼ�
   parser.add_argument('--ignore', type=int, default=GROUP_MAX_DELETION,
                    help='specify the max number of ASR phrase that can be ingnored from the front and end (impact performance if too high)\
                    DEFAULT={0} RANGE={1}'.format(GROUP_MAX_DELETION, '">1"'))
    parser.add_argument('--mingroup', type=int, default=GROUPING_MIN,
                    help='specify min groups of phrase that must be in a successive pattern (impact performance if too low)\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MIN, '">=1"'))
    parser.add_argument('--maxgroup', type=int, default=GROUPING_MAX,
                    help='specify max groups of phrase that must be in a successive pattern (impact performance if range of --maxgroup and --mingroup is too large_\
                    DEFAULT={0} RANGE={1}'.format(GROUPING_MAX, '">mingroup"'))

mingroup�N��̤p�ˬdgroup�� (�d��: 0~n,  0�N��index=0 ��Y�@��group)
maxgroup�N��̤j�ˬdgroup�� (�d��: mingroup~n)
ignore(default=GROUP_MAX_DELETION) �N���ˬd�ɥi�H���L��group�� 

�o�T�ӭȥi�����@�զP�ɽվ�  �w�]�� GROUP_MAX_DELETION 9 ; mingroup: 3 maxgroup: 6
�o����A�X�Φb�۰ʦ����U�Ӫ����� ���ֳt���j������d��

�Y�אּ  GROUP_MAX_DELETION 2 ; mingroup: 1 maxgroup: 2
����A�X�Φb�H�u�T�{�w�g���̥��T������  �������ǽT���d��  �n�����h���ɶ���� ����X�Ӫ��d��|�ܷǽT