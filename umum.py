# -*- coding: utf-8 -*-

import os
import hashlib
import random
import re
import secrets
import datetime
import smtplib

from email import message

from flask import Flask, request, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import Integer, String, DateTime
from sqlalchemy.orm import relation, backref, scoped_session
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['JSON_AS_ASCII'] = False

today = datetime.datetime.today()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

passw_re = re.compile("\A(?=.*?[a-z])(?=.*?\d)[a-z\d]{6,12}\Z(?i)")  # passwordの認証のための正規表現です
id_re = re.compile("\A(?=.*?[a-z])(?=.*?\d)[a-z\d]{4,12}\Z(?i)")  # idの認証のための正規表現です

Base = declarative_base()

talk_group_relation_table = Table('talk_group_relation', Base.metadata,
                                  Column('user_id', Integer, ForeignKey('users.id')),
                                  Column('talk_group_id', Integer, ForeignKey('talk_groups.id'))
                                  )

friendship = Table('friendship', Base.metadata,
                   Column('add_id', Integer, ForeignKey('users.id')),
                   Column('added_id', Integer, ForeignKey('users.id'))
                   )


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    token = Column(String, nullable=False)
    email = Column(String, nullable=False)
    friends = db.relationship(
        'User', secondary=friendship,
        primaryjoin=(friendship.c.add_id == id),
        secondaryjoin=(friendship.c.added_id == id),
        backref=db.backref('stalkers', lazy='dynamic'), lazy='dynamic')
    talk_groups = relation("Talk_group", order_by="Talk_group.id",
                           uselist=True, backref="users",
                           secondary=talk_group_relation_table, lazy="dynamic")

    def __init__(self, user_id, name, password, token, email):
        self.user_id = user_id
        self.name = name
        self.password = password
        self.token = token
        self.email = email

    def __repr__(self):
        return '<User(%d, %s)>' % (self.id, self.user_id)


class Talk_group(Base):
    __tablename__ = "talk_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    content = relation("Content", order_by="Content.id",
                       uselist=True, backref="talk_group", lazy="dynamic")

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Talk_group(%d)>' % self.id


