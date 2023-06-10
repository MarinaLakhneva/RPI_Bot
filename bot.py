from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from aiogram.dispatcher.filters import Text
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram.types import Message, CallbackQuery

from keyboards import *
from sqlite import *

from config import TOKEN_API
import datetime
from datetime import timedelta
import aioschedule
import asyncio

from google_drive import create_folder_in_folder, is_directory_or_file_exists, upload_file, get_list_of_files, \
    delete_files_from_google_disk

import os


#  запуск бота каждые полминуты
async def scheduler():
    aioschedule.every(0.5).minutes.do(notification_function)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(0.5)


#  пересчет дней для периодических дел
def add_days(date, add_type):
    date0 = datetime.datetime.strptime(str(date), "%d/%m/%Y").date()
    if add_type == 1:
        date = date0 + timedelta(days=1)
    if add_type == 2:
        date = date0 + timedelta(days=7)
    if add_type == 3:
        date = date0 + timedelta(days=30)

    date = str(date)
    if '-' in date:
        date = date.replace('-', '/')
        date = date.split('/')
        date.reverse()
        date = '/'.join(date)
        date = str(date)

    return date


#  сревнивает текущее время и дату с датой дела (пора ли отправлять?)
def check_for_notification(date, project_time):
    if date:
        if '-' in date:
            date = date.replace('-', '/')
            date = date.split('/')
            date.reverse()
            date = '/'.join(date)
            date = str(date)

        d1 = datetime.datetime.strptime(date, "%d/%m/%Y").date()
        d2 = datetime.datetime.now().date()

        t1 = datetime.datetime.strptime(project_time, '%H:%M').time()

        current_date_time = datetime.datetime.now()
        t2 = current_date_time.time()

        if d2 > d1:
            return True
        elif d2 == d1 and t2 >= t1:
            return True
        else:
            return False


async def on_startup(_):
    await db_start()
    asyncio.create_task(scheduler())


storage = MemoryStorage()
bot = Bot(TOKEN_API)
dp = Dispatcher(bot,
                storage=storage)


class NotificationStatesGroup(StatesGroup):
    """машина конечных состояний бота. Основные состояния"""
    description = State()
    calendar = State()
    time = State()
    file = State()


class UpdateNotificationsStateGroup(StatesGroup):
    """машина конечных состояний бота. Состояния редактирования"""
    actual_tasks = State()
    done_tasks = State()
    what_to_change = State()
    description = State()
    calendar = State()
    time = State()
    file = State()
    periodic = State()


#  обработчик первой команды start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    await message.answer('To-Do List Application 11!',
                         reply_markup=get_main_kb())
    await create_user_notifications_table(user_id=message.from_user.id)  # см. sqlite - file


#  возврат в главное меню
@dp.message_handler(Text(equals="Вернуться в главное меню"), state='*')
async def back_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await message.answer("Вы вернулись в главное меню",
                        reply_markup=get_main_kb())
    await state.finish()


"""-----ветка про добавление напоминания-----"""


#  обработчик команды "Добавить напонинание"
@dp.message_handler(Text(equals="Добавить напоминание"))
async def cmd_add_notify(message: types.Message) -> None:
    await message.answer("Введите текст напоминания!",
                        reply_markup=get_back_kb())
    await NotificationStatesGroup.description.set()  # установили состояние описания


