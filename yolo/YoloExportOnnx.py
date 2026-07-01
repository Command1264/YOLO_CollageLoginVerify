from ultralytics import YOLO  # pyright: ignore[reportPrivateImportUsage]
from pathlib import Path
import os
from tqdm import tqdm

if __name__ == "__main__":
    path = "./yoloSuccessCore"
    folder = Path(path)

    files = [f.name for f in folder.iterdir() if f.is_file() and f.suffix == ".pt"]
    # print(files)

    for file in tqdm(files, desc="Exporting models to ONNX"):
        model_path = os.path.join(path, file)
        model = YOLO(model_path)
        model.export(format="onnx")
