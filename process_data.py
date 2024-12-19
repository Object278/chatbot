import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import functools
import json
import requests
import time

'''
环境变量：
webdriver安装地址
本地vllm部署的大模型的端口
prompt最长token数，如果过长可能会需要使用rag获取以前的prompt里面的关键部分
模型名称
            "max_tokens": 50,
            "temperature": 0
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
        self.action = ""
        self.response = ""
        self.observation = []

    # def __init__(self, action: str, observation: list[str]):
    #     self.action = action
    #     self.observation = observation

    def set_action(self, action: str):
        self.action = action

    def append_observation(self, observation: str):
        self.observation.append(observation)

    def set_response(self, response: str):
        self.response = response

class RoundStateList():
    def __init__(self, user_instruction: str):
        # 预先初始化round 0，每次添加action之后，才会初始化下一个round
        # 一个round中，observation列表可以有多个或者没有，但是action必须有一个
        self.state_list = [RoundState()]
        self.latest_prompt_index = 0 # 这是roundstate之中当前最新的，也是唯一一个没有填充完成的prompt所在的index
        self.completed_prompt = [
            {"role": "system", "content": "Task instruction: " + user_instruction},
            {"role": "user", "content": "Round 0 " + user_instruction},
        ] # 这是所有已经填充完毕的prompt所组成的字符串
        
    # TODO 处理index错误时候怎么办，使用的时候必须遵守流程图定义的顺序
    def add_action(self, index: int, action: str):
        if index != self.latest_prompt_index:
            print("error")
        self.state_list[index].set_action(action)
        self.completed_prompt.append(
             {"role": "assistant", "content": action}
        )

    def add_observation(self, index: int, observation: str):
        if index != self.latest_prompt_index:
            print("error")
        self.state_list[index].append_observation(observation)

    def add_response(self, index: int, response: str):
        self.state_list.append(RoundState())
        self.latest_prompt_index += 1
        if index != self.latest_prompt_index:
            print("error")
        self.state_list[index].set_response(response)
        self.completed_prompt.append(
             {"role": "user", "content": response}
        )

    def get_new_prompt(self):
        last_content = self.completed_prompt[-1]["content"]
        self.completed_prompt[-1]["content"] = last_content + str(self.state_list[self.latest_prompt_index].observation)
        prompt = json.dumps(self.completed_prompt, indent=4, ensure_ascii=False)
        self.completed_prompt[-1]["content"] = last_content
        return prompt
    
    def get_state(self, index: int):
        if index > 0 and index < len(self.state_list):
            return self.state_list[index]
        return None
    
    def update_state(self, index: int, round_state: RoundState):
        if index > 0 and index < len(self.state_list):
            self.state_list[index] = round_state

# 对应一个selenium webdriver对象，可以独立操作网页并且进行推理。
# 对于web应用，一个websocket session内部一个Agent和多个用户。用户请求通过前端传递给Agent，Agent的操作大家都能看到
class Agent():

    def __init__(self, instruction: str):
        self.state = RoundStateList(instruction + """In the following web page, select the corresponding behavior according to the Task instruction, and give what the "action-id" of the html element corresponding to the action is. Example response format: do(action="Click", actionid="25") or do(action="Search", actionid="26", message="Search content")""")

    def __enter__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        service = Service(executable_path='/usr/local/bin/chromedriver-linux64/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.action_chains = ActionChains(self.driver)
        self.id_center_map = {}

        self.round = 0
        self.user_instruction = None
        self.url = "http://localhost:8000/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json"
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting with: " + str(exc_type) + str(exc_val), str(exc_tb))
        self.driver.quit()

    '''
    思考
    '''    
    def ask_oracle(self):
        prompt = self.generate_prompt()
        # 提问
        try:
            response = requests.post(self.url, headers=self.headers, data=prompt)
            
            # 检查响应状态
            if response.status_code == 200:
                print("Response:")
                print(response.json())  # 输出响应的 JSON 数据
            else:
                print(f"Request failed with status code {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

        # TODO 解析回答
        action = ""
        self.add_action(action)
        return action

    '''
    {
    "id": "chatcmpl-12345",
    "object": "chat.completion",
    "created": 1677652280,
    "model": "glm-4-9b",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "你好！请问有什么我可以帮助您的吗？"
            },
            "finish_reason": "stop"
        }
    ]
}
    '''

    '''
    观察
    '''
    def get_html_from_query(self, url):
        """
        根据用户输入的查询字符串获取相应的HTML内容。
        """
        # url = self.extract_url(query)
        html_raw = self.fetch_html_with_selenium(url)

        html_clean = self.clean_html_and_add_ids(html_raw)
        self.add_observation(html_clean)

    '''
    行动
    '''
    def do(self, action: str, **kwargs):
            action_id = kwargs["element"]
            element = self.id_center_map.get(action_id)
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            
            self.round += 1 
            # TODO汇报任务成功与否
            try:
                if action == "Click":
                    self.click_element(element)
                elif action == "Hover":
                    self.hover_element(element)
                elif action == "Type":
                    self.type_message(element, kwargs["message"])
                elif action == "Search":
                    self.search_message(element, kwargs["message"])
                elif action == "Press":
                    self.press_keys(*kwargs["keys"])
                elif action == "Scroll":
                    self.scroll_page(kwargs["direction"])
                elif action == "Select dropdown option":
                    self.select_dropdown_option(element, kwargs["value"])
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
                else:
                    self.add_response(f"Last action {action} failed, because the {action} function is not defined.")
            except Exception as e:
                self.add_response(f"Last action {action} failed, because of an error {e}. Please think again what to do.")

            self.add_response(f"Last action {action} succeed!")


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

    # 必须在do函数里的round+1之后调用add response
    def add_response(self, response):
        self.state.add_response(self.round, response)

    def generate_prompt(self):
        # 根据上下文限制处理prompt长度，以及其他的参数
        messages = self.state.get_new_prompt()
        data = {
            "model": "glm-4-9b",
            "messages": messages,
            "max_tokens": 50,
            "temperature": 0
        }
        return json.dumps(data, indent=4, ensure_ascii=False)
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
        # try:
        # 访问指定的URL
        driver.get(url)
        # 等待页面加载完成（可根据需要添加显式等待）
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # 获取页面的HTML内容
        html_content = driver.page_source
        time.sleep(2)# 必须睡眠2秒，不能直接进入create id center map的element.tag_name，好像是太快了就会stale element exception

        self.create_id_center_map()
        return html_content
        # except Exception as e:
        #     print(f"无法访问URL {url}: {e}")
        #     return None

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
            for attribute in ['class', 'style', 'id', 'onclick', 'onmouseover']:
                if tag is not None and isinstance(tag.attrs, dict) and attribute in tag.attrs:
                    del tag.attrs[attribute]
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

    def create_id_center_map(self):
        elements = self.driver.find_elements(By.XPATH, "//*")
        id_center_map = {}
        interactive_tags = ['a', 'button', 'input', 'select', 'textarea', 'label', 'form']
        action_id = 0

        for element in elements:
            if element.tag_name.lower() in interactive_tags:
                try:
                    id_center_map[action_id] = element
                except Exception as e:
                    print(f"Error processing element {element}: {e}")

        self.id_center_map = id_center_map

    '''
    行动部分辅助函数
    '''

    def scroll_to_action_id(self, element_id):
        try:
            center = self.id_center_map.get(element_id)
            if not center:
                print(f"No center for action id {element_id}")
                return False
            scroll_x = self.driver.execute_script("return window.scrollX")
            scroll_y = self.driver.execute_script("return window.scrollY")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            if not (scroll_x <= center[0] <= scroll_x + viewport_width and
                scroll_y <= center[1] <= scroll_y + viewport_height):
                # 目标不在视口内，滚动到目标位置
                scroll_origin = ScrollOrigin.from_viewport(0, 0)  # 从视口左上角开始滚动
                scroll_offset_x = center[0] - scroll_x  # 目标相对于当前视口的水平偏移
                scroll_offset_y = center[1] - scroll_y  # 目标相对于当前视口的垂直偏移
                ActionChains(self.driver).scroll_from_origin(scroll_origin, scroll_offset_x, scroll_offset_y).perform()
            return True
        except Exception as e:
            print(f"Error clicking element with action-id {element_id}: {e}")
            return False

    @action_error_detector
    def click_element(self, element):
        element.click()

    @action_error_detector
    def hover_element(self, element):
        self.actionChains(self.driver).move_to_element(element).perform()

    @action_error_detector
    def type_message(self, element, message: str):
        # error: 找到的元素不是input_box，返回一个错误信息给
        input_box = element
        input_box.clear()
        input_box.send_keys(message)

    @action_error_detector
    def search_message(self, element, message):
        input_box = element
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
    def select_dropdown_option(self, element, option_value):
        # error：option value不存在
        dropdown = Select(element)
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

    

# def format_round(round_index, user_content, assistant_content):
#     """
#     格式化单轮对话，包括用户输入和助手回复。
#     """
#     return f"Round {round_index}\nuser:\n{user_content}\n\nassistant:\n{assistant_content}\n"

# def format_trajectory(task_instruction, trajectory: list[RoundState]):
#     """
#     将单个轨迹转换为所需的输入格式。
#     """
#     formatted_input = f"Task Instruction: {task_instruction}\n\n"
#     for i, step in enumerate(trajectory):
#         user_html = step.observation[-1]
#         assistant_action = step.action
#         formatted_input += format_round(i, user_html, assistant_action)
#     return formatted_input

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

# def save_formatted_data(formatted_data, output_path):
#     """
#     将格式化的数据保存到文件。
#     """
#     with open(output_path, 'w') as f:
#         for item in formatted_data:
#             f.write(item + "\n---\n")

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

# '''
# 以上是把state转换为给模型的输入的部分，还有加上prompt的其他部分组成一个http请求，不过这个可以在website.py里完成
# 以下是接受用户请求，获取页面html并进行清洗、给每一个可以点击的组件加上id的部分
# website把请求发送给模型并且收到回复之后，执行action的部分需要再写代码action文件
# action执行完了之后也需要重新获取页面的html
# '''

