import os, re, sys
import asyncio
import signal
import socket
import logging
import logging.handlers
import time
from datetime import datetime
from pathlib import Path

from discord import Message
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context

try:
    from .LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
except ImportError:
    from LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck

collage_login_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'collageLogin'))
sys.path.append(collage_login_path)
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)
from utils.app_paths import get_bot_log_dir, get_linked_users_path, to_universal_path
from UI.check_runner import enqueue_main_check_job, get_main_check_job_status

log_dir = os.getenv("CYUT_DISCORD_LOG_DIR", to_universal_path(get_bot_log_dir("discord")))
Path(log_dir).mkdir(parents = True, exist_ok = True)
log_file_path = os.path.join(
    log_dir,
    f"discord_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)



handler = logging.handlers.RotatingFileHandler(
    filename = log_file_path,
    encoding = 'utf-8',
    mode = 'a',
    maxBytes = 32 * 1024 * 1024,  # 32 MiB
    backupCount = 5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)


def write_link_audit(user_id: str, username: str, digits: int, code: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_line = (
        f"[{timestamp}] [INFO    ] discord_link: "
        f"[LINK_CODE] platform=discord user_id={user_id} username={username} digits={digits} code={code}\n"
    )
    with open(log_file_path, "a", encoding="utf-8") as file:
        file.write(audit_line)


def build_system_message(action: str, platform: str = "Discord") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    computer_name = socket.gethostname()
    return f"[{platform}] {action} | 時間: {timestamp} | 電腦: {computer_name} | 平台: {platform}"


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True  # 啟用接收私訊的功能

# 創建 Bot 實例
bot = commands.Bot(
    command_prefix = "/",
    intents = intents,
)

linking_users: dict[str, LinkCheck] = {}
linked_users_file_name = os.getenv("CYUT_DISCORD_LINKED_USERS_FILE", to_universal_path(get_linked_users_path("discord")))
# LinkedUserJsonController
lujc = LinkedUserJsonController(linked_users_file_name)
startup_notified = False


def should_notify_lifecycle() -> bool:
    raw = os.getenv("CYUT_NOTIFY_BOT_LIFECYCLE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}

# 當 Bot 準備好時觸發
@bot.event
async def on_ready():
    global startup_notified
    print("初始化完成！")
    user = bot.user
    print(f'目前登入身份 --> {user.name if user is not None else "未知"} : {user}')
    if should_notify_lifecycle() and (not startup_notified):
        await broadcast(build_system_message("開機", "Discord"))
        startup_notified = True
    update_time_status.start()


# help - 取得幫助
# check - 立即檢查叫內外獎助學金更新
# history - 調取歷史紀錄
# link - 綁定訊息
# unlink - 解除綁定訊息

@bot.command(name = "check")
async def check_scholarships_update(context: Context):
    enqueue_result = await asyncio.to_thread(enqueue_main_check_job, None, "discord")
    if not enqueue_result.get("success", False):
        await context.send("無法連線主程式，請確認主視窗是否正在執行。")
        return

    status = str(enqueue_result.get("status", "")).strip().lower()
    if status == "loading":
        await context.send("ScholarshipService 啟動中，請稍後再試。")
        return

    queue_ahead = int(enqueue_result.get("queue_ahead", 0))
    job_id = str(enqueue_result.get("job_id", "")).strip()
    if job_id == "":
        await context.send("主程式未回傳工作編號，請稍後再試。")
        return
    status_message = await context.send(f"已加入佇列，前方還有 {queue_ahead} 筆。")

    last_text = ""
    for _ in range(900):
        state = await asyncio.to_thread(get_main_check_job_status, job_id)
        if not state.get("success", False):
            await status_message.edit(content="查詢檢查狀態失敗，請稍後再試。")
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
            await status_message.edit(content=f"檢查完成（{update_hint}）\n{summary_text}")
            return
        elif state_status == "failed":
            message = str(state.get("message", "未知錯誤"))
            await status_message.edit(content=f"檢查失敗\n{message}")
            return
        elif state_status == "loading":
            text = "ScholarshipService 啟動中，請稍後。"
        else:
            text = f"目前狀態：{state_status or 'unknown'}"

        if text != last_text:
            await status_message.edit(content=text)
            last_text = text
        await asyncio.sleep(1.2)

    await status_message.edit(content="等待檢查結果逾時，請稍後再試。")

@bot.command(name = "ping")
async def ping(context: Context):
    latency = round(bot.latency * 1000)  # 計算延遲（毫秒）
    await context.send(f"Pong! Latency is {latency} ms.")

@bot.command(name="api_ping")
async def api_ping(ctx):
    start_time = time.perf_counter()  # 開始計時
    message = await ctx.send("測試中...")
    end_time = time.perf_counter()  # 記錄時間

    api_latency = (end_time - start_time) * 1000  # 計算延遲
    await message.edit(content=f"API 延遲: {api_latency:.2f} ms")

@bot.command(name = "link")
async def link(context: Context):

    user_id = str(context.author.id)
    username = context.author.name
    chat_id = context.channel.id

    if lujc.find_linked_user(LinkedUserData(user_id, username, chat_id)):
        await context.send("你已完成綁定")
        return

    global linking_users
    link_check_obj = LinkCheck(user_id, chat_id)
    # print(update.message.from_user.username)
    linking_users[user_id] = link_check_obj
    await context.send("請輸入在後台端出現的六位數字")
    logger.info(
        "[LINK_CODE] platform=discord user_id=%s username=%s digits=%s code=%s",
        user_id,
        username,
        link_check_obj.link_length,
        link_check_obj.link,
    )
    write_link_audit(
        user_id=user_id,
        username=username,
        digits=link_check_obj.link_length,
        code=link_check_obj.link,
    )

@bot.event
async def on_message(message: discord.Message):
    # 確保不會回應自己
    if message.author == bot.user: return

    # 檢查消息是否來自私訊
    if isinstance(message.channel, discord.DMChannel):
        # 使用正則表達式檢查訊息內容
        user_id = str(message.author.id)
        global linking_users
        if user_id in linking_users:
            link_user = linking_users[user_id]
            if re.match(r"^\d{" + str(link_user.link_length) + r"}$", message.content):  # 假設匹配 6 位數字
                await link_check(message)  # 如果符合條件，調用處理函數

    # 處理其他邏輯（如命令等）
    await bot.process_commands(message)


async def link_check(message: discord.Message):
    user_id = str(message.author.id)
    chat_id = message.channel.id

    global linking_users
    # 前面有檢查了，所以這裡不檢查
    # if user_id not in linking_users.keys(): return
    link_check_obj = linking_users[user_id]
    # 這裡因為 link_check_obj.username 上面是丟入 user_id，所以這裡判斷也是用 user_id
    if (
        link_check_obj.link == message.content and
        link_check_obj.username == user_id and
        link_check_obj.chat_id == chat_id
    ):
        if lujc.add_linked_user(LinkedUserData(user_id, message.author.name, chat_id)):
            linking_users.pop(user_id, None)
            await message.author.send("綁定成功")
        else:
            await message.author.send("綁定失敗，請稍後在試")

    else:
        await message.author.send("驗證碼錯誤，請再試一次")

@bot.command(name = "unlink")
async def unlink(context: Context):
    user_id = str(context.author.id)
    username = context.author.name
    chat_id = context.channel.id

    linked_user_data = LinkedUserData(user_id, username, chat_id)
    if lujc.find_linked_user(linked_user_data):
        if lujc.remove_linked_user(linked_user_data):
            await context.send("解除綁定成功")
        else:
            await context.send("解除綁定失敗，請稍後在試")
        return

    # 如果找不到，代表沒綁定
    await context.send("你尚未綁定")

async def broadcast(message: str = "text") -> list[Message]:
    messages = []
    for linked_user in lujc.linked_users.values():
        try:
            messages.append(await ((await bot.fetch_user(int(linked_user.user_id)))
                                   .send(message)))
        except Exception as _:
            continue

    return messages


def handle_signal(signum, frame):
    try:
        if should_notify_lifecycle() and bot.loop and bot.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                broadcast(build_system_message("關機", "Discord")),
                bot.loop
            )
            future.result(timeout = 8)
    except Exception as exc:
        logger.error("關機通知送出失敗: %s", exc)
    finally:
        raise SystemExit(0)

@tasks.loop(seconds = 60)
async def update_time_status():
    activity = discord.Activity(
        type = discord.ActivityType.watching,
        name = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    await bot.change_presence(activity=activity)
    # print(f"Updated status to: {activity.name}")

def run_discord_bot() -> None:
    load_dotenv()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    token = os.getenv("CYUT_DISCORD_BOT_TOKEN", "").strip() or os.getenv("discordBotToken", "").strip()
    bot.run(token, log_handler = None)


if __name__ == "__main__":
    run_discord_bot()
