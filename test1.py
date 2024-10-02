import requests
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

# 使用 requests 來發送請求
url = 'https://auth2.cyut.edu.tw/User/VerificationCode?n=10%2F01%2F2024%2011%3A44%3A12'
r = requests.get(url)
r.raise_for_status()  # 確認請求成功
if (r.status_code == 200) :
# 讀取內容並處理圖片資料
    arr = np.asarray(bytearray(r.content), dtype=np.uint8)
    gifBytesIo = BytesIO()
    gifBytesIo.write(arr)

    gifImg = Image.open(gifBytesIo)
    gifImg.convert("RGBA")

    img = np.array(gifImg)[:, :].copy()

    # 顯示圖片
    cv2.imshow('lalala', img)
    if cv2.waitKey() & 0xff == 27: quit()
