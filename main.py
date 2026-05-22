import asyncio
import json
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ContentType

BOT_TOKEN = "8602088863:AAE6OaqX1XrseigB9cawnRrzzX7cQIOZjy8"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cache: dict[str, list[dict]] = {}

EMOJI_ID = "5330237710655306682"
E = f'<tg-emoji emoji-id="{EMOJI_ID}">⭐</tg-emoji>'


def keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 JSON", callback_data=f"fmt:json:{key}"),
            InlineKeyboardButton(text="📝 Plain", callback_data=f"fmt:plain:{key}"),
        ],
        [
            InlineKeyboardButton(text="🆔 ID Only", callback_data=f"fmt:ids:{key}"),
            InlineKeyboardButton(text="🧾 HTML Tag", callback_data=f"fmt:html:{key}"),
        ]
    ])


def utf16_char(text: str, offset: int, length: int) -> str:
    encoded = text.encode("utf-16-le")
    chunk = encoded[offset * 2: (offset + length) * 2]
    return chunk.decode("utf-16-le")


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"{E} <b>Emoji ID Bot</b>\n\n"
        f"Send me any custom emoji or sticker and I'll extract all the data.\n\n"
        f"{E} App icon emoji → send from sticker picker\n"
        f"{E} Inline custom emoji → just send it in text",
        parse_mode="HTML"
    )


@dp.message()
async def handle_all(message: Message):
    key = str(message.message_id)

    if message.content_type == ContentType.STICKER:
        s = message.sticker
        data = [{
            "source": "sticker",
            "file_id": s.file_id,
            "file_unique_id": s.file_unique_id,
            "custom_emoji_id": s.custom_emoji_id,
            "emoji": s.emoji,
            "set_name": s.set_name,
            "type": str(s.type),
            "is_animated": s.is_animated,
            "is_video": s.is_video,
            "width": s.width,
            "height": s.height,
            "thumbnail_file_id": s.thumbnail.file_id if s.thumbnail else None,
            "thumbnail_file_unique_id": s.thumbnail.file_unique_id if s.thumbnail else None,
        }]
        cache[key] = data
        await message.reply(
            f"{E} Sticker received! Pick a format:",
            parse_mode="HTML",
            reply_markup=keyboard(key)
        )
        return

    if message.content_type == ContentType.TEXT:
        entities = message.entities or []
        text = message.text or ""
        custom = [e for e in entities if e.type == "custom_emoji"]

        if custom:
            data = []
            for e in custom:
                char = utf16_char(text, e.offset, e.length)
                data.append({
                    "source": "custom_emoji",
                    "custom_emoji_id": e.custom_emoji_id,
                    "emoji_char": char,
                    "offset": e.offset,
                    "length": e.length,
                })
            cache[key] = data
            await message.reply(
                f"{E} Found <b>{len(data)}</b> custom emoji. Pick a format:",
                parse_mode="HTML",
                reply_markup=keyboard(key)
            )
            return

        await message.reply(
            f"{E} No custom emoji found.\n\n"
            "Send a custom emoji inline in text, or send an app icon as a sticker.",
            parse_mode="HTML"
        )
        return

    await message.reply(
        f"{E} Unsupported message type: <code>{message.content_type}</code>",
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("fmt:"))
async def handle_format(callback: CallbackQuery):
    parts = callback.data.split(":", 2)
    fmt = parts[1]
    key = parts[2]
    data = cache.get(key)

    if not data:
        await callback.answer("Session expired. Send the emoji again.", show_alert=True)
        return

    if fmt == "json":
        output = f"{E} <b>JSON Output</b>\n\n<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>"

    elif fmt == "plain":
        lines = []
        for i, e in enumerate(data, 1):
            line = f"{E} <b>#{i}</b>\n"
            for k, v in e.items():
                line += f"  <b>{k}:</b> <code>{v}</code>\n"
            lines.append(line.strip())
        output = "\n\n".join(lines)

    elif fmt == "ids":
        ids = [str(e.get("custom_emoji_id") or e.get("file_unique_id") or "N/A") for e in data]
        output = f"{E} <b>IDs</b>\n\n<pre>" + "\n".join(ids) + "</pre>"

    elif fmt == "html":
        tags = []
        for e in data:
            cid = e.get("custom_emoji_id")
            char = e.get("emoji_char") or e.get("emoji") or "⭐"
            if cid:
                tags.append(f'&lt;tg-emoji emoji-id="{cid}"&gt;{char}&lt;/tg-emoji&gt;')
            else:
                tags.append(f"No custom_emoji_id\nfile_unique_id: {e.get('file_unique_id')}")
        output = f"{E} <b>HTML Tags</b>\n\n" + "\n".join(tags)

    else:
        await callback.answer("Unknown format.", show_alert=True)
        return

    await callback.message.answer(output, parse_mode="HTML")
    await callback.answer()


async def health(request):
    return web.Response(text="OK")


async def main():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
