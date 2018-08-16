# -*- coding: utf-8 -*-

import os
import hashlib
import re
import secrets

from flask import Flask, redirect, request, session, send_from_directory, jsonify, make_response, abort
from flask_login import login_user, logout_user, LoginManager, UserMixin, login_required, current_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['JSON_AS_ASCII'] = False
login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

passw_re = re.compile("\A(?=.*?[a-z])(?=.*?\d)[a-z\d]{6,12}\Z(?i)")  # passwordの認証のための正規表現です
id_re = re.compile("\A(?=.*?[a-z])(?=.*?\d)[a-z\d]{4,12}\Z(?i)")  # idの認証のための正規表現です


class User(db.Model):
    __tablename__ = "user"  # tableはuserです
    id = db.Column(db.String(16), primary_key=True)  # 16文字までのidをprimary_keyにします
    name = db.Column(db.String(32))  # 32文字までのname(hash化されたもの。)
    password = db.Column(db.String(128))  # 128文字までのpassword(hash化されたもの。)
    token = db.Column(db.String(64))  # 64文字のtoken

    def __init__(self, id, name, password, token):
        self.id = id
        self.name = name
        self.password = password
        self.token = token


@app.errorhandler(404)  # 404のハンドラです
def page_not_found(e):
    return jsonify({"error": 1,
                    "content":
                        {"message": "missing Page"}
                    })


@app.errorhandler(500)  # 500のハンドラです
def page_not_found(e):
    return jsonify({"error": 1,
                    "content":
                        {"message": "Internal Server Error"}
                    })


def valid_auth(id, pass_):  # idとpass_に合致するユーザーが存在するか検証し、存在するなら返します。
    return User.query.filter(User.id.in_([id]),
                             User.password.in_(
                                 [str(hashlib.sha256(b"%a" % str(pass_)).digest())])).first()


def verify_token(id, token):
    return User.query.filter(User.id.in_([id]),
                             User.token.in_(
                                 [token])).first()


@app.route("/")  # ルートディレクトリです
def main():
    return jsonify({"error": 0,
                    "content":
                        {"message": "/[get]"}
                    })


@app.route('/register', methods=['GET', 'POST'])  # アカウント登録用のディレクトリです
def register():
    if request.method == "GET":
        return jsonify({"error": 0,
                        "content":
                            {"message": "/register[get]"}
                        })
        exist_id = 0  # アカウントの存在
        authenticated = 0  # すでにログインしているか
        bad_id = 0  # idのよしあし
        bad_name = 0  # nameのよしあし
        bad_password = 0  # passwordのよしあし
        password_confirm_does_not_match = 0  # passwordのコンファームが合致しているかどうかです・
        request_json = request.get_json()

        if request_json["authenticated"]:
            authenticated = 1
        if User.query.filter(User.id.in_([request_json["id"]])):
            exist_id = 1
        if not id_re.match(request_json["id"]):
            bad_id = 1
        if not 0 < len(request_json["name"]) < 32:
            bad_name = 1
        if not passw_re.match(request_json["password"]):
            bad_password = 1
        if request_json["password"] != request_json["password_confirm"]:
            password_confirm_does_not_match = 1

        if exist_id or authenticated or bad_id or bad_name or bad_password or password_confirm_does_not_match:  # エラーがあった場合です
            return jsonify({
                "error": 1,
                "content": {
                    "authentocated": authenticated,
                    "exist_id": exist_id,
                    "bad_id": bad_id,
                    "bad_name": bad_name,
                    "bad_password": bad_password,
                    "password_confirm_does_not_match": password_confirm_does_not_match
                }
            })
        token = secrets.token_hex()
        user = User(id=request_json["id"], name=request_json["name"],
                    password=str(hashlib.sha256(b"%a" % str(request_json["password"])).digest()), token=token)
        db.session.add(user)
        db.session.commit()  # 無かった場合、登録します。
        return jsonify({
            "error": 0,
            "content": {
                "logged_id": request_json["id"],
                "logged_pass": request_json["password"],
                "token": token,
                "message": "successful registration"
            }
        })


@app.route('/login', methods=["GET", "POST"])  # ログイン用のディレクトリです
def login():
    if request.method == 'GET':
        return jsonify({"error": 0,
                        "content":
                            {"message": "/login[get]"}
                        })

    request_json = request.get_json()

    result = User.query.filter(User.id.in_([request_json["id"]]),
                               User.password.in_(
                                   [str(hashlib.sha256(b"%a" % str(request_json["password"])).digest())])).first()
    if result and not request_json["authenticated"]:  # ログイン成功時です
        token = secrets.token_hex()
        result.token = token
        db.session.commit()
        return jsonify({
            "error": 0,
            "content": {
                "logged_id": request_json["id"],
                "logged_pass": request_json["password"],
                "token": token,
                "message": "logged in successfully"
            }
        })
    else:  # 失敗時
        missing_id = not bool(User.query.filter(User.id.in_([request_json["id"]])))
        return jsonify({
            "error": 1,
            "content": {
                "authenticated": request_json["authenticated"],
                "missing_id": missing_id,
                "invalid_password": not missing_id
            }
        })


