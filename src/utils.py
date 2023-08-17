import re
import numpy as np

from collections import defaultdict
from editdistance import eval as distance

def del_parentheses(text):
    pattern = r"\([^()]*\)"
    return re.sub(pattern, "", text)

def del_space(text):
    pattern = r"\s+"
    return re.sub(pattern, " ", text).strip()

def del_numbering(text):
    pattern = r"^(?:\d+[\.\)、]?\s*[\-\—\–]?\s*)?"
    return re.sub(pattern, "", text)

def is_in(text, items, threshold):
    for i in items:
        if (distance(i.lower(), text.lower()) <= threshold):
            return True
    return False

def nearest(text, items):
    """ given the raw text name and all candidates, 
        return {movie_name:, min_edit_distance: , nearest_movie: }
    """
    # calculate the edit distance
    items = list(set(items))
    dists = [distance(text.lower(), i.lower()) for i in items]
    # find the nearest movie
    nearest_idx = np.argmin(dists)
    nearest_movie = items[nearest_idx]
    return {
        'movie_name': text, 
        'min_edit_distance': dists[nearest_idx], 
        'nearest_movie': nearest_movie
    }


def extract_movie_name(text):
    text = text.split('/')[-1]
    text = text.replace('_', ' ').replace('-', ' ').replace('>', ' ')
    return del_space(del_parentheses(text))

def recall_score(gt_list, pred_list, ks, threshold, verbose=False):
    hits = defaultdict(list)
    for gt, preds in zip(gt_list, pred_list):
        for k in ks:
            hits[k].append(int(is_in(gt, preds[:k], threshold)))
    if verbose:
        for k in ks:
            print("Recall@{}: {:.4f}".format(k, np.mean(hits[k])))
    return hits
    

def mrr_score(gt_list, pred_list, ks, threshold, verbose=False):
    mrrs = defaultdict(list)
    for gt, preds in zip(gt_list, pred_list):
        for k in ks:
            for i, p in enumerate(preds[:k]):
                if is_in(gt, [p], threshold):
                    mrrs[k].append(1 / (i + 1))
                else:
                    mrrs[k].append(0)
    if verbose:
        for k in ks:
            print("MRR@{}: {:.4f}".format(k, np.mean(mrrs[k])))
    return mrrs

def ndcg_score(gt_list, pred_list, ks, threshold, verbose=False):
    ndcgs = defaultdict(list)
    for gt, preds in zip(gt_list, pred_list):
        for k in ks:
            for i, p in enumerate(preds[:k]):
                if is_in(gt, [p], threshold):
                    ndcgs[k].append(1 / np.log2(i + 2))
                    break
    if verbose:
        for k in ks:
            print("NDCG@{}: {:.4f}".format(k, np.mean(ndcgs[k])))
    return ndcgs