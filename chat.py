import random
import json
from keras.models import load_model
from utils import tokenize, bag_of_words
import pickle
import numpy as np
import scrapy
from scrapy.crawler import CrawlerProcess
from googletrans import Translator
from flask import Flask, render_template, request, jsonify
import os

app=Flask(__name__)

location_dict={"Ba Vì":"Ba Vi",
        "Bắc Từ Liêm": "Bac Tu Liem",
        "Biên Hòa": "Bien Hoa",
        "Bình Chánh": "Binh Chanh",
        "Bình Tân": "Binh Tan",
        "Bình Thạnh": "Binh Thanh",
        "Cần Thơ": "Can Tho",
        "Cầu Giấy": "Cau Giay",
        "Chương Mỹ": "Chuong My",
        "Củ Chi": "Cu Chi",
        "Đà Nẵng": "Da Nang",
        "Quận 12": "District 12",
        "Quận 8": "District 8",
        "Quận 9": "District 9",
        "Hải Phòng": "Hai phong",
        "Hà Nội": "Ha Noi",
        "Thành Phố Hồ Chí Minh": "Ho Chi Minh City",
        "Huế": "Hue",
        "Nha Trang": "Nha Trang",
        "Quy Nhơn": "Quy Nhon"
}

@app.route("/")
def home():
    return render_template('home.html')


class Weather(scrapy.Spider):
    name = "weather"
    start_urls = ["https://www.accuweather.com/vi/vn/vietnam-weather"]

    def parse(self, response):
        global all_weather
        all_weather = []
        for weather in response.css('div.nearby-locations-list a'):
            yield {
                'location': weather.css('span::text').get(),
                'temp': weather.css('span::text')[1].get().replace("°", "C")
            }
            all_weather.append([weather.css('span::text').get(), weather.css('span::text')[1].get().replace("°", "C")])


def get_temp(location):
    for l, t in all_weather:
        if location_dict[l]==location:
            global temp
            temp=int(t[:-1])
            return "Nhiệt độ ở "+ l + " là "+ t


with open('data.pkl', 'rb') as f:
    all_words, tags=pickle.load(f)
with open('intents.json', 'r') as f:
    data=json.load(f)

model=load_model('model.model')
translator=Translator()

def chat(sentence):
    try:
        sentence_=location_dict[sentence]
    except:
        sentence_=translator.translate(sentence, src='vi', dest='en').text
        sentence_ = sentence_.lower()
    X=tokenize(sentence_)
    X=bag_of_words(X, all_words)
    X=X.reshape(-1, len(all_words))
    prediction=model.predict(X)[0]
    predicted_tags=tags[np.argmax(prediction)]
    probability=prediction[np.argmax(prediction)]
    if probability>0.75:
        for intents in data['intents']:
            if predicted_tags==intents['tag']:
                if predicted_tags=='location':
                    try:
                        return get_temp(str(sentence)) + ". Bạn đang trồng ở đâu? (Ví dụ: Ban công, vườn, tầng thượng, trong nhà)"
                    except:
                        return "Tôi không tìm được chỗ bạn"
                if predicted_tags=='plant_location':
                    if 7<=temp<=25 and sentence=='ban công' or sentence=='trong nhà':
                        return "Điều kiện của bạn thích hợp để trồng SALAD"
                    elif 26<=temp<=35 and sentence=='vườn' or sentence=='tầng thượng':
                        return "Điều kiện của bạn thích hợp để trồng RAU MUỐNG"
                    else:
                        return "Không có loại cây nào thích hợp. Hãy chọn lại chỗ trồng"

                else:
                    response=random.choice(intents['responses'])
                    response=translator.translate(response, src='en', dest='vi').text
                    return response
    else:
        response=random.choice(data['error'])
        response = translator.translate(response, src='en', dest='vi').text
        return response

@app.route("/get")
def get_response():
    userText=str(request.args.get('msg'))
    if os.path.exists('response.json') == True:
        pass
    else:
        with open('response.json', 'w') as f:
            _={"responses":[]}
            json.dump(_, f)
    with open('response.json', 'r') as f:
        data=json.load(f)
        temp=data['responses']
        temp.append(userText)
    with open('response.json', 'w') as f:
        json.dump(data, f, indent=4)

    return str(chat(userText))

if __name__=='__main__':
    process = CrawlerProcess()
    process.crawl(Weather)
    process.start()
    app.run()

