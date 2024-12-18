import logging

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import asyncio, signal, sys, os
from LinkedUserData import *



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

linking_users = {}
linked_users_file_name = "linked_users.json"
# LinkedUserJsonController
lujc = LinkedUserJsonController(linked_users_file_name)

if os.path.exists("botToken.json"):
    with open("botToken.json", "r", encoding="utf-8") as f:
        token_dict = json.load(f)
        token = token_dict["token"]
else:
    token = ""


# def init_data():

    # if not os.path.exists(linked_users_file_name):
    #     with open(linked_users_file_name, "x", encoding="utf-8"): pass
    # with open(linked_users_file_name, "r", encoding="utf-8") as f:
    #     # 讀取檔案內容
    #     try:
    #         linked_lst = [LinkedUserData.from_dict(raw_data) for raw_data in json.load(f)]
    #     except json.JSONDecodeError:
    #         linked_lst = []
    #     global linked_users
    #     linked_users = linked_lst


async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # print(context.bot)
    username = update.message.from_user.username
    chat_id = update.effective_chat.id

    if lujc.find_linked_user(LinkedUserData(username, chat_id)):
        await context.bot.send_message(
            chat_id = chat_id,
            text = "你已完成綁定"
        )
        return

    global linking_users
    link_check_obj = LinkCheck(username, chat_id)
    # print(update.message.from_user.username)
    linking_users[username] = link_check_obj
    await context.bot.send_message(
        chat_id = chat_id,
        text = "請輸入在後台端出現的六位數字"
    )
    print(link_check_obj.link)

async def link_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    chat_id = update.effective_chat.id

    global linking_users
    if username not in linking_users.keys(): return
    link_check_obj = linking_users[username]
    if (
        link_check_obj.link == update.message.text and
        link_check_obj.username == username and
        link_check_obj.chat_id == chat_id
    ):
        if lujc.add_linked_user(LinkedUserData(username, chat_id)):
            linking_users.pop(username, None)
            await context.bot.send_message(
                chat_id = chat_id,
                text = "綁定成功"
            )
        else:
            await context.bot.send_message(
                chat_id = chat_id,
                text = "綁定失敗，請稍後在試"
            )
        # 避免重複紀錄
        # global linked_users
        # if find_valid_user(linked_users, LinkedUserData(username, chat_id)) is not None: return
        #
        # if not os.path.exists(linked_users_file_name):
        #     with open(linked_users_file_name, "x", encoding="utf-8"): pass
        # with open(linked_users_file_name, "r+", encoding="utf-8") as f:
        #     # 讀取檔案內容
        #     try :
        #         linked_lst = [LinkedUserData.from_dict(raw_data) for raw_data in json.load(f)]
        #     except json.JSONDecodeError:
        #         linked_lst = []
        #     linked_lst.append(LinkedUserData(link_check_obj.username, chat_id))
        #
        #     f.seek(0)
        #     # 轉成 set，避免重複的 id 出現
        #     # 再將其轉成 list，因為 set 不能 json 序列化
        #     json.dump(linked_lst,
        #               f,
        #               indent = 4,
        #               ensure_ascii = False,
        #               cls = LinkedUserDataEncoder
        #   )
        #     f.truncate()
        #
        #     linked_users = linked_lst

    else:
        await context.bot.send_message(
            chat_id = chat_id,
            text = "驗證碼錯誤，請再試一次"
        )


async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # print(context.bot)
    username = update.message.from_user.username
    chat_id = update.effective_chat.id
    linked_user_data = LinkedUserData(username, chat_id)
    if lujc.find_linked_user(linked_user_data):
        if lujc.remove_linked_user(linked_user_data):
            await context.bot.send_message(
                chat_id = chat_id,
                text = "解除綁定成功"
            )
        else:
            await context.bot.send_message(
                chat_id = chat_id,
                text = "解除綁定失敗，請稍後在試"
            )
        return

    # 如果找不到，代表沒綁定
    await context.bot.send_message(
        chat_id = chat_id,
        text = "你尚未綁定"
    )


async def broadcast(message: str = "text"):
    for linked_user in lujc.linked_users:
        await bot.send_message(
            chat_id = linked_user.chat_id,
            text = message
        )


# 設置信號處理器，捕捉 SIGINT (Ctrl+C) 或 SIGTERM（通常是關機信號）
def handle_signal(signum, frame):
    asyncio.create_task(broadcast("關機"))
    sys.exit(0)  # 優雅退出程序

# def find_valid_user(data, linked_user):
#     for entry in data:
#         if (linked_user.username == entry.username and
#             linked_user.chat_id == entry.chat_id):
#             # 當符合條件時返回
#             return entry
#     return None  # 如果沒有符合條件的項目，返回 None



if __name__ == '__main__':
    # init_data()
    # 設定程式結束時，發送關機訊息
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    application = (ApplicationBuilder()
                   .token(token)
                   .build())

    global bot
    bot = application.bot

    handlers = [
        CommandHandler('link', link),
        MessageHandler(filters.Regex(r"^\d{6}$"), link_check),
        CommandHandler('unlink', unlink)
    ]

    application.add_handlers(handlers)

    asyncio.get_event_loop().create_task(broadcast("開機"))

    application.run_polling()