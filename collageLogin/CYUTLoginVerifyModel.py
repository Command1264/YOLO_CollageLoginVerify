from ultralytics import YOLO
import numpy as np
import os, shutil
import cv2 as cv
import requests
from io import BytesIO
from PIL import Image


def create_directory(path):
    os.makedirs(path, exist_ok=True)


def calculate_distance_square(lst1, lst2):
    __sum = 1
    for i in range(min(len(lst1), len(lst2))):
        __sum += ((lst1[i] - lst2[i]) ** 2)
    return __sum


def calculate_distance(lst1, lst2):
    return calculate_distance_square(lst1, lst2) ** 0.5


def combine_numbers(numbers_lst: list) -> str:
    return "".join([num[0] for num in numbers_lst])

def sharpen(img: np.ndarray, sigma: int = 25):
    # sigma = 5、15、25
    blur_img = cv.GaussianBlur(img, (0, 0), sigma)
    usm = cv.addWeighted(img, 1.5, blur_img, -0.5, 0)

    return usm


def result_numbers_filter(numbers_lst: list, limit_distance: float = 30.0) -> list:
    limit_distance = limit_distance ** 2
    # print(f"numbersLst: {numbersLst}")
    lst = []
    tmp_lst = []
    numbers_lst = sorted(numbers_lst, key=lambda __number: __number[1][0])
    old_pos = [-1, -1, -1, -1]
    old_number = ""

    # 先將位置差距 >= limitDistance 或是不同數字的資料濾出來
    for number in numbers_lst:
        pos = number[1]
        if (
                (calculate_distance_square(old_pos[0:2], pos[0:2]) >= limit_distance and
                 calculate_distance_square(old_pos[2:4], pos[2:4]) >= limit_distance) or
                old_number != number[0]
        ):
            old_pos = pos
            old_number = number[0]
            tmp_lst.append(number)
    # print(f"tmpLst: {tmpLst}")

    # 再針對可能會出現同樣位置，到數值不同的資料，再取出最大機率的數值
    i = 0
    while i < len(tmp_lst):
        filter_lst = []
        old_pos = [-1, -1, -1, -1]
        first = True
        # 取出相近位置，數值不同的資料
        for j in range(i, len(tmp_lst)):
            number = tmp_lst[j]
            pos = number[1]
            if first:
                old_pos = pos[0:2]
                filter_lst.append(number)
                first = False
                continue
            if (
                    calculate_distance_square(old_pos[0:2], pos[0:2]) >= limit_distance or
                    calculate_distance_square(old_pos[2:4], pos[2:4]) >= limit_distance):
                break
            old_pos = pos[0:2]
            filter_lst.append(number)
        # 如果資料 >= 2，代表有不同數值，取機率最大的那個
        if len(filter_lst) >= 2:
            lst.append(sorted(filter_lst, key=lambda __number: __number[2], reverse=True)[0])
        else:
            lst.append(filter_lst[0])

        i += max(len(filter_lst), 1)

    return lst


class CYUTLoginVerifyModel:
    __model = None
    imgSize = [640, 640]

    def __init__(self, model_path: str = "./yoloSuccessCore/YOLO11n-google-best.pt"):
        self.set_model_path(model_path)

    def set_model_path(self, model_path: str):
        if os.path.isfile(model_path):
            self.__model = YOLO(model_path)
        else:
            self.__model = YOLO("yolo11n.pt")

    def url_gif_get_verify_code(
            self,
            url: str,
            cookies: dict = {},
            show: bool = False,
            save: bool = True,
            verbose: bool = True,
            project: str = "./runs/",
            name: str = "predict",
            output_raw_image_name: str = f"./image-%i%-raw.png",
            output_identify_image_name: str = f"./image-%i%.jpg",
            log: bool = False,
    ):
        r = requests.get(
            url,
            cookies = cookies
        )

        # 如果成功
        if r.status_code != 200:
            # 如果 HTTP GET 沒成功，就回傳空
            print(f"statusCode: {r.status_code}")
            return ""

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
        if not img.any(): return ""

        # 將其做圖片預處理
        img = img[:, :img.shape[1] // 2]
        size = img.shape[0:2]
        scale = min(self.imgSize[0] / size[0], self.imgSize[1] / size[1])
        new_size = [round(i * scale) for i in size]

        new_img = np.full((*self.imgSize, 3), 255)

        draw_loc = [
            (0 if (self.imgSize[i] == new_size[i]) else (self.imgSize[i] // 2) - (new_size[i] // 2)) for i in range(2)
        ]

        new_img[
            int(draw_loc[0]):int(draw_loc[0] + new_size[0]),
            int(draw_loc[1]):int(draw_loc[1] + new_size[1])
        ] = cv.resize(img, (0, 0), fx = scale, fy = scale)

        return self.get_verify_code(
            source=new_img,
            show = show,
            save = save,
            verbose = verbose,
            project = project,
            name = name,
            output_raw_image_name = output_raw_image_name,
            output_identify_image_name = output_identify_image_name,
            log = log,
        )


    def get_verify_code(
            self,
            source : np.ndarray,
            show: bool = False,
            save: bool = True,
            verbose: bool = True,
            project: str = "./runs/",
            name: str = "predict",
            output_raw_image_name: str = f"./image-%i%-raw.png",
            output_identify_image_name: str = f"./image-%i%.jpg",
            log: bool = False,
    ) -> str:
        project = project if project[-1] == '/' else project + '/'
        output_raw_image_path = f"{project}{output_raw_image_name}"
        output_identify_image_path = f"{project}{output_identify_image_name}"

        # print(source.shape)
        # cv.imshow("img", source)
        # cv.imshow("newImg", sharpen(source))
        results = self.__model(
            source = source,
            show = show,
            save = save,
            verbose = verbose,
            project = project,
            name = name
        )

        # 如果沒結果，就回傳空
        if not results: return ""

        for result in results:
            # 取得數字字典
            name_dir = result.names
            numbers_lst = []

            for box in result.boxes:
                # 提取檢測到的物體的類別
                cls = box.cls
                # 提取檢測到的物體的信心分數
                confidence = box.conf
                # print(box)

                # 確定類別至少有一個
                # 只要有判斷出數值，那就送入 resultNumbersFilter() 濾波
                if len(cls) >= 1:
                    numbers_lst.append([name_dir[cls[0].item()], box.xyxy[0].tolist(), confidence.tolist()])

            verify_code = combine_numbers(result_numbers_filter(numbers_lst))
            if log: print(f"verifyCode: {verify_code}")

            if save:
                # 輸出圖片
                output_raw_image = output_raw_image_path.replace(f"%i%", f"{verify_code}")
                if not os.path.isfile(output_raw_image):
                    cv.imwrite(output_raw_image, result.orig_img)

                # 將判斷圖片移到正確的位置，並將資料夾刪除
                identified_image = output_identify_image_path.replace(f"%i%", f"{verify_code}")
                if not os.path.isfile(identified_image):
                    shutil.copy2(f"{project}/{name}/image0.jpg", identified_image)

                shutil.rmtree(f"{project}/{name}")

            return verify_code