class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True)
    talk_group_id = Column(Integer, ForeignKey("talk_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(Integer)
    content = Column(String)
    timestamp = Column(String, nullable=False)

    def __repr__(self):
        return '<Contents(%d, %d, %s)>' % (self.id, self.user_id, self.content[:20])


class Mail_verify(Base):
    __tablename__ = "meil_verify"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    code = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    token = Column(String, nullable=False)


engine = create_engine('sqlite:///database.db', echo=False)
Base.metadata.create_all(engine)
SessionMaker = sessionmaker(bind=engine)
session = scoped_session(SessionMaker)


@app.errorhandler(404)  # 404のハンドラです
def page_not_found(e):
    return make_response(jsonify({"error": 1,
                                  "content":
                                      {"message": "missing Page"}
                                  })), e


@app.errorhandler(500)  # 500のハンドラです
def page_not_found(e):
    return make_response(jsonify({"error": 1,
                                  "content":
                                      {"message": "Internal Server Error"}
                                  })), e


def valid_auth(user_id, pass_):  # idとpass_に合致するユーザーが存在するか検証し、存在するなら返します。
    return User.query.filter(User.user_id.in_([user_id]),
                             User.password.in_(
                                 [str(hashlib.sha256(b"%a" % str(pass_)).digest())])).first()


def verify_token(id_, token):
    if token == "logout":
        return None
    user = session.query(User).get(id_)
    try:
        return user if user.token == token else None
    except:
        return None

def zero_or_go(his, talk):
    try:
        return his[str(talk.id)]
    except KeyError:
        return 0


def send_mail(code, email, name):
    text = f"""{name}様
    
LIMEです。
ご登録ありがとうございます。
以下の認証コードをLIMEの画面内に入力いただきますと、登録が完了いたします。

認証コード: 【{code}】 

認証コードは {datetime.datetime.today().strftime("%Y/%m/%d 23:59")} まで有効です。
心当たりのない方はこのメールを破棄してください。

LIME
    """
    smtp_host = 'smtp.gmail.com'
    smtp_port = 587
    from_email = 'do.not.reply.lime@gmail.com'
    to_email = 'gey3933@gmail.com'
    username = 'do.not.reply.lime@gmail.com'
    password = open("password.txt", "r").read()

    msg = message.EmailMessage()
    msg.set_content(text)
    msg['Subject'] = '【LIME】登録認証コード'
    msg['From'] = from_email
    msg['To'] = to_email

    server = smtplib.SMTP(smtp_host, smtp_port)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(username, password)
    server.send_message(msg)
    server.quit()


@app.route("/")  # ルートディレクトリです
def main():
    return make_response(jsonify({"error": 0,
                                  "content":
                                      {"message": "/[get]"}
                                  }))


@app.route('/account/register/register', methods=['GET', 'POST'])  # アカウント登録用のディレクトリです
def register():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content":
                                          {"message": "/account/register/register[get]"}
                                      }))
    exist_id = 0  # アカウントの存在
    authenticated = 0  # すでにログインしているか
    bad_id = 0  # idのよしあし
    bad_name = 0  # nameのよしあし
    bad_password = 0  # passwordのよしあし
    password_confirm_does_not_match = 0  # passwordのコンファームが合致しているかどうかです
    request_json = request.get_json()
    print(request_json)

    if request_json["authenticated"]:
        authenticated = 1
    if session.query(User).filter(User.user_id.in_([request_json["user_id"]])).first():
        exist_id = 1
    if not id_re.match(request_json["user_id"]):
        bad_id = 1
        print(request_json["user_id"])
    if not 0 < len(request_json["name"]) < 32:
        bad_name = 1
    if not passw_re.match(request_json["password"]):
        bad_password = 1
        print(request_json["password"])
    if request_json["password"] != request_json["password_confirm"]:
        password_confirm_does_not_match = 1

    if exist_id or authenticated or bad_id or bad_name or bad_password or password_confirm_does_not_match:
        return make_response(jsonify({
            "error": 1,
            "content": {
                "authenticated": authenticated,
                "exist_id": exist_id,
                "bad_id": bad_id,
                "bad_name": bad_name,
                "bad_password": bad_password,
                "password_confirm_does_not_match": password_confirm_does_not_match
            }
        }))
    code = "%04d" % random.randint(0, 9999)
    token = secrets.token_hex()
    user = Mail_verify(user_id=request_json["user_id"], name=request_json["name"],
                       password=str(hashlib.sha256(b"%a" % str(request_json["password"])).digest()), token=token,
                       code=code, email=request_json["email"])
    if today < datetime.datetime.today():
        session.query(User).delete()

    session.add(user)
    session.commit()
    send_mail(code=code, email=request_json["email"], name=request_json["name"])
    return make_response(jsonify({
        "error": 0,
        "content": {
            "verify_id": user.id
        }
    }))


@app.route('/account/register/verify', methods=['GET', 'POST'])  # アカウント登録用のディレクトリです
def register_verify():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content":
                                          {"message": "/account/register/verify[get]"}
                                      }))
    invalid_id = 0
    authenticated = 0
    invalid_code = 0
    request_json = request.get_json()
    print(request_json)

    if request_json["authenticated"]:
        authenticated = 1
    verify = session.query(Mail_verify).filter(Mail_verify.id.in_([request_json["verify_id"]])).first()
    if not verify:
        invalid_id = 1
    else:
        verify = session.query(Mail_verify).filter(Mail_verify.id.in_([request_json["verify_id"]]),
                                                   Mail_verify.code.in_([request_json["code"]])).first()
        if not verify:
            invalid_code = 1

    if invalid_code or authenticated or invalid_id:
        return make_response(jsonify({
            "error": 1,
            "content": {
                "authenticated": authenticated,
                "invalid_verify_id": invalid_id,
                "invalid_code": invalid_code
            }
        }))
    user = User(user_id=verify.user_id, name=verify.name,
                password=verify.password, token=verify.token,
                email=verify.email)
    session.add(user)
    session.delete(verify)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "logged_id": user.id,
                                      "logged_user_id": user.user_id,
                                      "token": user.token,
                                      "message": "successful registration"
                                  }
                                  }))


