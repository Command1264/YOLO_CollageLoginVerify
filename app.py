from ultralytics import YOLO
import cv2 as cv
import numpy as np
import requests, shutil
import os
from PIL import Image
import time
from flask import Flask
from io import BytesIO

# 初始化 API
app = Flask(__name__)

def createDirectroy(dirName: str) -> None:
    if (not os.path.exists(dirName)):
        os.makedirs(dirName)

# TODO 濾資料需要重寫
def repeatedNumbersFilter(numbersLst: list) -> list: 
    lst = []
    numbersLst = sorted(numbersLst, key = lambda number: number[1][0])
    oldPoint = [-1, -1]
    oldNumber = ""
    for number in numbersLst:
        if (
            (oldPoint[0] != int(number[1][0] * 100.0) and oldPoint[1] != int(number[1][1] * 100.0)) or
                oldNumber != number[0]):
            oldPoint = [int(number[1][0] * 100.0), int(number[1][1] * 100.0)]
            oldNumber = number[0]
            lst.append(number)
    return lst

def combineNumbers(numbersLst: list) -> str:
    # strLst = []
    # for number in numbersLst:
    #     strLst.append(number[0])
    return "".join([number[0] for number in numbersLst])

# 創建 API
# http://127.0.0.1:5000/api/v1/collageLogin/getVerifyCode
@app.route("/api/v1/collageLogin/getVerifyCode", methods=["GET"])
def getVerifyCode():
    # return "Hello"
    # exit()
# if (__name__ == "__main__"):
    # runDir = f"runTmp/"
    outputDir = f"output/"
    outputDateTimePath = outputDir + time.strftime('%Y-%m-%d/%H-%M-%S/', time.localtime())

    # 確保資料夾存在
    # createDirectroy(runDir)
    createDirectroy(outputDir)
    createDirectroy(outputDateTimePath)

    # gifPath = f"{runDir}image-%i%.gif"
    # pngPath = f"{runDir}image-%i%.png"

    outputPngPath = f"{outputDateTimePath}image-%i%.png"



    # model = YOLOv10('yolov10n.pt')
    model = YOLO('D:/Code/python/collageLogin/yoloSuccessCore/YOLOv8-best.pt')

    # for i in range(1000):
        # 取得現在時間來生成網址
    now = time.localtime()
    dateTimeLst = [
        "0" + str(now.tm_mon) if (now.tm_mon <= 9) else str(now.tm_mon),
        "0" + str(now.tm_mday) if (now.tm_mday <= 9) else str(now.tm_mday),
        now.tm_year,
        "0" + str(now.tm_hour) if (now.tm_hour <= 9) else str(now.tm_hour),
        "0" + str(now.tm_min) if (now.tm_min <= 9) else str(now.tm_min),
        "0" + str(now.tm_sec) if (now.tm_sec <= 9) else str(now.tm_sec)
    ]

        # https://auth2.cyut.edu.tw/User/VerificationCode?n=10/01/2024 11:44:12
        # "https://auth2.cyut.edu.tw/User/VerificationCode?n=10%2F01%2F2024%2011%3A44%3A12",
    url = f"https://auth2.cyut.edu.tw/User/VerificationCode?n={dateTimeLst[0]}%2F{dateTimeLst[1]}%2F{dateTimeLst[2]}%20{dateTimeLst[3]}%3A{dateTimeLst[4]}%3A{dateTimeLst[5]}"
    # 對伺服器做請求
    r = requests.get(url)

    # 如果成功
    if r.status_code == 200:
        
        arr = np.asarray(bytearray(r.content), dtype=np.uint8)
        gifBytesIo = BytesIO()
        gifBytesIo.write(arr)

        gifImg = Image.open(gifBytesIo)
        gifImg.convert("RGBA")
        
        # # 生成此次 gif 以及 png 的檔案路徑
        # thisTimeGifPath = gifPath.replace(f"%i%", "")
        # thisTimePngPath = pngPath.replace(f"%i%", "")
        
        # # 將檔案從網頁上抓下來(gif)
        # # TODO 需要把儲存檔案此步捨棄，不要在本地儲存
        # with open(thisTimeGifPath, 'wb') as f:
        #     r.raw.decode_content = True
        #     shutil.copyfileobj(r.raw, f)

        # # 將 gif 改成 png
        # img = Image.open(thisTimeGifPath)
        # img.convert("RGBA")
        # img.save(thisTimePngPath)
        # img.close()
        # os.remove(thisTimeGifPath)

        # 使用 cv2 讀取並 resize
        img = cv.resize(
            cv.cvtColor(np.array(gifImg)[:, :].copy(), cv.COLOR_GRAY2BGR), 
            (640, 640)
        )
        # 判斷數字
        results = model(source = img, show = False, save = True)

        # 如果沒結果，就執行下一次
        # if not results: continue
        if not results: return ""

        for result in results:
            # 取得數字字典
            nameDir = result.names
            numbersLst = []

            for box in result.boxes:
                #提取檢測到的物體的類別
                cls = box.cls
                #提取檢測到的物體的信心分數
                confidence = box.conf

                # 確認信心度 >= 80% 以外還需要確定類別至少有一個
                if (confidence >= 0.8 and len(cls) >= 1):
                    numbersLst.append([nameDir[cls[0].item()], box.xywhn[0]])
                        
            verifyCode = combineNumbers(repeatedNumbersFilter(numbersLst))
            print(verifyCode)

            # 輸出圖片
            cv.imwrite(outputPngPath.replace(f"%i%", f"{verifyCode}"), result.orig_img)
            return verifyCode



    else:
        print(f"statusCode: {r.status_code}")
        return ""
        

    # shutil.rmtree(runDir)

if (__name__ == "__main__"):
    app.run()