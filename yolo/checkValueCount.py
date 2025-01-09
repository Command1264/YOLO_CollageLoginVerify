import json


if __name__ == '__main__':
    with open('./testModel/test1-YOLO11x-google-best.pt/ans.json', 'r') as f:
        data = json.load(f)
    # with open('./testModel/test1-YOLO11x-google-best.pt/human_ans.json', 'r') as f:
    #     data = json.load(f)

    data_count_dict= {}
    for value in data.values():
        data_count_dict[value] = data_count_dict.get(value, 0) + 1

    data_count_dict = dict(sorted(
        data_count_dict.items(),
        key=lambda item: item[1],
        reverse=True
    ))
    print(json.dumps(
        data_count_dict,
        indent=4
    ))
    print(f"type count: {len(data_count_dict)}")
