from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import Integer, String
from sqlalchemy.orm import relation
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

Base = declarative_base()

talk_group_relation_table = Table('talk_group_relation', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('talk_group_id', Integer, ForeignKey('talk_groups.id'))
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    friends = relation('Friend', order_by='Friend.id',
                         uselist=True, backref='users')
    talk_groups = relation("Talk_group", order_by="Talk_group.id",
            uselist=True, backref="users",
            secondary=talk_group_relation_table)
    
    def __repr__(self):
        return '<User(%d, %s)>' % (self.id, self.name)

class Friend(Base):
    __tablename__ = 'friends'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    friend_id = Column(Integer, nullable=False)

    def __repr__(self):
        return '<Friend(%d, %d, %d)>' % (self.id, self.user_id, self.friend_id)

class Talk_group(Base):
    __tablename__ = "talk_groups"
    id = Column(Integer, primary_key=True)
    content = relation("Content", order_by="Content.id",
            uselist=True, backref="talk_group")

    def __repr__(self):
        return '<Talk_group(%d)>' % (self.id)

class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True)
    talk_group_id = Column(Integer, ForeignKey("talk_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)

    def __repr__(self):
        return '<Contents(%d, %d, %s)>' % (self.id, self.user_id, self.text)




if __name__ == '__main__':
    engine = create_engine('sqlite://', echo=False)
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    user1 = User(name='User1', password="pass1")
    user2 = User(name='User2', password="pass2")
    user3 = User(name='User3', password="pass3")
    user1.friends = [Friend(friend_id=2), 
                        Friend(friend_id=3)]
    user2.friends = [Friend(friend_id=1), 
                        Friend(friend_id=3)]
    user3.friends = [Friend(friend_id=1), 
                        Friend(friend_id=2)]
    
    content1 = Content(user_id = 1, talk_group_id=1,
            text = "Hello! 01")
    content2 = Content(user_id = user2.id, talk_group_id=2,
            text = "Hello! 02")

    group1 = Talk_group()
    group2 = Talk_group()
    group1.content = [content1]
    group2.content = [content2]

    user1.talk_groups = [group1, group2]
    user2.talk_groups = [group1]
    user3.talk_groups = [group2]

    session.add(user1)
    session.add(user2)
    session.add(user3)
    session.commit()

    selected_user = session.query(User).first()
    print(selected_user)
    print(selected_user.friends)
    print(selected_user.talk_groups)
    print(selected_user.talk_groups[0].content)
    
    # add conversation
    new_user1_text = "a-, nannka ra-menn tabetai."
    new_talk_group_id = 1
    new_content = Content(user_id=user1.id, 
            talk_group_id=new_talk_group_id, text=new_user1_text)
    session.add(new_content)
    session.commit()
    
    print(selected_user.talk_groups[0].content)



