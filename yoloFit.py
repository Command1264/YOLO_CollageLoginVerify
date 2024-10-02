from ultralytics import YOLO

if (__name__ == "__main__"):
    # Load a model
    model = YOLO("yolo11n.pt")

    # Train the model
    train_results = model.train(
        data="D:/Code/python/collageLogin/dataSet/numbers.v1i.yolov11/data.yaml",  # path to dataset YAML
        epochs=30,  # number of training epochs
        # batch=3,
        imgsz=640,  # training image size
        workers=3,
        device=0,  # device to run on, i.e. device=0 or device=0,1,2,3 or device=cpu
    )

    # Evaluate model performance on the validation set
    metrics = model.val()