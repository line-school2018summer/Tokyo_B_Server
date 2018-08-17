# -*- coding: utf-8 -*-

import os
import hashlib
import re
import secrets

from flask import Flask, request, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import Integer, String
from sqlalchemy.orm import relation, backref, scoped_session
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['JSON_AS_ASCII'] = False

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
    friends = db.relationship(
        'User', secondary=friendship,
        primaryjoin=(friendship.c.add_id == id),
        secondaryjoin=(friendship.c.added_id == id),
        backref=db.backref('friendship', lazy='dynamic'), lazy='dynamic')
    talk_groups = relation("Talk_group", order_by="Talk_group.id",
                           uselist=True, backref="users",
                           secondary=talk_group_relation_table, lazy="dynamic")

    def __init__(self, user_id, name, password, token):
        self.user_id = user_id
        self.name = name
        self.password = password
        self.token = token

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
        return '<Talk_group(%d)>' % (self.id)


class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True)
    talk_group_id = Column(Integer, ForeignKey("talk_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(Integer)
    content = Column(String)

    def __repr__(self):
        return '<Contents(%d, %d, %s)>' % (self.id, self.user_id, self.content[:20])


engine = create_engine('sqlite:///database.db', echo=False)
Base.metadata.create_all(engine)
SessionMaker = sessionmaker(bind=engine)
session = scoped_session(SessionMaker)


@app.errorhandler(404)  # 404のハンドラです
def page_not_found(e):
    return make_response(jsonify({"error": 1,
                                  "content":
                                      {"message": "missing Page"}
                                  }))


@app.errorhandler(500)  # 500のハンドラです
def page_not_found(e):
    return make_response(jsonify({"error": 1,
                                  "content":
                                      {"message": "Internal Server Error"}
                                  }))


def valid_auth(user_id, pass_):  # idとpass_に合致するユーザーが存在するか検証し、存在するなら返します。
    return User.query.filter(User.user_id.in_([user_id]),
                             User.password.in_(
                                 [str(hashlib.sha256(b"%a" % str(pass_)).digest())])).first()


def verify_token(id, token):
    if token == "logout":
        return None
    user = session.query(User).get(id)
    return user if user.token == token else None


def zero_or_go(his, talk):
    try:
        return his[str(talk.id)]
    except KeyError:
        return 0


@app.route("/")  # ルートディレクトリです
def main():
    return make_response(jsonify({"error": 0,
                                  "content":
                                      {"message": "/[get]"}
                                  }))


@app.route('/register', methods=['GET', 'POST'])  # アカウント登録用のディレクトリです
def register():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content":
                                          {"message": "/register[get]"}
                                      }))
    exist_id = 0  # アカウントの存在
    authenticated = 0  # すでにログインしているか
    bad_id = 0  # idのよしあし
    bad_name = 0  # nameのよしあし
    bad_password = 0  # passwordのよしあし
    password_confirm_does_not_match = 0  # passwordのコンファームが合致しているかどうかです・
    request_json = request.get_json()

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

    if exist_id or authenticated or bad_id or bad_name or bad_password or password_confirm_does_not_match:  # エラーがあった場合です
        return make_response(jsonify({
            "error": 1,
            "content": {
                "authentocated": authenticated,
                "exist_id": exist_id,
                "bad_id": bad_id,
                "bad_name": bad_name,
                "bad_password": bad_password,
                "password_confirm_does_not_match": password_confirm_does_not_match
            }
        }))
    token = secrets.token_hex()
    user = User(user_id=request_json["user_id"], name=request_json["name"],
                password=str(hashlib.sha256(b"%a" % str(request_json["password"])).digest()), token=token)
    session.add(user)
    session.commit()  # 無かった場合、登録します。
    return make_response(jsonify({
        "error": 0,
        "content": {
            "logged_id": user.id,
            "logged_user_id": request_json["user_id"],
            "logged_pass": request_json["password"],
            "token": token,
            "message": "successful registration"
        }
    }))


