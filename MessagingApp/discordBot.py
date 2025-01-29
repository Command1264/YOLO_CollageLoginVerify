import os
from dotenv import load_dotenv

import discord
from discord.ext import commands


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True  # 啟用接收私訊的功能

# 創建 Bot 實例
bot = commands.Bot(command_prefix = "/", intents = intents)

# 當 Bot 準備好時觸發
@bot.event
async def on_ready():
    print(f'目前登入身份 --> {bot.user.name} : {bot.user}')

    # 同步斜杠命令到 Discord
    # try:
    #     synced = await bot.tree.sync()
    #     print(f"同步 {len(synced)} 個指令")
    # except Exception as e:
    #     print(f"同步指令失敗: {e}")


# help - 取得幫助
# check - 立即檢查叫內外獎助學金更新
# history - 調取歷史紀錄
# link - 綁定訊息
# unlink - 解除綁定訊息

@bot.command(name = "check")
async def check_scholarships_update(context: discord.ext.commands.Context):
    await context.send(f"check")
    pass

@bot.command(name = "ping")
async def ping(context: discord.ext.commands.Context):
    latency = round(bot.latency * 1000)  # 計算延遲（毫秒）
    await context.send(f"Pong! Latency is {latency} ms.")

if __name__ == "__main__":
    load_dotenv()

    bot.run(os.getenv("discordBotToken", ""))
