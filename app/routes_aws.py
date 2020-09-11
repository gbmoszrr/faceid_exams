from app import app
from flask import request, render_template, redirect, url_for,flash, session
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from app import login_manager
from flask_wtf import FlaskForm
from wtforms import StringField
from app.api_logic_aws import add_faces_to_collection, execute_request, delete_faces_from_collection
import json
from cryptography.fernet import Fernet
import time
from PIL import Image, ImageDraw
 
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

#Route for handling ADMIN pages ------------------------------------------------
# Route for handling the login page logic
@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            user = User.query.filter_by(id=1).one()
            login_user(user, remember=True)
            return redirect('/admin/')
    return render_template('./admin/admin_login.html', error=error)


# Admin Routes-------------------------------
@app.route('/admin/')
@login_required
def admin_home():
    error = None
    if current_user.role != 'admin':
        return redirect('/admin/login/')

    return render_template('./admin/admin_home.html', error=error)

	
@app.route('/admin/add/user/', methods=['GET', 'POST'])
@login_required
def add_user():
 
    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')

    error = None
    template = './admin/admin_add_user.html'


    if request.method == 'POST':

        uploaded_files = request.files.getlist("file[]")
        print( uploaded_files)

        photo_files_os = []
        photo_files_web = []

        if 'file[]' not in request.files:
            error = 'Please select one image'
            return render_template(template, error=error)

         
        if len(uploaded_files) != 1:
            error = 'Please select one image'
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
                print('upload_image filename: ' + filename)

            else:
                error = 'Allowed image types are -> png, jpg, jpeg, gif'
                #return redirect(request.url, error=error)
                return render_template(template, error=error)
        

        if request.form['email'] != '' or len(request.form['email'])!=0:

            # Check if user image exists in album
            json_obj, response_error = execute_request(photo_files_os[0])
             

            if response_error:
    
                error = response_error
                return render_template(template, error=error)

            if len(json_obj) > 0:
                error = 'User already exists'
                return render_template(template, error=error)
 
 
            name = str(request.form['name'])
            email = str(request.form['email'])

            print('New signup try: email: ' + email + ' name: '+ name)


            # = User.query.filter(User.email==email).first()
            users = User.query.all()
            user_match_id = None

            for user in users:

                user_email = f.decrypt(user.email).decode('utf-8')
                if user_email == email:
                    user_match_id = user.id
                    break

            if user_match_id:
                new_user_id = user_match_id
                message = 'User '+ name + ' ID: ' + str(user_match_id) + ' is already registered'
 
            else:  

                name = f.encrypt(name.encode('utf-8'))
                email = f.encrypt(email.encode('utf-8'))    

                #Save thumbnail
                image = Image.open(photo_files_os[0])
                image.thumbnail((100,100))
                #rgb_im = image.convert('RGB')
                thumb_filename = str(uuid.uuid4()) + '.jpg'
                image.save(os.path.join(app.config['THUMB_FOLDER'], thumb_filename))      

                new_user = User(name=name, email=email, photo=thumb_filename, role='user')
                db.session.add(new_user)
                db.session.commit()
                new_user_id = new_user.id

                response_face_id = add_faces_to_collection('faceidexams', photo_files_os[0], 'users2', new_user_id)

                if response_face_id is not None:
                    user = User.query.filter_by(id=new_user_id).first()
                    user.faceid = response_face_id
                    db.session.add(user)
                    db.session.commit()
                    message = 'New user '+ request.form['name'] + ', ID:' + str(new_user_id) + ' has been added'

                    print(message)
                else:
                    
                    error = 'Faceid API error: ' + request.form['name'] + ', ID:' + str(new_user_id)
                    print(error)
                    return render_template(template, error=error)

        
            return redirect('/admin/list/users/')

    return render_template('./admin/admin_add_user.html', error=error)


@app.route('/admin/list/users/')
def list_users():


    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')

    error=None
 
    users = User.query.filter_by(deleted=False).all()

    # Decrypt names
    for user in users:

        username =  user.name
        user.name  = f.decrypt(username).decode('utf-8')

        email = user.email
        user.email = f.decrypt(email).decode('utf-8')


    return render_template('./admin/admin_list_users.html', users=users, error=error)


@app.route('/admin/enrolment/user/<user_id>')
@login_required
def user_enrolment(user_id):

    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')  

    title = 'User enrolment'
    error=None
 
    sq = db.session.query(Enrolment.exam_id).filter(Enrolment.user_id == user_id).subquery()
    available_exams =  db.session.query(Exams).filter(Exams.id.notin_(sq)).all()

    enrolment = db.session.query(Enrolment, Exams).outerjoin(Exams, Enrolment.exam_id == Exams.id).filter(Enrolment.user_id == user_id).order_by(Enrolment.date.desc()).all()

    return render_template('./admin/admin_user_enroll.html', error=error, user_id=user_id,  enrolment=enrolment, available_exams=available_exams, title=title)


