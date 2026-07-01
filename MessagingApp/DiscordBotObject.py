import os, sys
import re
import asyncio
import time
import importlib

import discord
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
from PySide6.QtCore import QObject, Signal
from typing import Protocol

messaging_app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'MessagingApp'))
sys.path.append(messaging_app_path)
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)

try:
    from .LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
except ImportError:
    from LinkedUserData import LinkedUserDataEncoder, LinkedUserJsonController, LinkedUserData, LinkCheck
from utils.app_paths import get_bot_log_dir, get_linked_users_path, to_universal_path

collage_login_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'collageLogin'))
sys.path.append(collage_login_path)


class DiscordBot(QObject):
    status_signal = Signal(str)
    command_signal = Signal(str, str)

    linking_users: dict[str, LinkCheck] = dict()
    linked_users_file_name = os.getenv("CYUT_DISCORD_LINKED_USERS_FILE", to_universal_path(get_linked_users_path("discord")))
    # LinkedUserJsonController
    lujc = LinkedUserJsonController(linked_users_file_name)

    class _ScholarshipApi(Protocol):
        def load_scholarships(self) -> tuple[bool, bool]:
            ...

        def load_apply_scholarships(self) -> tuple[bool, bool]:
            ...

    cyut_scholarships: _ScholarshipApi | None

    def __init__(self):
        super().__init__()
        load_dotenv()


        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.dm_messages = True  # 啟用接收私訊的功能
        self.bot = commands.Bot(
            command_prefix = "/",
            intents = intents,
        )

        self._setup_logging()
        self._setup_commands()

        self.cyut_scholarships = None

    def _get_cyut_scholarships(self) -> _ScholarshipApi:
        if self.cyut_scholarships is None:
            module = importlib.import_module("collageLogin.CYUTScholarships")
            scholarship_class = getattr(module, "CYUTScholarships")
            self.cyut_scholarships = scholarship_class(log=True)
        if self.cyut_scholarships is None:
            raise RuntimeError("CYUTScholarships 初始化失敗")
        return self.cyut_scholarships

    def _setup_logging(self):
        log_dir = os.getenv("CYUT_DISCORD_LOG_DIR", to_universal_path(get_bot_log_dir("discord")))
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file_path = os.path.join(
            log_dir,
            f"discord_object_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(
            filename = log_file_path,
            encoding = 'utf-8',
            maxBytes = 32 * 1024 * 1024,  # 32 MiB
            backupCount = 5,  # Rotate through 5 files
        )

        formatter = logging.Formatter(
            '[{asctime}] [{levelname:<8s}] {name}: {message}',
            '%Y-%m-%d %H:%M:%S',
            style='{'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _setup_commands(self):
        @tasks.loop(seconds=60)
        async def update_time_status():
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            await self.bot.change_presence(activity=activity)

        @self.bot.event
        async def on_ready():
            self.status_signal.emit(f"{self.bot.user} 已連線")
            print(f"{self.bot.user} 已連線")
            update_time_status.start()

        @self.bot.event
        async def on_message(message: discord.Message):
            # 確保不會回應自己
            if message.author == self.bot.user: return

            # 檢查消息是否來自私訊
            if isinstance(message.channel, discord.DMChannel):
                # 使用正則表達式檢查訊息內容
                user_id = str(message.author.id)
                if user_id in self.linking_users:
                    link_user = self.linking_users[user_id]
                    if re.match(r"^\d{" + str(link_user.link_length) + r"}$", message.content):  # 假設匹配 6 位數字
                        await self.link_check(message)  # 如果符合條件，調用處理函數

            # 將所有英文轉小寫，方便觸發指令
            message.content = message.content.lower()
            # 處理其他邏輯（如指令等）
            await self.bot.process_commands(message)

        @self.bot.command(name="check")
        async def check_scholarships_update(context: Context):
            try:
                scholarships = self._get_cyut_scholarships()
            except Exception as exc:
                await context.reply(f"初始化失敗: {exc}")
                return
            reply_message = await context.reply("檢查中，請稍後...")
            tmp_messages = []
            for title, (success, has_update) in [
                ["校內外獎助學金", scholarships.load_scholarships()],
                ["個人申請結果", scholarships.load_apply_scholarships()],
            ]:
                if success:
                    if has_update:
                        tmp_messages.append(f"{title} 上傳成功!")
                    else:
                        tmp_messages.append(f"{title} 沒有更新。")
                else:
                    tmp_messages.append(f"{title} 上傳失敗！！！")

            if len(tmp_messages) != 0:
                await reply_message.edit(content=f"\n".join(tmp_messages))

        @self.bot.command(name="ping")
        async def ping(context: Context):
            latency = round(self.bot.latency * 1000)  # 計算延遲（毫秒）
            await context.reply(f"WebSocket 延遲: {latency:.2f} ms")

        @self.bot.command(name="api_ping")
        async def api_ping(context: Context):
            start_time = time.perf_counter()  # 開始計時
            message = await context.reply("測試中...")
            end_time = time.perf_counter()  # 記錄時間

            api_latency = (end_time - start_time) * 1000  # 計算延遲
            await message.edit(content=f"API 延遲: {api_latency:.2f} ms")

        @self.bot.command(name="link")
        async def link(context: Context):

            user_id = str(context.author.id)
            username = context.author.name
            chat_id = context.channel.id

            if self.lujc.find_linked_user(LinkedUserData(user_id, username, chat_id)):
                await context.reply("你已完成綁定")
                return

            link_check_obj = LinkCheck(user_id, chat_id)
            # print(update.message.from_user.username)
            self.linking_users[user_id] = link_check_obj
            await context.reply("請輸入在後台端出現的六位數字")
            print(link_check_obj.link)

        @self.bot.command(name="unlink")
        async def unlink(context: Context):
            user_id = str(context.author.id)
            username = context.author.name
            chat_id = context.channel.id

            linked_user_data = LinkedUserData(user_id, username, chat_id)
            if self.lujc.find_linked_user(linked_user_data):
                if self.lujc.remove_linked_user(linked_user_data):
                    await context.reply("解除綁定成功")
                else:
                    await context.reply("解除綁定失敗，請稍後在試")
                return

            # 如果找不到，代表沒綁定
            await context.reply("你尚未綁定")


    async def start_bot(self):
        try:
            print("Discord Bot 啟動中...")
            token = os.getenv("CYUT_DISCORD_BOT_TOKEN", "").strip() or os.getenv("discordBotToken", "").strip()
            await self.bot.start(token)
            # print("Discord Bot 啟動完成")
        except Exception as e:
            self.status_signal.emit(f"連線錯誤: {str(e)}")
            print(f"連線錯誤: {str(e)}")
        finally:
            await self.bot.close()

    async def stop_bot(self):
        if self.bot.is_closed():
            return
        await self.bot.close()

    async def broadcast(self, message: str = "text") -> list[discord.Message]:
        messages = []
        for linked_user in self.lujc.linked_users.values():
            try:
                messages.append(await ((await self.bot.fetch_user(int(linked_user.user_id)))
                                       .send(message)))
            except Exception as _:
                continue

        return messages

    async def link_check(self, message: discord.Message):
        user_id = str(message.author.id)
        chat_id = message.channel.id

        # 前面有檢查了，所以這裡不檢查
        # if user_id not in linking_users.keys(): return
        link_check_obj = self.linking_users[user_id]
        # 這裡因為 link_check_obj.username 上面是丟入 user_id，所以這裡判斷也是用 user_id
        if (
                link_check_obj.link == message.content and
                link_check_obj.username == user_id and
                link_check_obj.chat_id == chat_id
        ):
            if self.lujc.add_linked_user(LinkedUserData(user_id, message.author.name, chat_id)):
                self.linking_users.pop(user_id, None)
                await message.reply("綁定成功")
            else:
                await message.reply("綁定失敗，請稍後在試")

        else:
            await message.reply("驗證碼錯誤，請再試一次")


async def main():
    discord_bot = DiscordBot()
    try:
        await discord_bot.start_bot()
    except asyncio.CancelledError:
        print("Bot task cancelled.")
    finally:
        await discord_bot.stop_bot()  # 確保結束時執行停止邏輯

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ctrl + C detected, shutting down...")
