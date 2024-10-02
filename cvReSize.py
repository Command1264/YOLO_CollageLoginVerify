import cv2 as cv
import os

for i in range(1000):
    oldPath = f"TestData/image-{i}-old.png"
    img = cv.resize(cv.imread(oldPath), (640, 640))
    cv.imwrite(f"TestData/image-{i}.png", img)
    os.remove(oldPath)