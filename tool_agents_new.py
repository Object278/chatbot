# New tool agents, EasyOCR + full simulation of mouse move and keyboard action
import easyocr

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from transformers import pipeline
from bs4 import BeautifulSoup
from main import State
from lxml import etree
from selenium.webdriver.common.action_chains import ActionChains

class Website():
    pass

def coordination_transformation(bbox):
    # 设计一套坐标体系，能包含页面坐标，视口坐标
    pass

def to_link_and_peek(link: str, state: State): 
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path='/path/to/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(link)
    # 用额外的函数保存page source和滚动页面之后的screenshot，测试版先这样
    page_source = driver.page_source
    screenshot_path = "screenshot.png"
    driver.save_screenshot(screenshot_path)
    # driver 需要作为一个长久存在的东西

    # Extract text
    soup = BeautifulSoup(page_source, 'html.parser')
    text = soup.get_text()
    # Summary
    summarizer = pipeline("summarization")
    summary = summarizer(text, max_length=130,
                             min_length=30, do_sample=False)
    # OCR
    reader = easyocr.Reader(['en', 'ch'])
    result = reader.readertext(screenshot_path)
    texts = [detection[1] for detection in result]
    bbox = [detection[0] for detection in result]
    # 对bbox进行坐标变换，变为以左上角为原点的坐标，并且计算中心点center
    bbox = coordination_transformation(bbox)

    ui_element = []
    ui_context = []
    actions = ActionChains(driver)
    for box in bbox:
        script = f"return document.elementFromPoint({box.center.x}, {box.center.y});"
        element_html = driver.execute_script(script)
        # 返回的html元素可以进行许多操作，甚至可以修订ocr识别出来的外框的范围，但python对象需要通过javascript脚本才能访问到原生的DOM属性
        # 想出来一种context的格式
        ui_element.append(element_html)
        ui_context.append("context TODO")

    # put all these information into the state

    # Form a prompt ask the llm what to do next based on user

    driver.quit()

    prompt = "" + str(state)

    return prompt

    # reason function ask the oracle this prompt


# 下面是在网页上，agent可以进行的基础操作，这些基础操作模仿人使用网站的操作而定义
# 均是可以由selenium完成的基础操作，但是稍微把一些过于细节的操作融合在一起
# Level 1较为基础
def input_text():
    # 输入一个文本框，用户名，邮箱或者密码都在这一类，search方法可以由这个和click组合出来
    pass

def click():
    # 点击一个元素，可以被语义化扩展为：select_element_in_sidebar, choose等等，本质都是执行一个点击操作
    pass

def forward():
    # Selenium操作页面往前
    pass

def backward():
    # Selenium操作页面回到上一步
    pass

def dropdown_list():
    # 处理下拉列表选择，可以组合为选择生日，选择预定日期等等
    pass

# Level 2 更加语义化集成
def search():
    input_text()
    click()


# 检测网页有没有因为操作由视觉上的更新，判断要不要重新peek网页
def check_update():
    pass

