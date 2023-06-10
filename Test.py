# from aiogram import types, executor, Bot, Dispatcher
# from aiogram.contrib.fsm_storage.memory import MemoryStorage
# from config import TOKEN_API
#
#
# storage = MemoryStorage()
# bot = Bot(TOKEN_API)
# dp = Dispatcher(bot,
#                 storage=storage)
#
# # cat 3
#
# #  обработчик первой команды start
# @dp.message_handler(commands=['start'])
# async def cmd_start(message: types.Message) -> None:
#     await message.answer('To-Do List Application! Yo')
#
#
# @dp.message_handler(content_types=['text'])
# async def echo_(message: types.Message) -> None:
#     await message.answer(message.text)
#
#
# if __name__ == '__main__':
#     executor.start_polling(dp,
#                            skip_updates=True)



