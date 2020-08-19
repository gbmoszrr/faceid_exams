from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, ForeignKey
engine = create_engine('sqlite:////home/ubuntu/faceid_exam/db/exams.db', echo=True)

meta=MetaData()
user = Table('user', meta, 
        Column('id', Integer, primary_key=True), 
        Column('name', String(80)), 
        Column('email', String(80)), 
        Column('photo', String(120)), 
        Column('authenticated',Boolean)
        )

# exams = Table('exams', meta, 
#         Column('id', Integer, primary_key=True), 
#         Column('title', String(80)), 
#         )

# question = Table('question', meta, 
#         Column('id', Integer, primary_key=True), 
#         Column('title', String(80)),
#         Column('option1', String(80)),
#         Column('option2', String(80)),
#         Column('option3', String(80)),
#         Column('option4', String(80)),
#         Column('option5', String(80)),
#         Column('exam_id', ForeignKey('exams.id')), 
#         )


# enrolment = Table('enrolment', meta,    
#     Column('id', Integer(), primary_key=True),    
#     Column('user_id', ForeignKey('user.id')),    
#     Column('exam_id', ForeignKey('exams.id')),    
 
#     )

# photos = Table('photos', meta,    
#     Column('id', Integer(), primary_key=True),    
#     Column('user_id', ForeignKey('user.id')),    
#     Column('filename', String(80)),   
 
#     )
 
 
meta.create_all(engine)
