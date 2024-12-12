from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
import time
import functools

# 所有的action操作，可能还要加上一些error recovery操作，但是有哪些error可能会发生呢
# 单个页面中，应该只有一些操作有用
# 这个driver需要融合到procecss_data里面的driver

# Initialize the WebDriver
driver = webdriver.Chrome()  # 这里需要安装 ChromeDriver
action_chains = ActionChains(driver)


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

@action_error_detector
def click_element(element_id):
    element = driver.find_element(By.ID, element_id)
    element.click()

@action_error_detector
def hover_element(element_id):
    element = driver.find_element(By.ID, element_id)
    action_chains.move_to_element(element).perform()

@action_error_detector
def type_message(element_id, message: str):
    # error: 找到的元素不是input_box，返回一个错误信息给
    input_box = driver.find_element(By.ID, element_id)
    input_box.clear()
    input_box.send_keys(message)

@action_error_detector
def search_message(element_id, message):
    input_box = driver.find_element(By.ID, element_id)
    input_box.clear()
    input_box.send_keys(message)
    input_box.send_keys(Keys.RETURN)

# 这个好像有点问题，按照顺序按下按钮应该是down+up，ctrl之类的才是down-down-up-up
#或者说这个方法单独是针对modified key的，只负责按下ctrl+x之类的
@action_error_detector
def press_keys(*keys):
    for key in keys:
        action_chains.key_down(key)
    for key in reversed(keys):
        action_chains.key_up(key)
    action_chains.perform()

@action_error_detector
def scroll_page(direction):
    if direction.lower() == "up":
        driver.execute_script("window.scrollBy(0, -window.innerHeight);")
    elif direction.lower() == "down":
        driver.execute_script("window.scrollBy(0, window.innerHeight);")

@action_error_detector
def select_dropdown_option(element_id, option_value):
    # error：option value不存在
    dropdown = Select(driver.find_element(By.ID, element_id))
    dropdown.select_by_value(option_value)

@action_error_detector
def open_new_tab():
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

@action_error_detector
def focus_tab(index):
    driver.switch_to.window(driver.window_handles[index])

@action_error_detector
def close_tab():
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])

@action_error_detector
def go_to_url(url):
    driver.get(url)

@action_error_detector
def go_back():
    driver.back()

@action_error_detector
def go_forward():
    driver.forward()

@action_error_detector
def exit_browser():
    driver.quit()

# 可以改善
def do(action, **kwargs):
    if action == "Click":
        click_element(kwargs["element"])
    elif action == "Hover":
        hover_element(kwargs["element"])
    elif action == "Type":
        type_message(kwargs["element"], kwargs["message"])
    elif action == "Search":
        search_message(kwargs["element"], kwargs["message"])
    elif action == "Press":
        press_keys(*kwargs["keys"])
    elif action == "Scroll":
        scroll_page(kwargs["direction"])
    elif action == "Select dropdown option":
        select_dropdown_option(kwargs["element"], kwargs["value"])
    elif action == "New tab":
        open_new_tab()
    elif action == "Tab focus":
        focus_tab(kwargs["index"])
    elif action == "Close tab":
        close_tab()
    elif action == "Goto":
        go_to_url(kwargs["url"])
    elif action == "Go back":
        go_back()
    elif action == "Go forward":
        go_forward()
    elif action == "Exit":
        exit_browser()






