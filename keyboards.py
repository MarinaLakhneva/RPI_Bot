from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить напоминание'), KeyboardButton('Редактировать текущие дела')) \
        .add(KeyboardButton('Посмотреть запланированные дела'), KeyboardButton('Посмотреть завершенные дела'))
    return kb


def get_file_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Файлы не требуются'))

    return kb


def get_what_to_change_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Описание'), KeyboardButton('Файлы')) \
        .add(KeyboardButton('Дата'), KeyboardButton('Время')) \
        .add(KeyboardButton('Отметить как выполненное'), KeyboardButton('Изменить периодичность')) \
        .add(KeyboardButton('Удалить напоминание'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_files_update_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить новый'), KeyboardButton('Удалить имеющийся')) \
        .add(KeyboardButton('Вернуться в главное меню'))

    return kb


def get_done_tasks_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Вернуть дело в незавершенное'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_back_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Вернуться в главное меню'))

    return kb


def get_ikb_with_notifications(list_of_notifications: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_notifications)):
        noty = list_of_notifications[i][1] + list_of_notifications[i][2] + list_of_notifications[i][3]
        ikb.add(InlineKeyboardButton(text=f'{noty}',
                                     callback_data=f'{list_of_notifications[i][0]}'))
    return ikb


def get_ikb_with_filenames(list_of_files: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_files)):
        callback_data = list_of_files[i] if len(list_of_files[i]) < 10 else list_of_files[i][:10]
        ikb.add(InlineKeyboardButton(text=f'{list_of_files[i]}',
                                     callback_data=callback_data))
    return ikb
