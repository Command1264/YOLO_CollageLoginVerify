import os
import re
import logging
import logging.handlers
import time
from datetime import datetime

from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks

from LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
from collageLogin.CYUTScholarships import CYUTScholarships

log_file_path = './logs/discord.log'
parent_path = os.path.dirname(log_file_path)
if not os.path.exists(parent_path):
    os.makedirs(parent_path, exist_ok=True)

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)



handler = logging.handlers.RotatingFileHandler(
    filename = './logs/discord.log',
    encoding = 'utf-8',
    maxBytes = 32 * 1024 * 1024,  # 32 MiB
    backupCount = 5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)


os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
linked_users_file_name = "discord_linked_users.json"
# LinkedUserJsonController
lujc = LinkedUserJsonController(linked_users_file_name)

# 當 Bot 準備好時觸發
@bot.event
async def on_ready():
    print("初始化完成！")
    print(f'目前登入身份 --> {bot.user.name} : {bot.user}')
    update_time_status.start()


# help - 取得幫助
# check - 立即檢查叫內外獎助學金更新
# history - 調取歷史紀錄
# link - 綁定訊息
# unlink - 解除綁定訊息

@bot.command(name = "check")
async def check_scholarships_update(context: discord.ext.commands.Context):

    await context.send(f"check")
    print(context.channel.id)
    print(context.author.name)
    print(context.author.id)

@bot.command(name = "ping")
async def ping(context: discord.ext.commands.Context):
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
async def link(context: discord.ext.commands.Context):

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
    print(link_check_obj.link)

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
async def unlink(context: discord.ext.commands.Context):
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

async def broadcast(message: str = "text"):
    for linked_user in lujc.linked_users.values():
        try:
            await ((await bot.fetch_user(int(linked_user.user_id)))
                   .send(message))

        except Exception as _:
            continue

@tasks.loop(seconds = 60)
async def update_time_status():
    activity = discord.Activity(
        type = discord.ActivityType.watching,
        name = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    await bot.change_presence(activity=activity)
    # print(f"Updated status to: {activity.name}")

if __name__ == "__main__":
    load_dotenv()
    cyut_scholarships = CYUTScholarships(log=True)

    bot.run(os.getenv("discordBotToken", ""), log_handler = None)
