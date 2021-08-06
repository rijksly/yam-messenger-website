import os
import json
from copy import deepcopy

from flask import Flask, render_template, request, redirect, make_response
import datetime
from hashlib import sha256

def checkuser(data, users): # NOTE: проверяет правильность данных пользователя
    for i in users:
        if users[i]['username'] == data[0] and users[i]['password'] == data[1]:
            return True
    return False

def getpassword(hash, users): # NOTE: расшифровывает пароль
    for i in users:
        if sha256(users[i]['password'].encode()).hexdigest() == hash:
            return users[i]['password']

def chatsofuser(username, chats, users): # NOTE: выдает чаты конкретного пользователя
    chatsofu = []
    gofu = []
    for i in chats:
        if chats[i]['is_group'] == 'false':
            try: # TODO: сюда isuserinchat
                k = chats[i]['users'].index(username)
                if k == 1:
                    h = 0
                elif k == 0:
                    h = 1
                chatsofu.append({'username':chats[i]['users'][h], 'id':list(chats)[list(chats).index(i)]})
            except ValueError:
                pass
        elif chats[i]['is_group'] == 'true':
            try: # TODO: сюда isuserinchat
                k = chats[i]['users'].index(username)
                gofu.append({'name':chats[i]['name'], 'id':list(chats)[list(chats).index(i)]})
            except ValueError:
                pass
    return {'logins':chatsofu, 'groups':gofu}

def getmessages(id, chats): # NOTE: получает сообщения
    messages = chats[id]['messages']
    messages = list(reversed(sorted(messages, key=lambda i:i['pub_date'])))
    for i in messages:
        i['pub_date'] = datetime.datetime.strptime(i['pub_date'], '%Y-%m-%d %H:%M:%S.%f').strftime("%d. %b %y %H:%M")
    return messages

def isinlist(whattofind, list): # NOTE: проверяет, есть ли значение в списке
    try:
        list.index(whattofind)
        return True
    except ValueError:
        return False

def isuserinchat(username, id, chats):
    try:
        j = chats[id]['users'][chats[id]['users'].index(username)]
        return True
    except ValueError:
        return False

app = Flask(__name__)

@app.route('/', methods=['GET']) # NOTE: начальная страница
def main():
    return render_template('start.html')

@app.route('/signin', methods=['GET']) # NOTE: вход
def signin():
    return render_template('signin.html')

@app.route('/chats', methods=['POST', 'GET']) # NOTE: список чатов, главный экран
def chatss():
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    if request.method == 'POST':
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)
        data = [request.form.to_dict()['login'], request.form.to_dict()['password']]
        if checkuser(data, users):
            try:
                rememberme = request.form.to_dict()['rememberme']
            except KeyError:
                rememberme = 'off'

            chatsofu = chatsofuser(data[0], chats, users)
            resp = make_response(render_template('chats.html', chats=chatsofu['logins'], gchats=chatsofu['groups'], username=users[data[0]]['username']))
            if rememberme == 'off':
                resp.set_cookie('yamlogin', value=data[0], samesite='Lax', httponly=True, secure=True)
                resp.set_cookie('yampassword', value=sha256(data[1].encode()).hexdigest(), samesite='Lax', httponly=True, secure=True)
            elif rememberme == 'on':
                resp.set_cookie('yamlogin', value=data[0], max_age=31536000, samesite='Lax', httponly=True, secure=True)
                resp.set_cookie('yampassword', value=sha256(data[1].encode()).hexdigest(), max_age=31536000, samesite='Lax', httponly=True, secure=True)
            return resp
        else:
            return render_template('error.html', mess="Войдите в аккаунт")
    elif request.method == 'GET':
        data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
        if checkuser(data, users):
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)
            chatsofu = chatsofuser(data[0], chats, users)
            return render_template('chats.html', chats=chatsofu['logins'], gchats=chatsofu['groups'], username=users[data[0]]['username'])
        else:
            return render_template('error.html', mess="Войдите в аккаунт")
    return redirect('/')

