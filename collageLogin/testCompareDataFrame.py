import pandas as pd
from ScholarshipObject import ScholarshipObject, ScholarshipApplyObject
import json
from dataclasses import asdict

if __name__ == "__main__":
    def _build_scholarship_object(row) -> ScholarshipObject:
        index_value = int(row[0]) if row[0] is not None else -1
        name_text = str(row[4])
        scholarship_id_text = name_text.split("-")[0] if len(name_text.split("-")) > 0 else ""
        scholarship_id = int(scholarship_id_text) if scholarship_id_text.isdigit() else -1
        return ScholarshipObject(
            index_value,
            row[1],
            row[2],
            row[3],
            scholarship_id,
            name_text,
            row[5],
            row[6],
            row[7],
        )


    names = ["old", "new"]
    dataframes = {}
    for name in names:
        dataframes[name] = pd.read_excel(f"./113-1 獎學金-{name}.xlsx")

    # Pandas(
    #     Index=116,
    #     學年=113,
    #     學期=1,
    #     類型='自申',
    #     _4='563-臺南市臺疆祖廟大觀音亭暨祀典興濟宮中低、低收入戶清寒優秀獎學金',
    #     外部連結='LINK',
    #     申請期限='2024/11/15',
    #     金額='10,000'
    # )
    scholarship_object_lists = {}
    for name in names:
        scholarship_object_lists[name] = {
            _build_scholarship_object(row)
            for row in dataframes[name].itertuples()
        }

    # 0: old
    # 1: new

    df_diff = pd.merge(
        dataframes["old"], dataframes["new"], how="outer", indicator=True
    )


    # 篩選出變更的部分
    added = df_diff[df_diff["_merge"] == "right_only"]
    removed = df_diff[df_diff["_merge"] == "left_only"]
    print(df_diff)

    print("新增的資料：")
    print(added)
    print("\n刪除的資料：")
    print(removed)

    # add
    # print(f'add: {scholarship_object_lists["new"] - scholarship_object_lists["old"]}\n')
    # # sub
    # print(f'sub: {scholarship_object_lists["old"] - scholarship_object_lists["new"]}\n')
