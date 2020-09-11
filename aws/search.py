import boto3
import os

if __name__ == "__main__":

    bucket='faceidexams'
    collectionId='users1'
    fileName='/home/andrew/ai/upwork_clients/GB/faceid_exams_aws/app/upload_folder/649dc0e8-d4aa-495c-b1db-b4f21e1b25d2.jpg'
    threshold = 70
    maxFaces=2
    S3_REGION = 'us-east-2'

    s3_client = boto3.client('s3', region_name=S3_REGION)


    filename = os.path.basename(fileName)
    s3_file = filename

    try:
        s3_client.upload_file(fileName, bucket, s3_file)
        s3_error = "Upload Successful"
         
    except FileNotFoundError:
        s3_error = 'The file was not found'
         
    except NoCredentialsError:
        s3_error = 'Credentials not available'

    print(s3_error)


    client=boto3.client('rekognition',region_name=S3_REGION)

  
    response=client.search_faces_by_image(CollectionId=collectionId,
                                Image={'S3Object':{'Bucket':bucket,'Name':s3_file}},
                                FaceMatchThreshold=threshold,
                                MaxFaces=maxFaces)

                                
    faceMatches=response['FaceMatches']
    print ('Matching faces')
    for match in faceMatches:
            print ('FaceId:' + match['Face']['FaceId'])
            print ('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            print