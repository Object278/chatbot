import streamlit as st
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk

# simple code for simulation, need to define a resful api to put the service on openai

st.header("Admin 1")
st.write(f"You are logged in as {st.session_state.role}.")


# 下载必要的nltk资源
nltk.download('punkt')
nltk.download('stopwords')

def extract_keywords_from_json(json_input: str, num_keywords: int = 10) -> str:
    """
    接受文章JSON输入，使用TF-IDF算法提取关键词，并返回关键词JSON输出。

    :param json_input: 包含文章内容的JSON字符串，例如：{"article": "文章内容"}
    :param num_keywords: 每篇文章提取的关键词数量，默认为10
    :return: 包含关键词的JSON字符串，例如：{"keywords": ["关键词1", "关键词2", ...]}
    """
    try:
        # 解析JSON输入
        data = json.loads(json_input)
        #article = data.get("article", "")
        article = data
        
        if not article.strip():
            raise ValueError("文章内容不能为空")
        
        # 预处理：分词、去除停用词
        stop_words = set(stopwords.words('english'))
        tokens = word_tokenize(article.lower())
        filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
        processed_text = " ".join(filtered_tokens)
        
        # 使用TF-IDF提取关键词
        vectorizer = TfidfVectorizer(max_features=num_keywords)
        tfidf_matrix = vectorizer.fit_transform([processed_text])
        keywords = vectorizer.get_feature_names_out()
        
        # 返回关键词JSON
        result = {"keywords": list(keywords)}
        return json.dumps(result, ensure_ascii=False)
    
    except json.JSONDecodeError:
        raise ValueError("输入的JSON格式不正确")
    except Exception as e:
        raise RuntimeError(f"提取关键词时发生错误: {str(e)}")

prompt = st.chat_input("Say something")
if prompt:
    prompt = json.dumps(prompt)
    st.write(f"User has sent the following prompt: {extract_keywords_from_json(prompt)}")