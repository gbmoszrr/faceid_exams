import json, requests, subprocess, shlex
import requests
import boto3
from boto3 import Session
import os
from PIL import Image, ImageDraw

TRESHOLD = 95
BUCKET='faceidexams'
COLLECTION='users2'
S3_REGION = 'us-east-2'

def execute_request(image_path):

    error = None
    maxFaces=2
 
    s3_client = boto3.client('s3', region_name=S3_REGION)
  
    s3_file = os.path.basename(image_path)

    try:
        s3_client.upload_file(image_path, BUCKET, s3_file)
        s3_error = "Upload Successful"
         
    except FileNotFoundError:
        s3_error = 'The file was not found'
         
    except NoCredentialsError:
        s3_error = 'Credentials not available'

    print(s3_error)
    json_obj = {}

    client=boto3.client('rekognition',region_name=S3_REGION)

    try:
        response=client.search_faces_by_image(CollectionId=COLLECTION,
                                    Image={'S3Object':{'Bucket':BUCKET,'Name':s3_file}},
                                    FaceMatchThreshold=TRESHOLD,
                                    MaxFaces=maxFaces)

    except Exception as e:
        print(e)
        error = str(e.args[0])

    if error is None:                                
        faceMatches=response['FaceMatches']
        print ('Matching faces')
        
        for match in faceMatches:
            if match['Similarity'] > TRESHOLD:
                json_obj['faceid'] = match['Face']['FaceId']
                json_obj['confidence'] = match['Similarity']
                json_obj['location'] = ''

                print ('FaceId:' + match['Face']['FaceId'])
                print ('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            else:
                error = '{ "error": "Your photo was not recognized as user photo. Please, try again."}'
                print('User was not recognized')

        if len(faceMatches) == 0:
            print('No faces matched')


    return json_obj, error
 
def add_faces_to_collection(bucket,photo,collection_id, user_id):

    s3_client = boto3.client('s3', region_name=S3_REGION)


    filename = os.path.basename(photo)
    s3_file = filename

    try:
        s3_client.upload_file(photo, bucket, s3_file)
        s3_error = "Upload Successful"
         
    except FileNotFoundError:
        s3_error = 'The file was not found'
         
    except NoCredentialsError:
        s3_error = 'Credentials not available'
    
    client=boto3.client('rekognition')

    response=client.index_faces(CollectionId=collection_id,
                                Image={'S3Object':{'Bucket':bucket,'Name':s3_file}},
                                ExternalImageId=s3_file,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])

    print ('Results for ' + photo) 	
    print('Faces indexed:')			

    faceid_reply = None			
    for faceRecord in response['FaceRecords']:
        #if faceRecord['Face']['FaceId'] == user_str:
        faceid_reply = faceRecord['Face']['FaceId']
        print('  Face ID: ' + faceRecord['Face']['FaceId'])
        print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))
         
        source_img = Image.open(photo).convert("RGB")
        width, height = source_img.size
        h = int(faceRecord['FaceDetail']['BoundingBox']['Height'] * height)
        w = int(faceRecord['FaceDetail']['BoundingBox']['Width'] * width)
        left = int(faceRecord['FaceDetail']['BoundingBox']['Left'] * width)
        top = int(faceRecord['FaceDetail']['BoundingBox']['Top'] * height)
         
        shape = [ (left, top), (left + w, top +h)]

        
        draw = ImageDraw.Draw(source_img) 
        draw.rectangle(shape, fill = None, outline ="red")
        source_img.save('/home/andrew/ai/upwork_clients/GB/Pictures/bbox_aws.jpg')

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)
    return faceid_reply



def delete_faces_from_collection(faces):

    client=boto3.client('rekognition')

    response=client.delete_faces(CollectionId=COLLECTION, FaceIds=faces)
    
    print(str(len(response['DeletedFaces'])) + ' faces deleted:') 							
    for faceId in response['DeletedFaces']:
         print (faceId)
    return len(response['DeletedFaces'])