@app.route('/chats/<id>', methods=['GET']) # NOTE: страница конкретного чата
def chat(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)

        try:
            if chats[id]['is_group'] == 'false': # NOTE: для чата с пользователем
                username1 = deepcopy(chats[id]['users'])
                try:
                    username1.remove(data[0])
                except ValueError:
                    return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
                username1 = username1[0]

                messages = getmessages(id, chats)
                return render_template('chat.html', messages=messages, username=users[username1]['username'], id=id, is_group=False)
            elif chats[id]['is_group'] == 'true': # NOTE: для группового чата
                try:
                    chats[id]['users'].index(data[0])
                except ValueError:
                    return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
                messages = getmessages(id, chats)
                return render_template('chat.html', messages=messages, name=chats[id]['name'], id=id, banned='', is_group=True, author_name=data[0])
        except KeyError:
            return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/write/<id>', methods=['POST']) # NOTE: написать сообщение
def write(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)

        message = request.form.to_dict()['message']
        date = datetime.datetime.now()

        #file = request.files['file']
        #if isextensionallowed(file.filename):
        #    filename = secure_filename(file.filename)
            # NOTE: не могу тут найти способ присваивать файлу нужное название (число, которое будет тупо по порядку увеличиваться), все способы (перебор всех media_id всех чатов, получение названий и поиск самого большого числа, запись в файлик последнего числа, ввод при каждом запуске последнего числа) слишком рукожопые, чтобы назвать их адекватными, есть идея написать, что ради безопасности и для бесплатности медиа нельзя отправлять, но тоже слишком тупо
        #    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if not message == '':
            username1 = deepcopy(chats[id]['users'])
            try:
                username1.remove(data[0])
            except ValueError:
                return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
            username1 = username1[0]

            if users[username1]['banned'].count(data[0]) == 0:
                idsofm = []
                for i in chats[id]['messages']:
                    idsofm.append(int(i['id']))
                try:
                    mid = int(max(idsofm)) + 1
                except ValueError:
                    mid = 0

                chats[id]['messages'].append({'text':message, 'id':str(mid), 'author':users[data[0]]['username'], 'pub_date':str(date)})

                with open("chats.json", 'w') as f:
                    f.write(json.dumps(chats))
                return redirect('/chats/' + id)
            else:
                return render_template('error.html', mess='Вы забанены')
        else:
            return redirect('/chats/' + id)
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/logout', methods=['GET']) # NOTE: выйти из аккаунта
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('yamlogin', value='', max_age=0, samesite='Lax', httponly=True, secure=True)
    resp.set_cookie('yampassword', value='', max_age=0, samesite='Lax', httponly=True, secure=True)
    return resp

@app.route('/new_chat', methods=['GET', 'POST']) # NOTE: создать новый чат
def new_chat():
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)

            username = request.form.to_dict()['name']
            if isinlist(username, list(users.keys())):
                id = int(max(list(chats.keys()))) + 1
                try:
                    chats[id] = {"users":[data[0], username], 'messages':[], 'is_group':'false'}
                except NameError:
                    return render_template('error.html', mess='Аккаунта с таким именем не существует')

                with open("chats.json", 'w') as f:
                    f.write(json.dumps(chats))
                return redirect('/chats/' + str(id))
            else:
                return render_template('error.html', mess='Аккаунта с таким именем не существует')
        elif request.method == 'GET':
            return render_template('newchat.html')

@app.route('/signup', methods=['GET', 'POST']) # NOTE: регистрация
def signup():
    if request.method == 'POST':
        with open(r"users.json") as read_file:
            users = json.load(read_file)

        login = request.form.to_dict()['login']
        if login == '' or login == ' ' or login == '  ' or login == '   ' or login == '    ' or login == '     ':
            return render_template('error.html', mess="Нельзя делать ник пустым")
        if list(login).count(',') > 0:
            return render_template('error.html', mess='Запятую нельзя ставить в ник')
        if isinlist(login, list(users.keys())):
            return render_template('error.html', mess='Ник занят')

        password = request.form.to_dict()['password']
        passwordcheck = request.form.to_dict()['passwordcheck']
        if password == passwordcheck:
            users[login] = {}
            users[login]['username'] = login
            users[login]['password'] = password
            users[login]['banned'] = []
            with open("users.json", 'w') as f:
                f.write(json.dumps(users))

            resp = make_response(redirect('/chats'))
            resp.set_cookie('yamlogin', value=login, samesite='Lax', httponly=True, secure=True)
            resp.set_cookie('yampassword', value=sha256(password.encode()).hexdigest(), samesite='Lax', httponly=True, secure=True)
            return resp
        else:
            return render_template('error.html', mess='Пароли не совпадают')
    elif request.method == 'GET':
        return render_template('signup.html')

