import torch
import numpy as np
import pandas as pd
from tqdm import tqdm


cuda0 = torch.device('cuda:0')
testLst = [
    ["3", [20, 30, 20, 30], 0.950],
    ["3", [20, 31, 20, 31], 0.950],
    ["4", [20, 31, 20, 31], 0.321],
    ["2", [50, 60, 50, 60], 0.798],
    ["1", [70, 31, 70, 31], 0.923],
    ["5", [90, 90, 90, 90], 0.832],
]
testLstTensor = [
    ["3", torch.tensor([20, 30, 20, 30], device=cuda0), torch.tensor(0.950, device=cuda0)],
    ["3", torch.tensor([20, 31, 20, 31], device=cuda0), torch.tensor(0.950, device=cuda0)],
    ["4", torch.tensor([20, 31, 20, 31], device=cuda0), torch.tensor(0.321, device=cuda0)],
    ["2", torch.tensor([50, 60, 50, 60], device=cuda0), torch.tensor(0.798, device=cuda0)],
    ["1", torch.tensor([70, 31, 70, 31], device=cuda0), torch.tensor(0.923, device=cuda0)],
    ["5", torch.tensor([90, 90, 90, 90], device=cuda0), torch.tensor(0.832, device=cuda0)],
]
testLstTensorNumpy = [
    ["3", torch.tensor([20, 30, 20, 30], device=cuda0).detach().cpu().numpy(), torch.tensor(0.950, device=cuda0).detach().cpu().numpy()],
    ["3", torch.tensor([20, 31, 20, 31], device=cuda0).detach().cpu().numpy(), torch.tensor(0.950, device=cuda0).detach().cpu().numpy()],
    ["4", torch.tensor([20, 31, 20, 31], device=cuda0).detach().cpu().numpy(), torch.tensor(0.321, device=cuda0).detach().cpu().numpy()],
    ["2", torch.tensor([50, 60, 50, 60], device=cuda0).detach().cpu().numpy(), torch.tensor(0.798, device=cuda0).detach().cpu().numpy()],
    ["1", torch.tensor([70, 31, 70, 31], device=cuda0).detach().cpu().numpy(), torch.tensor(0.923, device=cuda0).detach().cpu().numpy()],
    ["5", torch.tensor([90, 90, 90, 90], device=cuda0).detach().cpu().numpy(), torch.tensor(0.832, device=cuda0).detach().cpu().numpy()],
]
testLstTensorList = [
    ["3", torch.tensor([20, 30, 20, 30], device=cuda0).tolist(), torch.tensor(0.950, device=cuda0).tolist()],
    ["3", torch.tensor([20, 31, 20, 31], device=cuda0).tolist(), torch.tensor(0.950, device=cuda0).tolist()],
    ["4", torch.tensor([20, 31, 20, 31], device=cuda0).tolist(), torch.tensor(0.321, device=cuda0).tolist()],
    ["2", torch.tensor([50, 60, 50, 60], device=cuda0).tolist(), torch.tensor(0.798, device=cuda0).tolist()],
    ["1", torch.tensor([70, 31, 70, 31], device=cuda0).tolist(), torch.tensor(0.923, device=cuda0).tolist()],
    ["5", torch.tensor([90, 90, 90, 90], device=cuda0).tolist(), torch.tensor(0.832, device=cuda0).tolist()],
]
# def calculateDistanceSquare(x1, y1, x2, y2):
#     return ((x1- x2) ** 2) * ((y1 - y2) ** 2)

def calculateDistanceSquare(xy1, xy2):
    return ((xy1[0]- xy2[0]) ** 2) + ((xy1[1] - xy2[1]) ** 2)

def combineNumbers(numbersLst: list) -> str:
    return "".join([num[0] for num in numbersLst])

def resultNumbersFilter_GPT(numbersLst: list, limitDistance: float = 30.0) -> list:
    limitDistance = limitDistance ** 2
    # 將數據轉換為 DataFrame，方便操作
    df = pd.DataFrame(numbersLst, columns=['number', 'xyxy', 'probability'])
    
    # 根據 xywh 中的 x 座標進行排序
    df['x'] = df['xyxy'].apply(lambda xyxy: xyxy[0])
    df = df.sort_values(by='x').reset_index(drop=True)
    
    # 儲存結果的資料
    filteredLst = []
    
    # 先過濾掉距離 >= limitDistance 且數字不同的項目
    oldXY = torch.tensor([-1, -1])
    oldNumber = ""
    tmpLst = []
    for _, row in df.iterrows():
        xyxy = row['xyxy']
        distanceSquare = calculateDistanceSquare(oldXY[0:2], xyxy[0:2])
        
        if distanceSquare >= limitDistance or oldNumber != row['number']:
            oldXY = xyxy[0:2]
            oldNumber = row['number']
            tmpLst.append((row['number'], row['xyxy'], row['probability']))
    
    # 將資料轉換回 DataFrame 進行後續處理
    tmpDf = pd.DataFrame(tmpLst, columns=['number', 'xyxy', 'probability'])
    
    # 再進行位置相近但數值不同的篩選
    i = 0
    while i < len(tmpDf):
        currentXY = tmpDf.iloc[i]['xyxy'][0:2]
        filterLst = [tmpDf.iloc[i]]
        
        for j in range(i + 1, len(tmpDf)):
            nextXY = tmpDf.iloc[j]['xyxy'][0:2]
            distanceSquare = calculateDistanceSquare(
                currentXY[0:2],
                nextXY[0:2]
            )
            
            if distanceSquare >= limitDistance:
                break
            
            filterLst.append(tmpDf.iloc[j])
        
        # 取出最大機率的數值
        filterDf = pd.DataFrame(filterLst)
        bestMatch = filterDf.sort_values(by='probability', ascending=False).iloc[0]
        filteredLst.append((bestMatch['number'], bestMatch['xyxy'], bestMatch['probability']))
        i += len(filterLst)
    
    return filteredLst


