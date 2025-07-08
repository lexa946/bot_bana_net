from aiogram.utils.keyboard import InlineKeyboardBuilder


def yes_no_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data=f"yes")
    kb.button(text="Нет", callback_data="no")
    kb.adjust(1)
    return kb.as_markup()