@app.route('/deletem/<cid>/<mid>', methods=['GET']) # NOTE: удалить сообщение
def deletemessage(cid, mid):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)

        if isuserinchat(data[0], cid, chats):
            if chats[cid]['is_group'] == 'false':
                for i in chats[cid]['messages']:
                    if mid == i['id']:
                        chats[cid]['messages'].remove(i)
                        break
            elif chats[cid]['is_group'] == 'true':
                for i in chats[cid]['messages']:
                    print('fddf')
                    if mid == i['id']:
                        if i['author'] == data[0]:
                            chats[cid]['messages'].remove(i)
                            break
                        else:
                            return render_template('error.html', mess='Нельзя удалять чужие сообщения в групповом чате')
            with open("chats.json", 'w') as f:
                f.write(json.dumps(chats))

            return redirect('/chats/' + cid)
        else:
            return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/deletea', methods=['POST', 'GET']) # NOTE: удалить аккаунт
def deleteaccount():
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            password = request.form.to_dict()['password']
            if password == request.form.to_dict()['passwordcheck']:
                if data == [request.form.to_dict()['login'], password]:
                    with open(r"chats.json") as read_file:
                        chats = json.load(read_file)

                    try:
                        del users[data[0]]
                    except NameError:
                        return render_template('error.html', mess='Такого аккаунта не существует')

                    todelete = []
                    for i in chats:
                        if chats[i]['is_group'] == 'false':
                            if isuserinchat(data[0], i, chats):
                                todelete.append(i)
                        elif chats[i]['is_group'] == 'true':
                            if isuserinchat(data[0], i, chats):
                                del chats[i]['users'][chats[i]['users'].index(key)]
                    for i in todelete: # NOTE: чтобы for не ругался на изменение списка во время его итерирования
                        del chats[i]

                    with open("users.json", 'w') as f:
                        f.write(json.dumps(users))
                    with open("chats.json", 'w') as f:
                        f.write(json.dumps(chats))
                    return redirect('/logout')
                else:
                    return render_template('error.html', mess="Неправильные данные")
            else:
                return render_template('error.html', mess="Пароли не совпадают")
        elif request.method == 'GET':
            return render_template('deleteaccount.html')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/chats/<id>/deletec', methods=['GET']) # NOTE: удалить чат
def deletechat(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)

            if chats[id]['is_group'] == 'false':
                if isuserinchat(data[0], id, chats):
                    del chats[id]
                    with open("chats.json", 'w') as f:
                        f.write(json.dumps(chats))
                    return redirect('/chats')
                else:
                    return render_template('error.html', mess="Вы не состоите в этом чате/его не существует")
            elif chats[id]['is_group'] == 'true':
                if isuserinchat(data[0], id, chats):
                    if isinlist(data[0], chats[id]['admins']):
                        del chats[id]
                        with open("chats.json", 'w') as f:
                            f.write(json.dumps(chats))
                        return redirect('/chats')
                    else:
                        return render_template('error.html', mess='Вы не админ в этой группе')
                else:
                    return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
        elif request.method == 'GET':
            return render_template('deletechat.html')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/ban/<whotoban>', methods=['GET']) # NOTE: забанить пользователя
def ban(whotoban):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        # TODO: сюда isusernamevalid
        if isinlist(whotoban, users[data[0]]['banned']):
            return render_template('error.html', mess='Этот пользователь уже забанен')
        users[data[0]]['banned'].append(whotoban)

        with open("users.json", 'w') as f:
            f.write(json.dumps(users))
        return redirect('/chats')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/unban/<whotounban>', methods=['GET']) # NOTE: разбанить пользователя
