from typing import Union

from fastapi import FastAPI
import json

app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "See for yourself."}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

def user_request(task_description: str, parameter: json, ret: str):
    '''
    从高层次任务（定义目标，比如说填写酒店并预定）到低层次任务，其中的细节操作需要函数定义
    这些函数的作用，输入和输出都有自然语言描述并且变成了embedding
    这让我们可以使用Embedding相似度进行不同函数之间的routing，当然routing的部分也可以交给LLM，但是从性能上没必要
    甚至可以自动给相近的函数生成一个embedding，而不取决于编程者的自然语言描述
    这相当于推荐系统中的粗排，不同函数之间的功能区分如果比较大的话，粗排的精度应该完全足够
    LLM主要用于更精细的，更泛化的高级routing。

    control flow prototype 1
    task_description to embedding: des
    parameter to embedding: para
    用户期望的输出 to embedding: ret

    des match function des, get function object 1
    para match function para, get function object 2
    ret match function para, get function object 3
        here, match = RAG

    check if function object 1 and 2 are the same
        if not
            check who's similarity is lower, try to figure out which is wrong, contact user
        if yes
            continue execute function 1
                now we move from croase layer to a more detailed layer
    
    get result from function object 1
    use the function 1 return description and some information from the output of function 1(need a general method to extract information)
        比如说访问网页，访问完获取网页之后，可以使用一个description字段描述刚才这个任务做了什么
    identify the new task now，这一步需要访问LLM来进行自然语言推理（有没有可能有更简单的embedding transfer关系可以查找呢）
        比如说我们之前要在booking搜索房间，现在我们到了booking的网站，获取了网页，结合**一般**在租房网站的操作现在做什么？
        这里可以额外问llm一个问题，关于一般在这种场合干什么，然后和上一次的信息联合推理
    
    比如说下一步我们决定要找到搜索表格在哪里
    selenium此时可以出场帮我们省力

    名词对应：
    选择哪个是对的--route
    下一步应该做什么--reason
    LLM可以route，可以reason
    RAG可以route，不可以reason，route上的功能类似于推荐系统的粗排
    使用什么工具route，可以有一个层级，层级低的失败了就去用层级高的
    在比较结构化的场合，具体的工具可以帮助我们代替用LLM和RAG route和reason
    '''
    pass
