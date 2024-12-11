def format_round(round_index, user_content, assistant_content):
    """
    格式化单轮对话，包括用户输入和助手回复。
    """
    return f"Round {round_index}\nuser:\n{user_content}\n\nassistant:\n{assistant_content}\n"

def format_trajectory(task_instruction, trajectory):
    """
    将单个轨迹转换为所需的输入格式。
    """
    formatted_input = f"Task Instruction: {task_instruction}\n\n"
    for i, step in enumerate(trajectory):
        user_html = step['observation'][-1]['html']
        assistant_action = step['action']
        formatted_input += format_round(i, user_html, assistant_action)
    return formatted_input

def process_data_for_input_format(data):
    """
    将所有轨迹处理为所需的输入格式。
    """
    formatted_data = []
    for traj in data:
        task_instruction = traj[0]['task']
        formatted_input = format_trajectory(task_instruction, traj)
        formatted_data.append(formatted_input)
    return formatted_data

def save_formatted_data(formatted_data, output_path):
    """
    将格式化的数据保存到文件。
    """
    with open(output_path, 'w') as f:
        for item in formatted_data:
            f.write(item + "\n---\n")

# 第一步：记录用户需求和网站HTML
user_demand = "我要查看最新的科技新闻"
website_html = "<html>...</html>"  # 这是您从网站获取的HTML内容

# 第二步：构建单轮对话数据
round_index = 0
user_content = user_demand
assistant_content = ""  # 如果助手尚未回复，可以暂时留空

# 第三步：使用 format_round 函数格式化对话轮次
formatted_round = format_round(round_index, user_content, assistant_content)

# 第四步：构建完整的任务指令和对话历史
task_instruction = user_demand
dialogue_history = [formatted_round]

# 第五步：使用 format_trajectory 函数生成完整输入
formatted_input = format_trajectory(task_instruction, dialogue_history)

# 第六步：保存格式化的数据
output_path = "formatted_input.txt"
save_formatted_data([formatted_input], output_path)            