import sqlite3 as sq


async def db_start():
    global db, cur

    db = sq.connect('files/new.db')
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY)")
    db.commit()


async def create_user_notifications_table(user_id):
    """
    Таблица users уже создана. Если пользователь еще не добавлен в нее, то
    добавляем + создаем таблицу {user_id}_notifications - таблица его дел
    Period_type: 0 - не периодична, 1 - каждый день, 2 - каждую неделю, 3 - каждый месяц
    """
    user = cur.execute("SELECT 1 FROM users WHERE user_id == '{key}'".format(key=user_id)).fetchone()
    if not user:
        print(user_id)
        cur.execute("INSERT INTO users VALUES(?)", (user_id, ))
        cur.execute("CREATE TABLE '{id}_notifications'(id INTEGER PRIMARY KEY AUTOINCREMENT, is_Done INT, description TEXT, calendar TEXT, time TEXT,"
                    "is_Sent INT, period_type INT, user_ TEXT, FOREIGN KEY (user_) REFERENCES users(user_id) ON DELETE CASCADE)".format(id=user_id))
        db.commit()


async def add_notification_in_table(state, user_id):
    async with state.proxy() as data:
        cur.execute("INSERT INTO '{user_id}_notifications' (is_Done, description, calendar, time, is_Sent, period_type, user_) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?)".format(user_id=user_id),
                    (0, data['description'], data['calendar'], data['time'], 0, 0, user_id,))
        db.commit()


def get_used_ids():
    ids = cur.execute("SELECT * FROM users").fetchall()
    return ids


def get_last_notification(user_id):
    last = cur.execute("SELECT * FROM '{user_id}_notifications' ORDER BY id DESC LIMIT 1"
                       .format(user_id=user_id)).fetchone()
    return last


def get_undone_tasks(user_id):
    done_tasks = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE  is_Done = 0 ORDER BY calendar"
                             .format(user_id=user_id)).fetchall()
    return done_tasks


def get_unsent_tasks(user_id):
    done_tasks = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE is_Sent = 0 ORDER BY calendar"
                             .format(user_id=user_id)).fetchall()
    return done_tasks


def get_done_tasks(user_id):
    done_tasks = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE  is_Done = 1 ORDER BY calendar"
                             .format(user_id=user_id)).fetchall()
    return done_tasks


def get_task_by_number(user_id, number):
    notify = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE id == '{number}'"
                .format(user_id=user_id, number=number)).fetchone()
    return notify


async def update_notification_field(state, user_id, field_data, field_name):
    async with state.proxy() as data:
        cur.execute("UPDATE '{user_id}_notifications' SET '{field_name}' = '{field_data}' WHERE id == {number}".format(
                    user_id=user_id, field_name=field_name, field_data=field_data, number=data['notification_number']))
        db.commit()


async def update_notification_field_by_number(number, user_id, field_data, field_name):
    cur.execute("UPDATE '{user_id}_notifications' SET '{field_name}' = '{field_data}' WHERE id == {number}".format(
                user_id=user_id, field_name=field_name, field_data=field_data, number=number))
    db.commit()


async def delete_notification_field(state, user_id):
    async with state.proxy() as data:
        cur.execute("DELETE FROM '{user_id}_notifications'  WHERE id == {number}".format(
                    user_id=user_id, number=data['notification_number']))
        db.commit()

