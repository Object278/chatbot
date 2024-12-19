from process_data import Agent
import time
import json

MAX_STEP = 5

def test_observation():
    print("test1")
    with Agent("访问当前网站，获取网页信息。") as agent:
        agent.get_html_from_query("https://www.baidu.com/")
        print(agent.generate_prompt())


def test_action():
    print("test2")
    with Agent("访问当前网站，获取网页信息。") as agent:
        agent.get_html_from_query("https://www.baidu.com/")
        action = """do(action="Click", actionid="0")"""
        # 0 号可交互元素，百度首页的“百度首页”图标
        agent.add_action(action)
        agent.do("Click", element=0)
        # do 里面自动调用add_response
        time.sleep(2)
        print("Get new page")
        current_url = agent.driver.execute_script("return window.location.href;")
        print(current_url)
        agent.get_html_from_query(current_url)
        print(json.loads(agent.generate_prompt()))

def test_oracle():
    print("test3")
    with Agent("Randomly do something.") as agent:
        for i in range(MAX_STEP):
            # 观察
            agent.get_html_from_query("https://www.baidu.com/")
            print(str(i) + "-----------------------------------------------------------------------------------------------------------------")
            # 思考，作出决定
            action = agent.ask_oracle()
            # 行动
            time.sleep(2)



if __name__ == "__main__":
    test_oracle()