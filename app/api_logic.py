import json, requests, subprocess, shlex
import requests
import config

def execute_request(image_path):
    bashCommand = '''curl --request POST --url https://lambda-face-recognition.p.rapidapi.com/recognize 
    --header 'content-type: multipart/form-data' 
    --header 'x-rapidapi-host: lambda-face-recognition.p.rapidapi.com' 
    --header 'x-rapidapi-key: 00882e5b93msh86028921959febdp1b1876jsn5805e7355b02' 
    --form albumkey=3310cdaa4c5906dcac7f8c62482d4302279e738a2efb610ce82b7ec29495233d
    --form album=USERS1 --form files=@''' + image_path

    args = shlex.split(bashCommand)
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, error = process.communicate()
    json_obj = json.loads(output)
    print(json_obj)
    return json_obj

def check_confidence(json_obj):
    if json_obj['status'] == 'success':
        if len(json_obj['photos'][0]['tags']) == 0:
            return False


        confidence = 0.0

        try: 
            confidence = json_obj['photos'][0]['tags'][0]['uids'][0]['confidence']
        except Exception as e:
            error = str(e.args[0]) 
        
        flag = False
        if confidence > 0.75:
            flag = True
        return flag



def execute_train(user_id, image_path):
    bashCommand = '''curl --request POST --url https://lambda-face-recognition.p.rapidapi.com/album_train 
    --header 'content-type: multipart/form-data' 
    --header 'x-rapidapi-host: lambda-face-recognition.p.rapidapi.com' 
    --header 'x-rapidapi-key: 00882e5b93msh86028921959febdp1b1876jsn5805e7355b02'
    --form entryid=''' + str(user_id) + '''
    --form albumkey=3310cdaa4c5906dcac7f8c62482d4302279e738a2efb610ce82b7ec29495233d
    --form album=USERS1 --form files=@'''  + image_path

 
    args = shlex.split(bashCommand)
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, error = process.communicate()
    if len(output) < 30:
        error = {'error':'Connection error'}
        return error
    json_obj = json.loads(output)
    print(json_obj)
    return json_obj


def rebuild_album():

    error = None
    bashCommand = '''curl --request POST --url https://lambda-face-recognition.p.rapidapi.com/album_rebuild 
    --header 'content-type: multipart/form-data' 
    --header 'x-rapidapi-host: lambda-face-recognition.p.rapidapi.com' 
    --header 'x-rapidapi-key: 00882e5b93msh86028921959febdp1b1876jsn5805e7355b02'
    --form albumkey=3310cdaa4c5906dcac7f8c62482d4302279e738a2efb610ce82b7ec29495233d
    --form album=USERS1'''
 
    args = shlex.split(bashCommand)
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    output, error = process.communicate()
    data = json.loads(output)
    if 'error' in data:
        error = {'error': data['error']}
        return error


    return error
