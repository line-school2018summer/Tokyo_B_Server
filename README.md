# Tokyo_B_server
Server Side repository of Tokyo B Group


## DB仕様

User
- id
- user_id
- name
- password
- token
- friends
- stalker
- talk_groups

Talk_group
- id
- name
- users
- content

Content
- id
- talk_group_id
- talk_group
- user_id
- type
- content