#  обработчик введенного описания
@dp.message_handler(content_types=['text'], state=NotificationStatesGroup.description)
async def load_description(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['description'] = message.text

    await message.answer("Теперь выберите дату: ",
                         reply_markup=await SimpleCalendar().start_calendar())  # клавиатура с календарем
    await NotificationStatesGroup.calendar.set()


# обработчик календаря (callback!)
@dp.callback_query_handler(simple_cal_callback.filter(), state=NotificationStatesGroup.calendar)
async def load_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    async with state.proxy() as data_dict:
        data_dict['calendar'] = date.strftime("%d/%m/%Y")
    if selected:
        await callback_query.message.answer(
            f'Вы выбрали дату: {date.strftime("%d/%m/%Y")} \n Теперь введите время в формате HH:MM',
            reply_markup=get_back_kb()
        )
    await NotificationStatesGroup.time.set()
    await callback_query.message.delete()


#  обработчик времени
@dp.message_handler(content_types=['text'], state=NotificationStatesGroup.time)
async def load_time(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['time'] = message.text

    if not check_for_notification(data['calendar'], data['time']):
    #  добавляем запись в таблицу на этом этапе! Тогда устанавливается и номер в бд
        await add_notification_in_table(state, user_id=message.from_user.id)
        await message.answer(f'Время зафиксировано: {message.text} Теперь добавьте файлы', reply_markup=get_file_kb())
        await NotificationStatesGroup.file.set()
        await message.delete()
    else:
        await message.answer('Пожалуйста выбирайте будущие дату и время', reply_markup=await SimpleCalendar().start_calendar())
        await NotificationStatesGroup.calendar.set()
        await message.delete()


#  обработчик отсутствия файлов
@dp.message_handler(Text(equals="Файлы не требуются"), state=NotificationStatesGroup.file)
async def load_no_file(message: types.Message, state: FSMContext) -> None:
    # await add_notification_in_table(state, user_id=message.from_user.id)  # это здесь уже не нужно, получается
    await message.answer('Напоминание создано!', reply_markup=get_main_kb())
    await state.finish()
    await message.delete()


# обработчик файлов: загрузка их сначала в локальную директорию
'''
1) файл добавляется в локальную директорию в папку files/id
2) напоминание только создается, пожтому надо создать дир. на диске: files/id/notification_id
3) добавляем в нее файл
'''
@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=NotificationStatesGroup.file)
async def load_file(message: types.Message, state: FSMContext) -> None:
    if document := message.document:
        await document.download(
            destination_file=f"files/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_directory_or_file_exists('files', f'{message.from_user.id}'):
        create_folder_in_folder('files', f'{message.from_user.id}')

    #  создаем папку с id НАПОМИНАНМЯ!
    this_notify = get_last_notification(message.from_user.id)
    create_folder_in_folder(f'{message.from_user.id}', f'{this_notify[0]}')

    if not is_directory_or_file_exists(f'{this_notify[0]}', f'{document.file_name}'):
        upload_file(f'{message.from_user.id}', f'{this_notify[0]}', f'files/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

        #  удаляем файлы из локальной директории
        os.remove(f'files/{message.from_user.id}/{document.file_name}')

        await bot.send_message(chat_id=message.from_user.id,
                               text='Файл загружен. Напоминание создано',
                               reply_markup=get_main_kb())
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Данный файл уже прикреплен к напоминанию. Напоминание создано',
                               reply_markup=get_main_kb())
    await state.finish()


@dp.message_handler(content_types=['photo'], state=NotificationStatesGroup.file)
async def load_file(message: types.Message, state: FSMContext) -> None:
    # file_id = message.photo[-1].file_id
    # document = message.photo
    # await document.download(
    #     destination_file=f"files/{message.from_user.id}/{document.file_name}",
    # )
    document_id = message.photo[-1].file_id
    document = await bot.get_file(document_id)
    # await message.photo[-1].download(destination_file=f"files/{message.from_user.id}/{message.photo.name}")
    await document.download(
        destination_file=f"files/{message.from_user.id}/{document.file_id}",
    )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_directory_or_file_exists('files', f'{message.from_user.id}'):
        create_folder_in_folder('files', f'{message.from_user.id}')

    #  создаем папку с id НАПОМИНАНМЯ!
    this_notify = get_last_notification(message.from_user.id)
    create_folder_in_folder(f'{message.from_user.id}', f'{this_notify[0]}')

    if not is_directory_or_file_exists(f'{this_notify[0]}', f'{document.file_id}'):
        upload_file(f'{message.from_user.id}', f'{this_notify[0]}', f'files/{message.from_user.id}/{document.file_id}', f'{document.file_id}')

        #  удаляем файлы из локальной директории
        os.remove(f'files/{message.from_user.id}/{document.file_id}')

        await bot.send_message(chat_id=message.from_user.id,
                               text='Файл загружен. Напоминание создано',
                               reply_markup=get_main_kb())
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Данный файл уже прикреплен к напоминанию. Напоминание создано',
                               reply_markup=get_main_kb())
    await state.finish()



"""----- Просмотр списков напоминаний -----"""


@dp.message_handler(Text(equals="Посмотреть запланированные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    undone_tasks = ""
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список текущих дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Ваши текущие дела:</b>\n\n' + undone_tasks,
                               parse_mode=types.ParseMode.HTML)


@dp.message_handler(Text(equals="Посмотреть завершенные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    done_tasks = ""
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Ваши завершенные дела:</b>\n\n' + done_tasks,
                               parse_mode=types.ParseMode.HTML, reply_markup=get_done_tasks_kb())


'----- Редактор текущих напоминаний -----'


@dp.message_handler(Text(equals="Редактировать текущие дела"))
async def check_actual_tasks(message: types.Message) -> None:
    undone_tasks = []
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список текущих дел пуст')
    else:
        await UpdateNotificationsStateGroup.actual_tasks.set()
        await bot.send_message(message.chat.id, '<b>Какое из текущих дел вы хотите отредактировать?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(undone_tasks))


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.actual_tasks)
async def callback_check_actual_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number

    await callback.message.answer(f'Вы изменяете напоминание:\n{notify[3]}, {notify[4]}, {notify[2]}\nЧто именно вы ходите изменить?',
                                  reply_markup=get_what_to_change_kb())
    await UpdateNotificationsStateGroup.what_to_change.set()
    await callback.answer(f'{notification_number}')
    await callback.message.delete()


#  обновляем описание
@dp.message_handler(Text(equals="Описание"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новое описание для нопоминания",
                        reply_markup=get_back_kb())
    await UpdateNotificationsStateGroup.description.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.description)
async def save_update_description(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text,
                                    field_name='description')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое описание успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем периодичность
@dp.message_handler(Text(equals="Изменить периодичность"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_periodic(message: types.Message) -> None:
    await message.reply("Введите тип периодичности:\n"
                        "0 - дело не периодично\n"
                        "1 - повтор каждый день\n"
                        "2 - повтор каждую неделю\n"
                        "3 - повтор каждый месяц",
                        reply_markup=get_back_kb())
    await UpdateNotificationsStateGroup.periodic.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.periodic)
async def save_update_periodic(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=int(message.text),
                                    field_name='period_type')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Периодичность обновлена",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем календарную дату
@dp.message_handler(Text(equals="Дата"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новую дату для нопоминания",
                        reply_markup=await SimpleCalendar().start_calendar())
    await UpdateNotificationsStateGroup.calendar.set()  # установили состояние описания


#  callback календаря!
@dp.callback_query_handler(simple_cal_callback.filter(), state=UpdateNotificationsStateGroup.calendar)
async def save_update_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    new_date = date.strftime("%d/%m/%Y")
    if selected:
        if not check_for_notification(new_date, '01:00'):
            await update_notification_field(state, user_id=callback_query.from_user.id, field_data=new_date,
                                            field_name='calendar')
            #  после обновления напоминания его надо будет отправить еще раз
            await update_notification_field(state, user_id=callback_query.from_user.id, field_data=0, field_name='is_Sent')
            await callback_query.message.answer(
                f'Вы изменили дату: {date.strftime("%d/%m/%Y")}',
                reply_markup=get_main_kb()
            )
        else:
            await callback_query.message.answer(
                'Нельзя выставить прошедшую дату',
                reply_markup=get_main_kb()
            )
    await state.finish()


#  обновляем время
@dp.message_handler(Text(equals="Время"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_time(message: types.Message) -> None:
    await message.reply("Введите новое время для нопоминания",
                        reply_markup=get_back_kb())
    await UpdateNotificationsStateGroup.time.set()


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.time)
async def save_update_time(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text, field_name='time')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое время успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  отмечаем как выполненное
@dp.message_handler(Text(equals="Отметить как выполненное"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_is_Done(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Done')
    #  сделанные дела, даже если их время и не пришло, отправлять уже не нужно
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Sent')
    await message.reply("Задача выполнена",
                        reply_markup=get_main_kb())
    await state.finish()


#  удаляем напоминание
@dp.message_handler(Text(equals="Удалить напоминание"), state=UpdateNotificationsStateGroup.what_to_change)
async def back_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await delete_notification_field(state, user_id=message.from_user.id)
    await message.reply("Вы удалили напоминание",
                        reply_markup=get_main_kb())
    await state.finish()


#  редактор файлов
@dp.message_handler(Text(equals="Файлы"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_files(message: types.Message) -> None:
    await message.reply("Что вы хотеите сделать с файлами?",
                        reply_markup=get_files_update_kb())
    await UpdateNotificationsStateGroup.file.set()


@dp.message_handler(Text(equals="Добавить новый"), state=UpdateNotificationsStateGroup.file)
async def update_files_new(message: types.Message) -> None:
    await message.reply("Добавьте файл",
                        reply_markup=get_main_kb())
    await UpdateNotificationsStateGroup.file.set()


@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=UpdateNotificationsStateGroup.file)
async def update_files_new(message: types.Message, state: FSMContext) -> None:
    """
    Тут код почти полностью повторяет код другой функции. Это надо по-хорошему потому убрать. Хотя нормально
    """
    if document := message.document:
        await document.download(
            destination_file=f"files/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_directory_or_file_exists('files', f'{message.from_user.id}'):
        create_folder_in_folder('files', f'{message.from_user.id}')

    async with state.proxy() as data:
        notification_number = data['notification_number']

    if not is_directory_or_file_exists(f'{message.from_user.id}', f'{notification_number}'):
        create_folder_in_folder(f'{message.from_user.id}', f'{notification_number}')

    if not is_directory_or_file_exists(f'{notification_number}', f'{document.file_name}'):
        upload_file(f'{message.from_user.id}', f'{notification_number}',
                    f'files/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

        #  удаляем файлы из локальной директории
        os.remove(f'files/{message.from_user.id}/{document.file_name}')

        await bot.send_message(chat_id=message.from_user.id,
                               text='Успешно! Файл загружен',
                               reply_markup=get_main_kb())

    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Данный файл уже прикреплен к напоминанию',
                               reply_markup=get_main_kb())
    await state.finish()


@dp.message_handler(Text(equals="Удалить имеющийся"), state=UpdateNotificationsStateGroup.file)
async def update_files_delete(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(message.from_user.id, 'Секунду, подгружаем файлы...')
    list_of_files = get_list_of_files(message.from_user.id, notification_number)
    if len(list_of_files) != 0:
        await message.reply("Выберите, какой файл вы хотите удалить",
                            reply_markup=get_ikb_with_filenames(list_of_files))
        await UpdateNotificationsStateGroup.file.set()
    else:
        await message.reply("К задаче не прикреплено ни одного файла",
                            reply_markup=get_main_kb())
        await state.finish()


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.file)
async def delete_files_from_disk(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(chat_id=callback.from_user.id, text='Удаляем файл...')

    delete_files_from_google_disk(f'{callback.from_user.id}', f'{notification_number}', f'{callback.data}')
    await bot.send_message(chat_id=callback.from_user.id, text='Файл успено удалён!', reply_markup=get_main_kb())
    await state.finish()


'''----- Редактор завершенных напоминаний-----'''


@dp.message_handler(Text(equals="Вернуть дело в незавершенное"))
async def check_done_tasks(message: types.Message) -> None:
    done_tasks = []
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Какое из выполненных дел вы хотите вернуть?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(done_tasks))
    await UpdateNotificationsStateGroup.done_tasks.set()


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.done_tasks)
async def callback_check_done_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Done')
    #  вернули дело в невыполненные => его еще предстоит отправить
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Sent')
    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nКакую дату необходимо поставить??',
                                  reply_markup=await SimpleCalendar().start_calendar())
    await UpdateNotificationsStateGroup.calendar.set()
    await callback.answer(f'{notification_number}')


'''----- Отправка уведомлений о заплпнированных делах -----'''


@dp.message_handler()
async def notification_function():
    # выгружаем все задания, которые находятся в статусе "текущие"
    users = get_used_ids()
    for user_id in users:
        user_id = list(user_id)[0]
        tasks = get_unsent_tasks(user_id)
        for task in tasks:
            # проверяем не наступила ли дата и время уведомления.
            if check_for_notification(task[3], task[4]):
                # если наступило - отправляем уведомление
                #  выгружаем файлы
                titles = get_list_of_files(f'{user_id}', f'{task[0]}')

                await bot.send_message(chat_id=user_id, text=f"⛳️Напоминание\n {task[2]}")

                for i in range(len(titles)):
                    await bot.send_document(user_id, (f'{titles[i]}', f'files/{user_id}/{titles[i]}'))
                    os.remove(f'files/{user_id}/{titles[i]}')  # удаляем из локальной директории

                # флажок, проверка на "периодичность дела"
                if task[6] == 0:
                    # если дело не переодическое то заменяем стус "в ожидании" на "отправлено"
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=1,
                                                              field_name='is_Sent')
                else:
                    # вычисляем новую дату для уведомления у периодических дел
                    new_date = add_days(task[3], task[6])
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=new_date,
                                                              field_name='calendar')



if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
