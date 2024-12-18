from flask import Flask, jsonify

import os, time

from collageLogin.CYUTLoginVerifyModel import CYUTLoginVerifyModel

saveImage = True
# (WIP)
showLog = True
# 初始化 API
app = Flask(__name__)

cyut_model = CYUTLoginVerifyModel()
imgSize = [640, 640]

def create_directory(path):
    os.makedirs(path, exist_ok=True)

# 創建 API
# http://127.0.0.1:5000/api/v1/collageLogin/getVerifyCode
@app.route("/api/v1/collageLogin/getVerifyCode", methods=["GET"])
def get_verify_code():
    return_json = {
        "success": False,
        "verifyCode": ""
    }

    output_dir = f"./output/"
    output_date_time_path = output_dir + time.strftime('%Y-%m-%d/%H-%M-%S/', time.localtime())

    # 確保資料夾存在
    create_directory(output_date_time_path)

    output_raw_image_path = f"{output_date_time_path}image-%i%-raw.png"
    output_identify_image_path = f"{output_date_time_path}image-%i%.jpg"


    # 取得現在時間來生成網址
    now = time.localtime()
    formatted_time = time.strftime("%m%%2F%d%%2F%Y%%20%H%%3A%M%%3A%S", now)

    url = f"https://auth2.cyut.edu.tw/User/VerificationCode?n={formatted_time}"
    # 判斷數字
    verify_code = cyut_model.url_gif_get_verify_code(
        url = url,
        show = False,
        save = saveImage,
        verbose = showLog,
        project = output_date_time_path,
        log = True
    )


    return_json["success"] = (len(verify_code) == 4)
    return_json["verifyCode"] = verify_code
    return jsonify(return_json)

# 程式進入點
if __name__ == "__main__":
    app.run(debug = False)