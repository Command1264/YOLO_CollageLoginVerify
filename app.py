from ultralytics import YOLO
import torch

import cv2 as cv
from PIL import Image

import numpy as np, pandas as pd

from flask import Flask, jsonify

import requests, shutil

import os, time
from io import BytesIO

saveImage = True
# (WIP)
showLog = True
# 初始化 API
app = Flask(__name__)

# 初始化 model
# model = YOLOv10('yolov10n.pt')
model = YOLO('./yoloSuccessCore/YOLO11x-google-best.pt')


def createDirectory(path):
    os.makedirs(path, exist_ok=True)

def calculateDistanceSquare(lst1, lst2):
    sum = 1
    for i in range(min(len(lst1), len(lst2))):
        sum += ((lst1[i]- lst2[i]) ** 2)
    return sum

def calculateDistance(lst1, lst2):
    return calculateDistanceSquare(lst1, lst2) ** 0.5

def combineNumbers(numbersLst: list) -> str:
    return "".join([num[0] for num in numbersLst])

def resultNumbersFilter(numbersLst: list, limitDistance: float = 30.0) -> list:
    limitDistance = limitDistance ** 2
    print(f"numbersLst: {numbersLst}")
    lst = []
    tmpLst = []
    numbersLst = sorted(numbersLst, key = lambda number: number[1][0])
    oldPos = [-1, -1, -1, -1]
    oldNumber = ""

    # 先將位置差距 >= limitDistance 或是不同數字的資料濾出來
    for number in numbersLst:
        pos = number[1]
        if (
            (calculateDistanceSquare(oldPos[0:2], pos[0:2]) >= limitDistance and 
            calculateDistanceSquare(oldPos[2:4], pos[2:4]) >= limitDistance) or
                oldNumber != number[0]
            ):
            oldPos = pos
            oldNumber = number[0]
            tmpLst.append(number)
    # print(f"tmpLst: {tmpLst}")

    # 再針對可能會出現同樣位置，到數值不同的資料，再取出最大機率的數值
    i = 0
    while (i < len(tmpLst)):
        filterLst = []
        oldPos = [-1, -1, -1, -1]
        first = True
        # 取出相近位置，數值不同的資料
        for j in range(i, len(tmpLst)):
            number = tmpLst[j]
            pos = number[1]
            if (first):
                oldPos = pos[0:2]
                filterLst.append(number)
                first = False
                continue
            if (
                calculateDistanceSquare(oldPos[0:2], pos[0:2]) >= limitDistance and 
                calculateDistanceSquare(oldPos[2:4], pos[2:4]) >= limitDistance):
                break
            oldPos = pos[0:2]
            filterLst.append(number)
        # 如果資料 >= 2，代表有不同數值，取機率最大的那個
        if (len(filterLst) >= 2):
            lst.append(sorted(filterLst, key = lambda number: number[2], reverse=True)[0])
        else:
            lst.append(filterLst[0])
        
        i += max(len(filterLst), 1)
    # print(f"lst: {lst}")

    return lst


# 創建 API
# http://127.0.0.1:5000/api/v1/collageLogin/getVerifyCode
@app.route("/api/v1/collageLogin/getVerifyCode", methods=["GET"])
def getVerifyCode():
    returnJson = {
        "success": False,
        "verifyCode": ""
    }
    outputDir = f"./output/"
    outputDateTimePath = outputDir + time.strftime('%Y-%m-%d/%H-%M-%S/', time.localtime())

    # 確保資料夾存在
    createDirectory(outputDateTimePath)

    outputRawImagePath = f"{outputDateTimePath}image-%i%-raw.png"
    outputIdentifyImagePath = f"{outputDateTimePath}image-%i%.jpg"


    # 取得現在時間來生成網址
    now = time.localtime()
    formatted_time = time.strftime("%m%%2F%d%%2F%Y%%20%H%%3A%M%%3A%S", now)

    url = f"https://auth2.cyut.edu.tw/User/VerificationCode?n={formatted_time}"
    # 對伺服器做請求
    r = requests.get(url)

    # 如果成功
    if (r.status_code != 200):
        # 如果 HTTP GET 沒成功，就回傳空
        print(f"statusCode: {r.status_code}")
        return jsonify(returnJson)
    
    # 先將網頁資料轉成 BytesIO
    gifBytesIo = BytesIO()
    gifBytesIo.write(np.frombuffer(r.content, dtype = np.uint8))

    # 讓 Image 讀取
    gifImg = Image.open(gifBytesIo)
    # 將編碼轉成 RGBA (PNG)
    gifImg.convert("RGBA")

    # 使用 cv2 將灰階轉彩色、讀取並 resize
    img = cv.cvtColor(np.array(gifImg)[:, :].copy(), cv.COLOR_GRAY2BGR)
    # 如果圖片尺寸不正確，再進行 resize
    if (img.shape[0:2] != (640, 640)):
        img = cv.resize(img, (640, 640))

    # 檢查圖像是否有效
    if (not img.any()): return jsonify(returnJson)

    # 判斷數字
    results = model(
        source = img,
        show = False,
        save = saveImage,
        verbose = showLog,
        project = outputDateTimePath
    )


    # 如果沒結果，就回傳空
    if not results: return jsonify(returnJson)

    for result in results:
        # 取得數字字典
        nameDir = result.names
        numbersLst = []

        for box in result.boxes:
            #提取檢測到的物體的類別
            cls = box.cls
            #提取檢測到的物體的信心分數
            confidence = box.conf
            # print(box)

            # 確定類別至少有一個
            # 只要有判斷出數值，那就送入 resultNumbersFilter() 濾波
            if (len(cls) >= 1):
                numbersLst.append([nameDir[cls[0].item()], box.xyxy[0].tolist(), confidence.tolist()])
                    
        verifyCode = combineNumbers(resultNumbersFilter(numbersLst))
        print(f"verifyCode: {verifyCode}")

        if (saveImage):
            # 輸出圖片
            output_raw_image = outputRawImagePath.replace(f"%i%", f"{verifyCode}")
            if not os.path.exists(output_raw_image):
                cv.imwrite(output_raw_image, result.orig_img)
                
            # 將判斷圖片移到正確的位置，並將資料夾刪除
            identified_image = outputIdentifyImagePath.replace(f"%i%", f"{verifyCode}")
            if not os.path.exists(identified_image):
                shutil.copy2(f"{outputDateTimePath}predict/image0.jpg", identified_image)

            shutil.rmtree(f"{outputDateTimePath}predict/")

        returnJson["success"] = (len(verifyCode) == 4)
        returnJson["verifyCode"] = verifyCode
        return jsonify(returnJson)

# 程式進入點
if (__name__ == "__main__"):
    app.run(debug = False)
    # lst = [
    #     ['6', [287.04620361328125, 390.62255859375, 46.786376953125, 333.06494140625], [0.9032233953475952]], 
    #     ['6', [205.694580078125, 350.01361083984375, 47.8909912109375, 329.31396484375], [0.8944045901298523]], 
    #     ['4', [123.73724365234375, 363.9913330078125, 47.905029296875, 345.560302734375], [0.8871923685073853]],
    #     ['4', [42.66637420654297, 384.0327453613281, 47.359588623046875, 348.04852294921875], [0.8845589756965637]]
    # ]
    # print(combineNumbers(resultNumbersFilter(lst)))