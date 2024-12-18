from collageLogin.CYUTLoginVerifyModel import *
import json, os
from tqdm import tqdm


def list_files_with_parent(directory):
    # 取得所有檔案的完整路徑
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # 根據檔案名稱中的數字部分排序
    return sorted(files, key=lambda x: int(''.join(filter(str.isdigit, os.path.basename(x)))))

    # 印出檔案及父目錄名稱
    # for file_path in sorted_files:
    #     parent_dir = os.path.basename(os.path.dirname(file_path))
    #     file_name = os.path.basename(file_path)
    #     print(f"File: {file_name}, Parent Directory: {parent_dir}")

if __name__ == "__main__":
    model = CYUTLoginVerifyModel("./yoloSuccessCore/YOLO11x-google-best.pt")
    parent_dir = "./TestData/"
    file_paths = list_files_with_parent(parent_dir)
    test_model_ans_dict = {}
    for file_path in tqdm(file_paths, desc = "test Model", total = len(file_paths)):
        file_name = os.path.basename(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]  # 移除副檔名

        verify_code = model.get_verify_code(
            cv.imread(file_path, 1),
            project = f"./testModel/test1-YOLO11X-google-best.pt/{file_name_without_ext}",
        )
        test_model_ans_dict[file_name] = verify_code
        # break
    print(test_model_ans_dict)
    with open("./testModel/test1-YOLO11X-google-best.pt/ans.json", "w", encoding="utf-8") as f:
        json.dump(test_model_ans_dict, f, indent=4, ensure_ascii=False)

        # print(os.getcwd())
    pass

