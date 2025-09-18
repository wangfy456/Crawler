import requests
from PIL import Image
from io import BytesIO
import pandas as pd
import time

session = requests.Session()
session.cookies.set("PHPSESSID", "027f406ba3eda3aef162a62ea707f3f6")
session.cookies.set("expires", "Wed, 17 Sep 2025 06:36:12 GMT")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0.0.0 Safari/537.36",
    "Referer": "https://www.gouguoa.com/adm/official/datalist",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "X-Requested-With": "XMLHttpRequest"
}

url = "https://www.gouguoa.com/adm/official/datalist?page=1&limit=20"
response = session.get(url, headers=headers)
print(response.text)

class GouguoaCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.gouguoa.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/login"
        }
        self.uuid = None

    def get_captcha(self):
        """获取验证码图片和uuid"""
        # 先访问登录页获取cookie
        self.session.get(f"{self.base_url}/login", headers=self.headers)
        # 生成uuid（实际项目请用抓包获得真实uuid参数）
        self.uuid = str(int(time.time() * 1000))
        captcha_url = f"{self.base_url}/captcha?uuid={self.uuid}"
        response = self.session.get(captcha_url, headers=self.headers)
        if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image"):
            img = Image.open(BytesIO(response.content))
            img.show()
            print("验证码已弹出，请输入验证码")
            return True
        else:
            print("验证码获取失败，返回内容：", response.text[:200])
            return False

    def login(self, username, password, captcha):
        login_url = f"{self.base_url}/home/login/login_submit"
        login_data = {
            "username": username,
            "password": password,
            "captcha": captcha,
            "uuid": self.uuid
        }
        headers = {
            **self.headers,
            "Content-Type": "application/json"
        }
        response = self.session.post(login_url, headers=headers, json=login_data)
        result = response.json()
        print("登录接口返回：", result)
        if result.get("msg") == "登录成功":
            print("登录成功！")
            return True
        else:
            print(f"登录失败: {result.get('msg', '未知错误')}")
            return False

    def get_documents(self):
        """获取公文管理-公文列表内容"""
        documents_url = f"{self.base_url}/adm/official/datalist"
        params = {
            "page": 1,
            "limit": 20
        }
        # 只用 session，不加 Authorization
        response = self.session.get(documents_url, headers=self.headers, params=params)
        try:
            data = response.json()
        except Exception:
            print("公文列表接口返回异常：", response.text[:200])
            return
        if data.get("code") == 0:
            records = data.get("data", {}).get("list", [])
            if records:
                import pandas as pd
                df = pd.DataFrame(records)
                df.to_excel("gouguoa_documents.xlsx", index=False)
                print("公文数据已保存到 gouguoa_documents.xlsx")
            else:
                print("没有获取到公文数据")
        else:
            print("公文列表接口返回失败：", data.get("msg", "未知错误"))

def main():
    crawler = GouguoaCrawler()
    if crawler.get_captcha():
        username = input("请输入用户名: ")
        password = input("请输入密码: ")
        captcha = input("请输入验证码: ")
        if crawler.login(username, password, captcha):
            crawler.get_documents()
        else:
            print("登录失败，程序退出")
    else:
        print("获取验证码失败，程序退出")

if __name__ == "__main__":
    main()