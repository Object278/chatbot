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

def coordination_transformation(bbox):
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
        actions.move_by_offset(box.center.x, box.center.y)


    driver.quit()


