""" Extract the prediction samples from the raw prediction file.
    i.e., ${data}/test_raw.jsonl -> ${data}/test_p2.jsonl
    here p* means placeholder 2, which is from https://github.com/AaronHeee/Probing-LLMs-Conv-Rec/issues/1.
"""

import random
import json
from jsonargparse import CLI
from collections import defaultdict
import itertools
import numpy as np

def context2input(l, placeholder, movie_names, movie_names_all, start=0):
    """ Given a list of context, just following UniCRS to format the context.
    """
    context = ''

    movie_names_flatten = [element for sublist in movie_names for element in sublist]

    for i, (utt, movie_name) in enumerate(zip(l['context'], [[]] + movie_names)):
        if utt == '' or utt == ' ':
            continue
        if i % 2 == start:
            context += '\nUser: '
        else:
            context += '\nSystem: '

        # Placeholder 2: using historical mentioned movies only;
        if placeholder == 'p2':
            utt_ = ", ".join(movie_name)

        # Placeholder 3: using historical conversational text without mentioned movies;
        if placeholder == 'p3':
            utt_ = utt
            for movie_name in movie_names_flatten:
                utt_ = utt_.replace(movie_name, '')

        # Placeholder 4: using historical conversational text with randomly mentioned movies.
        if placeholder == 'p4':
            utt_ = utt
            for movie_name in movie_names_flatten:
                utt_ = utt_.replace(movie_name, random.choice(movie_names_all))
        
        context += utt_
    
    return context + '\nSystem: '

def main(from_json: str = None, placeholder: str = 'p2', start: int = 0):
    to_json = from_json.replace('raw', placeholder)

    movie_names_all, movie_names = set(), defaultdict(list)
    with open(from_json) as fr, open(to_json, 'w') as fw:
        for l in fr:
            l = json.loads(l)
            movie_names_all |= set(l['entity_name'][len(l['entity_name'])-len(l['rec']):]) # the movie names are last len(rec) entity names

    movie_names_all = list(movie_names_all)

    with open(from_json) as fr, open(to_json, 'w') as fw:
        for l in fr:
            l = json.loads(l)
            movie_names[l['dialog_id']].append(l['entity_name'][len(l['entity_name'])-len(l['rec']):])

            if l['is_user'] == 0 and len(l['rec']) > 0:
                l['input'] = context2input(l, placeholder, movie_names[l['dialog_id']], movie_names_all, start=start)
                fw.write(json.dumps(l) + '\n')

if __name__ == '__main__':
    # python extract_ablation.py --from_json=inspired/test_raw.jsonl --placeholder=p2
    # python extract_ablation.py --from_json=reddit/test_raw.jsonl --placeholder=p2
    CLI(main)