def resultNumbersFilter_old(numbersLst: list, limitDistance: float = 30.0) -> list:
    limitDistance = limitDistance ** 2
    # print(numbersLst)
    lst = []
    tmpLst = []
    numbersLst = sorted(numbersLst, key = lambda number: number[1][0])
    oldXY = [-1, -1]
    oldNumber = ""

    # 先將位置差距 >= limitDistance 或是不同數字的資料濾出來
    for number in numbersLst:
        xyxy = number[1]
        if (
            calculateDistanceSquare(oldXY[0:2], xyxy[0:2]) >= limitDistance or
                oldNumber != number[0]
            ):
            oldXY = xyxy[0:2]
            oldNumber = number[0]
            tmpLst.append(number)

    # 再針對可能會出現同樣位置，到數值不同的資料，再取出最大機率的數值
    i = 0
    while (i < len(tmpLst)):
        filterLst = [tmpLst[i]]
        oldXY = tmpLst[i][1][0:2]
        # 取出相近位置，數值不同的資料
        for j in range(i + 1, len(tmpLst)):
            number = tmpLst[j]
            xyxy = number[1]

            if (calculateDistanceSquare(oldXY[0:2], xyxy[0:2]) >= limitDistance):
                break
            
            oldXY = xyxy[0:2]
            filterLst.append(number)
        # 如果資料 >= 2，代表有不同數值，取機率最大的那個
        if (len(filterLst) >= 2):
            lst.append(sorted(filterLst, key = lambda number: number[2], reverse=True)[0])
        else:
            lst.append(filterLst[0])
        
        i += len(filterLst)
    
    return lst

def resultNumbersFilter(numbersLst: list, limitDistance: float = 30.0) -> list:
    limitDistance = limitDistance ** 2
    # print(numbersLst)
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
            if (calculateDistanceSquare(oldPos[0:2], pos[0:2]) >= limitDistance):
                break
            oldPos = pos[0:2]
            filterLst.append(number)
        # 如果資料 >= 2，代表有不同數值，取機率最大的那個
        if (len(filterLst) >= 2):
            lst.append(sorted(filterLst, key = lambda number: number[2], reverse=True)[0])
        else:
            lst.append(filterLst[0])
        
        i += max(len(filterLst), 1)
    
    return lst



if (__name__ == "__main__"):
    num = 100_000
    limitDistance = 10.0
        
    for i in tqdm(range(num), desc = "GPT testLst"):
        resultNumbersFilter_GPT(testLst, limitDistance)

    for i in tqdm(range(num), desc = "GPT testLstTensor"):
        resultNumbersFilter_GPT(testLstTensor, limitDistance)

    for i in tqdm(range(num), desc = "GPT testLstTensorNumpy"):
        resultNumbersFilter_GPT(testLstTensorNumpy, limitDistance)

    for i in tqdm(range(num), desc = "GPT testLstTensorList"):
        resultNumbersFilter_GPT(testLstTensorList, limitDistance)

    print("".join(["-" for _ in range(50)]))

    for i in tqdm(range(num), desc = "old testLst"):
        resultNumbersFilter_old(testLst, limitDistance)

    for i in tqdm(range(num), desc = "old testLstTensor"):
        resultNumbersFilter_old(testLstTensor, limitDistance)

    for i in tqdm(range(num), desc = "old testLstTensorNumpy"):
        resultNumbersFilter_old(testLstTensorNumpy, limitDistance)

    for i in tqdm(range(num), desc = "old testLstTensorList"):
        resultNumbersFilter_old(testLstTensorList, limitDistance)



    print("".join(["-" for _ in range(50)]))


    for i in tqdm(range(num), desc = "new testLst"):
        resultNumbersFilter(testLst, limitDistance)

    for i in tqdm(range(num), desc = "new testLstTensor"):
        resultNumbersFilter(testLstTensor, limitDistance)

    for i in tqdm(range(num), desc = "new testLstTensorNumpy"):
        resultNumbersFilter(testLstTensorNumpy, limitDistance)

    for i in tqdm(range(num), desc = "new testLstTensorList"):
        resultNumbersFilter(testLstTensorList, limitDistance)

