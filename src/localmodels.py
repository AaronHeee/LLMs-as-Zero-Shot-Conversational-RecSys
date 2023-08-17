import os
import json
import time
import torch
import transformers

from fastchat.conversation import get_default_conv_template, compute_skip_echo_len
from fastchat.serve.inference import load_model
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"  
from easydict import EasyDict as edict
from jsonargparse import CLI
from tqdm import tqdm
from transformers import AutoTokenizer


def get_hf_model_response(
    model, 
    tokenizer, 
    index, 
    text, 
    prompt, 
    temperature=0.0, 
    max_tokens=1024, 
    results=None,
    args=None
):
    """
    Get response from a general huggingface model that has .generate method implemented
    """
    try:
        # block of code for generating output
        # since vicuna is trained in a very specific way
        model_input = prompt.format(text)
        inputs = tokenizer([model_input])
        output_ids = model.generate(
            torch.as_tensor(inputs.input_ids).to(model.device),
            temperature=temperature,
            max_new_tokens=max_tokens,
        )
        outputs = tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
        # wrap this into openAI-like format so it won't break evaluation code.
        outputs = {
            'id' : 'dummy',
            'object' : 'dummy',
            'created' : 'dummy',
            'model': args.model_path,
            'usage' : 'dummy',
            'choices':[{'message': {'role': 'assistant','content': outputs},'finish_reason': 'stop','index': 0}]
        }
        response = {'index': index, 'prompt': model_input, 'resp': outputs}
        if results is not None:
            results.append(response)
        return response
    except Exception as e:
        if e == KeyboardInterrupt:
            raise e
        print(e)
        time.sleep(2)
        if results is not None:
            results.append({'index': index, 'prompt': model_input,
                           'resp': "model Failed"})


def get_vicuna_response(
    model, 
    tokenizer, 
    index, 
    text, 
    prompt, 
    temperature=0.0, 
    max_tokens=1024, 
    results=None,
    args=None
):
    """
    Get response from vicuna
    """
    try:
        # block of code for generating output
        # since vicuna is trained in a very specific way
        conv = get_default_conv_template(args.model_path).copy()
        conv.append_message(conv.roles[0], prompt.format(text))
        conv.append_message(conv.roles[1], None)
        vicuna_input = conv.get_prompt()
        inputs = tokenizer([vicuna_input])
        output_ids = model.generate(
            torch.as_tensor(inputs.input_ids).to(model.device),
            temperature=temperature,
            max_new_tokens=max_tokens,
        )
        outputs = tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
        skip_echo_len = compute_skip_echo_len(args.model_path, conv, prompt)
        outputs = outputs[len(vicuna_input):]
        # wrap this into openAI-like format so it won't break evaluation code.
        outputs = {
            'id' : 'dummy',
            'object' : 'dummy',
            'created' : 'dummy',
            'model': args.model_path,
            'usage' : 'dummy',
            'choices':[{'message': {'role': 'assistant','content': outputs},'finish_reason': 'stop','index': 0}]
        }
        response = {'index': index, 'prompt': vicuna_input, 'resp': outputs}
        if results is not None:
            results.append(response)
        return response
    except Exception as e:
        if e == KeyboardInterrupt:
            raise e
        print(e)
        time.sleep(2)
        if results is not None:
            results.append({'index': index, 'prompt': vicuna_input,
                           'resp': "model Failed"})
            

def main(from_json: str = None, to_json: str = None, prompt: str = None,
         pretrained_model_name_or_path: str = 'gpt-3.5-turbo', temperature: float = 0, max_tokens: int = 512, 
         n_print: int = 100, n_samples: int = -1, input_field: str = 'input',use_tqdm=True,
         huggingface_model_type='AutoModelForCausalLM'):
    
    if ('vicuna' in pretrained_model_name_or_path) or\
    ('baize' in pretrained_model_name_or_path):
        print('using lmsys inference mode')
        # this is some psuedo args for using lmsys
        # to load vicuna
        args = edict({
            'model_path' : pretrained_model_name_or_path,
            'device' : 'cuda',
            'num_gpus' : '1',
            'max_gpu_memory' : '44Gib',
            'load_8bit' : False,
            'debug' : False,
        })
        model, tokenizer = load_model(
                args.model_path,
                args.device,
                args.num_gpus,
                args.max_gpu_memory,
                args.load_8bit,
                debug=args.debug,
            )
        get_response = get_vicuna_response
    else:
        get_response = get_hf_model_response
        model = eval('transformers.'+huggingface_model_type).from_pretrained(pretrained_model_name_or_path)
        tokenizer = AutoTokenizer.from_pretrained(pretrained_model_name_or_path)
        args = edict({
            'model_path' : pretrained_model_name_or_path
        })
    

    with open(from_json, "r") as fr, open(to_json, 'w') as fw:

        threads, results = [], []

        lines = fr.readlines()
        total_lines = len(lines)
        start_time = time.time()
        
        for i,l in tqdm(enumerate(lines), total=len(lines), disable=not use_tqdm):
            if i == n_samples:
                break 
            text = json.loads(l)[input_field]
            get_response(
                index=i, 
                text=text, 
                prompt=prompt, 
                model=model, 
                tokenizer=tokenizer,
                temperature=temperature, 
                max_tokens=max_tokens, 
                results=results, 
                args=args
            )
            if i % n_print == 0:
                print(f'Time elapsed: {time.time() - start_time:.2f} sec. {i} / {total_lines} samples generated. ')

        for res in results:
            fw.write(json.dumps(res)+'\n')


if __name__ == '__main__':
    CLI(main)