@app.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "GET":
        return jsonify({"error": 0,
                        "content": {
                            "message": "/logout[get]"
                        }
                        })
    request_json = request.get_json()
    not_authenticated = 0
    invalid_verify = 0
    if not request_json["authenticated"]:
        not_authenticated = 1
    user = verify_token
    if not user:
        invalid_verify = 1
    if not not_authenticated or invalid_verify:
        user.token = "logout"
        db.session.commit()
        return jsonify({"error": 0,
                        "content": {
                            "message": "logged out successfully"
                        }
                        })
    return jsonify({"error": 1,
                    "content": {
                        "not_authenticated": not_authenticated,
                        "invalid_verify": invalid_verify
                    }
                    })


@app.route('/account_modify', methods=['GET', 'POST'])  # ユーザー情報変更のディレクトリです。
def account_modify():
    if request.method == "GET":
        return jsonify({"error": 0,
                        "content": {
                            "message": "/account_modify[get]"
                        }
                        })
    not_authenticated = 0
    exist_id = 0
    bad_id = 0
    bad_name = 0
    bad_password = 0
    password_confirm_does_not_match = 0

    request_json = request.get_json()
    user = valid_auth(request_json["id"], request_json["password"])

    if not user:
        not_authenticated = 1
    else:
        if User.query.filter(User.id.in_([request_json["modify"]["id"]])):
            exist_id = 1
        if not id_re.match(request_json["modify"]["id"]) and request_json["modify"]["id"] != "":
            bad_id = 1
        if not 0 < len(request_json["modify"]["name"]) < 32:
            bad_name = 1
        if not passw_re.match(request_json["modify"]["password"]) and request_json["modify"]["password"] != "":
            bad_password = 1
        if request_json["modify"]["password"] != request_json["modify"]["password_confirm"]:
            password_confirm_does_not_match = 1
        if not exist_id or bad_id or bad_name or bad_password or password_confirm_does_not_match:
            if request_json["modify"]["id"]:
                user.id = request_json["modify"]["id"]
            if request_json["modify"]["password"]:
                user.password = str(hashlib.sha256(b"%a" % str(request_json["modify"]["password"])).digest())
            if request_json["modify"]["name"]:
                user.name = request_json["modify"]["name"]
            db.session.commit()
            return jsonify({"error": 0,
                            "content": {
                                "new_id": user.id,
                                "new_name": user.name,
                                "message": "modified successfully"
                            }
                            })
    return jsonify({"error": 1,
                    "content": {
                        "not_authenticated": not_authenticated,
                        "exist_id": exist_id,
                        "bad_id": bad_id,
                        "bad_name": bad_name,
                        "bad_password": bad_password,
                        "password_confirm_does_not_match": password_confirm_does_not_match
                    }
                    })


@app.route("/chat/personal", methods=["GET", "POST"])
def personal_chat():
    if request.method == "GET":
        return jsonify({"error": 0,
                        "content": {
                            "message": "/chat/personal[get]"
                        }
                        })
    request_json = request.get_json()
    not_authenticated = 0
    invalid__verify = 0
    missing_target = 0
    too_long_text = 0
    meaningless_text = 0

    user = verify_token(request_json["id"], request_json["token"])

    if not request_json["authenticated"]:
        not_authenticated = 1
    if not user:
        invalid__verify = 1
    if not User.query.filter(User.id.in_([request_json["content"]["target"]])).first():
        missing_target = 1
    if len(request_json["content"]["text"]) > 1024:
        too_long_text = 1
    if not request_json["content"]["text"].strip():
        meaningless_text = 1
    if not_authenticated or invalid__verify or missing_target or too_long_text or meaningless_text:
        return jsonify({"error": 1,
                        "content": {
                            "not_authenticated": not_authenticated,
                            "invalid_verify": invalid_verify,
                            "missing_target": missing_target,
                            "too_long_text": too_long_text,
                            "meaningless_text": meaningless_text
                        }
                        })
    pass  # ここでトークの処理
    return jsonify({"error": 0,
                    "content": {
                        "message": "sent successfully"
                    }
                    })


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
            db.session.delete(p)
            db.session.commit()
            return redirect("/")
        db.session.commit()
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
            db.session.delete(ent)
            deleted = True
    if deleted:
        db.session.commit()


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


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)
"""
