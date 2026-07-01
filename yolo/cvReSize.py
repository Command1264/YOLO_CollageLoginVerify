import cv2 as cv
import os

for i in range(1000):
    oldPath = f"TestData/image-{i}-old.png"
    source = cv.imread(oldPath)
    if source is None:
        continue
    img = cv.resize(source, (640, 640))
    cv.imwrite(f"TestData/image-{i}.png", img)
    os.remove(oldPath)
