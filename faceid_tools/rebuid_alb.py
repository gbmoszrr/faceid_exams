import requests
import json

url = "https://lambda-face-recognition.p.rapidapi.com/album_rebuild"
querystring = {"album":"FUSERS","albumkey":"b2e8ff53041404b788910fe6aaee1a907a6058176615a4f501df34209f9000f0"}
headers = {
    'x-rapidapi-host': "lambda-face-recognition.p.rapidapi.com",
    'x-rapidapi-key': "00882e5b93msh86028921959febdp1b1876jsn5805e7355b02cd"
    }

response = requests.get(url, headers=headers, params=querystring)
print(response.text)