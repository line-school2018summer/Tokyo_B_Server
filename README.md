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


~~~

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
       
~~~