def unban(whotounban):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        # TODO: сюда isusernamevalid
        if not isinlist(whotounban, users[data[0]]['banned']):
            return render_template('error.html', mess="Этот пользователь не забанен")
        del users[data[0]]['banned'][users[data[0]]['banned'].index(whotounban)]

        with open("users.json", 'w') as f:
            f.write(json.dumps(users))
        return redirect('/chats')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/new_group_chat', methods=['POST', 'GET']) # NOTE: новый групповой чат
def newgroupchat():
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)

            names = request.form.to_dict()['names'].split(', ')
            invalidnames = []
            for i in names: # TODO: сюда isusernamevalid
                if not isinlist(i, list(users.keys())):
                    invalidnames.append(i)
            for i in invalidnames:
                del names[names.index(i)]

            names.append(data[0])

            chatname = request.form.to_dict()['chatname']
            if chatname == '' or chatname == ' ' or chatname == '  ' or chatname == '   ' or chatname == '    ' or chatname == '     ':
                return render_template('error.html', mess="Нельзя делать название чата пустым")
            id = int(max(list(chats.keys()))) + 1
            chats[id] = {"users":names, 'messages':[], 'is_group':'true', 'name':chatname, 'admins':[data[0]]}

            with open("chats.json", 'w') as f:
                f.write(json.dumps(chats))
            return redirect('/chats')
        elif request.method == 'GET':
            return render_template('newgroupchat.html')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/new_username', methods=['GET', 'POST']) # NOTE: поменять ник
def newusername():
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)

            newusername = request.form.to_dict()['username']
            newusernamecheck = request.form.to_dict()['usernamecheck']
            if newusername == newusernamecheck:
                if newusername == '' or newusername == ' ' or newusername == '  ' or newusername == '   ' or newusername == '    ' or newusername == '     ':
                    return render_template('error.html', mess="Нельзя делать название чата пустым")
                for i in users: # TODO: сюда isinlist
                    if users[i]['username'] == newusername:
                        return render_template('error.html', mess='Ник занят')
                if list(newusername).count(',') > 0:
                    return render_template('error.html', mess='Запятую нельзя ставить в ник')

                for i in chats:
                    if isuserinchat(data[0], i, chats):
                        chats[i]['users'][chats[i]['users'].index(data[0])] = newusername

                        for n in chats[i]['messages']:
                            index = chats[i]['messages'].index(n)
                            if chats[i]['messages'][index]['author'] == users[data[0]]['username']:
                                chats[i]['messages'][index]['author'] = newusername

                for i in chats:
                    if chats[i]['is_group'] == 'true':
                        try:
                            k = chats[i]['admins'].index(data[0]) # TODO: сюда isinlist
                            chats[i]['admins'][k] = newusername
                        except ValueError:
                            pass

                users[newusername] = users[data[0]]
                users[newusername]['username'] = newusername
                del users[data[0]]

                with open("chats.json", 'w') as f:
                    f.write(json.dumps(chats))
                with open("users.json", 'w') as f:
                    f.write(json.dumps(users))

                resp = make_response(redirect('/chats'))
                resp.set_cookie('yamlogin', value=newusername, samesite='Lax', httponly=True, secure=True)
                resp.set_cookie('yampassword', value=sha256(data[1].encode()).hexdigest(), samesite='Lax', httponly=True, secure=True)
                return resp
            else:
                return render_template('error.html', mess='Ники не совпадают')
        elif request.method == 'GET':
            return render_template('newusername.html')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/chats/<id>/info', methods=['GET']) # NOTE: страница информации о чате (и групповом, и обычном)
