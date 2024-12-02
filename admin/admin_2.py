import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd


st.header("Admin 2")
st.write(f"You are logged in as {st.session_state.role}.")

def interact_with_chatgpt(topics, email, password, max_responses=5):
    """
    自动与ChatGPT网页版交互，按不同话题获取对话历史和时间戳。
    
    :param topics: 话题列表
    :param email: 用户账号
    :param password: 用户密码
    :param max_responses: 每个话题最多获取的回复数
    :return: 包含话题、对话历史和时间戳的数据框
    """
    # 设置 WebDriver
    driver = webdriver.Chrome(service=Service('./chromedriver'))  # 替换为 WebDriver 路径
    wait = WebDriverWait(driver, 20)
    
    try:
        # 访问 ChatGPT 网页版
        driver.get("https://chat.openai.com/")
        
        # 登录操作
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Log in']"))).click()
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email, Keys.RETURN)
        wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(password, Keys.RETURN)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))).click()
        
        # 确保登录成功并加载主界面
        wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@data-id='input']")))
        
        interaction_data = []
        
        for topic in topics:
            # 输入话题到 ChatGPT 输入框
            input_box = driver.find_element(By.XPATH, "//textarea[@data-id='input']")
            input_box.clear()
            input_box.send_keys(f"让我们讨论关于 {topic} 的问题", Keys.RETURN)
            
            responses = []
            timestamps = []
            
            for _ in range(max_responses):
                try:
                    # 等待新的消息出现
                    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-id='chat-message']")))
                    messages = driver.find_elements(By.XPATH, "//div[@data-id='chat-message']")
                    
                    # 获取最新消息和时间戳
                    response = messages[-1].text
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    
                    responses.append(response)
                    timestamps.append(timestamp)
                    
                    # 输入下一条交互问题
                    input_box.send_keys("继续讨论这个话题", Keys.RETURN)
                    time.sleep(2)  # 避免速率限制
                except Exception as e:
                    print(f"错误: {e}")
                    break
            
            # 保存单个话题的对话历史
            interaction_data.append({
                "Topic": topic,
                "Responses": responses,
                "Timestamps": timestamps
            })
        
        # 保存到 DataFrame 并返回
        df = pd.DataFrame(interaction_data)
        driver.quit()
        return df
    
    except Exception as e:
        driver.quit()
        raise RuntimeError(f"自动化失败: {str(e)}")