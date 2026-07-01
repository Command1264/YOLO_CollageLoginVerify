import logging
import logging.handlers
from datetime import datetime
import socket
from pathlib import Path
from typing import Tuple

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import asyncio, sys, os
try:
    from .LinkedUserData import LinkCheck, LinkedUserData, LinkedUserJsonController
except ImportError:
    from LinkedUserData import LinkCheck, LinkedUserData, LinkedUserJsonController

from dotenv import load_dotenv

project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)
from utils.app_paths import get_bot_log_dir, get_linked_users_path, to_universal_path
from UI.check_runner import enqueue_main_check_job, get_main_check_job_status

base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.getenv("CYUT_TELEGRAM_LOG_DIR", to_universal_path(get_bot_log_dir("telegram")))
Path(log_dir).mkdir(parents = True, exist_ok = True)
log_file_path = os.path.join(
    log_dir,
    f"telegram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
logger = logging.getLogger("telegram_bot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.handlers.RotatingFileHandler(
        filename = log_file_path,
        encoding = "utf-8",
        mode = "a",
        maxBytes = 32 * 1024 * 1024,
        backupCount = 5,
    )
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def build_system_message(action: str, platform: str = "Telegram") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    computer_name = socket.gethostname()
    return f"[{platform}] {action} | 時間: {timestamp} | 電腦: {computer_name} | 平台: {platform}"

linking_users = {}
linked_users_file_name = os.getenv("CYUT_TELEGRAM_LINKED_USERS_FILE", to_universal_path(get_linked_users_path("telegram")))
# LinkedUserJsonController
lujc = LinkedUserJsonController(linked_users_file_name)

load_dotenv()


def should_notify_lifecycle() -> bool:
    raw = os.getenv("CYUT_NOTIFY_BOT_LIFECYCLE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _get_message_user_chat(update: Update) -> Tuple[str, str, int] | None:
    message = update.message
    if message is None or message.from_user is None or update.effective_chat is None:
        return None
    user_id = str(message.from_user.id)
    username = str(message.from_user.username or user_id)
    chat_id = int(update.effective_chat.id)
    return user_id, username, chat_id

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
    user_info = _get_message_user_chat(update)
    if user_info is None:
        return
    user_id, username, chat_id = user_info

    if lujc.find_linked_user(LinkedUserData(user_id, username, chat_id)):
        await context.bot.send_message(
            chat_id = chat_id,
            text = "你已完成綁定"
        )
        return

    global linking_users
    link_check_obj = LinkCheck(user_id, chat_id)
    # print(update.message.from_user.username)
    linking_users[username] = link_check_obj
    await context.bot.send_message(
        chat_id = chat_id,
        text = f"請輸入在後台端出現的{link_check_obj.link_length}位數字"
    )
    logger.info(
        "[LINK_CODE] platform=telegram user_id=%s username=%s digits=%s code=%s",
        user_id,
        username,
        link_check_obj.link_length,
        link_check_obj.link,
    )

async def link_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = _get_message_user_chat(update)
    if user_info is None:
        return
    user_id, username, chat_id = user_info
    message = update.message
    if message is None:
        return

    global linking_users
    if user_id not in linking_users.keys(): return
    link_check_obj = linking_users[user_id]
    if (
        link_check_obj.link == str(message.text or "") and
        link_check_obj.username == user_id and
        link_check_obj.chat_id == chat_id
    ):
        if lujc.add_linked_user(LinkedUserData(user_id, username, chat_id)):
            linking_users.pop(user_id, None)
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
    user_info = _get_message_user_chat(update)
    if user_info is None:
        return
    user_id, username, chat_id = user_info
    linked_user_data = LinkedUserData(user_id, username, chat_id)
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


async def check_scholarships_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None:
        return
    chat_id = int(update.effective_chat.id)
    enqueue_result = await asyncio.to_thread(enqueue_main_check_job, None, "telegram")
    if not enqueue_result.get("success", False):
        await context.bot.send_message(
            chat_id=chat_id,
            text="無法連線主程式，請確認主視窗是否正在執行。",
        )
        return

    status = str(enqueue_result.get("status", "")).strip().lower()
    if status == "loading":
        await context.bot.send_message(
            chat_id=chat_id,
            text="ScholarshipService 啟動中，請稍後再試。",
        )
        return

    queue_ahead = int(enqueue_result.get("queue_ahead", 0))
    job_id = str(enqueue_result.get("job_id", "")).strip()
    if job_id == "":
        await context.bot.send_message(
            chat_id=chat_id,
            text="主程式未回傳工作編號，請稍後再試。",
        )
        return

    message_obj = await context.bot.send_message(
        chat_id=chat_id,
        text=f"已加入佇列，前方還有 {queue_ahead} 筆。"
    )
    last_text = ""
    for _ in range(900):
        state = await asyncio.to_thread(get_main_check_job_status, job_id)
        if not state.get("success", False):
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_obj.message_id,
                text="查詢檢查狀態失敗，請稍後再試。",
            )
            return
        state_status = str(state.get("status", "")).strip().lower()
        if state_status == "queued":
            ahead = int(state.get("queue_ahead", 0))
            text = f"排隊中，前方還有 {ahead} 筆。"
        elif state_status == "running":
            progress = int(state.get("progress", 0))
            message = str(state.get("message", "檢查中"))
            text = f"檢查中... {progress}% | {message}"
        elif state_status == "completed":
            result = state.get("result", {})
            if not isinstance(result, dict):
                result = {}
            update_hint = "有更新" if result.get("has_updates", False) else "無更新"
            summary_text = "\n".join(result.get("lines", [])) or "無資料"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_obj.message_id,
                text=f"檢查完成（{update_hint}）\n{summary_text}",
            )
            return
        elif state_status == "failed":
            message = str(state.get("message", "未知錯誤"))
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_obj.message_id,
                text=f"檢查失敗\n{message}",
            )
            return
        elif state_status == "loading":
            text = "ScholarshipService 啟動中，請稍後。"
        else:
            text = f"目前狀態：{state_status or 'unknown'}"

        if text != last_text:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_obj.message_id,
                text=text,
            )
            last_text = text
        await asyncio.sleep(1.2)

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_obj.message_id,
        text="等待檢查結果逾時，請稍後再試。",
    )


async def broadcast(message: str = "text"):
    for linked_user in lujc.linked_users.values():
        await bot.send_message(
            chat_id = linked_user.chat_id,
            text = message
        )


# def find_valid_user(data, linked_user):
#     for entry in data:
#         if (linked_user.username == entry.username and
#             linked_user.chat_id == entry.chat_id):
#             # 當符合條件時返回
#             return entry
#     return None  # 如果沒有符合條件的項目，返回 None



def run_telegram_bot() -> None:
    token = os.getenv("CYUT_TELEGRAM_BOT_TOKEN", "").strip() or os.getenv("telegramBotToken", "").strip()
    async def post_init(_application):
        if should_notify_lifecycle():
            await broadcast(build_system_message("開機", "Telegram"))

    async def post_shutdown(_application):
        if should_notify_lifecycle():
            await broadcast(build_system_message("關機", "Telegram"))

    application = (ApplicationBuilder()
                   .token(token)
                   .post_init(post_init)
                   .post_shutdown(post_shutdown)
                   .build())

    global bot
    bot = application.bot

    handlers = [
        CommandHandler('link', link),
        CommandHandler('check', check_scholarships_update),
        MessageHandler(filters.Regex(r"^\d+$"), link_check),
        CommandHandler('unlink', unlink)
    ]

    application.add_handlers(handlers)

    application.run_polling()


if __name__ == '__main__':
    run_telegram_bot()