def infoaboutchat(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)
        if chats[id]['is_group'] == 'true':
            try: # TODO: сюда isuserinchat
                chats[id]['users'].index(data[0])
            except ValueError:
                return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не групповой')
            if isinlist(data[0], chats[id]['admins']):
                is_admin = True
            else:
                is_admin = False

            members = chats[id]['users']
            membersusernames = []
            for i in members:
                membersusernames.append(users[i]['username'])
            admins = chats[id]['admins']
            adminsusernames = []
            for i in admins:
                adminsusernames.append(users[i]['username'])

            return render_template('aboutgroup.html', name=chats[id]['name'], members=membersusernames, admins=adminsusernames, is_admin=is_admin, id=id)
        elif chats[id]['is_group'] == 'false':
            try: # TODO: сюда isuserinchat
                chats[id]['users'].index(data[0])
            except ValueError:
                return redirect('error.html', mess='Вы не состоите в этом чате/его не существует')

            username1 = deepcopy(chats[id]['users'])
            try:
                username1.remove(data[0])
            except ValueError:
                return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
            username1 = username1[0]

            if users[data[0]]['banned'].count(username1) > 0:
                banned = True
            else:
                banned = False

            members = chats[id]['users']
            membersusernames = []
            for i in members:
                membersusernames.append(users[i]['username'])
            return render_template('aboutchat.html', name=membersusernames, members=chats[id]['users'], id=id, totalmessages=len(chats[id]['messages']), isbanned=banned, username=username1)
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/chats/<id>/deletefc/<who>', methods=['GET']) # NOTE: кикнуть пользователя из чата
def deletefc(id, who):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)
        if chats[id]['is_group'] == 'true':
            if isuserinchat(data[0], id, chats):
                if isinlist(data[0], chats[id]['admins']):
                    if isinlist(who, list(users.keys())): # TODO: сюда isusernamevalid
                        if isuserinchat(who, id, chats):
                            if not isinlist(who, chats[id]['admins']):
                                del chats[id]['users'][chats[id]['users'].index(who)]
                                with open("chats.json", 'w') as f:
                                    f.write(json.dumps(chats))
                                return redirect('/chats/' + id + '/info')
                            else:
                                return render_template('error.html', mess='Админов нельзя удалять')
                        else:
                            return render_template('error.html', mess='Пользователь не состоит в чате')
                    else:
                        return render_template('error.html', mess='Невалидный ник')
                else:
                    return render_template('error.html', mess='Вы не админ в этой группе')
            else:
                return render_template('error.html', mess='Вы не состоите в этом чате/его не существует')
        elif chats[id]['is_group'] == 'false':
            return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не групповой')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/chats/<id>/adduser', methods=['GET', 'POST']) # NOTE: добавление пользователя в чат
def adduser(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)
        if chats[id]['is_group'] == 'true':
            if request.method == 'POST':
                if isuserinchat(data[0], id, chats):
                    if isinlist(data[0], chats[id]['admins']):
                        username = request.form.to_dict()['username']
                        if isinlist(username, list(users.keys())): # TODO: сюда isusernamevalid
                            if not isinlist(username, chats[id]['users']):
                                chats[id]['users'].append(username)
                                with open("chats.json", 'w') as f:
                                    f.write(json.dumps(chats))
                                return redirect('/chats/' + id + '/info')
                            else:
                                return render_template('error.html', mess='Пользователь уже состоит чате')
                        else:
                            return render_template('error.html', mess='Неправильное имя пользователя')
                    else:
                        return render_template('error.html', mess='Вы не админ в этой группе')
                else:
                    return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
            elif request.method == 'GET':
                return render_template('adduser.html', id=id)
        elif chats[id]['is_group'] == 'false':
            return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не групповой')
    else:
        return render_template('error.html', mess="Войдите в аккаунт")

@app.route('/chats/<id>/exit', methods=['GET']) # NOTE: выход из чата
def exitfc(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        with open(r"chats.json") as read_file:
            chats = json.load(read_file)
        if chats[id]['is_group'] == 'true':
            if isuserinchat(data[0], id, chats):
                del chats[id]['users'][chats[id]['users'].index(data[0])]
                with open("chats.json", 'w') as f:
                    f.write(json.dumps(chats))
                return redirect('/chats')
            else:
                return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
        elif chats[id]['is_group'] == 'false':
            return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
    else:
        return render_template('error.html', mess='Войдите в аккаунт')

@app.route('/chats/<id>/addadmin', methods=['GET', 'POST']) # NOTE: добавить админа
def addadmin(id):
    if request.method == 'POST':
        with open(r"users.json") as read_file:
            users = json.load(read_file)
        data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
        if checkuser(data, users):
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)
            if chats[id]['is_group'] == 'true':
                if isuserinchat(data[0], id, chats):
                    if isinlist(data[0], chats[id]['admins']):
                        username = request.form.to_dict()['username']
                        if isinlist(username, list(users.keys())): # TODO: сюда isusernamevalid
                            if not isinlist(username, chats[id]['admins']):
                                if not isuserinchat(username, id, chats):
                                    chats[id]['users'].append(username)
                                chats[id]['admins'].append(username)
                                with open("chats.json", 'w') as f:
                                    f.write(json.dumps(chats))
                                return redirect('/chats/' + id)
                            else:
                                return render_template('error.html', mess='Этот пользователь уже админ')
                        else:
                            return render_template('error.html', mess='Неправильное имя пользователя')
                    else:
                        return render_template('error.html', mess='Вы не админ в этой группе')
                else:
                    return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
            elif chats[id]['is_group'] == 'false':
                return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
        else:
            return render_template('error.html', mess='Войдите в аккаунт')
    elif request.method == 'GET':
        return render_template('addadmin.html')

