"""
    基于FastAPI的后端
"""

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sutil import cut_sent, replace_char, get_paragraphs_text
import uvicorn
import paddlehub as hub
from paddlenlp import Taskflow
import time
import openai
import requests
import json
import asyncio
from paddleocr import PaddleOCR

openai.api_key = "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" # 将 YOUR_API_KEY 替换为您的实际 API 密钥

# 设置API请求的URL和参数
url = "https://api.openai.com/v1/chat/completions"


headers={"authority": "api.openai.com",
         "Content-Type": "application/json",
         "Authorization": f"Bearer {openai.api_key}"
}

proxies={'http': 'http://127.0.0.1:1080',
         'https': 'https://127.0.0.1:1080'
}

async def TextErrorCorrection(document):
    try:
        # 获取要进行识别的文本内容
        text = document.text
        print(text)
        # 精细分句处理以更好处理长文本
        # data = cut_sent(text) 暂不使用
        key = document.key
        # 进行文本识别和标记
        prompt = 'A：'+ text +'//B：'+ key
        print(key)
        result = chat(prompt)
        print(result)
        results = {"message": "success", "originalText": document.text, "correctionResults": result}
        return results
    # 异常处理
    except Exception as e:
        print("异常信息：", e)
        raise HTTPException(status_code=500, detail=str("请求失败，服务器端发生异常！异常信息提示：" + str(e)))

async def ImageErrorCorrection(file, key, value):
    # 读取上传的文件
    imgBytes = file.file.read()
    imgName = file.filename
    print(key)
    array = key.split('，')
    # 判断上传文件类型
    imgType = imgName.split(".")[-1]
    if imgType != "png" and imgType != "jpg" and imgType != "jpeg" :
        raise HTTPException(status_code=406, detail=str("请求失败，上传图片格式不正确！请上传jpg或png图片！"))
    try:
        now_time = int(time.mktime(time.localtime(time.time())))
        # 拼接生成随机文件名，注意名称不能包含中文否则后面读取出错
        imgPath = "backend/resources/" + str(now_time) + "_image." + imgType
        print(imgPath)
        fout = open(imgPath, 'wb')
        fout.write(imgBytes)
        fout.close()
        print("文件上传成功！")
        if value == 1 :
        # ERNIE文本识别和提取
            answer=docprompt({"doc": imgPath, "prompt": array})
            # format数组
            new_list = []
            for item in answer:
                result = item['result'][0]
                new_item = {'prompt': item['prompt'], 'value': result['value'], 'prob': result['prob'], 'start': result['start'], 'end': result['end']}
                new_list.append(new_item)
        else:
            result = ocr.ocr(imgPath, cls=False)
            txts = [detection[1][0] for line in result for detection in line] # Nested loop added
            all_context = "".join(txts)
            print(all_context)
            prompt = 'A：'+ all_context +'//B：'+ key
            new_list = chat(prompt)

        # 接口结果返回
        print(new_list)
        results = {"message": "success", "orcResult": "str(ocr_image_results[0])", "correctionResults": new_list}
        return results
    # 异常处理
    except Exception as e:
        print("异常信息：", e)
        raise HTTPException(status_code=500, detail=str("请求失败，服务器端发生异常！异常信息提示：" + str(e)))

def chat(prompt):  #定义一个函数

    try:
        data = {"model": "gpt-3.5-turbo",
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "你是一个信息提取机器人，接下来我会用：“A：内容//B：信息提示”给你多个prompt，你需要返回给我一个数组，数组的格式为：[{\"prompt\":\"prompt的内容\",\"value\":\"提取的内容\"}]"},
                    {"role": "user", "content": "A：甲方购房总价款是12000元，税费为3%//B：甲方购房总价款，甲方购房税费"},
                    {"role": "assistant", "content": "[{\"prompt\":\"甲方购房总价款\",\"value\":\"12000元\"},{\"prompt\":\"甲方购房税费\",\"value\":\"360元\"}]"},
                    {"role": "user", "content": prompt}
                ]
        }
        # 发送HTTP请求
        response = requests.post(url, headers=headers,json=data)

        # 解析响应并输出结果
        if response.status_code == 200:
            answer = response.json()["choices"][0]["message"]["content"].strip()
            answer = json.loads(answer)
        else:
            raise Exception(f"Request failed with status code {response.status_code}")        
        return answer
    
    except Exception as exc:
        #print(exc)  #需要打印出故障
        return "broken"

print("开始预热！")
# 加载paddle模型
print("ERNIE模型启动")
docprompt = Taskflow("document_intelligence")
ocr = PaddleOCR(use_angle_cls=False)


# 创建一个 FastAPI「实例」，名字为app
app = FastAPI()

# 设置允许跨域请求，解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求体数据类型：text
class Document(BaseModel):
    text: str
    key: str

# 定义路径操作装饰器：POST方法 + API接口路径

# 文本识别接口
@app.post("/v1/textCorrect/", status_code=200)
# 定义路径操作函数，当接口被访问将调用该函数
async def handle_request(document: Document):
    # 创建一个事件循环
    loop = asyncio.get_running_loop()
    print('创建事件循环成功')
    # 创建一个协程，用于处理当前请求
    coroutine = TextErrorCorrection(document)
    print('创建协程成功')
    # 并行处理当前请求
    result = await asyncio.gather(coroutine, return_exceptions=True)
    print('并行处理当前请求成功')
    print(result)
    return result[0]


# 图片识别接口
@app.post("/v1/imageCorrect/", status_code=200)
# 定义路径操作函数，当接口被访问将调用该函数
async def handle_request(file: UploadFile, key: str, value: int):
    # 创建一个事件循环
    loop = asyncio.get_running_loop()
    print('创建事件循环成功')
    # 创建一个协程，用于处理当前请求
    coroutine = ImageErrorCorrection(file, key, value)
    print('创建协程成功')
    # 并行处理当前请求
    result = await asyncio.gather(coroutine, return_exceptions=True)
    print('并行处理当前请求成功')
    print(result)
    return result[0]

# 启动创建的实例app，设置启动ip和端口号
uvicorn.run(app, host="127.0.0.1", port=8000)