@app.route('/admin/delete/<user_id>/exam/<exam_id>')
@login_required
def delete_enrolment(user_id,exam_id):

    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')
    
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
@login_required
def list_exams():

    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')
    error=None
    exams = Exams.query.all()

    return render_template('./admin/admin_list_exams.html', exams=exams, error=error)


@app.route('/admin/list/exam/<exam_id>')
@login_required
def get_exam(exam_id):
    if not hasattr(current_user, 'role'):
        return redirect('/admin/login/')

    if current_user.role != 'admin':
        return redirect('/admin/login/')
    error=None
    exam = Exams.query.filter_by(id=exam_id).first()
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.id).all()

    return render_template('./admin/admin_list_exam_by_id.html', exam=exam, questions=questions, error=error)


# @app.route('/admin/key')
# def get_key():
#     error='Key written to /cr/dbencr.key'

 
#     # key = Fernet.generate_key()
#     # with open("./cr/dbencr.key", "wb") as key_file:
#     #     key_file.write(key)
 
#     return render_template('./admin/admin_home.html', error=error)

# End Admin Routes-------------------------------


#User routes---------------------------
@app.route('/user/')
@login_required
def user_home():

    if current_user.is_authenticated:
        pass
 
    user_name = f.decrypt(current_user.name).decode('utf-8') 
    user_id = current_user.id
    confidence = current_user.confidence
    timing = current_user.timing
 
    title = 'Homepage'
    error=None
 
    sq = db.session.query(Enrolment.exam_id).filter(Enrolment.user_id == user_id).subquery()
    available_exams =  db.session.query(Exams).filter(Exams.id.notin_(sq)).all()

    enrolment = db.session.query(Enrolment, Exams).outerjoin(Exams, Enrolment.exam_id == Exams.id).filter(Enrolment.user_id == user_id).order_by(Enrolment.date.desc()).all()
 
    return render_template('./user/user_home.html', error=error, user_name = user_name, user_id=user_id, confidence=confidence, timing =timing, enrolment=enrolment, available_exams=available_exams, title=title)


@app.route('/login/', methods=['POST'])
def user_login():
    #login_form = LoginForm()
 
    if request.method == 'POST':

        print('Login request received')
        

        upload_folder = app.config.get('UPLOAD_FOLDER')
        current_folder = os.getcwd()
         
        file = request.files['file']
        image = Image.open(file)
        image_path = upload_folder + str(uuid.uuid4()) + '.jpg'
        image.save(image_path)

        print('Uploading image')

        # Record recognition time
        start = time.time()

        json_obj, response_error = execute_request(image_path)
        end = time.time()

        if response_error:
 
            error = '{ "error": "' + response_error + '"}'
            return error

        if len(json_obj) > 0:
            flag = True
        else:
            flag = False

        image.save(image_path)

        #flag = True  #for testing purposes

        if flag:
            faceid = json_obj['faceid']
            confidence = '{:.2f}%'.format(json_obj['confidence'])

            # Draw bounding box and save image
            # x_center = json_obj['photos'][0]['tags'][0]['center']['x']
            # y_center = json_obj['photos'][0]['tags'][0]['center']['y']
            # w = json_obj['photos'][0]['tags'][0]['width']
            # h = json_obj['photos'][0]['tags'][0]['height']
            # shape = [ (x_center - int(w/2), y_center - int(h/2)), (w + int(w/2), h + int(w/2))]
            # draw = ImageDraw.Draw(image) 
            # draw.rectangle(shape, fill = None, outline ="red") 
            
            #Login manager
            
            user = User.query.filter_by(faceid=faceid).first()
 
            if user is None:
                redirect = '{ "redirect": "/"}'
                return redirect

            user.authenticated = True
            user.confidence = confidence
            timing = '{:.4f}'.format(end - start)
            user.timing = timing
            user.errors = 0
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)

            message = 'User ID:' + str(user.id) + ' has been authenticated'
            print(message)
            redirect = '{ "redirect": "/user/"}'
            return redirect

            #return render_template('admin_panel.html', user=user_id, confidence=confidence)
        else:
            error = '{ "error": "Your photo was not recognized as user photo. Please, try again."}'
            return error
    return render_template('home_page.html', title='Login', form=login_form, message="")


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

    message = 'User ID:' + str(current_user.id) + ' has been logged out'
    print(message)

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
            error = 'Please select one image'
            return render_template(template, error=error)

         
        if len(uploaded_files) != 1:
            error = 'Please select one image'
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
                print('upload_image filename: ' + filename)

            else:
                error = 'Allowed image types are -> png, jpg, jpeg, gif'
                #return redirect(request.url, error=error)
                return render_template(template, error=error)
        

        if request.form['email'] != '' or len(request.form['email'])!=0:

            # Check if user image exists in album
            json_obj, response_error = execute_request(photo_files_os[0])
             

            if response_error:
    
                error = response_error
                return render_template(template, error=error)

            if len(json_obj) > 0:
                error = 'User already exists'
                return render_template(template, error=error)
 
 
            name = str(request.form['name'])
            email = str(request.form['email'])

            print('New signup try: email: ' + email + ' name: '+ name)


            # = User.query.filter(User.email==email).first()
            users = User.query.all()
            user_match_id = None

            for user in users:

                user_email = f.decrypt(user.email).decode('utf-8')
                if user_email == email:
                    user_match_id = user.id
                    break

            if user_match_id:
                new_user_id = user_match_id
                message = 'User '+ name + ' ID: ' + str(user_match_id) + ' is already registered'
 
            else:  

                name = f.encrypt(name.encode('utf-8'))
                email = f.encrypt(email.encode('utf-8'))    

                #Save thumbnail
                image = Image.open(photo_files_os[0])
                image.thumbnail((100,100))
                #rgb_im = image.convert('RGB')
                thumb_filename = str(uuid.uuid4()) + '.jpg'
                image.save(os.path.join(app.config['THUMB_FOLDER'], thumb_filename))      

                new_user = User(name=name, email=email, photo=thumb_filename, role='user')
                db.session.add(new_user)
                db.session.commit()
                new_user_id = new_user.id

                response_face_id = add_faces_to_collection('faceidexams', photo_files_os[0], 'users2', new_user_id)

                if response_face_id is not None:
                    user = User.query.filter_by(id=new_user_id).first()
                    user.faceid = response_face_id
                    db.session.add(user)
                    db.session.commit()
                    message = 'New user '+ request.form['name'] + ', ID:' + str(new_user_id) + ' has been added'

                    print(message)
                else:
                    
                    error = 'Faceid API error: ' + request.form['name'] + ', ID:' + str(new_user_id)
                    print(error)
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
    SENDER = "FaceID <openaiworld@gmail.com>"
    RECIPIENT = "gbmoszr1@gmail.com"

    # Specify a configuration set. If you do not want to use a configuration
    # set, comment the following variable, and the 
    # ConfigurationSetName=CONFIGURATION_SET argument below.
    #CONFIGURATION_SET = "ConfigSet"

    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "us-east-2"

    # The subject line for the email.
    SUBJECT = "New exam submission from " + f.decrypt(user.name).decode('utf-8')

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