@app.route('/account/login', methods=["GET", "POST"])  # ログイン用のディレクトリです
def login():
    if request.method == 'GET':
        return make_response(jsonify({"error": 0,
                                      "content":
                                          {"message": "/account/login[get]"}
                                      }))

    request_json = request.get_json()

    result = session.query(User).filter(User.user_id.in_([request_json["user_id"]]),
                                        User.password.in_(
                                            [str(hashlib.sha256(
                                                b"%a" % str(request_json["password"])).digest())])).first()
    if result and not request_json["authenticated"]:  # ログイン成功時です
        token = secrets.token_hex()
        result.token = token
        session.commit()
        return make_response(jsonify({
            "error": 0,
            "content": {
                "logged_id": result.id,
                "logged_user_id": request_json["user_id"],
                "logged_pass": request_json["password"],
                "token": token,
                "message": "logged in successfully"
            }
        }))
    else:  # 失敗時
        missing_id = not bool(User.query.filter(User.user_id.in_([request_json["user_id"]])).first())
        return make_response(jsonify({
            "error": 1,
            "content": {
                "authenticated": request_json["authenticated"],
                "missing_id": missing_id,
                "invalid_password": not missing_id
            }
        }))

@app.route("/account/logout", methods=["GET", "POST"])
def logout():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/account/logout[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    if not request_json["authenticated"]:
        not_authenticated = 1
    user = verify_token(request_json["id"], request_json["token"])
    if not user:
        invalid_verify = 1
    if not not_authenticated or invalid_verify:
        user.token = "logout"
        session.commit()
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "logged out successfully"
                                      }
                                      }))
    return make_response(jsonify({"error": 1,
                                  "content": {
                                      "not_authenticated": not_authenticated,
                                      "invalid_verify": invalid_verify
                                  }
                                  }))

@app.route('/account/modify', methods=['GET', 'POST'])  # ユーザー情報変更のディレクトリです。
def account_modify():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/account/modify[get]"
                                      }
                                      }))
    not_authenticated = 0
    invalid_verify = 0
    exist_id = 0
    bad_id = 0
    bad_name = 0
    bad_password = 0
    password_confirm_does_not_match = 0

    request_json = request.get_json()
    user = valid_auth(request_json["user_id"], request_json["password"])

    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if not (invalid_verify or not_authenticated):
        if session.query(User).filter(User.user_id.in_([request_json["modify"]["user_id"]])).first():
            exist_id = 1
        if not id_re.match(request_json["modify"]["user_id"]) and request_json["modify"]["user_id"] != "":
            bad_id = 1
        if not 0 < len(request_json["modify"]["name"]) < 32:
            bad_name = 1
        if not passw_re.match(request_json["modify"]["password"]) and request_json["modify"]["password"] != "":
            bad_password = 1
        if request_json["modify"]["password"] != request_json["modify"]["password_confirm"]:
            password_confirm_does_not_match = 1
        if not (
                exist_id or bad_id or bad_name or bad_password or password_confirm_does_not_match or invalid_verify):
            if request_json["modify"]["user_id"]:
                user.user_id = request_json["modify"]["user_id"]
            if request_json["modify"]["password"]:
                user.password = str(hashlib.sha256(b"%a" % str(request_json["modify"]["password"])).digest())
            if request_json["modify"]["name"]:
                user.name = request_json["modify"]["name"]
            session.commit()
            return make_response(jsonify({"error": 0,
                                          "content": {
                                              "new_id": user.user_id,
                                              "new_name": user.name,
                                              "message": "modified successfully"
                                          }
                                          }))
    return make_response(jsonify({"error": 1,
                                  "content": {
                                      "not_authenticated": not_authenticated,
                                      "invalid_verify": invalid_verify,
                                      "exist_id": exist_id,
                                      "bad_id": bad_id,
                                      "bad_name": bad_name,
                                      "bad_password": bad_password,
                                      "password_confirm_does_not_match": password_confirm_does_not_match
                                  }
                                  }))

@app.route("/friend/add", methods=["GET", "POST"])
def add_friend():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/friend/add[get]"
                                      }
                                      }))
    request_json = request.get_json()

    not_authenticated = 0
    invalid_verify = 0
    unexist_id = 0
    self_adding = 0
    already_friend = 0

    user = verify_token(request_json["id"], request_json["token"])
    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if request_json["use_id"]:
        target = session.query(User).get(request_json["target_id"])
    else:
        target = session.query(User).filter(User.uesr_id.in_(request_json["target_id"])).first()
    if not target:
        unexist_id = 1
    if user == target:
        self_adding = 1
    if not (invalid_verify or unexist_id):
        if target in user.friends:
            already_friend = 1
    if not_authenticated or unexist_id or already_friend or self_adding or invalid_verify:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "unexist_id": unexist_id,
                                          "self_adding": self_adding,
                                          "already_friend": already_friend
                                      }
                                      }))
    user.friends.append(target)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "added successfully"
                                  }
                                  }))

