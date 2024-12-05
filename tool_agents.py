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
        # Summary
        summarizer = pipeline("summarization")
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)

        # Find function elements

        parser = etree.HTML(str(soup))
    
        # 定义功能性组件
        functional_tags = ["form", "input", "button", "select", "option", 
                       "textarea", "table", "tr", "td", "th", "a"]
    
        # 保存结果
        elements_with_info = []
    
        for tag in soup.find_all(functional_tags):
        # 转换为 lxml 的元素
            tag_string = str(tag)
            # why this?
            lxml_element = parser.xpath(f"//*[text()='{tag.get_text(strip=True)}' or @*='{tag.attrs.get(list(tag.attrs.keys())[0], '')}']")
            
            if lxml_element:  # 如果找到对应的 lxml 元素
                # 提取 XPath
                xpath = parser.getpath(lxml_element[0])
                # 记录元素信息
                elements_with_info.append({
                    "tag": tag.name,
                    "attributes": tag.attrs,
                    "text": tag.get_text(strip=True),
                    "xpath": xpath,
                    "start_position": tag.sourceline
                })

        # 把summary和page_source放在state里

        return {"website_list": [(link, summary, page_source, elements_with_info)]}

    # 在给llm的决策prompt中，应该规定只能选择有意义的http 元素，比如说div是无意义的，form，button是有意义的
    def find_target_element(target_type: str, target_des: str, state: State):
        '''
        the agent want a target http element with certain description
        this could also be a agent, which ask the llm to decide 
        if the element meets the need

        '''
        html_content = state['websites_list']["?"]
        soup = BeautifulSoup(html_content, 'html.parser')

        elements = soup.find_all(target_type)
        for element in elements:
            pass
        
        target_element = None
        # 将页面summary，每个element（的summary？）和target des对比，可以问llm或者rag？看哪个是对应的
        return target_element

    def fill_form(form_location):
        '''
        fill a http form and submit, interact with website using Seleioum 
        '''
        pass
