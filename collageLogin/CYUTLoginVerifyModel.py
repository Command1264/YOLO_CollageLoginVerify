from ultralytics import YOLO
import numpy as np
import os, requests
import cv2 as cv
from io import BytesIO
from PIL import Image


def create_directory(path):
    os.makedirs(path, exist_ok=True)

def calculate_area_with_xyxy(xyxy: list[float | int]) -> float:
    return calculate_area(abs(xyxy[2] - xyxy[0]), abs(xyxy[3] - xyxy[1]))

def calculate_area(w: float | int, h: float | int) -> float:
    return w * h

def calculate_distance_square(ps1: list[float | int], ps2: list[float | int]) -> float:
    if len(ps1) != len(ps2): return -1
    __sum = 0
    for p1, p2 in zip(ps1, ps2):
        __sum += ((p1 - p2) ** 2)
    return __sum


def calculate_distance(ps1: list[float | int], ps2: list[float | int]) -> float:
    return calculate_distance_square(ps1, ps2) ** 0.5


def combine_numbers(numbers_lst: list) -> str:
    return "".join([num[0] for num in numbers_lst])

def sharpen(img: np.ndarray, sigma: int = 25) -> np.ndarray:
    # sigma = 5、15、25
    blur_img = cv.GaussianBlur(img, (0, 0), sigma)
    usm = cv.addWeighted(img, 1.5, blur_img, -0.5, 0)

    return usm


def result_numbers_filter(numbers_lst: list, limit_distance: float = 30.0) -> list:
    limit_distance = limit_distance ** 2
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

    verbose: bool = False
    log: bool = False


    @staticmethod
    def __get_class_name():
        return CYUTLoginVerifyModel.__name__

    def __init__(
        self,
        model_path: str = "./yoloSuccessCore/YOLO11n-google-best.pt",
        verbose: bool = False,
        log: bool = False
    ):
        self.set_model_path(model_path)
        self.verbose = verbose
        self.log = log

    def set_model_path(self, model_path: str):
        if os.path.isfile(model_path):
            self.__model = YOLO(model_path)
        else:
            print("找不到模型，將使用 yolo11n")
            self.__model = YOLO("yolo11n.pt")

    def url_gif_get_verify_code(
            self,
            url: str,
            cookies: dict = {},
            show: bool = False,
            save: bool = True,
            verbose: bool | None = None,
            project: str = "./runs/",
            output_raw_image_name: str = f"./image-%i%-raw.png",
            output_identify_image_name: str = f"./image-%i%.jpg",
            log: bool = False,
    ) -> str | None:
        r = requests.get(
            url,
            cookies = cookies
        )
        if verbose is None: verbose = self.verbose

        # 如果成功
        if r.status_code != 200:
            # 如果 HTTP GET 沒成功，就回傳空
            print(f"statusCode: {r.status_code}")
            return ""

        # 先將網頁資料轉成 BytesIO
        with BytesIO() as gif_bytes_io:
            gif_bytes_io.write(r.content)
            # gif_bytes_io.write(np.frombuffer(r.content, dtype = np.uint8))

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
            output_raw_image_name = output_raw_image_name,
            output_identify_image_name = output_identify_image_name,
            log = log,
        )


    def get_verify_code(
            self,
            source : np.ndarray,
            show: bool = False,
            save: bool = True,
            verbose: bool | None = None,
            project: str = "./runs/",
            # name: str = "predict",
            output_raw_image_name: str = f"./image-%i%-raw.png",
            output_identify_image_name: str = f"./image-%i%.jpg",
            log: bool = False,
    ) -> str | None:
        project = project if project[-1] == '/' else project + '/'
        output_raw_image_path = f"{project}{output_raw_image_name}"
        output_identify_image_path = f"{project}{output_identify_image_name}"

        if verbose is None: verbose = self.verbose

        results = self.__model.predict(
            source = source,
            show = show,
            save = False,
            verbose = verbose,
            project = project,
        )

        # 如果沒結果，就回傳空
        if not results or len(results) != 1: return None
        result = results[0]

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
            if len(cls) < 1: continue
            xywhn = box.xywhn[0].tolist()
            # 避免模型抓出太大或是太小的數字(把雜訊當數字)
            if (
                    0.18 < xywhn[2] or
                    xywhn[2] < 0.09 or
                    0.30 < xywhn[3] or
                    xywhn[3] < 0.17
            ): continue

            numbers_lst.append([
                name_dir[cls[0].item()],
                box.xyxy[0].tolist(),
                confidence.tolist()
            ])

        verify_code = combine_numbers(result_numbers_filter(numbers_lst))
        if log: print(f"verifyCode: {verify_code}")

        if save:
            # 輸出圖片

            # 创建多级目录
            os.makedirs(project, exist_ok=True)

            # 生成原始圖片
            output_raw_image = output_raw_image_path.replace(f"%i%", f"{verify_code}")
            if not os.path.isfile(output_raw_image):
                cv.imwrite(output_raw_image, result.orig_img)

            # 生成判斷圖片
            identified_image = output_identify_image_path.replace(f"%i%", f"{verify_code}")
            drawn_image = result.plot()

            # 将绘制的图像转换为 PIL 格式并保存
            img = Image.fromarray(drawn_image)
            img.save(identified_image)

        return verify_code