@app.route("/friend/remove", methods=["GET", "POST"])
def remove_friend():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/friend/remove[get]"
                                      }
                                      }))
    request_json = request.get_json()

    not_authenticated = 0
    invalid_verify = 0
    unexist_id = 0
    self_removing = 0
    already_stranger = 0
    print(request_json)

    user = verify_token(request_json["id"], request_json["token"])
    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if request_json["use_id"]:
        target = session.query(User).get(request_json["target_id"])
    else:
        target = session.query(User).filter(User.uesr_id.in_(request_json["target_id"])).first()
    if not target:
        unexist_id = 1
    if user == target:
        self_removing = 1
    if not (invalid_verify or unexist_id):
        if target not in user.friends:
            already_stranger = 1
    if not_authenticated or unexist_id or already_stranger or self_removing or invalid_verify:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "unexist_id": unexist_id,
                                          "self_removing": self_removing,
                                          "already_stranger": already_stranger
                                      }
                                      }))
    user.friends.remove(target)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "removed successfully"
                                  }
                                  }))

@app.route("/friend/list", methods=["GET", "POST"])
def friends_list():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/friend/list[get]"
                                      }
                                      }))
    request_json = request.get_json()

    not_authenticated = 0
    invalid_verify = 0

    if not request_json["authenticated"]:
        not_authenticated = 1
    user = verify_token(request_json["id"], request_json["token"])
    if not user:
        invalid_verify = 1
    if invalid_verify or not_authenticated:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify
                                      }
                                      }))
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "friends_list",
                                      "friends": {g.id: {"user_id": str(g.user_id),
                                                         "name": str(g.name)} for g in user.friends
                                                  }
                                  }
                                  }))

@app.route("/chat/get", methods=["GET", "POST"])
def chat_get():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/get[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0

    user = verify_token(request_json["id"], request_json["token"])

    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if not_authenticated or invalid_verify:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify
                                      }
                                      }))
    if request_json["content"]["talk_all_need"]:
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "talk": {
                                              str(talk.id): {
                                                  "name": talk.name,
                                                  "content": {
                                                      "new": [
                                                          {"sent_user_id": cont.user_id,
                                                           "sent_user_name": session.query(User).get(
                                                               cont.user_id).name,
                                                           "content_type": cont.type,
                                                           "content_content": cont.content,
                                                           "content_id": cont.id,
                                                           "timestamp": cont.timestamp
                                                           } for cont in talk.content.filter(
                                                              Content.id > zero_or_go(
                                                                  request_json["content"]["talk_his"], talk)).all()]
                                                  }
                                              } for talk in user.talk_groups
                                          }
                                      },
                                      }
                                     ))

    else:
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "talk": {
                                              str(talk.id): {
                                                  "name": talk.name,
                                                  "content": {
                                                      "new": [
                                                          {"sent_user_id": cont.user_id,
                                                           "sent_user_name": session.query(User).get(
                                                               cont.user_id).name,
                                                           "content_type": cont.type,
                                                           "content_content": cont.content,
                                                           "content_id": cont.id
                                                           } for cont in talk.content.filter(
                                                              Content.id > zero_or_go(
                                                                  request_json["content"]["talk_his"], talk)).all()]
                                                  }
                                              } for talk in user.talk_groups.filter(
                                              Talk_group.id.in_(request_json["content"]["talk_his"].keys())).all()
                                          }
                                      },
                                      }))

@app.route("/chat/send", methods=["GET", "POST"])
def chat_send():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/send[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_talk_id = 0
    invalid_verify = 0
    too_long_text = 0
    meaningless_text = 0

    user = verify_token(request_json["id"], request_json["token"])

    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if request_json["content"]["content"] == 1:
        if len(request_json["content"]["content"]) > 1024:
            too_long_text = 1
        if not request_json["content"]["content"].strip():
            meaningless_text = 1
    talk = session.query(Talk_group).get(request_json["content"]["talk_id"])
    if not talk:
        invalid_talk_id = 1
    if not_authenticated or invalid_verify or too_long_text or meaningless_text or invalid_talk_id:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": invalid_talk_id,
                                          "too_long_text": too_long_text,
                                          "meaningless_text": meaningless_text
                                      }
                                      }))

    cont = Content(user_id=user.id, talk_group_id=talk.id, type=request_json["content"]["type"],
                   content=request_json["content"]["content"].strip(),
                   timestamp=datetime.datetime.utcnow().strftime("%Y:%m:%d:%H:%M:%S"))
    session.add(cont)
    talk.content.append(cont)
    session.commit()

    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "talk_id": talk.id,
                                      "message": "sent successfully"
                                  }
                                  }))

