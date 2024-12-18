import cv2 as cv
import os
import numpy as np

# def getImageMinScale(img, newSize):
#     size = img.shape[0:2]
#     return min(newSize[0] / size[0], newSize[1] / size[1])


imgSize = [640, 640]

for i in range(1000):
    oldPath = f"TrainingAndTestData/image-{i}-old.png"
    newPath = f"TrainingAndTestData/image-{i}.png"
    img = cv.imread(oldPath)

    img = img[:, :img.shape[1] // 2]
    size = img.shape[0:2]
    scale = min(imgSize[0] / size[0], imgSize[1] / size[1])
    newSize = [round(i * scale) for i in size]
    # print(newSize)

    newImg = np.full((*imgSize, 3), 255)

    drawLoc = [
        (0 if (imgSize[i] == newSize[i]) else (imgSize[i] // 2) - (newSize[i] // 2)) for i in range(2)
    ]

    newImg[
        int(drawLoc[0]):int(drawLoc[0] + newSize[0]),
        int(drawLoc[1]):int(drawLoc[1] + newSize[1])
    ] = cv.resize(img, (0, 0), fx = scale, fy = scale)

    cv.imwrite(newPath.replace(f"%i%", str(i)), newImg)
    os.remove(oldPath)

    # windowName = "Image"
    
    # cv.imshow(windowName, newImg)
    # cv.waitKey(0)
    # cv.destroyWindow(windowName)