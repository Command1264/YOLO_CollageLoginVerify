import json
import os

# model_name = "YOLO11x-google-best.pt"
# model_name = "YOLO11x-google-1-best.pt"
# model_name = "YOLO11x-self-best.pt"
# model_name = "YOLO11x-0.1%Train-best.pt"
# model_name = "YOLO11x-1%Train-best.pt"
# model_name = "YOLO11x-10%Train-best.pt"

model_file_path = f"./testModel/%model_name%/ans.json"
human_file_path = "./testModel/human_ans.json"

def get_file_name_number(file_name):
    return file_name.split(".")[0].split("-")[-1]

if __name__ == '__main__':
    for model_name in [
        # "YOLO11x-google-best.pt",
        # "YOLO11x-google-1-best.pt",
        "YOLO11x-0.1%Train-best.pt",
        "YOLO11x-1%Train-best.pt",
        "YOLO11x-10%Train-best.pt",
        "YOLO11x-self-best.pt",
    ]:
        if not os.path.exists(human_file_path):
            exit("找不到人類資料")
        try:
            with open(human_file_path) as f:
                human_data_dict = json.load(f)
        except:
            exit("找不到人類資料")

        self_model_file_path = model_file_path.replace("%model_name%", model_name)
        if not os.path.exists(self_model_file_path):
            exit("找不到YOLO資料")
        try:
            with open(self_model_file_path) as f:
                model_data_dict = json.load(f)
        except:
            exit("找不到YOLO資料")

        current = 0
        all_count = 0
        error_keys = []

        print(f"{model_name} 模型測試")

        human_data_dict = dict(sorted(
            human_data_dict.items(),
            key=lambda item: int(get_file_name_number(item[0]))
        ))
        model_data_dict = dict(sorted(
            model_data_dict.items(),
            key=lambda item: int(get_file_name_number(item[0]))
        ))

        for (human_key, human_value), (model_key, model_value) \
                in zip(human_data_dict.items(), model_data_dict.items()):
            if human_key != model_key:
                exit("Key 錯誤")

            if human_value == model_value:
                current += 1
            else:
                error_keys.append(human_key)
                # print(("-" * 20) + f"\n數值錯誤\nKey: {human_key}\nhuman value: {human_value}\nmodel value: {model_value}\n" + ("-" * 20))
            all_count += 1

        print(f"正確: {current} / 所有數量: {all_count}")
        print(f"正確率: {(current / all_count) * 100:.2f}%")
        print("-" * 30)
