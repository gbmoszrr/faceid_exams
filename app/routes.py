from app import app
from flask import request, render_template, redirect, url_for,flash, session
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from app import login_manager
from flask_wtf import FlaskForm
from wtforms import StringField
from app.api_logic import execute_request, execute_train, rebuild_album, check_confidence
import json
from cryptography.fernet import Fernet

from PIL import Image
 
from app.models import db, User, Exams, Enrolment, Question, Photos, Answers
 

from werkzeug.utils import secure_filename
import os
import uuid
import config

import boto3
from botocore.exceptions import ClientError

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

f = Fernet(app.config['KEY'])


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class LoginForm(FlaskForm):
    username = StringField('Username')

@login_manager.user_loader
def user_loader(user_id):
    user = User.query.get(user_id)
    return user

@app.route('/', methods=['GET'])
def index():

    login_form = LoginForm()
   
    return render_template('index.html', title='Login', form=login_form, message="")


@app.route('/login/', methods=['POST'])
def user_login():
    #login_form = LoginForm()

    if request.method == 'POST':
        

        upload_folder = app.config.get('UPLOAD_FOLDER')
        current_folder = os.getcwd()
         
        file = request.files['file']
        image = Image.open(file)
        image_path = upload_folder + str(uuid.uuid4()) + '.jpg'
        image.save(image_path)

        json_obj = execute_request(image_path)
        flag = check_confidence(json_obj)


        #flag = True  #for testing purposes

        if flag:
            user_id = json_obj['photos'][0]['tags'][0]['uids'][0]['prediction']
            confidence = json_obj['photos'][0]['tags'][0]['uids'][0]['confidence']
            

            
 
            #Login manager
            
            user = User.query.filter_by(id=user_id).first()
 
            if user is None:
                redirect = '{ "redirect": "/"}'
                return redirect

            user.authenticated = True
            user.confidence = confidence
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            redirect = '{ "redirect": "/user/"}'
            return redirect

            #return render_template('admin_panel.html', user=user_id, confidence=confidence)
        else:
            error = '{ "error": "Your photo was not recognized as user photo. Please, try again."}'
            return error
    return render_template('home_page.html', title='Login', form=login_form, message="")




