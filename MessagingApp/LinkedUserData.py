import json, os, functools, random

class LinkCheck:
    link: str = ""
    def __init__(self, username, chat_id, link_length: int = 6):
        self.username = username
        self.chat_id = chat_id
        self.link_length = link_length
        self.generate_link_number()

    def generate_link_number(self):
        tmp_num = -1
        for _ in range(self.link_length):
            rand_lst = [i for i in range(10)]
            if tmp_num in rand_lst: rand_lst.remove(tmp_num)

            tmp_num = rand_lst[random.randint(0, len(rand_lst) - 1)]
            self.link += str(tmp_num)

class LinkedUserData:
    username: str = ""
    chat_id: int = 0
    def __init__(self, username: str, chat_id: int):
        self.username = username
        self.chat_id = chat_id

    def __jsonencode__(self):
        return {
            "username": self.username,
            "chat_id": self.chat_id,
        }

    @staticmethod
    def from_dict(data):
        return LinkedUserData(
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

class LinkedUserJsonController:
    file_name: str = "linked_users.json"
    linked_users: list = []

    def __init__(self, file_name: str):
        self.file_name = file_name
        self.read_json()

    def read_json(self):
        self.__check_file_exists__()
        with open(self.file_name, "r", encoding="utf-8") as f:
            # 讀取檔案內容
            try:
                self.linked_users = [LinkedUserData.from_dict(raw_data) for raw_data in json.load(f)]
            except json.JSONDecodeError:
                self.linked_users = []

    def __check_file_exists__(self):
        if not os.path.exists(self.file_name):
            with open(self.file_name, "x", encoding="utf-8"): pass

    def add_linked_user(self, linked_user: LinkedUserData) -> bool:
        self.read_json()
        if self.find_linked_user(linked_user): return False

        with open(self.file_name, "w", encoding="utf-8") as f:
            self.linked_users.append(linked_user)

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
            self.linked_users.remove(linked_user)

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
        for entry in self.linked_users:
            if (linked_user.username == entry.username and
                    linked_user.chat_id == entry.chat_id):
                # 當符合條件時返回
                return True
        return False  # 如果沒有符合條件的項目，返回 None
    def get_linked_user(self, linked_user: LinkedUserData) -> LinkedUserData | None:
        for entry in self.linked_users:
            if (linked_user.username == entry.username and
                    linked_user.chat_id == entry.chat_id):
                # 當符合條件時返回
                return entry
        return None  # 如果沒有符合條件的項目，返回 None