@app.route('/chats/<id>/changename', methods=['GET', 'POST']) # NOTE: поменять имя группы
def changegroupname(id):
    with open(r"users.json") as read_file:
        users = json.load(read_file)
    data = [request.cookies.get('yamlogin'), getpassword(request.cookies.get('yampassword'), users)]
    if checkuser(data, users):
        if request.method == 'POST':
            with open(r"chats.json") as read_file:
                chats = json.load(read_file)
            if chats[id]['is_group'] == 'true':
                if isuserinchat(data[0], id, chats):
                    if isinlist(data[0], chats[id]['admins']):
                        chats[id]['name'] = request.form.to_dict()['name']
                        with open("chats.json", 'w') as f:
                            f.write(json.dumps(chats))
                        return redirect('/chats/' + id)
                    else:
                        return render_template('error.html', mess='Вы не админ в этой группе')
                else:
                    return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
            elif chats[id]['is_group'] == 'false':
                return render_template('error.html', mess='Вы не состоите в группе/группы не существует/этот чат не группа')
        elif request.method == 'GET':
            return render_template('changegroupname.html')
    else:
        return render_template('error.html', mess='Войдите в аккаунт')

@app.route('/info', methods=['GET']) # NOTE: просто страница важной инфы
def info():
    return render_template('info.html')

@app.route('/infobr', methods=['GET']) # NOTE: в общем то же самое почти, только нужное при регистрации
def info2():
    return render_template('info2.html')

if __name__ == '__main__':
    app.run(debug=True)

# TODO: зашифровать БД
# IDEA: сделать нормальные ошибки, не кривой html-кой (лучше alert'ами)
# TODO: сделать поддержку медиафайлов, в первую очередь фотографий
# TODO: сделать поддержку часовых поясов (tzinfo в datetime)
# TODO: сделать вынесение чата вверх списка по самому новому сообщению (https://www.programiz.com/python-programming/datetime/strptime)
# TODO: сделать страницы ошибок (https://flask-russian-docs.readthedocs.io/ru/latest/quickstart.html#id15)
# TODO: сделать публичные групповые чаты, куда могут вступить все по ссылке
# TODO: isusernamevalid написать и расставить, isinlist и isuserinchat расставить
# IDEA: сделать архив чатов
# TODO: разделить ник и логин
# IDEA: сделать на главном экране отображение у каждого чата последнего сообщения мелким текстом
# TODO: добавить капчи
# TODO: сделать смену пароля
# TODO: сделать шаблон getinfo и использовать его когда надо чтобы пользователь ввел что-то, подставляя разный текст
# TODO: сделать подтверждение для удаления чата
# IDEA: сделать пользователям id чтобы по истории браузера нельзя было узнать кто кого банил
# TODO: разобраться со слэшами в конце URL-адреса
# IDEA: сделать страницу пользователя
# TODO: добавить конкретные версии браузеров в страницу инфы
# TODO: разобраться с булевыми значениями в JSON и сделать там нормальный is_group после (а то сейчас все через жопу)
# TODO: сделать привязку к почте и восстановление через нее
# TODO: убрать в БД username и сделать через items()

# TODO: сделать несколько уровней админов
# TODO: добавить возможность перестать быть админом