@app.route('/admin/delete/user/<user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect('/admin/login/')
    
    error=None

    try:
        user_id = int(user_id)
    except ValueError as verr:
        error= 'Delete exception'
        
    user = User.query.filter_by(id=user_id).first()

    #Delete user from AWS account
    faces=[]
    faces.append(user.faceid)
    response = delete_faces_from_collection(faces)

    if response > 0:
        message = 'Image of user ID:' + str(user_id) + ' has been deleted'

        print(message)

    else:
        error = 'No faceid found. User image was not deleted'
        print(error)

    user.deleted = True
    #user.authenticated = False
    db.session.add(user)
    db.session.commit()
    message = 'User ID:' + str(user_id) + ' has been deleted'


    return redirect('/admin/list/users/')


@app.route('/user/status/',methods=['POST'])
@login_required
def user_status():
    print('Processing status')
    print('Current user: ', current_user)
    status_message = '<span style="color: red">' + str(time.strftime("%H:%M:%S", time.gmtime())) + ' User was not recognized or no user ' + '</span>'
    
    upload_folder = app.config.get('UPLOAD_FOLDER')
    current_folder = os.getcwd()
        
    file = request.files['file']
    image = Image.open(file)
    image_path = upload_folder + str(uuid.uuid4()) + '.jpg'
    image.save(image_path)

    print('Uploading image')

    # Record recognition time
    start = time.time()

    json_obj, response_error = execute_request(image_path)
    end = time.time()

    if response_error:

        status_message = '<span style="color: red">' + str(time.strftime("%H:%M:%S", time.gmtime())) + ' Error: User was not recognized or no user ' + '</span>'

    if len(json_obj) > 0:
        flag = True
    else:
        flag = False

    

    #flag = True

    if flag:
        faceid = json_obj['faceid']
        confidence = '{:.2f}%'.format(json_obj['confidence'])

        if current_user.faceid == faceid :
            status_message = str(time.strftime("%H:%M:%S", time.gmtime())) + ' User: ' + str(f.decrypt(current_user.name).decode('utf-8')) + ' Conf: ' + confidence
        else:
            status_message = '<span style="color: red">' + str(time.strftime("%H:%M:%S", time.gmtime())) + ' User was not recognized ' + '</span>'

    else:
        user = current_user

        if current_user.errors == 2:
            user.errors = 0
            db.session.add(user)
            db.session.commit()
            status_message = 'User ID:' + str(current_user.id) + ' has been logged out'
            print(status_message)
            logout_user()

        else:
            user.errors += 1
            db.session.add(user)
            db.session.commit()

  
    return status_message