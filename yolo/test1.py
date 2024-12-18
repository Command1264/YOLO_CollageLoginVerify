import requests
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

def calculateDistanceSquare(lst1, lst2):
    sum = 1
    for i in range(min(len(lst1), len(lst2))):
        sum += ((lst1[i]- lst2[i]) ** 2)
    return sum

def calculateDistance(lst1, lst2):
    return calculateDistanceSquare(lst1, lst2) ** 0.5

def combineNumbers(numbersLst: list) -> str:
    return "".join([num[0] for num in numbersLst])

def resultNumbersFilter(numbersLst: list, limitDistance: float = 30.0) -> list:
    limitDistance = limitDistance ** 2
    print(f"numbersLst: {numbersLst}")
    lst = []
    tmpLst = []
    numbersLst = sorted(numbersLst, key = lambda number: number[1][0])
    oldPos = [-1, -1, -1, -1]
    oldNumber = ""

    # 先將位置差距 >= limitDistance 或是不同數字的資料濾出來
    for number in numbersLst:
        pos = number[1]
        if (
            (calculateDistanceSquare(oldPos[0:2], pos[0:2]) >= limitDistance and 
            calculateDistanceSquare(oldPos[2:4], pos[2:4]) >= limitDistance) or
                oldNumber != number[0]
            ):
            oldPos = pos
            oldNumber = number[0]
            tmpLst.append(number)
    # print(f"tmpLst: {tmpLst}")

    # 再針對可能會出現同樣位置，到數值不同的資料，再取出最大機率的數值
    i = 0
    while (i < len(tmpLst)):
        filterLst = []
        oldPos = [-1, -1, -1, -1]
        first = True
        # 取出相近位置，數值不同的資料
        for j in range(i, len(tmpLst)):
            number = tmpLst[j]
            pos = number[1]
            if (first):
                oldPos = pos[0:2]
                filterLst.append(number)
                first = False
                continue
            if (
                calculateDistanceSquare(oldPos[0:2], pos[0:2]) >= limitDistance or 
                calculateDistanceSquare(oldPos[2:4], pos[2:4]) >= limitDistance):
                break
            oldPos = pos[0:2]
            filterLst.append(number)
        # 如果資料 >= 2，代表有不同數值，取機率最大的那個
        if (len(filterLst) >= 2):
            lst.append(sorted(filterLst, key = lambda number: number[2], reverse=True)[0])
        else:
            lst.append(filterLst[0])
        
        i += max(len(filterLst), 1)
    # print(f"lst: {lst}")

    return lst

lst = [
    ['2', [19.555091857910156, 145.35479736328125, 63.93622589111328, 495.65228271484375], [0.9332618117332458]], 
    ['3', [181.48741149902344, 262.3876953125, 225.9477081298828, 594.724365234375], [0.9126720428466797]], 
    ['6', [262.7509765625, 149.10577392578125, 310.2252197265625, 513.986572265625], [0.86927330493927]], 
    ['1', [105.74519348144531, 131.53424072265625, 143.43861389160156, 481.363525390625], [0.6799551248550415]]
    ]

import os
if __name__ == "__main__":
    # print("resullt: " + combineNumbers(resultNumbersFilter(lst)))
    print(os.path.basename("image-1234.png"))
    basename = str(os.path.basename("image-1234-1.png"))
    number = basename.split(".")[0].split("-")[1]
    print(number)
    # if (basename is not None):
    #     filter(str.isdigit, basename)
    print(int(''.join(filter(str.isdigit, basename))))