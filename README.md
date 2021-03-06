# The exam portal with Face ID authentication method
         
FaceID application is Exam portal that provides intuitive and secure authentication enabled by camera to accurately map the geometry of user's face.

## Features
    • FaceID user authorizaton 
    • New user signup 
    • User login/logout s
    • Exams enrolment and results view
    • Modern user interface 
    • Admin section: add users, view exams and user answers

## Building Locally
To get started building this application locally, the application can be run by cloning the code from GitHub:
``` 
git clone https://github.com/gbmoszrr/faceid_exams
cd faceid_exams
``` 

Download the project dependencies from project root with:
``` 
pip3 install -r requirements.txt
``` 

To run FaceID application locally:

Add FLASK_APP environment variable
``` 
FLASK_APP=main.py
``` 
And run the application
``` 
flask run
``` 

FaceID application is running at: http://localhost:5000/ in your browser