@app.route("/chat/make", methods=["GET", "POST"])
def chat_goup_make():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/make[get]"
                                      }
                                      }))

    request_json = request.get_json()
    user = verify_token(request_json["id"], request_json["token"])
    talk = Talk_group(name=request_json["content"]["group_name"])
    session.add(talk)
    user.talk_groups.append(talk)
    session.commit()
    return jsonify({"error": 0,
                    "content": {
                        "talk_id": talk.id,
                        "message": "sent successfully"
                    }
                    })

@app.route("/chat/join/self", methods=["GET", "POST"])
def chat_join():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/join/self[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    invalid_talk_id = 0
    already_joined = 0
    user = verify_token(request_json["id"], request_json["token"])
    target = session.query(Talk_group).get(request_json["content"]["target_group"])
    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    elif target in user.talk_groups:
        already_joined = 1
    if not target:
        invalid_talk_id = 1
    if not_authenticated or invalid_verify or already_joined or invalid_talk_id:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": invalid_talk_id,
                                          "already_joined": already_joined
                                      }
                                      }))
    user.talk_groups.append(target)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "seccess"
                                  }
                                  }))

@app.route("/chat/leave/self", methods=["GET", "POST"])
def chat_leave():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/leave/self[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    invalid_talk_id = 0
    not_joined = 0
    user = verify_token(request_json["id"], request_json["token"])
    target = session.query(Talk_group).get(request_json["content"]["target_group"])
    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    elif target not in user.talk_groups:
        not_joined = 1
    if not target:
        invalid_talk_id = 1
    if not_authenticated or invalid_verify or not_joined or invalid_talk_id:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": invalid_talk_id,
                                          "not_joined": not_joined
                                      }
                                      }))
    user.talk_groups.remove(target)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "seccess"
                                  }
                                  }))

@app.route("/chat/leave/other", methods=["GET", "POST"])
def chat_leave_other():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/leave/other[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    invalid_user_id = 0
    invalid_talk_id = 0
    user_not_joined = 0
    target_not_joined = 0
    user = verify_token(request_json["id"], request_json["token"])
    if request_json["content"]["use_id"]:
        target_user = session.query(User).get(request_json["content"]["target_user_id"])
    else:
        target_user = session.query(User).filter(
            User.user_id.in_([request_json["content"]["target_user_id"]])).first()
    target_group = session.query(Talk_group).get(request_json["content"]["target_group"])
    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    else:
        if target_group not in user.talk_groups:
            user_not_joined = 1
    if not target_user:
        invalid_user_id = 1
    elif target_group not in target_user.talk_groups:
        target_not_joined = 1
    if not target_group:
        invalid_talk_id = 1
    if not_authenticated or invalid_verify or already_joined or invalid_talk_id or \
            invalid_user_id or target_not_joined:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_user_id": invalid_user_id,
                                          "invalid_talk_id": invalid_talk_id,
                                          "personal_chat": personal_chat,
                                          "user_not_joined": user_not_joined,
                                          "target_not_joined": target_not_joined
                                      }
                                      }))
    target_user.talk_groups.remve(target_group)
    session.commit()
    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "message": "seccess"
                                  }
                                  }))

@app.route("/friend/search", methods=["GET", "POST"])
def friend_search():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/friend/search[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    invalid_user_id = 0

    user = verify_token(request_json["id"], request_json["token"])
    if request_json["content"]["use_id"]:
        target_user = session.query(User).get(request_json["content"]["target_user_id"])
    else:
        target_user = session.query(User).filter(
            User.user_id.in_([request_json["content"]["target_user_id"]])).first()

    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid_verify = 1
    if not target_user:
        invalid_user_id = 1
    if not_authenticated or invalid_verify or invalid_user_id:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_user_id": invalid_user_id
                                      }
                                      }))

    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "id": target_user.id,
                                      "user_id": target_user.user_id,
                                      "name": target_user.name
                                  }
                                  }))


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='0.0.0.0', port=80, threaded=True)
