
- /
- /account/register
- /account/login
- /account/logout
- /account/modify
- /friend/add
- /friend/remove
- /friend/list
- /friend/search
- /chat/get
- /chat/send
- /chat/make
- /chat/join/self
- /chat/join/other

# / [get]
---
### GET
```
{"error": 0,
"content": {
    "message": "/[get]"
    }
}
```
# /account/register [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/account/register[get]"
    }
}
```
### POST

#### request
```
{"target": "/account/register",
"authenticated": <authenticated>,
"user_id": <user_id>,
"name": <name>,
"password": <password>,
"password_confirm": <password>
}
```
#### response
* エラー有りの場合
    * すでにログインしている状態での/account/registerへのpostは認められません。
    * 既存アカウントに重複するような"user_id"は使用できません。
    * 3文字以下、13文字以上、英数字以外の"user_id"は認められません。
    * 0文字、もしくは32文字以上の"name"は認められません。
    * 5文字以下、13文字以上、英数字以外の"password"は認められません。
    * "password"と"password_confirm"は等しくなければいけません。
```
{"error": 1,
"content": {
    "authenticated": <0 or 1>,
    "exist_id": <0 or 1>,
    "bad_id": <0 or 1>,
    "bad_name": <0 or 1>,
    "bad_password": <0 or 1>,
    "password_confirm_does_not_match": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "logged_id": <id>
    "logged_user_id": <user_id>,
    "logged_pass" <password>,
    "token": <token>,
    "message": "successful registration"
    }
}
```
# /account/login [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/account/login[get]"
    }
}
```
### POST
#### request
```
{"target": "/account/login", 
"authenticated": <authenticated>,
"user_id": <user_id>,
"password": <password>
```
#### response
* エラー有りの場合 
    * すでにログインしている状態での/account/registerへのpostは認められません。
    * 存在している"user_id"でなければいけません。
    * "user_id"が存在していた場合、"password"が合致していなければいけません。
    * (missing_id が 1 の時、invalid_password は自動的に 0 になるので、両者が常に同じ結果になることはありえません。)
```
{"error": 1, 
"content": {
    "authenticated": <0 or 1>,
    "missing_id": <0 or 1>,
    "invalid_password": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0, 
"content": {
    "logged_id": <id>
    "logged_user_id": <user_id>,
    "logged_pass" <password>,
    "token": <token>,
    "message": "logged in successfully"
    }
}
```
# /account/logout [get]
---
### GET
```
{"error": 0,
"content": {
    "message": "/account/logout[get]"
    }
}
```
### POST
#### request
```
{"target": "/account/logout", 
"authenticated": <authenticated>,
"id": <id>,
"token": <token>
```
#### response
* エラー有りの場合
    * ログインしていない状態での/account/logoutへのpostは認められません。
    * 合致しない"user_id", "token"でのpostは認められません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "logged out successfully"
    }
}
```
# /account/modify [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/account/modify[get]"
    }
}
```
### POST
#### request
"modify"内は変更先の情報を入力してください。空白は変更なしと捉えます。
```
{"target": "/account/modify",
"authenticated": <authenticated>,
"id": <user_id>,
"password": <password>,
"modify": {
    "user_id": <modify_id>,
    "name": <modify_name>,
    "password": <modify_password>,
    "password_confirm": <modify_password>
},
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/account/modifyへのpostは認められません。
    * 存在しない"user_id", "password"でのpostは認められません。
    * 既存の他のアカウントに重複するような"modify"-"user_id"は使用できません。
    * 3文字以下、13文字以上、英数字以外の"modify"-"user_id"は認められません。
    * 0文字、もしくは32文字以上の"modify"-"name"は認められません。
    * 5文字以下、13文字以上、英数字以外の"modift"-"password"は認められません。
    * "modify"-"password"と"modify"-"password_confirm"は等しくなければいけません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "exist_id": <0 or 1>,
    "bad_id": <0 or 1>,
    "bad_name": <0 or 1>,
    "bad_password": <0 or 1>,
    "password_confirm_does_not_match": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "new_id": <user_id>,
    "new_name": <name>,
    "message": "modified successfully"
    }
}
```
# /friend/add [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/friend/add[get]"
    }
}
```
### POST
* "use_id"が1の場合、"User.id"で走査を行います。そうでない場合、"User.user_id"で走査を行います。
#### request
```
{"target": "/friend/add",
"authenticated": <authenticated>,
"use_id": <0 or 1>
"id": <id>,
"token": <token>,
"target_id": <target_user_id>
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/friend/addへのpostは認められません。
    * 合致しない"user_id", "token"でのpostは認められません。
    * "terget_id"には、既存で、かつ、post元のユーザーとは異なるユーザーに合致する"user_id"のみ認められます。
    * 自分自身を"target_id"に指定することはできません。
    * すでに追加しているユーザーは重複で追加できません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "unexist_id": <0 or 1>,
    "self_adding": <0 or 1>,
    "already_friend": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "added successfully"
    }
}
```

# /friend/remove [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/friend/remove[get]"
    }
}
```
### POST
* "use_id"が1の場合、"User.id"で走査を行います。そうでない場合、"User.user_id"で走査を行います。
#### request
```
{"target": "/friend/remove",
"authenticated": <authenticated>,
"use_id": <0 or 1>
"id": <id>,
"token": <token>,
"target_id": <target_user_id>
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/friend/addへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 自分自身を"target_id"に指定することはできません。
    * "target_id"には、既存で、かつ、post元のユーザーとは異なるユーザーに合致する"user_id"のみ認められます。
    * friendに追加していないユーザーを"target_id"にすることはできません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>
    "unexist_id": <0 or 1>,
    "self_removing": <0 or 1>,
    "already_stranger": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "removed successfully"
    }
}
```

