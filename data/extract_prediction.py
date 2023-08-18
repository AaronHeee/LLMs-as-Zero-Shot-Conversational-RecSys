""" Extract the prediction samples from the raw prediction file.
    i.e., ${data}/test_raw.jsonl to ${data}/test.jsonl
"""


import json
from jsonargparse import CLI

def context2input(l, start=0):
    """ Given a list of context, just following UniCRS to format the context.
    """
    context = ''
    for i, utt in enumerate(l):
        if utt == '' or utt == ' ':
            continue
        if i % 2 == start:
            context += '\nUser: '
        else:
            context += '\nSystem: '
        context += utt
    return context + '\nSystem: '

def main(from_json: str = None, to_json: str = None, start: int = 0):
    with open(from_json) as fr, open(to_json, 'w') as fw:
        for l in fr:
            l = json.loads(l)
            if l['is_user'] == 0 and len(l['rec']) > 0:
                l['input'] = context2input(l['context'], start=start)
                fw.write(json.dumps(l) + '\n')

if __name__ == '__main__':
    # python extract_prediction.py --from_json=inspired/test_raw.jsonl --to_json=inspired/test.jsonl --start 0
    # python extract_prediction.py --from_json=redial/test_raw.jsonl --to_json=redial/test.jsonl --start 1
    # python extract_prediction.py --from_json=reddit/test_raw.jsonl --to_json=reddit/test.jsonl --start 1
    CLI(main)