from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import shutil
import aioschedule


def gogle_auth():
    gauth = GoogleAuth()

    #пробуем загрузить сохраненные данные о пользователе, чтобы не проходить ручную аутентификацию
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        # входим, если не вошли по сохраненным данным
        gauth.GetFlow()
        gauth.flow.params.update({'access_type': 'offline'})
        gauth.flow.params.update({'approval_prompt': 'force'})

        gauth.LocalWebserverAuth()

    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    # сохраняем пользовательские данных для последующих автоматических аутентификаций
    gauth.SaveCredentialsFile("mycreds.txt")
    return gauth

#  вспомогательная функция
def create_folder(folder_id, folderName, drive):
    file_metadata = {
        'title': folderName,
        'parents': [{'id': folder_id}],  # parent folder
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive.CreateFile(file_metadata)
    folder.Upload()


#  создаем папку под названием folderName в директории с folder_id
def create_folder_in_folder(root_folder, new_folder):
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder:
            create_folder(folder['id'], new_folder, drive)


def is_directory_or_file_exists(root_folder, check_folder_or_file):
    """
    Применим только к первым двум иерархиям моей архитектуры!!! Далее появляется неоднозначность
    :param root_folder:
    :param check_folder_or_file:
    :return:
    """
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)

    root_folder_id = ''
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == check_folder_or_file:
            return True
    return False


def upload_file(root_folder1, root_folder2, local_path, filename):
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)

    root_folder_id = ''
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder1 + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder1:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder2:
            my_file = drive.CreateFile({'title': f'{filename}', 'parents': [{'id': folder['id']}]})  # создаем файл на диске
            my_file.SetContentFile(local_path)
            my_file.Upload()
            break


def get_list_of_files(user_id, notify_number):
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)
    fileID = ''
    fileList = drive.ListFile({'q': f"'root' in parents and trashed=false"}).GetList()
    for file in fileList:
        if (file['title'] == "files"):
            fileID = file['id']
            break
    str = "\'" + fileID + "\'" + " in parents and trashed=false"

    file_list = drive.ListFile({'q': str}).GetList()
    for file in file_list:
        if (file['title'] == f"{user_id}"):
            fileID = file['id']
            break
    str = "\'" + fileID + "\'" + " in parents and trashed=false"

    fileID2 = ''
    file_list = drive.ListFile({'q': str}).GetList()
    for file in file_list:
        if (file['title'] == f"{notify_number}"):
            fileID2 = file['id']
            break
    str = "\'" + fileID2 + "\'" + " in parents and trashed=false"  # указывает папку 9

    if fileID2 != '':
        file_list = drive.ListFile({'q': str}).GetList()

        for index, file in enumerate(file_list):
            file.GetContentFile('files/' + f'{user_id}/' + file['title'])

        titles_list = []
        for file in file_list:
            titles_list.append(file['title'])

        return titles_list
    else:
        return ''


def delete_files_from_google_disk(root_folder1, root_folder2, deliting_file):
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)
    root_folder_id = ''
    folders = drive.ListFile(
        {
            'q': "title='" + root_folder1 + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder1:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == root_folder2:
            root_folder_id = folder['id']

    folders = drive.ListFile({'q': "\'" + root_folder_id + "\'" + " in parents and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == deliting_file:
            file1 = drive.CreateFile({'id': folder['id']})
            file1.Trash()  # убираем файл в карзину
    return False


def download_folder():
    """used to make backup"""
    gauth = gogle_auth()
    drive = GoogleDrive(gauth)
    fileID = ''
    fileList = drive.ListFile({'q': f"'root' in parents and trashed=false"}).GetList()
    for file in fileList:
        if (file['title'] == "files"):
            fileID = file['id']
            break
    str = "\'" + fileID + "\'" + " in parents and trashed=false"  # 'files' folder path

    file_list = drive.ListFile({'q': str}).GetList()
    for file in file_list:  # file -> users ids
        fileID = file['id']
        str1 = "\'" + fileID + "\'" + " in parents and trashed=false"  # user_id

        fileID2 = ''
        file_list_2 = drive.ListFile({'q': str1}).GetList()
        for file_2 in file_list_2:
            fileID2 = file_2['id']
            str2 = "\'" + fileID2 + "\'" + " in parents and trashed=false"  # notification folder

            if fileID2 != '':
                file_list_3 = drive.ListFile({'q': str2}).GetList()
                for file_3 in file_list_3:
                    my_dir = f"files/{file['title']}/{file_2['title']}"
                    if not os.path.exists(my_dir):
                        os.makedirs(my_dir)
                    file_3.GetContentFile(f"{my_dir}/{file_3['title']}")  # downloads

            else:
                return ''


def make_archive():
    if os.path.exists('my_archive.zip'):
        os.remove('my_archive.zip')
    shutil.make_archive('my_archive', 'zip', 'files')


def make_backup():
    download_folder()
    make_archive()
    gauth = gogle_auth()

    drive = GoogleDrive(gauth)
    fileID = ''
    fileList = drive.ListFile({'q': f"'root' in parents and trashed=false"}).GetList()
    for file in fileList:
        if file['title'] == "backup":
            fileID = file['id']
            break

    my_file = drive.CreateFile({'title': f'my_archive', 'parents': [{'id': fileID}]})  # создаем файл на диске
    my_file.SetContentFile(f'my_archive.zip')
    my_file.Upload()






