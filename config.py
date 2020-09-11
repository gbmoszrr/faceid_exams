import os
class Config(object):
    #SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key_facerecognition'
    UPLOAD_FOLDER= './app/upload_folder/'
    THUMB_FOLDER = './app/static/photos/'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../db/exams.db'
    KEY = open('./cr/dbencr.key', 'rb').read()



