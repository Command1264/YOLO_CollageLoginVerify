import requests
import shutil

for i in range(100,1000):
    r = requests.get("https://auth2.cyut.edu.tw/User/VerificationCode?n=10%2F01%2F2024%2011%3A44%3A12", stream=True)
    if r.status_code == 200:
        print(f"{i}")
        with open(f"TracingData/image-{i}.png", 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f) 
    else:
        print(f"statusCode: {r.status_code}")
        exit()
    