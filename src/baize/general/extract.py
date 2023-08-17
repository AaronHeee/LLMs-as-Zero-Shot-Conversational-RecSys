"""
we create a extract.py under s2q1t1, we try to maintain the results:
  a. all previous results;
  b. rec_list, which record the results of {movie_name:, min_edit_distance: , nearest_movie: };
  c. prev_list, records the previous mentioned movies;
  d. gt_list, which record the results from the ground truth list with standard movie names.
"""


import os
import sys 
import json
from jsonargparse import CLI
from tqdm import tqdm

sys.path.append('./')
from utils import del_parentheses, del_space, del_numbering, extract_movie_name, nearest

DIR = os.path.dirname(os.path.abspath(__file__))

def extract_list(l, candidates=None):
    text = l['resp']['choices'][0]['message']['content']
    try:
        preference, text = text.split('1.', maxsplit=1)
    except Exception as e:
        print(e)
        preference = ""
        text = text.replace(',', '\n')
    rec_list = [del_numbering(del_space(del_parentheses(i.strip()))) for i in text.split('\n')]
    if candidates is not None:
        rec_list = [nearest(i, candidates) for i in rec_list]
    l['rec_list'] = rec_list
    l['preference'] = preference
    return l

def condition(keyword, rec, prev_entity):
    if keyword == 'recommendation':
        return rec not in prev_entity
    elif keyword == 'discussion':
        return rec in prev_entity
    else:
        return True
        
def main(dataset: str = None):
    """ evaluate the genered recommendation list.

    Args:
        dataset (str): dataset name; Defaults to None, can be selected from {redial, inpsired, reddit}.
    """

    # get paths
    pred_json = os.path.join(DIR, f'post_fix/{dataset}_test.jsonl')
    gt_json = os.path.join(DIR, f'../../../data/{dataset}/test.jsonl')
    meta_json = os.path.join(DIR, f'../../../data/{dataset}/entity2id.json')

    # load pred_json
    preds = [json.loads(l) for l in open(pred_json)]

    # load gt_json
    gts = [json.loads(l) for l in open(gt_json)][:len(preds)]
    gts = {i: g for i, g in enumerate(gts)}

    # load meta_json
    name2id = json.load(open(meta_json))
    id2name = {v: extract_movie_name(k) for k, v in name2id.items()}

    # get candidates
    candidates = list(id2name.values())
    pred_list = [extract_list(l, candidates) for l in tqdm(preds)]
    # make sure the index of gts and preds are the same
    pred_dict = {p['index']: p for p in pred_list} 

    # get gt_list and prev_list
    for idx in gts:
        gt = gts[idx]
        gt_list = [id2name[r] for r in gt['rec']]
        prev_list = [id2name[r] for r in gt['prev_entity']]
        pred_dict[idx]['gt_list'] = gt_list
        pred_dict[idx]['prev_list'] = prev_list

    # save the intermediate results
    os.makedirs(os.path.join(DIR, f'intermediate/{dataset}'), exist_ok=True)
    with open(os.path.join(DIR, f'intermediate/{dataset}/extracted.jsonl'), 'w') as f:
        # sorted keys
        for idx in sorted(pred_dict.keys()):
            json.dump(pred_dict[idx], f)
            f.write('\n')

if __name__ == '__main__':
    CLI(main)