@app.route('/login', methods=["GET", "POST"])  # ログイン用のディレクトリです
def login():
    if request.method == 'GET':
        return make_response(jsonify({"error": 0,
                                      "content":
                                          {"message": "/login[get]"}
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


@app.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/logout[get]"
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


@app.route('/account_modify', methods=['GET', 'POST'])  # ユーザー情報変更のディレクトリです。
def account_modify():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/account_modify[get]"
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
        if not (exist_id or bad_id or bad_name or bad_password or password_confirm_does_not_match or invalid_verify):
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


@app.route("/add_friend", methods=["GET", "POST"])
def add_friend():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/add_friend[get]"
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


@app.route("/remove_friend", methods=["GET", "POST"])
def remove_friend():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/remove_friend[get]"
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


@app.route("/friends_list", methods=["GET", "POST"])
def friends_list():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/friends_list[get]"
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
    invalid_talk_id = 0
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
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": 0
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
                                                           "sent_user_name": session.query(User).get(cont.user_id).name,
                                                           "content_type": cont.type,
                                                           "content_content": cont.content,
                                                           "content_id": cont.id
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
                                                           "sent_user_name": session.query(User).get(cont.user_id).name,
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
    return make_response(jsonify({"error": 1,
                                  "content": {
                                      "not_authenticated": 0,
                                      "invalid_verify": 0,
                                      "invalid_talk_id": 1
                                  }
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
    if not_authenticated or invalid_verify or missing_target or too_long_text or meaningless_text or invalid_talk_id:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": invalid_talk_id,
                                          "too_long_text": too_long_text,
                                          "meaningless_text": meaningless_text
                                      }
                                      }))

    cont = Content(user_id=user.id, talk_group_id=talk.id, type=request_json["content"]["type"], content=request_json["content"]["content"].strip())
    session.add(cont)
    talk.content.append(cont)
    session.commit()

    return make_response(jsonify({"error": 0,
                                  "content": {
                                      "talk_id": talk.id,
                                      "message": "sent successfully"
                                  }
                                  }))


@app.route("/chat/make/group", methods=["GET", "POST"])
def chat_goup_make():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/make/group[get]"
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
    personal_chat = 0
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
    elif target.name == "_personal":
        personal_chat = 1
    if not_authenticated or invalid_verify or already_joined or invalid_talk_id or personal_chat:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_talk_id": invalid_talk_id,
                                          "personal_chat": personal_chat,
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


@app.route("/chat/join/other", methods=["GET", "POST"])
def chat_join_other():
    if request.method == "GET":
        return make_response(jsonify({"error": 0,
                                      "content": {
                                          "message": "/chat/join/other[get]"
                                      }
                                      }))
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    invalid_user_id = 0
    invalid_talk_id = 0
    personal_chat = 0
    user_not_joined = 0
    already_joined = 0
    user = verify_token(request_json["id"], request_json["token"])
    if request_json["content"]["use_id"]:
        target_user = session.query(User).get(request_json["content"]["target_user_id"])
    else:
        target_user = session.query(User).filter(User.user_id.in_([request_json["content"]["target_user_id"]])).first()
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
    elif target_group in target_user.talk_groups:
        already_joined = 1
    if not target_group:
        invalid_talk_id = 1
    elif target_group.name == "_personal":
        personal_chat = 1
    if not_authenticated or invalid_verify or already_joined or invalid_talk_id or personal_chat or invalid_user_id or user_not_joined:
        return make_response(jsonify({"error": 1,
                                      "content": {
                                          "not_authenticated": not_authenticated,
                                          "invalid_verify": invalid_verify,
                                          "invalid_user_id": invalid_user_id,
                                          "invalid_talk_id": invalid_talk_id,
                                          "personal_chat": personal_chat,
                                          "user_not_joined": user_not_joined,
                                          "already_joined": already_joined
                                      }
                                      }))
    target_user.talk_groups.append(target_group)
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
        target_user = session.query(User).filter(User.user_id.in_([request_json["content"]["target_user_id"]])).first()

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


# YYYY-MM-DD:HH:MM:SS


"""

@app.route("/json/date/<day>")
def json_date(day):
    try:
        try:
            global today
            if today < datetime.date.today():
                del_lim()
        except:
            del_lim()
            today = datetime.date.today()
        jsons = {i: "" for i in day.replace(" ", "").split(";")}
        for date in day.split(";"):
            tmp = date.split("-")
            tmp = datetime.date(*map(int, tmp))
            p_from = Entry.query.filter(Entry.change_from_date.in_([date])).order_by(Entry.target_depart).all()
            p_to = Entry.query.filter(Entry.change_to_date.in_([date])).order_by(Entry.target_depart).all()
            p_all = list(set(p_from) | set(p_to))
            json = {
                "from_match": {str(i): json_it(m) for i, m in enumerate(p_from)
                               },
                "to_match": {str(i): json_it(m) for i, m in enumerate(p_to)
                             },
                "all_match": {str(i): json_it(m) for i, m in enumerate(p_all)
                              }
            }
            json["from_match"]["count"] = len(p_from)
            json["to_match"]["count"] = len(p_to)
            json["all_match"]["count"] = len(p_all)
            jsons[date] = json
        return jsonify(jsons)
    except:
        abort(500)


@app.route("/json/class/<depart>")
def json_depart(depart):
    try:
        global dat
        try:
            global today
            if today < datetime.date.today():
                del_lim()
        except:
            del_lim()
            today = datetime.date.today()
        p = Entry.query.all()

        dat_rev = {value: key for key, value in dat.items()}

        tmp = set(dat_rev[i] for i in depart.upper().replace(" ", "").split(";"))
        over = defaultdict(list)
        for i in p[::]:
            if not prime_factors(i.target_depart) & tmp:
                p.remove(i)
            for j in tmp:
                if j in prime_factors(i.target_depart):
                    over[dat[j]] += [i]
        json = {
            "all_match": {str(i): json_it(m) for i, m in enumerate(p)
                          }
        }
        json["all_match"]["count"] = len(p)
        for key, value in over.items():
            json[key] = {str(k): json_it(m) for k, m in enumerate(value)}
            json[key]["count"] = len(value)
        return jsonify(json)
    except:
        abort(500)


@app.route("/json/reference")
def api_reference():
    return render_template("reference.html")


@app.route("/edit/<int:num>", methods=['GET', 'POST'])
@login_required
def edit(num=0):
    p = Entry.query.filter(Entry.changeid.in_([num])).first()
    if not p:
        return render_template("404.html")
    global dat
    if request.method == 'POST':
        edited = 0
        tmp = 1
        for key, item in request.form.items():
            if key == "all":
                edited = 1
                break
            if key[:5] == "radio":
                tmp *= int(item)
        if tmp == 1 and not edited:
            tmp = p.target_depart
        if p.contributor != current_user.id:
            return render_template("404.html")
        p.target_depart = tmp
        p.change_from_date = request.form["from_date"]
        p.change_from_class = request.form["from_class"]
        p.change_from_time = request.form["from_time"]
        p.change_from_teacher = request.form["from_teacher"]
        p.change_to_date = request.form["to_date"]
        if request.form["from_class"] == request.form["to_class"]:
            p.change_to_class = ""
        else:
            p.change_to_class = request.form["to_class"]
        p.change_to_time = request.form["to_time"]
        p.change_to_teacher = request.form["to_teacher"]
        p.remark = request.form["remark"]
        p.published = request.form["published"]
        if str(request.form["delete"]) == "いいよ！こいよ！":
            session.delete(p)
            session.commit()
            return redirect("/")
        session.commit()
    return render_template('editprofile.html', page=p, prim=prime_factors, dat=dat)


@app.route("/<passw>/count")
def count(passw):
    global hashed_pass
    if hashlib.sha256(b"%a" % passw).digest() == hashed_pass:
        return render_template("count.html", que=View.query.all())
    else:
        return redirect("404.html")


@app.route("/proposal", methods=["GET", "POST"])
def proposal():
    if request.method == "GET":
        return render_template("proposal.html")
    else:
        with open("art.txt", "a") as file:
            file.write(request.form["string"].replace("[EOA]", "") + "[EOA]")
        flash("メッセージが投稿されました。")
        return render_template("proposal.html")


@app.route("/proposals/<passw>")
def proposals(passw):
    if hashlib.sha256(
                    b"%a" % passw).digest() == b'\xf8\x83\xa7i;\x17 \xe3\xf4\x7f\xb8j\xbe\xd6I\xd2*\xeb\xe9*:c\xcf\xc9\x0e\xb5\xe3Lu\xb4\x94\xd9':
        try:
            with open("art.txt", "r") as file:
                tmp = file.read().split("[EOA]")[:-1]
            txt = "<table border=\"1\" width=\"400\"><tr><th>body</th></tr><tr><td>" + "</td></tr><tr><td>".join(
                tmp) + "</tb></tr></table>"
            return txt
        except:
            return "no proposals"


@app.route("/flush")
@login_required
def flush():
    del_lim()
    return "flushed!"


@app.route('/<passw>/static/<filename>')
def static_dir(passw, filename):
    global hashed_pass
    if hashlib.sha256(b"%a" % passw).digest() == hashed_pass:
        return send_from_directory('static', filename)
    else:
        return redirect("404.html")


@app.route('/<passw>/image/<filename>')
def image_dir(passw, filename):
    global hashed_pass
    if hashlib.sha256(b"%a" % passw).digest() == hashed_pass:
        return send_from_directory('image', filename)
    else:
        return redirect("404.html")


@app.route('/file/<filename>')
@login_required
def files(filename):
    return send_from_directory("./", filename)


def feed_cookie(content, cookie, now):
    response = make_response(content)
    max_age = 60 * 60 * 24 * 120
    expires = int(datetime.datetime.now().timestamp()) + max_age
    response.set_cookie('depart', value=str(cookie * 810893), max_age=max_age)
    return response


def intize(cookie):
    return int(cookie.get("depart"))


def json_it(entry):
    dat = {2: '1M', 3: '1E', 5: '1C', 7: '1A', 11: '2M', 13: '2E', 17: '2C', 19: '2A', 23: '3M', 29: '3E',
           31: '3C', 37: '3A', 41: '4M', 43: '4EJ', 47: '4ED', 53: '4C', 59: '4A', 61: '5M', 67: '5EJ',
           71: '5ED', 73: '5C', 79: '5A', 83: '1A.ME', 89: '1A.CA', 97: '2A.ME', 101: '2A.CA'}
    json = {
        "from": {
            "class": entry.change_from_class,
            "date": entry.change_from_date,
            "time": entry.change_from_time,
            "teacher": entry.change_from_teacher
        },
        "to": {
            "class": entry.change_to_class,
            "date": entry.change_to_date,
            "time": entry.change_to_time,
            "teacher": entry.change_to_teacher
        },
        "depart": ";".join([dat[i] for i in prime_factors(entry.target_depart)]),
        "remark": entry.remark
    }
    return json


def del_lim():
    p = Entry.query.all()
    deleted = False
    for ent in p:
        try:
            bef = datetime.date(*list(map(int, ent.change_from_date.split("-"))))
        except:
            bef = datetime.date(1, 1, 1)
        try:
            to = datetime.date(*list(map(int, ent.change_to_date.split("-"))))
        except:
            to = datetime.date(1, 1, 1)
        if max(bef, to) < datetime.date.today():
            session.delete(ent)
            deleted = True
    if deleted:
        session.commit()


def prime_factors(n):
    global all_set
    if not n:
        return set()
    i = 2
    factors = []
    for i in all_set:
        if not n % i:
            factors.append(i)
    return set(factors)
"""

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