#Route for handling ADMIN pages ------------------------------------------------
# Route for handling the login page logic
@app.route('/admin_login/', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return redirect(url_for('/admin/home/'))
    return render_template('./admin/admin_login.html', error=error)






# Admin Routes-------------------------------
@app.route('/admin/')
def admin_home():
    error = None

    return render_template('./admin/admin_home.html', error=error)


	
@app.route('/admin/add/user/', methods=['GET', 'POST'])
def add_user():
    error = None
    template = './admin/admin_add_user.html'
 

    if request.method == 'POST':

        uploaded_files = request.files.getlist("file[]")
        print( uploaded_files)

        photo_files_os = []
        photo_files_web = []

        if 'file[]' not in request.files:
            error = 'No file part'
            return render_template(template, error=error)

         
        if len(uploaded_files) < 5:
            error = 'Please select at least 5 images'
            return render_template(template, error=error)

        for file in uploaded_files:

            if file.filename == '':
                error= 'No image selected for uploading'
                return render_template(template, error=error)

            if file and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + '.jpg' #secure_filename(file.filename)
                photo_files_web.append(filename)

                filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo_files_os.append(filename)

                image = Image.open(file)
                image.thumbnail((500,500))
 
                image.save(filename)
                #file.save(filename)
                print('upload_image filename: ' + filename)
                message = 'Image successfully uploaded and displayed'
                #return render_template('upload.html', filename=filename, message=message)
            else:
                error = 'Allowed image types are -> png, jpg, jpeg, gif'
                #return redirect(request.url, error=error)
                return render_template(template, error=error)

        

        if request.form['name'] != '' or len(request.form['name'])!=0:


            #Save thumbnail
            image = Image.open(photo_files_os[0])
            image.thumbnail((100,100))
            #rgb_im = image.convert('RGB')
            thumb_filename = str(uuid.uuid4()) + '.jpg'
            image.save(os.path.join(app.config['THUMB_FOLDER'], thumb_filename))

            name = request.form['name']
            name = f.encrypt(name.encode())

            email = request.form['email']
            email = f.encrypt(email.encode())

            

            new_user = User(name=name, email=email, photo=thumb_filename)
            db.session.add(new_user)
            db.session.commit()
            message = 'New user '+ request.form['name'] + ' has been added'
            #return redirect(url_for('/admin/list/users/',message=message))

            #add photo 
            # for photo_file in photo_files_web:
            #     new_photo = Photos(user_id = new_user.id, filename=photo_file)
            #     db.session.add(new_photo)
            #     db.session.commit()

            #Train faceID
            for photo_file in photo_files_os:
                response = execute_train(new_user.id, photo_file)
                if 'error' in response:
                    error = 'FaceID ' + response['error']
                    return render_template(template, error=error)


            if new_user.id > 2:
                error = rebuild_album()
                if error is not None:
                    return render_template(template, error=error)

            users = User.query.all()
            return render_template('./admin/admin_list_users.html', users=users, message=message, error=error)

            #error = 'Invalid Credentials. Please try again.'
  
    return render_template('./admin/admin_add_user.html', error=error)

@app.route('/admin/list/users/')
def list_users():
    error=None
    users = User.query.all()

    # Decrypt names
    for user in users:

        username =  user.name
        user.name  = f.decrypt(username.encode('utf-8')).decode('utf-8')

        email = user.email
        user.email = f.decrypt(email.encode('utf-8')).decode('utf-8')

 

    return render_template('./admin/admin_list_users.html', users=users, error=error)





@app.route('/admin/enrolment/user/<user_id>')
#@login_required
def user_enrolment(user_id):

  

    title = 'User enrolment'
    error=None
 

    sq = db.session.query(Enrolment.exam_id).filter(Enrolment.user_id == user_id).subquery()
    available_exams =  db.session.query(Exams).filter(Exams.id.notin_(sq)).all()

    enrolment = db.session.query(Enrolment, Exams).outerjoin(Exams, Enrolment.exam_id == Exams.id).filter(Enrolment.user_id == user_id).order_by(Enrolment.date.desc()).all()
 
 

    return render_template('./admin/admin_user_enroll.html', error=error, user_id=user_id,  enrolment=enrolment, available_exams=available_exams, title=title)




@app.route('/admin/delete/<user_id>/exam/<exam_id>')
def delete_enrolment(user_id,exam_id):
    error=None

    try:
        user_id = int(user_id)
        exam_id = int(exam_id)
    except ValueError as verr:
        error= 'Delete exception'
        
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

     
    for question in questions:

        question_id = question.id
         
        try:
            answer = Answers.query.filter(Answers.user_id==user_id).filter(Answers.question_id==question_id).one() #, Question.id==question_id
            db.session.delete(answer)
            db.session.commit()
        except ValueError as verr:
            error= 'Delete exception: answer not found'



    enroll = Enrolment.query.filter(Enrolment.user_id==user_id).filter(Enrolment.exam_id==exam_id).one()
    db.session.delete(enroll)
    db.session.commit()

 
    

    return render_template('./admin/admin_home.html', error=error)


@app.route('/admin/list/exams/')
def list_exams():
    error=None
    exams = Exams.query.all()

    return render_template('./admin/admin_list_exams.html', exams=exams, error=error)

@app.route('/admin/list/exam/<exam_id>')
def get_exam(exam_id):
    error=None
    exam = Exams.query.filter_by(id=exam_id).first()
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

    return render_template('./admin/admin_list_exam_by_id.html', exam=exam, questions=questions, error=error)


@app.route('/admin/key')
def get_key():
    error='Key written to /cr/dbencr.key'

 
    # key = Fernet.generate_key()
    # with open("./cr/dbencr.key", "wb") as key_file:
    #     key_file.write(key)
 
    return render_template('./admin/admin_home.html', error=error)

# End Admin Routes-------------------------------


#User routes---------------------------
@app.route('/user/')
#@login_required
def user_home():

    if current_user.is_authenticated:
        pass
 
    user_name = f.decrypt(current_user.name.encode('utf-8')).decode('utf-8') 
    user_id = current_user.id
    confidence = current_user.confidence
 

    title = 'Homepage'
    error=None
 

    sq = db.session.query(Enrolment.exam_id).filter(Enrolment.user_id == user_id).subquery()
    available_exams =  db.session.query(Exams).filter(Exams.id.notin_(sq)).all()

    enrolment = db.session.query(Enrolment, Exams).outerjoin(Exams, Enrolment.exam_id == Exams.id).filter(Enrolment.user_id == user_id).order_by(Enrolment.date.desc()).all()
 
 

    return render_template('./user/user_home.html', error=error, user_name = user_name, user_id=user_id, confidence=confidence, enrolment=enrolment, available_exams=available_exams, title=title)

 

@app.route('/user/<user_id>/enroll/<exam_id>', methods=['GET', 'POST'])
@login_required
def enrol_exam(user_id, exam_id):

    if request.method == 'POST':
        
        error=None
        message = ''

 
        for field_name in request.form:
            value = request.form[field_name]

            question_id = int(field_name)
            if type(question_id) == int and question_id < 1000 and value != '':
 
                try:
                    new_answer = Answers(user_id=user_id, question_id=question_id, answer=int(value))
                    db.session.add(new_answer)
                    db.session.commit()

                except Exception as e:
                    error = str(e.args[0])
                    break
                     
            else:
                error = 'Invalid question ID'

        

        try:
            new_enrollment = Enrolment(user_id=user_id, exam_id=exam_id, date = db.func.current_timestamp(), status='Passed')
            db.session.add(new_enrollment)
            db.session.commit()

            send_email(user_id, exam_id)

        except Exception as e:
            error += ' ' + str(e.args[0])
             
        if error == None:
            title = 'Exam #' + exam_id + ' has been completed'
            message = title
        else:
            title = error

 
        return render_template('./user/user_exam_completed.html',  message=message, error=error, title=title)

    else:
        title = 'Enroll Exam #'+ exam_id
        error=None

        try:
            exam = Exams.query.filter_by(id=exam_id).first()
            questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()
        except Exception as e:
            error = str(e.args[0])
            

        return render_template('./user/user_enroll_exam_by_id.html', exam=exam, questions=questions, user_id=user_id, exam_id=exam_id, error=error, title=title)





@app.route('/user/<user_id>/list/<exam_id>', methods=['GET'])
@login_required
def list_exam(user_id, exam_id):

        title = 'Answers for Exam #'+ exam_id
        error=None

        try:
 
             
            sq = db.session.query(Question.id).filter(Question.exam_id == exam_id).subquery()
            answers =  db.session.query(Answers).filter(Answers.question_id.in_(sq)).filter(Answers.user_id == user_id).order_by(Answers.question_id).all()

            questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

            exam = Exams.query.filter_by(id=exam_id).first()

            list_of_questions = []
            answer_str = 'Not defined'

            for answer in answers:

                for question in questions:
                    if question.id == answer.question_id:

                        title = question.title
                        if answer.answer == 1:
                            answer_str = question.option1
                        if answer.answer == 2:
                            answer_str = question.option2
                        if answer.answer == 3:
                            answer_str = question.option3
                        if answer.answer == 4:
                            answer_str = question.option4
                        if answer.answer == 5:
                            answer_str = question.option5


                tmp = { 'title': title, 
                        'answer_str': answer_str
                        }

                list_of_questions.append(tmp)

             
 
        except Exception as e:
            error = str(e.args[0])
            

        return render_template('./user/user_list_answers.html', exam=exam, list_of_questions=list_of_questions, user_id=user_id, exam_id=exam_id, error=error, title=title)

@app.route('/user/logout/')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/terms/')
def terms():
 
    return render_template('./terms.html') 


	
@app.route('/signup/', methods=['GET', 'POST'])
def user_signup():
    error = None
    message = ''
    template = './user_signup.html'
 

    if request.method == 'POST':

        uploaded_files = request.files.getlist("file[]")
        print( uploaded_files)

        photo_files_os = []
        photo_files_web = []

        if 'file[]' not in request.files:
            error = 'No file part'
            return render_template(template, error=error)

         
        if len(uploaded_files) < 5:
            error = 'Please select at least 5 images'
            return render_template(template, error=error)

        for file in uploaded_files:

            if file.filename == '':
                error= 'No image selected for uploading'
                return render_template(template, error=error)

            if file and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + '.jpg' #secure_filename(file.filename)
                photo_files_web.append(filename)

                filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo_files_os.append(filename)

                image = Image.open(file)
                image.thumbnail((500,500))
 
                image.save(filename)
                #file.save(filename)
                print('upload_image filename: ' + filename)
                message = 'Image successfully uploaded and displayed'
                #return render_template('upload.html', filename=filename, message=message)
            else:
                error = 'Allowed image types are -> png, jpg, jpeg, gif'
                #return redirect(request.url, error=error)
                return render_template(template, error=error)

        

        if request.form['email'] != '' or len(request.form['email'])!=0:

 
            name = request.form['name']
            email = request.form['email']

            #Save thumbnail
            image = Image.open(photo_files_os[0])
            image.thumbnail((100,100))
            #rgb_im = image.convert('RGB')
            thumb_filename = str(uuid.uuid4()) + '.jpg'
            image.save(os.path.join(app.config['THUMB_FOLDER'], thumb_filename))


            user = User.query.filter_by(email=email).first()
            
            if user:
                new_user_id = user.id
                message = 'New user '+ request.form['name'] + ' has been updated'
            else:            
                name = f.encrypt(name.encode())
                email = f.encrypt(email.encode())

                new_user = User(name=name, email=email, photo=thumb_filename)
                db.session.add(new_user)
                db.session.commit()
                new_user_id = new_user.id
            
                message = 'New user '+ request.form['name'] + ' has been added'

 
            
            #Train faceID
            for photo_file in photo_files_os:
                response = execute_train(new_user_id, photo_file)
                if 'error' in response:
                    error = 'FaceID ' + response['error']
                    return render_template(template, error=error)


            if new_user.id > 2:
                error = rebuild_album()
                if error is not None:
                    return render_template(template, error=error)

             
            return render_template('./sigup_result.html', message=message, error=error)

            #error = 'Invalid Credentials. Please try again.'
 

    return render_template('./user_signup.html', error=error)



def send_email(user_id, exam_id):
    
    error=None

    try:

        user = User.query.filter_by(id=user_id).first()

            
        sq = db.session.query(Question.id).filter(Question.exam_id == exam_id).subquery()
        answers =  db.session.query(Answers).filter(Answers.question_id.in_(sq)).filter(Answers.user_id == user_id).order_by(Answers.question_id).all()

        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

        exam = Exams.query.filter_by(id=exam_id).first()

        list_of_questions = []
        answer_str = 'Not defined'

        for answer in answers:

            for question in questions:
                if question.id == answer.question_id:

                    title = question.title
                    if answer.answer == 1:
                        answer_str = question.option1
                    if answer.answer == 2:
                        answer_str = question.option2
                    if answer.answer == 3:
                        answer_str = question.option3
                    if answer.answer == 4:
                        answer_str = question.option4
                    if answer.answer == 5:
                        answer_str = question.option5


            tmp = { 'title': title, 
                    'answer_str': answer_str
                    }

            list_of_questions.append(tmp)

            

    except Exception as e:
        error = str(e.args[0])


    #add to /.aws/credentials
    Access_key_ID = 'AKIA2OAGHLAMRQEHLPHQ'
    Secret_access_key = 'IJJS78CFkZA1mQlfAI8YjMRcPmbehgbXa8GpxhoE'


    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = "FaceID <openaiworld@gmail.com>"

    # Replace recipient@example.com with a "To" address. If your account 
    # is still in the sandbox, this address must be verified.
    #RECIPIENT = "sas.aitech@gmail.com"
    RECIPIENT = "gbmoszr1@gmail.com"

    # Specify a configuration set. If you do not want to use a configuration
    # set, comment the following variable, and the 
    # ConfigurationSetName=CONFIGURATION_SET argument below.
    #CONFIGURATION_SET = "ConfigSet"

    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "us-east-2"



    # The subject line for the email.
    SUBJECT = "New exam submission from " + user.name

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ''
    counter = 1
    for question in list_of_questions:

        BODY_TEXT += str(counter) + '. ' + question['title'] + '\r\n'
        BODY_TEXT += question['answer_str'] + '\r\n\r\n'

        counter += 1
                
 
    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
 
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            #ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])



def encrypt_srt():
    error=None
    users = User.query.all()


    for user in users:

        name = user.name 
        encrypted_name = f.encrypt(name.encode())

        email = user.email
        encrypted_email = f.encrypt(email.encode())

        

        print(user.name  + ' ', encrypted_name)
        print(user.email + ' ', encrypted_email)