
"""
We assume only a few requests are failed, so we don't need to use threading in this file, 
we maintain a pool to collect all successful requests, and maintain another pool for 
all the failed requests. All the API Failed requests would not be removed til they get response. 
The results will be put into the configuration folder as post_fix/*.jsonl.
"""


import os
import json
import time

try:
    import openai
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    if openai.api_key is None or openai.api_key == '':
        raise Exception('OPENAI_API_KEY is not set')
except:
    print('[Warning] You do not have openai installed, output fixing might fail！')
    pass
from jsonargparse import CLI

import threading



# set organization
if os.environ.get('OPENAI_ORG') is not None and len(os.environ.get('OPENAI_ORG')) > 6:
    openai.organization = os.environ.get('OPENAI_ORG')

import yaml


def get_response(content, model, temperature, max_tokens):

    res =  openai.ChatCompletion.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": content},
        ])
    
    return res


def main(from_json: str = None, prompt_config: str = None):

    # The results will be put into the configuration folder as post_fix/*.jsonl
    DIR = os.path.dirname(from_json)
    filename = os.path.basename(from_json)
    os.makedirs(os.path.join(DIR, 'post_fix'), exist_ok=True)
    to_json = os.path.join(os.path.dirname(from_json), 'post_fix', filename)

    # Load the prompt config from yaml file
    with open(prompt_config, 'r') as f:
        config = yaml.safe_load(f)

    # Collect succuessful requests and failed requests
    success, failed = [], []

    with open(from_json, "r") as fr:
        for l in fr:
            res = json.loads(l)
            if res['resp'] == 'API Failed':
                failed.append(res)
            else:
                success.append(res)
    print(f'Failed requests: {len(failed)} / {len(success) + len(failed)}')

    # Re-request the failed requests
    while len(failed) > 0:

        current = failed[0]

        try:
            response = get_response(current['prompt'], config['model'], config['temperature'], config['max_tokens'])
            current['resp'] = response 
            success.append(current)
            failed.pop(0)
            print(f'Failed requests: {len(failed)} / {len(success) + len(failed)}')

        except Exception as e:
            print(e)
            time.sleep(1)

    # Sort the results by the order of index
    success = sorted(success, key=lambda x: x['index'])

    # Write the results into the file
    with open(to_json, 'w') as fw:
        for s in success:
            fw.write(json.dumps(s) + '\n')


if __name__ == '__main__':
    CLI(main)
