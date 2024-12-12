import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
from bs4 import BeautifulSoup


class RoundState():
    def __init__(self):
        self.action = None
        self.observation = []

    def __init__(self, action: str, observation: list[str]):
        self.action = action
        self.observation = observation

    def set_action(self, action: str):
        self.action = action

    def append_observation(self, observation: list[str]):
        self.observation.append(observation)

class RoundStateList():
    pass

# 对应一个selenium webdriver对象，可以独立操作网页并且进行推理。
# 对于web应用，一个websocket session内部一个Agent和多个用户。用户请求通过前端传递给Agent，Agent的操作大家都能看到
class Agent():
    def __start__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        service = Service(executable_path='/usr/local/bin/chromedriver-linux64/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.state = RoundStateList()

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting with: " + str(exc_type) + str(exc_val), str(exc_tb))
        self.driver.quit()

    def add_state():
        # action是模型返回的，user字段是自己构建的，在同一个round，二者不同时出现，需要分别加入
        pass

    def do():
        pass

    def get_html_from_query(query):
        pass

    def run():
        pass

    

def format_round(round_index, user_content, assistant_content):
    """
    格式化单轮对话，包括用户输入和助手回复。
    """
    return f"Round {round_index}\nuser:\n{user_content}\n\nassistant:\n{assistant_content}\n"

def format_trajectory(task_instruction, trajectory: list[RoundState]):
    """
    将单个轨迹转换为所需的输入格式。
    """
    formatted_input = f"Task Instruction: {task_instruction}\n\n"
    for i, step in enumerate(trajectory):
        user_html = step.observation[-1]
        assistant_action = step.action
        formatted_input += format_round(i, user_html, assistant_action)
    return formatted_input

# def process_data_for_input_format(data):
#     """
#     将所有轨迹处理为所需的输入格式。
#     """
#     formatted_data = []
#     for traj in data:
#         task_instruction = traj[0]['task']
#         formatted_input = format_trajectory(task_instruction, traj)
#         formatted_data.append(formatted_input)
#     return formatted_data

def save_formatted_data(formatted_data, output_path):
    """
    将格式化的数据保存到文件。
    """
    with open(output_path, 'w') as f:
        for item in formatted_data:
            f.write(item + "\n---\n")

# 第一步：记录用户需求和网站HTML
# user_demand = "User instruction"
# website_html = "<html>...</html>"  # 这是您从网站获取的HTML内容
# round0state = RoundState("""# Element: the 'Sales' menu item on the left sidebar, second from the top do(action="Click", element="2")""", ["Simplified HTML"])
# round1state = RoundState("""# Element: the 'Orders' link \n do(action="Click", element="4")""", ["** Simplified html **"])
# round2state = RoundState("", [""" <html data-bbox="0,0,1280,720"><body data-bbox="0,0,1280,968"><div data-bbox="0,0,88,721"> <ul data-bbox="0,75,88,646"> <span id="1" data-bbox="14,112,60,13"> Dashboard </span> <button id="24" type="button" data-bbox="548,305,18,17"> </button> </li> </ul> """])
# trajectory = [round0state, round1state, round2state]

# # 第五步：使用 format_trajectory 函数生成完整输入
# formatted_input = format_trajectory(user_demand, trajectory)
# print(formatted_input)

'''
以上是把state转换为给模型的输入的部分，还有加上prompt的其他部分组成一个http请求，不过这个可以在website.py里完成
以下是接受用户请求，获取页面html并进行清洗、给每一个可以点击的组件加上id的部分
website把请求发送给模型并且收到回复之后，执行action的部分需要再写代码action文件
action执行完了之后也需要重新获取页面的html
'''

def extract_url(query):
    """
    从查询字符串中提取URL。
    """
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    urls = url_pattern.findall(query)
    return urls[0] if urls else None

def fetch_html_with_selenium(url):
    """
    使用Selenium访问指定URL并获取HTML内容。
    """
    # 配置Selenium的Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式，不打开浏览器界面
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 设置ChromeDriver的路径
    service = Service(executable_path='/usr/local/bin/chromedriver-linux64/chromedriver')  # 请将此路径替换为实际的ChromeDriver路径

    # 创建WebDriver实例
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        # 访问指定的URL
        driver.get(url)
        # 等待页面加载完成（可根据需要添加显式等待）
        driver.implicitly_wait(10)  # 隐式等待10秒 TODO 优化
        # 获取页面的HTML内容
        html_content = driver.page_source
        return html_content
    except Exception as e:
        print(f"无法访问URL {url}: {e}")
        return None
    finally:
        # 关闭WebDriver实例
        driver.quit()

def clean_html_and_add_ids(html_content):
    """
    清洗 HTML 内容，保留用户可见和可交互的功能性组件，不影响整体结构，
    并为所有可点击的组件添加唯一的 id。
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 移除 <script> 和 <style> 标签，也许也可以移除div和span标签
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()

    # 移除隐藏的元素
    for hidden_element in soup.find_all(style=lambda value: value and 'display:none' in value):
        hidden_element.decompose()

    # 定义可交互的标签
    interactive_tags = ['a', 'button', 'input', 'select', 'textarea', 'label', 'form']
    id_counter = 0  # 初始化 id 计数器

    for tag in soup.find_all(True):  # True 匹配所有标签，也许还可以创建一个索引，保存哪个action_id对应哪个组件，方便后期action文件操作
        if tag.name in interactive_tags:
            # 为可交互的标签添加唯一的 id
            if not tag.has_attr('action_id'):
                tag['action_id'] = f'{id_counter}'
                id_counter += 1
        elif not tag.get_text(strip=True):
            # 移除不在可交互列表中且不包含可见文本的标签
            tag.decompose()

    # 返回清洗并添加 id 后的 HTML 内容
    return str(soup)

def get_html_from_query(query):
    """
    根据用户输入的查询字符串获取相应的HTML内容。
    """
    url = extract_url(query)
    html_raw = None
    if url:
        print(f"检测到URL: {url}")
        html_raw = fetch_html_with_selenium(url)
    else:
        print("未检测到URL，访问本地主机的FastAPI服务。")
        html_raw = fetch_html_with_selenium("http://localhost:8000")
    return clean_html_and_add_ids(html_raw)

x = get_html_from_query("https://www.baidu.com/")
print(x)

          