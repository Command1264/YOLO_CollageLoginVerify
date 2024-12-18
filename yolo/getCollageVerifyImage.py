import requests
from io import BytesIO
import numpy as np
import cv2 as cv
from PIL import Image
from tqdm import trange
import time

img_size = [640, 640]

if __name__ == "__main__":
    for i in trange(4611, 10_000):
        url = "https://auth2.cyut.edu.tw/User/VerificationCode"
        r = requests.get(
            url
        )

        # 如果成功
        if r.status_code != 200:
            # 如果 HTTP GET 沒成功，就回傳空
            print(f"statusCode: {r.status_code}")
            continue

        # 先將網頁資料轉成 BytesIO
        gif_bytes_io = BytesIO()
        gif_bytes_io.write(np.frombuffer(r.content, dtype = np.uint8))

        # 讓 Image 讀取
        gif_img = Image.open(gif_bytes_io)
        # 將編碼轉成 RGBA (PNG)
        gif_img.convert("RGBA")

        # 使用 cv2 將灰階轉彩色、讀取並 resize
        img = cv.cvtColor(np.array(gif_img)[:, :].copy(), cv.COLOR_GRAY2BGR)

        # 檢查圖像是否有效
        if not img.any(): continue

        # 將其做圖片預處理
        img = img[:, :img.shape[1] // 2]
        size = img.shape[0:2]
        scale = min(img_size[0] / size[0], img_size[1] / size[1])
        new_size = [round(i * scale) for i in size]

        new_img = np.full((*img_size, 3), 255).astype(np.uint8)

        draw_loc = [
            (0 if (img_size[i] == new_size[i]) else (img_size[i] // 2) - (new_size[i] // 2)) for i in range(2)
        ]

        new_img[
            int(draw_loc[0]):int(draw_loc[0] + new_size[0]),
            int(draw_loc[1]):int(draw_loc[1] + new_size[1])
        ] = cv.resize(img, (0, 0), fx = scale, fy = scale)
        # print(new_img)
        # print(new_img.shape)

        cv.imwrite(f"./TestData/image-{i}.png", new_img)
        time.sleep(0.01)
        # cv.imshow("Collage Image", new_img)
        # cv.waitKey(0)
        # cv.destroyAllWindows()