# def extract_url(query):
#     """
#     从查询字符串中提取URL。
#     """
#     url_pattern = re.compile(
#         r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
#     )
#     urls = url_pattern.findall(query)
#     return urls[0] if urls else None

# def fetch_html_with_selenium(url):
#     """
#     使用Selenium访问指定URL并获取HTML内容。
#     """
#     # 配置Selenium的Chrome选项
#     chrome_options = Options()
#     chrome_options.add_argument('--headless')  # 无头模式，不打开浏览器界面
#     chrome_options.add_argument('--disable-gpu')
#     chrome_options.add_argument('--no-sandbox')
#     chrome_options.add_argument('--disable-dev-shm-usage')

#     # 设置ChromeDriver的路径
#     service = Service(executable_path='/usr/local/bin/chromedriver-linux64/chromedriver')  # 请将此路径替换为实际的ChromeDriver路径

#     # 创建WebDriver实例
#     driver = webdriver.Chrome(service=service, options=chrome_options)
#     try:
#         # 访问指定的URL
#         driver.get(url)
#         # 等待页面加载完成（可根据需要添加显式等待）
#         driver.implicitly_wait(10)  # 隐式等待10秒 TODO 优化
#         # 获取页面的HTML内容
#         html_content = driver.page_source
#         return html_content
#     except Exception as e:
#         print(f"无法访问URL {url}: {e}")
#         return None
#     finally:
#         # 关闭WebDriver实例
#         driver.quit()

