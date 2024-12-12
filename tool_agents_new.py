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
import time

class Website():
    pass

class Peek():
    # 需要定义一下一次peek结束之后的
    # 只有ocr，大模型也许也可以推理的，加上html元素肯定更好，可以都测试一下
    # ui元素，bbox最终都需要采用绝对坐标表示位置，但是需要用相对坐标获取
    # 需要对ocr，获取html元素等等做时间分析
    '''
    边界框: [[(15, 30), (150, 30), (150, 70), (15, 70)]]
    识别文本: Hello, World!
    置信度: 0.987
    边界框中心：(x, y)
    中心点对应的ui元素：str
    ui元素的上下文：str
    '''
    def __enter__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        service = Service(executable_path='/usr/local/bin/chromedriver-linux64/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.ocr_reader = easyocr.Reader(['en', 'ch'])

        self.peekCount = 0

    def __init__(self, resolution = (1920, 1080), max_screenshots = 3):
        self.resolution = resolution
        self.max_screenshots = max_screenshots
        self.driver.set_window_size(resolution[0], resolution[1])

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting with: " + str(exc_type) + str(exc_val), str(exc_tb))
        self.driver.quit()

    def _coordination_transformation(self, detection_result):
        # 设计一套坐标体系，能包含页面坐标，视口坐标
        script = "return {x: window.scrollX, y: window.scrollY};"
        scroll_offset = self.driver.execute_script(script)

        for detection in detection_result:
            # 页面绝对坐标
            detection = list(detection)
            bbox = detection[0][0]
            for point in bbox:
                point = (point[0] + scroll_offset['x'], point[1] + scroll_offset['y'])
            # 这样写应该不用绝对值
            center = ((bbox[1][0] - bbox[0][0]) / 2, (bbox[2][1] - bbox[0][1]) / 2)
            detection.append(center)

    def _calculate_center(self, result):
        for detection in result:
            bbox = detection[0][0]
            center = ((bbox[1][0] - bbox[0][0]) / 2, (bbox[2][1] - bbox[0][1]) / 2)
            detection.append(center)

    def _get_html_element(self, result):
        pass
    
    def _take_screenshot_and_OCR(self):
        # 滚动页面，最多拍max_screenshots张照片，目前只支持往下滚
        # peekCount代表peek页面的次数，是否peek由页面是否发生视觉改变决定
        # peekCount也是这次peek形成的state的唯一id
        # 以后可以变成文件夹
        pixels = self.resolution[1]
        scroll_script = f"window.scrollBy(0, {pixels})"
        
        for i in range(self.max_screenshots):
            screenshot_path = f"screenshot_{self.peekCount}_{i}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # time.sleep(1),也许ocr的时间就相当于主动等了半秒？
            ocr_result = self.ocr_reader.readtext(screenshot_path)
            # 转变List[Tuple] to List[List]方便添加别的内容
            ocr_result = [list(detection) for detection in ocr_result]
            # 计算中心点相对坐标
            self._calculate_center(ocr_result)
            ui_element = []
            ui_context = []
            for detection in ocr_result:
                script = f"return document.elementFromPoint({box.center.x}, {box.center.y});"
                element_html = self.driver.execute_script(script)
                # 返回的html元素可以进行许多操作，甚至可以修订ocr识别出来的外框的范围，但python对象需要通过javascript脚本才能访问到原生的DOM属性
                # 想出来一种context的格式
                ui_element.append(element_html)
                ui_context.append("context TODO")
                
            self.driver.execute_script(scroll_script)
            ocr_result = self._coordination_transformation(ocr_result)
            time.sleep(0.5)


    def to_link_and_peek(self, link: str, state: State): 
        
        self.driver.get(link)
        # 用额外的函数保存page source和滚动页面之后的screenshot，测试版先这样
        page_source = self.driver.page_source
        screenshot_path = "screenshot.png"
        self.driver.save_screenshot(screenshot_path)
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
        
        # 对bbox进行坐标变换，变为以左上角为原点的坐标，并且计算中心点center
        result = self._coordination_transformation(result)
        bbox = [detection[0][0] for detection in result]

        ui_element = []
        ui_context = []
        actions = ActionChains(self.driver)
        for box in bbox:
            script = f"return document.elementFromPoint({box.center.x}, {box.center.y});"
            element_html = self.driver.execute_script(script)
            # 返回的html元素可以进行许多操作，甚至可以修订ocr识别出来的外框的范围，但python对象需要通过javascript脚本才能访问到原生的DOM属性
            # 想出来一种context的格式
            ui_element.append(element_html)
            ui_context.append("context TODO")

        # put all these information into the state

        # Form a prompt ask the llm what to do next based on user


        prompt = "" + str(state)

        self.peekCount += 1
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

