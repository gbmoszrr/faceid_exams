import requests
import json

url = "https://lambda-face-recognition.p.rapidapi.com/album"
headers = {
    'x-rapidapi-host': "lambda-face-recognition.p.rapidapi.com",
    'x-rapidapi-key': "b2e8ff53041404b788910fe6aaee1a907a6058176615a4f501df34209f9000f0",
    'content-type': "application/x-www-form-urlencoded"
    }
payload = "album=FUSERS"

response = requests.post(url, headers=headers, data=payload)
resp = json.loads(response.text)
print(resp)



# "album":"FUSERS"
# "msg":"Please put this in a safe place and remember it, you'll need it!"
# "albumkey":"b2e8ff53041404b788910fe6aaee1a907a6058176615a4f501df34209f9000f0"