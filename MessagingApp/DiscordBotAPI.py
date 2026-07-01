import os
import sys
import re
import time
import asyncio
import threading
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 專案導入
dir_path = os.path.dirname(__file__)
messaging_app_path = os.path.abspath(os.path.join(dir_path, '..', 'MessagingApp'))
sys.path.append(messaging_app_path)
project_root_path = os.path.abspath(os.path.join(dir_path, '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)
try:
    from .LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
except ImportError:
    from LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
from utils.app_paths import get_bot_log_dir, get_linked_users_path, to_universal_path


class ColoredFormatter(logging.Formatter):
    # ANSI escape codes
    COLORS = {
        'DEBUG': '\033[94m',    # 藍
        'INFO': '\033[97m',     # 綠
        'WARNING': '\033[93m',  # 黃
        'ERROR': '\033[91m',    # 紅
        'CRITICAL': '\033[1;41m', # 白字紅底
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


# Discord Bot 定義
class DiscordBot:

    linking_users: dict[str, LinkCheck] = dict()
    linked_users_file_name = os.getenv("CYUT_DISCORD_LINKED_USERS_FILE", to_universal_path(get_linked_users_path("discord")))
    lujc = LinkedUserJsonController(linked_users_file_name)
    logger: logging.Logger
    # cyut_scholarships: CYUTScholarships

    def __init__(self):
        super().__init__()
        load_dotenv()

        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.dm_messages = True

        self.bot = commands.Bot(command_prefix="/", intents=intents)
        self._setup_logging()
        self._setup_bot()
        # self.cyut_scholarships = CYUTScholarships(log=True)

    def _setup_logging(self):
        log_dir = os.getenv("CYUT_DISCORD_LOG_DIR", to_universal_path(get_bot_log_dir("discord")))
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file_path = os.path.join(
            log_dir,
            f"discord_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,
            backupCount=5,
        )
        # Console handler（顯示在終端機）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '[{asctime}] [{levelname:^8s}] {name}: {message}',
            '%Y-%m-%d %H:%M:%S', style='{'
        )
        color_formatter = ColoredFormatter(
            '[{asctime}] [{levelname:^8s}] {name}: {message}',
            '%Y-%m-%d %H:%M:%S', style='{'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(color_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _setup_bot(self):
        @self.bot.event
        async def on_disconnect():
            self.logger.warning("⚠️ Bot 與 Discord Gateway 連線中斷，正在嘗試重新連線...")

        @self.bot.event
        async def on_resumed():
            self.logger.info("🔄 已重新連線到 Discord Gateway。")

        @tasks.loop(seconds=60)
        async def update_time_status():
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            await self.bot.change_presence(activity=activity)

        @self.bot.event
        async def on_ready():
            self.logger.info(f"{self.bot.user} 已連線")
            update_time_status.start()

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author == self.bot.user:
                return
            if isinstance(message.channel, discord.DMChannel):
                user_id = str(message.author.id)
                if user_id in self.linking_users:
                    link_user = self.linking_users[user_id]
                    if re.match(r"^\d{" + str(link_user.link_length) + r"}$", message.content):
                        await self.link_check(message)
            message.content = message.content.lower()
            await self.bot.process_commands(message)

        @self.bot.command(name="check")
        async def check_scholarships_update(ctx):
            pass
            # reply = await ctx.reply("檢查中，請稍後...")
            # messages = []
            # for title, (success, updated) in [
            #     ("校內外獎助學金", self.cyut_scholarships.load_scholarships()),
            #     ("個人申請結果", self.cyut_scholarships.load_apply_scholarships()),
            # ]:
            #     messages.append(f"{title} {'上傳成功!' if updated else '沒有更新。' if success else '上傳失敗！！！'}")
            # await reply.edit(content="\n".join(messages))

        @self.bot.command(name="ping")
        async def ping(ctx):
            latency = round(self.bot.latency * 1000)
            await ctx.reply(f"WebSocket 延遲: {latency:.2f} ms")

        @self.bot.command(name="api_ping")
        async def api_ping(ctx):
            start = time.perf_counter()
            msg = await ctx.reply("測試中...")
            latency = (time.perf_counter() - start) * 1000
            await msg.edit(content=f"API 延遲: {latency:.2f} ms")

        @self.bot.command(name="link")
        async def link(ctx):
            user_id = str(ctx.author.id)
            username = ctx.author.name
            chat_id = ctx.channel.id

            if self.lujc.find_linked_user(LinkedUserData(user_id, username, chat_id)):
                await ctx.reply("你已完成綁定")
                return

            link_check_obj = LinkCheck(user_id, chat_id)
            self.linking_users[user_id] = link_check_obj
            await ctx.reply("請輸入在後台端出現的六位數字")
            self.logger.info(link_check_obj.link)

        @self.bot.command(name="unlink")
        async def unlink(ctx):
            user_id = str(ctx.author.id)
            username = ctx.author.name
            chat_id = ctx.channel.id

            user_data = LinkedUserData(user_id, username, chat_id)
            if self.lujc.find_linked_user(user_data):
                if self.lujc.remove_linked_user(user_data):
                    await ctx.reply("解除綁定成功")
                else:
                    await ctx.reply("解除綁定失敗，請稍後再試")
            else:
                await ctx.reply("你尚未綁定")

    async def start_bot(self):
        try:
            self.logger.info("Discord Bot 啟動中...")
            token = os.getenv("CYUT_DISCORD_BOT_TOKEN", "").strip() or os.getenv("discordBotToken", "").strip()
            await self.bot.start(token)
        except Exception as e:
            self.logger.error(f"連線錯誤: {e}")
        finally:
            await self.bot.close()

    async def stop_bot(self):
        if not self.bot.is_closed():
            await self.bot.close()

    async def broadcast(self, message: str = "text") -> list[discord.Message]:
        sent = []
        for user in self.lujc.linked_users.values():
            try:
                sent.append(await (await self.bot.fetch_user(int(user.user_id))).send(message))
            except:
                continue
        return sent

    async def link_check(self, message: discord.Message):
        user_id = str(message.author.id)
        chat_id = message.channel.id
        link_obj = self.linking_users[user_id]

        if (
            link_obj.link == message.content and
            link_obj.username == user_id and
            link_obj.chat_id == chat_id
        ):
            if self.lujc.add_linked_user(LinkedUserData(user_id, message.author.name, chat_id)):
                self.linking_users.pop(user_id, None)
                await message.reply("綁定成功")
            else:
                await message.reply("綁定失敗，請稍後再試")
        else:
            await message.reply("驗證碼錯誤，請再試一次")


# ---------------- Flask 與 Discord 整合 ------------------

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

discord_bot = DiscordBot()


@app.route("/api/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    message = data.get("message", "Hello from Flask")

    future = asyncio.run_coroutine_threadsafe(discord_bot.broadcast(message), loop)
    try:
        result = future.result(timeout=10)
        return jsonify({"status": "success", "sent_count": len(result)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def start_bot_thread():
    loop.run_until_complete(discord_bot.start_bot())


if __name__ == "__main__":
    threading.Thread(target=start_bot_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