# def clean_html_and_add_ids(html_content):
#     """
#     清洗 HTML 内容，保留用户可见和可交互的功能性组件，不影响整体结构，
#     并为所有可点击的组件添加唯一的 id。
#     """
#     soup = BeautifulSoup(html_content, 'html.parser')

#     # 移除 <script> 和 <style> 标签，也许也可以移除div和span标签
#     for script_or_style in soup(['script', 'style']):
#         script_or_style.decompose()

#     # 移除隐藏的元素
#     for hidden_element in soup.find_all(style=lambda value: value and 'display:none' in value):
#         hidden_element.decompose()

#     # 定义可交互的标签
#     interactive_tags = ['a', 'button', 'input', 'select', 'textarea', 'label', 'form']
#     id_counter = 0  # 初始化 id 计数器

#     for tag in soup.find_all(True):  # True 匹配所有标签，也许还可以创建一个索引，保存哪个action_id对应哪个组件，方便后期action文件操作
#         if tag.name in interactive_tags:
#             # 为可交互的标签添加唯一的 id
#             if not tag.has_attr('action_id'):
#                 tag['action_id'] = f'{id_counter}'
#                 id_counter += 1
#         elif not tag.get_text(strip=True):
#             # 移除不在可交互列表中且不包含可见文本的标签
#             tag.decompose()

#     # 返回清洗并添加 id 后的 HTML 内容
#     return str(soup)

# def get_html_from_query(query):
#     """
#     根据用户输入的查询字符串获取相应的HTML内容。
#     """
#     url = extract_url(query)
#     html_raw = None
#     if url:
#         print(f"检测到URL: {url}")
#         html_raw = fetch_html_with_selenium(url)
#     else:
#         print("未检测到URL，访问本地主机的FastAPI服务。")
#         html_raw = fetch_html_with_selenium("http://localhost:8000")
#     return clean_html_and_add_ids(html_raw)

# x = get_html_from_query("https://www.baidu.com/")
# print(x)

          