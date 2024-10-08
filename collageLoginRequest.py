import requests
from bs4 import BeautifulSoup
import re, json, os


class CYUTLogin():
    cookies = {}
    domain = "https://auth2.cyut.edu.tw"
    headers = {
        # 'Sec-Ch-Ua': '"Chromium";v="129", "Not=A?Brand";v="8"',
        # 'Sec-Ch-Ua-Mobile': '?0',
        # 'Sec-Ch-Ua-Platform': '"Windows"',
        # 'Accept-Language': 'zh-TW,zh;q=0.9',
        # 'Upgrade-Insecure-Requests': '1',
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.71 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        # 'Sec-Fetch-Site': 'none',
        # 'Sec-Fetch-Mode': 'navigate',
        # 'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    jsonFilePath = f"./cyutLoginCookies.json"

    def __init__(self):
        self.loadCookies()
        url = f"{self.domain}/User/Login"
        response = requests.get(
            url,
            headers = self.headers,
            cookies = self.cookies
        )

        status_code = response.status_code
        if (not re.match("[23][0-9]{2}", str(status_code))):
            exit(f"status_code: {status_code}")

        cookies = response.cookies.get_dict()
        self.cookies.update(cookies)
        print(f"Cookies: {self.cookies}")

        htmlBS = BeautifulSoup(response.text, "html.parser")
        print(f"{self.domain}{htmlBS.img['src']}")
        pass

    def saveCookies(self):
        with open(self.jsonFilePath, "w") as file:
            file.write(json.dumps(self.cookies, indent = 4))

    def loadCookies(self):
        if (not os.path.isfile(self.jsonFilePath)): return
        with open(self.jsonFilePath, "r") as file:
            self.cookies = json.load(fp = file)

cyutLogin = CYUTLogin()
cyutLogin.saveCookies()










# url = "https://auth2.cyut.edu.tw/User/Login"
# cookies = {
#     'ASP.NET_SessionId': 'wikbf5235xhpviynn3rtr3re',
#     '__RequestVerificationToken': 'yJSnl57EH_NaSpM9horPdw3NCXLVAyUJvoHDyGp4dS18Nx8ONEGaBDak5mrIsT36vSMHj_HYWdV-QuLMydmifSCplyzWzr6Z3tmNZY3S6jM1'
# }
# headers = {
#     'Content-Type': 'application/x-www-form-urlencoded',
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.71 Safari/537.36',
#     'Accept-Language': 'zh-TW,zh;q=0.9',
#     'Referer': 'https://auth2.cyut.edu.tw/User/Login',
#     'Origin': 'https://auth2.cyut.edu.tw'
# }
# data = {
#     '__RequestVerificationToken': 'haVd37IGH5Nkgb_fowm-1fphnUWxGuS4MekZebcaarkRKsk5Eaa2VTH8nCEQ8wgcqOhYXv7Y80bBXZnyAxQ5X6jwlsyiBl2Jv_Qgt6ep5aI1',
#     'ReturnUrl': '',
#     'Account': 's11127028',
#     'Password': 'Margaret20070922~',
#     'VerificationCode': '6879'
# }

# response = requests.post(url, cookies=cookies, headers=headers, data=data)

# print(response.status_code)
# print(response.headers)
# print(response.text)