# /friend/list [get / post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/friend/list[get]"
    }
}
```
### POST
#### request
```
{"target": "/friend/list",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/friend_listへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "friends_list",
    "friends":{
        <id>: {"user_id": <str(user_id)>, "name": <str(name)>},
        <id>: {"user_id": <str(user_id)>, "name": <str(name)>},
        <id>: {"user_id": <str(user_id)>, "name": <str(name)>},
        ...
        }
    }
}
```
# /friend/search [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/friend/search[get]"
    }
}
```
### POST
#### request
* "content"-"use_id"が1の場合、targetユーザの特定にはUser.idを用います。そうでない場合、User.user_idを用います。
```
{"target": "/friend/search",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "use_id": <0 or 1>,
    "target_user_id": <user_id>
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/join/otherへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 存在しない"content"-"target_user_id"は認められません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "invalid_user_id": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
    "content": {
        "id": <id>,
        "user_id": <user_id>,
        "name": <name>
    }
}
```

# /chat/send [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/chat/send[get]"
    }
}
```
### POST
#### request
```
{"target": "/chat/send",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "talk_id": <talk_id>,
    "type": <type>,
    "content": <content>
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/personalへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 存在しない"content"-"talk_id"でのpostは認められません。
    * "content"-"type"には{1: text, 2: stamp, 3: image}に割り当てられた数字しか認められません。
    * "content"-"type"が1のとき、1024文字以上の"content"-"content"は認められません。
    * "content"-"type"が1のとき、空白、改行を除いたとき 0文字の"content"-"content"は認められません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "invalid_talk_id": <0 or 1>,
    "too_long_text": <0 or 1>,
    "meaningless_text": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "talk_id": <talk_id>,
    "message": "sent successfully"
    }
}
```

# /chat/get [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/chat/get[get]"
    }
}
```
### POST
#### request
```
{"target": "/chat/get",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "talk_all_need": <0 or 1>
    "talk_his": {
            <talk_id>: <latest_content_id>,
            <talk_id>: <latest_content_id>,
            <talk_id>: <latest_content_id>,
            ...
        }
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/getへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 存在しない"content"-"talk_id"は認められません。
    * これは負荷がかかる動作なので、"not_authenticated"か"invalid_verify"の内1つ以上が1の場合、"talk"の走査を行うことなくreturnされます。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>
    }
}
```
* エラーなしの場合
    * "content"-"talk_all_need"が1の場合、"content"-"talk_his"に含まれていないtalkの情報も返します。(外部からの新しいトークグループ作成に対応できるのはこちらのみです。)
    * "content"-"talk_all_need"が1の場合、"content"-"talk_his"に含まれているtalkの情報のみ返します(既存の一部のトークのみ更新したい場合便利です。トーク画面中などに用いると負荷を軽減させられるでしょう。)
```
{"error": 0,
"content": {
    "talk": {
        <talk_id>: {
            "name": <talk_group_name>,
            "new": {
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                ...
                }
            }
        },
        <talk_id>: {
            "name": <talk_group_name>,
            "new": {
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                {"sent_user_id": <user_id>, "sent_user_name": <user_name>, "content_type": <content_type> "content_content"<content>, "content_id": <content_id>},
                ...
                }
            },
        ...
        },
        "message": "success"
    }
}
```

# /chat/join/self [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/chat/join/self[get]"
    }
}
```
### POST
#### request
```
{"target": "/chat/join/self",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "target_group": <group_id>
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/join/selfへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 存在しない"content"-"target_group"は認められません。
    * すでに参加しているgroupをtargetには指定できません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "invalid_talk_id": <0 or 1>,
    "personal_chat": <0 or 1>,
    "already_joined": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "seccess"
    }
}
```

# /chat/make [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/chat/make[get]"
    }
}
```
### POST
#### request
```
{"target": "/chat/make",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "group_name": <group_name>
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/makeへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "invalid_talk_id": <0 or 1>,
    "personal_chat": <0 or 1>,
    "already_joined": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "seccess"
    }
}
```

# /chat/join/other [get, post]
---
### GET
```
{"error": 0,
"content": {
    "message": "/chat/join/other[get]"
    }
}
```
### POST
#### request
* "content"-"use_id"が1の場合、targetユーザの特定にはUser.idを用います。そうでない場合、User.user_idを用います。
```
{"target": "/chat/join/other",
"authenticated": <authenticated>,
"id": <id>,
"token": <token>,
"content": {
    "use_id": <0 or 1>,
    "target_user_id": <user_id>,
    "target_group": <group_id>
    }
}
```
#### response
* エラー有りの場合
    * ログインしていない状態での/chat/join/otherへのpostは認められません。
    * 合致しない"id", "token"でのpostは認められません。
    * 存在しない"content"-"target_user_id"は認められません。
    * 存在しない"content"-"target_group"は認められません。
    * "content"-"target_group"にはpost元のユーザが参加していなければなりません。
    * すでにターゲットユーザが参加しているgroupを"content"-"target_group"には指定できません。
```
{"error": 1,
"content": {
    "not_authenticated": <0 or 1>,
    "invalid_verify": <0 or 1>,
    "invalid_user_id": <0 or 1>,
    "invalid_talk_id": <0 or 1>,
    "personal_chat": <0 or 1>,
    "user_not_joined": <0 or 1>,
    "already_joined": <0 or 1>
    }
}
```
* エラーなしの場合
```
{"error": 0,
"content": {
    "message": "seccess"
    }
}
```
