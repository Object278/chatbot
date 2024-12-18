import os
import tqdm
import json
import torch


def save_jsonl(content, path, mode='w'):
    with open(path, mode) as f:
        for i, line in enumerate(content):
            if i == len(content) - 1:
                f.write(json.dumps(line))
            else:
                f.write(json.dumps(line) + "\n")
                
def read_jsonl(path):
    with open(path, 'r') as f:
        return [json.loads(line) for line in f]

def build_policy_data(dir_path, ouput_path):
    def format_history(contents, index):
            history = ""
            if index == 0:
                return history
            for i in range(index - 1, -1, -1):
                history = f"Round {i}\n\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n{contents[i]['prompt']}\n\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n{contents[i]['fixed_response']}\n\n" + history
            return history

    def format_prompt(instruction, index, html_text, contents):
        history = format_history(contents, index)
        if len(history) + len(html_text) > (16384 - 512):
            html_text = html_text[:(16384 - 512)-len(history)]
        current_turn = f"Round {index}\n\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n{html_text}\n\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        prompt = f"Task Instruction: {instruction}\n\n{history}{current_turn}"
        return prompt

    def template(all_trajectories):
        for traj in all_trajectories:
            for i, step in enumerate(traj):
                instruction = step['task']
                index = i
                html_text = step['observation'][-1]['html']
                contents = step['observation']
                step['observation'] = format_prompt(instruction, index, html_text, contents)
                step['next_observation'] = format_prompt(instruction, index + 1, step['next_observation']['html'], contents + [step['next_observation']])
        return all_trajectories

    traces_dir = 'fixed_traces'
    traces = os.listdir(os.path.join(dir_path, traces_dir))
    data = []
    for trace in tqdm(traces):
        if trace.endswith('.jsonl') == False:
            continue
        trace_content = read_jsonl(os.path.join(dir_path, traces_dir, trace))
        try:
            target = trace_content[-1]['target']
            label = 1 if trace_content[-1]['score'] >= 0.5 else 0
        except:
            continue
        
        new_trace = []
        for i, item in enumerate(trace_content):
            if 'fixed_response' not in item:
                new_trace = []
                break
            new_item = {
                'observation': trace_content[:i + 1],
                'next_observation': trace_content[i + 1] if i != len(trace_content) - 1 else trace_content[i],
                'task': target, 
                'reward': trace_content[-1]['score'], 
                'done': False if i != len(trace_content) - 1 else True, 
                'action': item['fixed_response'], 
                'trajectory_reward': label
            }
            new_trace.append(new_item)
        if len(new_trace) == 0:
            continue
        data.append(new_trace)
    data = template(data)
    torch.save(data, ouput_path)