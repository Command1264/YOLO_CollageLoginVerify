import json, os, functools, random
from dataclasses import dataclass, field


@dataclass
class LinkCheck:
    username: str
    chat_id: int
    link_length: int = 6
    link: str = ""

    def __post_init__(self):
        self.generate_link_number()

    def generate_link_number(self):
        tmp_num = -1
        for _ in range(self.link_length):
            rand_lst = [i for i in range(10)]
            if tmp_num in rand_lst: rand_lst.remove(tmp_num)

            tmp_num = rand_lst[random.randint(0, len(rand_lst) - 1)]
            self.link += str(tmp_num)

@dataclass
class LinkedUserData:
    user_id: str
    username: str
    chat_id: int

    def __jsonencode__(self):
        return {
            "username": self.username,
            "chat_id": self.chat_id,
        }

    @staticmethod
    def from_dict(data):
        return LinkedUserData(
            user_id = data["user_id"],
            username = data["username"],
            chat_id = data["chat_id"]
        )

class LinkedUserDataEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__jsonencode__'):
            return obj.__jsonencode__()

        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

@dataclass
class LinkedUserJsonController:
    file_name: str = "linked_users.json"
    linked_users: dict[str, LinkedUserData] = field(default_factory=dict)

    def __post_init__(self):
        self.read_json()

    def read_json(self):
        self.__check_file_exists__()
        with open(self.file_name, "r", encoding="utf-8") as f:
            # 讀取檔案內容
            try:
                self.linked_users = {
                    key: LinkedUserData.from_dict(raw_data)
                    for key, raw_data in json.load(f).itmes()
                }
            except json.JSONDecodeError:
                self.linked_users = dict()

    def __check_file_exists__(self):
        if not os.path.exists(self.file_name):
            with open(self.file_name, "x", encoding="utf-8"): pass

    def add_linked_user(self, linked_user: LinkedUserData) -> bool:
        self.read_json()
        if self.find_linked_user(linked_user): return False

        with open(self.file_name, "w", encoding="utf-8") as f:
            self.linked_users[linked_user.user_id] = linked_user

            # f.seek(0)
            # 轉成 set，避免重複的 id 出現
            # 再將其轉成 list，因為 set 不能 json 序列化
            json.dump(self.linked_users,
                      f,
                      indent = 4,
                      ensure_ascii = False,
                      cls = LinkedUserDataEncoder
            )
            # f.truncate()
        return True

    def remove_linked_user(self, linked_user: LinkedUserData) -> bool:
        self.read_json()
        if not self.find_linked_user(linked_user): return False

        with open(self.file_name, "w", encoding="utf-8") as f:
            linked_user = self.get_linked_user(linked_user)
            if linked_user is None: return False

            self.linked_users.pop(linked_user.user_id, None)

            # f.seek(0)
            # 轉成 set，避免重複的 id 出現
            # 再將其轉成 list，因為 set 不能 json 序列化
            json.dump(self.linked_users,
                      f,
                      indent = 4,
                      ensure_ascii = False,
                      cls = LinkedUserDataEncoder
            )
            # f.truncate()
        return True

    def find_linked_user(self, linked_user: LinkedUserData) -> bool:
        return (linked_user.user_id in self.linked_users and
                linked_user in self.linked_users.values())



    def get_linked_user(self, linked_user: LinkedUserData) -> LinkedUserData | None:
        return self.linked_users.get(linked_user.user_id, None)














