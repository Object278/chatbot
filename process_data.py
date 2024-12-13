import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import functools

from langchain.prompts import PromptTemplate
from langchain.prompts import PartialPromptTemplate

'''
环境变量：
webdriver安装地址
本地vllm部署的大模型的端口
prompt最长token数，如果过长可能会需要使用rag获取以前的prompt里面的关键部分
模型名称
'''

def action_error_detector(func):
    """
    A decorator to handle exceptions in action functions.

    Args:
        func (function): The action function to wrap.

    Returns:
        function: The wrapped function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 执行原函数
            func(*args, **kwargs)
            message = f"'{func.__name__}' success."
            return True, message
        except Exception as e:
            # 捕获异常并记录
            error_message = f"'{func.__name__}' error: {str(e)}"
            return False, error_message
    return wrapper

class RoundState():
    def __init__(self):
        self.action = None
        self.observation = []

    def __init__(self, action: str, observation: list[str]):
        self.action = action
        self.observation = observation

    def set_action(self, action: str):
        self.action = action

    def append_observation(self, observation: str):
        self.observation.append(observation)

class RoundPrompt():
    def __init__(self):
        self.round = ""
        self.observation = ""
        self.action = ""

    def __str__(self):
        return f"{self.round}{self.observation}{self.action}"

class RoundStateList():
    def __init__(self):
        # 预先初始化round 0，每次添加action之后，才会初始化下一个round
        # 一个round中，observation列表可以有多个或者没有，但是action必须有一个
        self.state_list = [RoundState()]
        self.prompt_list = [RoundPrompt()]
        self.latest_prompt_index = 0 # 这是roundstate之中当前最新的，也是唯一一个没有填充完成的prompt所在的index
        self.completed_prompt = '' # 这是所有已经填充完毕的prompt所组成的字符串
        self.action_prompt = PromptTemplate(
            input_variables=["action"],
            template="assistant:\n{action}\n"    
        )
        self.observation_prompt = PromptTemplate(
            input_variables=["observation"],
            template="user:\n{observation}\n"
        )
        self.round_prompt = PromptTemplate(
            input_variables=["index"],
            template="Round {index}\n"
        )
        
    # TODO 处理index错误时候怎么办，使用的时候必须遵守流程图定义的顺序
    def add_action(self, index: int, action: str):
        if index != self.latest_prompt_index:
            print("error")
        self.state_list[index].set_action(action)
        self.prompt_list[index].action = self.action_prompt.format(action=action)
        self.state_list.append(RoundState())
        self.prompt_list.append(RoundPrompt())
        self.completed_prompt = self.completed_prompt + str(self.prompt_list[index])
        self.latest_prompt_index += 1

    def add_observation(self, index: int, observation: str):
        if index != self.latest_prompt_index:
            print("error")
        self.state_list[index].append_observation(observation)
        self.prompt_list[index].observation = self.observation_prompt.format(observation=observation)
        self.prompt_list[index].round = self.round_prompt.format(index=index)

    def get_new_prompt(self):
        return self.completed_prompt + str(self.prompt_list[self.latest_prompt_index])
    
    def get_state(self, index: int):
        if index > 0 and index < len(self.state_list):
            return self.state_list[index]
        return None
    
    def update_state(self, index: int, round_state: RoundState):
        if index > 0 and index < len(self.state_list):
            self.state_list[index] = round_state
            self.completed_prompt = str(self)

    def __str__(self):
        ret = ""
        # 只输出已经完成的round
        for i in range(0, self.latest_prompt_index):
            ret = ret + str(self.prompt_list[i])
        return ret

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
        self.action_chains = ActionChains(self.driver)
        self.state = RoundStateList()

        self.round = 0
        self.user_instruction = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting with: " + str(exc_type) + str(exc_val), str(exc_tb))
        self.driver.quit()

    '''
    思考
    '''    
    def ask_oracle(self):
        prompt = self.generate_prompt()
        # 提问

        # 解析回答
        action = ""
        self.add_action(action)

    '''
    观察
    '''
    def get_html_from_query(self, query):
        """
        根据用户输入的查询字符串获取相应的HTML内容。
        """
        url = self.extract_url(query)
        html_raw = None
        if url:
            print(f"检测到URL: {url}")
            html_raw = self.fetch_html_with_selenium(url)
        else:
            print("未检测到URL，访问本地主机的FastAPI服务。")
            html_raw = fetch_html_with_selenium("http://localhost:8000")
        html_clean = self.clean_html_and_add_ids(html_raw)
        self.add_observation(html_clean)

    '''
    行动
    '''
    def do(self, action, **kwargs):
            self.round += 1 
            # TODO汇报任务成功与否
            if action == "Click":
                self.click_element(kwargs["element"])
            elif action == "Hover":
                self.hover_element(kwargs["element"])
            elif action == "Type":
                self.type_message(kwargs["element"], kwargs["message"])
            elif action == "Search":
                self.search_message(kwargs["element"], kwargs["message"])
            elif action == "Press":
                self.press_keys(*kwargs["keys"])
            elif action == "Scroll":
                self.scroll_page(kwargs["direction"])
            elif action == "Select dropdown option":
                self.select_dropdown_option(kwargs["element"], kwargs["value"])
            elif action == "New tab":
                self.open_new_tab()
            elif action == "Tab focus":
                self.focus_tab(kwargs["index"])
            elif action == "Close tab":
                self.close_tab()
            elif action == "Goto":
                self.go_to_url(kwargs["url"])
            elif action == "Go back":
                self.go_back()
            elif action == "Go forward":
                self.go_forward()
            elif action == "Exit":
                self.exit_browser()


    # 一次用户请求执行完了，准备下一次
    def reset():
        pass

    '''
    内部状态管理部分（根据观察和行动结果更新state，生成prompt）
    '''
    def set_user_instruction(self, instruction: str):
        # action是模型返回的，user字段是自己构建的，在同一个round，二者不同时出现，需要分别加入
        self.user_instruction = instruction

    # observation 和 action 都只能添加在当前round的state中，根据规划的工作流程，每次执行action（do函数），round加1，不论action成功还是失败
    def add_observation(self, observation: str):
        self.state.add_observation(self.round, observation)

    def add_action(self, action: str):
        self.state.add_action(self.round, action)

    def generate_prompt(self):
        # 根据上下文限制处理prompt长度，以及其他的参数
        return f"Task Instruction: {self.user_instruction}\n{self.state.get_new_prompt()}"
    '''
    观察部分辅助函数
    '''
    def extract_url(self, query):
        """
        从查询字符串中提取URL。
        """
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        urls = url_pattern.findall(query)
        return urls[0] if urls else None

    def fetch_html_with_selenium(self, url):
        """
        使用Selenium访问指定URL并获取HTML内容。
        """
        # 创建WebDriver实例
        driver = self.driver
        try:
            # 访问指定的URL
            driver.get(url)
            # 等待页面加载完成（可根据需要添加显式等待）
            driver.implicitly_wait(5)  # 隐式等待5秒 TODO 优化
            # 获取页面的HTML内容
            html_content = driver.page_source
            return html_content
        except Exception as e:
            print(f"无法访问URL {url}: {e}")
            return None

    def clean_html_and_add_ids(self, html_content):
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
                # 为可交互的标签添加唯一的 id TODO 再添加每个可交互元素的data-bbox
                if not tag.has_attr('action_id'):
                    tag['action_id'] = f'{id_counter}'
                    id_counter += 1
            elif not tag.get_text(strip=True):
                # 移除不在可交互列表中且不包含可见文本的标签
                tag.decompose()

        # 返回清洗并添加 id 后的 HTML 内容
        return str(soup)

    '''
    行动部分辅助函数
    '''
    @action_error_detector
    def click_element(self, element_id):
        element = self.driver.find_element(By.ID, element_id)
        element.click()

    @action_error_detector
    def hover_element(self, element_id):
        element = self.driver.find_element(By.ID, element_id)
        self.action_chains.move_to_element(element).perform()

    @action_error_detector
    def type_message(self, element_id, message: str):
        # error: 找到的元素不是input_box，返回一个错误信息给
        input_box = self.driver.find_element(By.ID, element_id)
        input_box.clear()
        input_box.send_keys(message)

    @action_error_detector
    def search_message(self, element_id, message):
        input_box = self.driver.find_element(By.ID, element_id)
        input_box.clear()
        input_box.send_keys(message)
        input_box.send_keys(Keys.RETURN)

    # 这个好像有点问题，按照顺序按下按钮应该是down+up，ctrl之类的才是down-down-up-up
    #或者说这个方法单独是针对modified key的，只负责按下ctrl+x之类的
    @action_error_detector
    def press_keys(self, *keys):
        for key in keys:
            self.action_chains.key_down(key)
        for key in reversed(keys):
            self.action_chains.key_up(key)
        self.action_chains.perform()

    @action_error_detector
    def scroll_page(self, direction):
        if direction.lower() == "up":
            self.driver.execute_script("window.scrollBy(0, -window.innerHeight);")
        elif direction.lower() == "down":
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")

    @action_error_detector
    def select_dropdown_option(self, element_id, option_value):
        # error：option value不存在
        dropdown = Select(self.driver.find_element(By.ID, element_id))
        dropdown.select_by_value(option_value)

    @action_error_detector
    def open_new_tab(self):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])

    @action_error_detector
    def focus_tab(self, index):
        self.driver.switch_to.window(self.driver.window_handles[index])

    @action_error_detector
    def close_tab(self):
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[-1])

    @action_error_detector
    def go_to_url(self, url):
        self.driver.get(url)

    @action_error_detector
    def go_back(self):
        self.driver.back()

    @action_error_detector
    def go_forward(self):
        self.driver.forward()

    @action_error_detector
    def exit_browser(self):
        self.driver.quit()

    

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

          