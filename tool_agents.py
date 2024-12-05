from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from transformers import pipeline
from bs4 import BeautifulSoup
from main import State

class Tool_Agents:
    def to_link_and_peek(link: str, state: State):
        '''
        go to a link

        state:
            add whole content of link into state/memory
            生成页面的总结，或者DOM树上值得注意的结构，加入state
        
        '''
        chrome_options = Options()
        chrome_options.add_argument("--headless")

        service = Service(executable_path='/path/to/chromedriver')

        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(link)

        page_source = driver.page_source

        # driver 需要作为一个长久存在的东西
        driver.quit()

        soup = BeautifulSoup(page_source, 'html.parser')
        text = soup.get_text()

        summarizer = pipeline("summarization")
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)

        # 把summary和page_source放在state里

        return {"website_dict": [(link, summary, page_source)]}

    def find_target_element(target_type: str, target_des: str):
        '''
        the agent want a target http element with certain description
        this could also be a agent, which ask the llm to decide 
        if the element meets the need

        '''
        pass

    def fill_form(form_location):
        '''
        fill a http form and submit, interact with website using Seleioum 
        '''
        pass
