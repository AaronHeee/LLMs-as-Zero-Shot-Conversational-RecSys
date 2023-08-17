""" 
1. We actually want to report results in different settings using `_tools/evaluate.py`
    `{filtered_False, filtered_True} x {exclude_seen_False, exclude_seen_True}`;
2. For each setting, we also consider `{recommendation, discussion, all}` conditions.
3. We save the sample-wise results per setting (which can be used for significance test), which named:
    - `filtered_*_exclude_seen_*/{condition}.csv`
4. We also report the aggregated results in each setting, where we record the mean, standard error, CI (w/ 95% confidence level) of the metric:
    - `filtered_*_exclude_seen_*/summary.csv`
5. All the processed results are saved into the `intermediate/**/extracted.jsonl`'s directory.
"""

import os
import json
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

import numpy as np
from jsonargparse import CLI


def main(from_json: str = None, threshold: int = 2):
    # get to_dir
    to_dir = os.path.dirname(from_json)

    # settings
    settings = {
        'filtered': [False, True],
        'exclude_seen': [False, True],
    }

    # load from_json
    preds = [json.loads(l)['rec_list'] for l in open(from_json)]
    gts = [json.loads(l)['gt_list'] for l in open(from_json)]
    prevs = [json.loads(l)['prev_list'] for l in open(from_json)]

    # get the results
    for filtered in settings['filtered']:
        for exclude_seen in settings['exclude_seen']:
            # get pred_list, gt_list and condition list
            pred_list, gt_list, condition_list, idx_list = [], [], [], []
            for idx, (pred, gt, prev) in enumerate(zip(preds, gts, prevs)):
                # filter the pred_list
                if filtered: # exclude items that are out-of-vocabulary
                    pred = [p['nearest_movie'] for p in pred if p['min_edit_distance'] <= threshold]
                else:
                    pred = [p['nearest_movie'] for p in pred]

                # exclude items that are already seen
                if exclude_seen: 
                    pred = [p for p in pred if p not in prev]

                # extend gt list
                for gt_ in gt:
                    gt_list.append(gt_)
                    pred_list.append(pred)
                    condition_list.append(gt_ in prev) # whether this gt was mentioned in the previous conversation
                    idx_list.append(idx)

            # get the results
            res_rec, res_dis, res_all = evaluate(pred_list, gt_list, condition_list, idx_list)

            # save the results
            os.makedirs(os.path.join(to_dir, f'filtered_{filtered}_exclude_seen_{exclude_seen}'), exist_ok=True)
            res_rec.to_csv(os.path.join(to_dir, f'filtered_{filtered}_exclude_seen_{exclude_seen}/rec.csv'), index=False)
            res_dis.to_csv(os.path.join(to_dir, f'filtered_{filtered}_exclude_seen_{exclude_seen}/dis.csv'), index=False)
            res_all.to_csv(os.path.join(to_dir, f'filtered_{filtered}_exclude_seen_{exclude_seen}/all.csv'), index=False)

            # aggregate the results
            df = pd.DataFrame()
            for name, res in [('recommendation', res_rec), ('discussion', res_dis), ('all', res_all)]:
                res_agg = aggreagte(res)
                res_agg.insert(0, 'condition', name)
                df = pd.concat([df, res_agg], ignore_index=True)

            # save the aggregated results
            df.to_csv(os.path.join(to_dir, f'filtered_{filtered}_exclude_seen_{exclude_seen}/summary.csv'), index=False)

    print(f'Results are saved in {to_dir}!')

def evaluate(pred_list, gt_list, condition_list, idx_list, Ks=[1, 5, 10, 20]):
    """ evaluate the genered recommendation list and return the results in pd.DataFrame.
    Args:
        pred_list (list of list of str): movie names in the vocabulary, which is predicted by the model.
        gt_list (list of str): movie name in the ground truth list.
        condition_list (list): whether this gt was mentioned in the previous conversation.
    Returns:
        res_rec (pd.DataFrame): results of recommendation list.
        res_dis (pd.DataFrame): results of discussion list.
        res_all (pd.DataFrame): results of all list.
    """

    # calculate the results
    results = defaultdict(list)
    for idx, pred, gt, condition in tqdm(zip(idx_list, pred_list, gt_list, condition_list)):
        results['idx'].append(idx)
        results['condition'].append('dis' if condition else 'rec')
        for k in Ks:
            # recall@k
            recall = int(gt in pred[:k])
            # ndcg@k
            ndcg = 1 / np.log2(pred[:k].index(gt) + 2) if gt in pred[:k] else 0
            # mrr@k
            mrr = 1 / (pred[:k].index(gt) + 1) if gt in pred[:k] else 0
            # save the results
            results[f'recall@{k}'].append(recall)
            results[f'ndcg@{k}'].append(ndcg)
            results[f'mrr@{k}'].append(mrr)

    # create the dataframe
    res_all = pd.DataFrame(results)
    res_rec = res_all[res_all['condition'] == 'rec']
    res_dis = res_all[res_all['condition'] == 'dis']

    # return the results
    return res_rec, res_dis, res_all


def aggreagte(res):
    """ all the fileds except `condition` are aggregated.
    Args:
        res (pd.DataFrame): results of recommendation results sample-wisely, 
            in terms of recall@k, ndcg@k, mrr@k.
    Returns:
        res_agg (pd.DataFrame): aggregated results of recommendation results, 
            in terms of {metric}@k_mean, {metric}@k_se, {metric}@k_ci.
    """
    # remove the condition and idx column
    res = res.drop(columns=['condition'])
    res = res.drop(columns=['idx'])

    # get the mean, standard error, 95% CI
    res_agg = pd.DataFrame()
    for k in res.columns:
        # mean
        mean = res[k].mean()
        # standard error
        se = res[k].sem()
        # 95% CI
        ci = 1.96 * se
        # save the results
        res_agg[f'{k}_mean'] = [mean]
        res_agg[f'{k}_se'] = [se]
        res_agg[f'{k}_ci'] = [ci]

    # return the results
    return res_agg


if __name__ == '__main__':
    CLI(main)

