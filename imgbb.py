import requests
import os, dotenv, json

dotenv.load_dotenv()
api_key = os.getenv("imgbb_api_key")

class ImgBB:
    def upload_file(url=None):
        res = requests.post("https://api.imgbb.com/1/upload", data={"image": url}, params={"key":api_key})
        return json.loads(res.content)
