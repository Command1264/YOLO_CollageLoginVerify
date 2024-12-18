from ultralytics import YOLO
import os

if (__name__ == "__main__"):
    # 確認 train 的母資料夾存在
    runResultPath = f"./runs/"
    if (not os.path.exists(runResultPath)):
        os.makedirs(runResultPath)
    
    # 確認 train 的資料夾要幾號
    trainDir = f"train%i%"
    valDir = f"train%i%-2"
    i = 1
    while (True):
        if (os.path.exists(runResultPath + trainDir.replace(f"%i%", str(i)))):
            i += 1
            continue
        else:
            break
    trainDir = trainDir.replace(f"%i%", str(i))
    valDir = valDir.replace(f"%i%", str(i))

    # 載入模型
    model = YOLO("yoloCore/yolov8n.pt")

    # 訓練模型
    train_results = model.train(
        data="./dataSet/numbers.v1i.yolov11/data.yaml",  # path to dataset YAML
        epochs=100,  # number of training epochs
        batch=1,
        imgsz=640,  # training image size
        workers=3,
        device=0,  # device to run on, i.e. device=0 or device=0,1,2,3 or device=cpu
        project = runResultPath,
        name = trainDir,
    )

    # 評估模型
    metrics = model.val(
        project = runResultPath,
        name = valDir,
    )