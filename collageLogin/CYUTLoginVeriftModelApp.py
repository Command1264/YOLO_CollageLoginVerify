from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import cv2 as cv
import numpy as np
import os, sys
# from multiprocessing import Process

app = Flask(__name__)
CORS(app)

# 假設這是你封裝的類別
collage_login_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'collageLogin'))
sys.path.append(collage_login_path)
os.chdir(collage_login_path)

from CYUTLoginVerifyModel import CYUTLoginVerifyModel

model = CYUTLoginVerifyModel("../yolo/yoloSuccessCore/YOLO11n-google-best.pt")  # 你要根據實際建立方式做初始化


imgSize = [640, 640]
@app.route('/solve_captcha', methods=['POST'])
def solve_captcha():
    try:
        data = request.get_json()
        image_base64 = data['image'].split(',')[1]
        img_bytes = base64.b64decode(image_base64)

        # 將 bytes 轉成 numpy array
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv.imdecode(np_arr, cv.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'invalid image'}), 400

        img = img[:, :img.shape[1] // 2]
        size = img.shape[0:2]
        scale = min(imgSize[0] / size[0], imgSize[1] / size[1])
        new_size = [round(i * scale) for i in size]

        new_img = np.full((*imgSize, 3), 255)

        draw_loc = [
            (0 if (imgSize[i] == new_size[i]) else (imgSize[i] // 2) - (new_size[i] // 2)) for i in range(2)
        ]

        new_img[
            int(draw_loc[0]):int(draw_loc[0] + new_size[0]),
            int(draw_loc[1]):int(draw_loc[1] + new_size[1])
        ] = cv.resize(img, (0, 0), fx = scale, fy = scale)

        # 傳給你自定義的函式做辨識
        result = model.get_verify_code(
            source = new_img,
            log = True,
            save = False,
        )
        print(result)
        if result:
            return jsonify({'text': result})
        else:
            return jsonify({'error': 'no result'}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def start_flask():
    app.run(host='0.0.0.0', port=5000, debug = True)

if __name__ == '__main__':
    start_flask()
    # p = Process(target=start_flask)
    # p.daemon = True  # 讓它隨主程式結束自動關閉
    # p.start()
