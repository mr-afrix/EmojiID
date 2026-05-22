import asyncio
import json
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import MessageEntityType

BOT_TOKEN = "8602088863:AAE6OaqX1XrseigB9cawnRrzzX7cQIOZjy8"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cache: dict[str, list[dict]] = {}


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


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Send me any custom emoji or sticker and I'll extract all data from it.\n\n"
        "Works with:\n"
        "• Custom emoji in text\n"
        "• Animated stickers\n"
        "• App icon emoji packs\n"
        "• Regular stickers"
    )


@dp.message(F.sticker)
async def handle_sticker(message: Message):
    s = message.sticker
    data = [{
        "source": "sticker",
        "file_id": s.file_id,
        "file_unique_id": s.file_unique_id,
        "custom_emoji_id": s.custom_emoji_id,
        "emoji": s.emoji,
        "set_name": s.set_name,
        "type": s.type,
        "is_animated": s.is_animated,
        "is_video": s.is_video,
        "width": s.width,
        "height": s.height,
        "thumbnail_file_id": s.thumbnail.file_id if s.thumbnail else None,
        "thumbnail_file_unique_id": s.thumbnail.file_unique_id if s.thumbnail else None,
    }]
    key = str(message.message_id)
    cache[key] = data
    await message.reply("Sticker received! Pick a format:", reply_markup=keyboard(key))


@dp.message(F.text | F.caption)
async def handle_text(message: Message):
    entities = message.entities or message.caption_entities or []
    text = message.text or message.caption or ""

    custom = [e for e in entities if e.type == MessageEntityType.CUSTOM_EMOJI]

    if not custom:
        await message.reply(
            "No custom emoji found.\n\n"
            "Make sure you're sending emoji from the <b>custom emoji packs</b> (not standard unicode emoji).\n"
            "Try sending them as stickers instead.",
            parse_mode="HTML"
        )
        return

    data = []
    for e in custom:
        try:
            char = text[e.offset: e.offset + e.length]
        except Exception:
            char = ""
        data.append({
            "source": "custom_emoji_entity",
            "type": e.type,
            "custom_emoji_id": e.custom_emoji_id,
            "emoji_char": char,
            "offset": e.offset,
            "length": e.length,
        })

    key = str(message.message_id)
    cache[key] = data
    await message.reply(
        f"Found <b>{len(data)}</b> custom emoji. Pick a format:",
        parse_mode="HTML",
        reply_markup=keyboard(key)
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
        output = f"<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>"

    elif fmt == "plain":
        lines = []
        for i, e in enumerate(data, 1):
            line = f"<b>#{i}</b>\n"
            for k, v in e.items():
                line += f"  <b>{k}:</b> {v}\n"
            lines.append(line.strip())
        output = "\n\n".join(lines)

    elif fmt == "ids":
        ids = []
        for e in data:
            val = e.get("custom_emoji_id") or e.get("file_unique_id") or "N/A"
            ids.append(str(val))
        output = "<pre>" + "\n".join(ids) + "</pre>"

    elif fmt == "html":
        tags = []
        for e in data:
            if e.get("source") == "custom_emoji_entity":
                tags.append(
                    f'&lt;tg-emoji emoji-id="{e["custom_emoji_id"]}"&gt;'
                    f'{e.get("emoji_char", "⭐")}'
                    f'&lt;/tg-emoji&gt;'
                )
            else:
                cid = e.get("custom_emoji_id")
                emoji = e.get("emoji", "⭐")
                if cid:
                    tags.append(f'&lt;tg-emoji emoji-id="{cid}"&gt;{emoji}&lt;/tg-emoji&gt;')
                else:
                    tags.append(f"No HTML tag available\nfile_unique_id: {e.get('file_unique_id')}")
        output = "\n".join(tags)

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
