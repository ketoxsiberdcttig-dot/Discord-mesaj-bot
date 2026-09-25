import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

# Discord token Render/GitHub ortam değişkeninden alınır
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN bulunamadı.")

TG_ME = "https://api.telegram.org/bot{}/getMe"
TG_SEND = "https://api.telegram.org/bot{}/sendMessage"

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tokens = {}


async def tg_request(url, token, data=None):
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        if data is None:
            async with session.get(url.format(token)) as response:
                return await response.json()

        async with session.post(
            url.format(token),
            data=data
        ) as response:
            return await response.json()


class TokenModal(discord.ui.Modal, title="Telegram Botu Bağla"):

    token = discord.ui.TextInput(
        label="Telegram Bot Token",
        placeholder="123456:ABC...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction):
        tg_token = self.token.value.strip()

        await interaction.response.defer(ephemeral=True)

        try:
            data = await tg_request(TG_ME, tg_token)
        except Exception:
            await interaction.followup.send(
                "❌ Telegram API bağlantısı başarısız.",
                ephemeral=True
            )
            return

        if not data.get("ok"):
            await interaction.followup.send(
                "❌ Telegram bot tokenı geçersiz.",
                ephemeral=True
            )
            return

        tokens[interaction.user.id] = tg_token

        username = data["result"].get("username", "?")

        await interaction.followup.send(
            f"✅ Telegram botu bağlandı!\n"
            f"🤖 @{username}",
            ephemeral=True
        )


class QueueModal(discord.ui.Modal, title="Bildirim Gönder"):

    chat_ids = discord.ui.TextInput(
        label="Chat ID'leri",
        placeholder="123456789,987654321",
        required=True,
        max_length=1000
    )

    message = discord.ui.TextInput(
        label="Mesaj",
        placeholder="Gönderilecek mesaj...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction):

        token = tokens.get(interaction.user.id)

        if not token:
            await interaction.response.send_message(
                "❌ Önce 🔑 Bot Bağla.",
                ephemeral=True
            )
            return

        ids = [
            x.strip()
            for x in self.chat_ids.value.split(",")
            if x.strip()
        ]

        if not ids:
            await interaction.response.send_message(
                "❌ En az 1 Chat ID gir.",
                ephemeral=True
            )
            return

        if len(ids) > 20:
            await interaction.response.send_message(
                "❌ En fazla 20 Chat ID girebilirsin.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"📨 **Gönderim başladı**\n"
            f"👥 Hedef: `{len(ids)}`\n"
            f"📊 İlerleme: `0/{len(ids)}`\n"
            f"✅ Başarılı: `0`\n"
            f"❌ Hatalı: `0`",
            ephemeral=True
        )

        status_message = await interaction.original_response()

        success = 0
        failed = 0

        for index, chat_id in enumerate(ids, start=1):

            try:
                data = await tg_request(
                    TG_SEND,
                    token,
                    {
                        "chat_id": chat_id,
                        "text": self.message.value
                    }
                )

                if data.get("ok"):
                    success += 1
                else:
                    failed += 1

            except Exception:
                failed += 1

            try:
                await status_message.edit(
                    content=(
                        f"📨 **Gönderim devam ediyor**\n"
                        f"👥 Hedef: `{len(ids)}`\n"
                        f"📊 İlerleme: `{index}/{len(ids)}`\n"
                        f"✅ Başarılı: `{success}`\n"
                        f"❌ Hatalı: `{failed}`"
                    )
                )
            except discord.HTTPException:
                pass

            # Telegram API'yi gereksiz yere zorlamamak için
            # istekler arasında kısa bekleme.
            if index < len(ids):
                await asyncio.sleep(1)

        try:
            await status_message.edit(
                content=(
                    f"🏁 **Gönderim tamamlandı**\n"
                    f"👥 Hedef: `{len(ids)}`\n"
                    f"📊 İlerleme: `{len(ids)}/{len(ids)}`\n"
                    f"✅ Başarılı: `{success}`\n"
                    f"❌ Hatalı: `{failed}`"
                )
            )
        except discord.HTTPException:
            pass


class FounderView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Kurucu",
        emoji="👑",
        style=discord.ButtonStyle.secondary
    )
    async def founder(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "👑 **Kurucu**\n"
            "@ketoxhuporj",
            "https://t.me/mahserturkey",
            ephemeral=True
        )


class Panel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="BOT BAĞLA",
        emoji="🔑",
        style=discord.ButtonStyle.primary,
        custom_id="tg:bind"
    )
    async def bind(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TokenModal()
        )

    @discord.ui.button(
        label="BİLDİRİM GÖNDER",
        emoji="📨",
        style=discord.ButtonStyle.success,
        custom_id="tg:queue"
    )
    async def queue(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            QueueModal()
        )

    @discord.ui.button(
        label="DURUM",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="tg:status"
    )
    async def status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id in tokens:
            text = "🟢 Telegram botu bağlı."
        else:
            text = "🔴 Telegram botu bağlı değil."

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @discord.ui.button(
        label="KURUCU",
        emoji="👑",
        style=discord.ButtonStyle.secondary,
        custom_id="tg:founder"
    )
    async def founder(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "👑 **Kurucu**\n"
            "@ketoxhuporj",
            ephemeral=True
        )


async def ensure_panel(guild):

    me = guild.me

    if not me:
        return

    if not me.guild_permissions.manage_channels:
        print(
            f"[{guild.name}] "
            "MANAGE_CHANNELS yetkisi yok."
        )
        return

    category = discord.utils.get(
        guild.categories,
        name="TELEGRAM PANEL"
    )

    if category is None:
        category = await guild.create_category(
            "TELEGRAM PANEL"
        )

    channel = discord.utils.get(
        category.text_channels,
        name="telegram-panel"
    )

    if channel is None:
        channel = await guild.create_text_channel(
            "telegram-panel",
            category=category
        )

        await channel.send(
            "## 🤖 TELEGRAM BİLDİRİM PANELİ\n\n"
            "🔑 **Bot Bağla**\n"
            "Telegram botunu bağla.\n\n"
            "📨 **Bildirim Gönder**\n"
            "Belirlediğin Chat ID'lerine bildirim gönder.\n\n"
            "📊 **Durum**\n"
            "Telegram bağlantısını kontrol et.\n\n"
            "👑 **Kurucu**\n"
            "@ketoxhuporj",
            view=Panel()
        )


@bot.event
async def on_ready():

    if not getattr(bot, "_panel_ready", False):

        bot.add_view(Panel())

        for guild in bot.guilds:
            try:
                await ensure_panel(guild)
            except Exception as error:
                print(
                    f"[{guild.name}] Panel hatası: {error}"
                )

        bot._panel_ready = True

    print(f"✅ Giriş yapıldı: {bot.user}")


@bot.event
async def on_guild_join(guild):

    try:
        await ensure_panel(guild)
    except Exception as error:
        print(
            f"[{guild.name}] Panel hatası: {error}"
        )


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
