import asyncio
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

BOT_TOKEN = "8602088863:AAE6OaqX1XrseigB9cawnRrzzX7cQIOZjy8"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

emoji_cache: dict[str, list[dict]] = {}


def build_format_keyboard(msg_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 JSON", callback_data=f"fmt:json:{msg_id}"),
            InlineKeyboardButton(text="📝 Plain Text", callback_data=f"fmt:plain:{msg_id}"),
        ],
        [
            InlineKeyboardButton(text="🆔 IDs Only", callback_data=f"fmt:ids:{msg_id}"),
            InlineKeyboardButton(text="🧾 HTML Tag", callback_data=f"fmt:html:{msg_id}"),
        ]
    ])


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Send me any message containing custom emoji and I'll extract all the data.\n\nChoose your output format after sending."
    )


@dp.message(F.text | F.caption)
async def handle_message(message: Message):
    entities = message.entities or message.caption_entities or []
    custom_emojis = [e for e in entities if e.type == "custom_emoji"]

    if not custom_emojis:
        await message.reply("No custom emoji found in your message.")
        return

    text = message.text or message.caption or ""

    data = []
    for e in custom_emojis:
        emoji_char = text[e.offset:e.offset + e.length]
        data.append({
            "type": e.type,
            "offset": e.offset,
            "length": e.length,
            "custom_emoji_id": e.custom_emoji_id,
            "emoji_char": emoji_char
        })

    cache_key = str(message.message_id)
    emoji_cache[cache_key] = data

    await message.reply(
        f"Found <b>{len(data)}</b> custom emoji. Pick a format:",
        parse_mode="HTML",
        reply_markup=build_format_keyboard(cache_key)
    )


@dp.callback_query(F.data.startswith("fmt:"))
async def handle_format(callback: CallbackQuery):
    _, fmt, cache_key = callback.data.split(":", 2)
    data = emoji_cache.get(cache_key)

    if not data:
        await callback.answer("Session expired. Send the emoji again.", show_alert=True)
        return

    if fmt == "json":
        output = f"<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>"
    elif fmt == "plain":
        lines = []
        for i, e in enumerate(data, 1):
            lines.append(
                f"#{i}\n"
                f"  Emoji: {e['emoji_char']}\n"
                f"  ID: {e['custom_emoji_id']}\n"
                f"  Offset: {e['offset']}\n"
                f"  Length: {e['length']}"
            )
        output = "\n\n".join(lines)
    elif fmt == "ids":
        ids = [e["custom_emoji_id"] for e in data]
        output = "\n".join(ids)
    elif fmt == "html":
        tags = [
            f'&lt;tg-emoji emoji-id="{e["custom_emoji_id"]}"&gt;{e["emoji_char"]}&lt;/tg-emoji&gt;'
            for e in data
        ]
        output = "\n".join(tags)
    else:
        await callback.answer("Unknown format.", show_alert=True)
        return

    await callback.message.answer(output, parse_mode="HTML")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
