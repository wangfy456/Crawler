import requests
from PIL import Image
from io import BytesIO
import pandas as pd
import time

class JeecgCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://boot3.jeecg.com/jeecgboot"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://boot3.jeecg.com/login"
        }

    # ...existing code...
    def get_captcha(self):
        """获取验证码图片和checkKey"""
        import time, random, string
        self.session.get("https://boot3.jeecg.com/login", headers=self.headers)
        t = str(int(time.time() * 1000))
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        check_key = t + rand_str
        captcha_url = f"{self.base_url}/sys/randomImage/{check_key}?_t={t}"
        response = self.session.get(captcha_url, headers=self.headers)
        try:
            data = response.json()
            base64_img = data.get("result", "")
            if base64_img.startswith("data:image"):
                import base64
                from PIL import Image
                from io import BytesIO
                img_str = base64_img.split(",")[1]
                img_data = base64.b64decode(img_str)
                img = Image.open(BytesIO(img_data))
                img.show()
                print("验证码已弹出，请输入验证码")
                return check_key
            else:
                print("未获取到有效的验证码图片数据")
                return None
        except Exception as e:
            print(f"验证码获取异常: {str(e)}")
            print("返回内容：", response.text[:200])
            return None

    def login(self, username, password, captcha, check_key):
        login_url = f"{self.base_url}/sys/login"
        login_data = {
            "username": username,
            "password": password,
            "captcha": captcha,
            "checkKey": check_key
        }
        response = self.session.post(login_url, headers=self.headers, json=login_data)
        result = response.json()
        if result.get("success"):
            print("登录成功！")
            token = result.get("result", {}).get("token")
            if token:
                self.headers["X-Access-Token"] = token
            return True
        else:
            print(f"登录失败: {result.get('message')}")
            return False

    def get_my_tasks(self):
        """获取所有任务办理中我的任务数据"""
        import pandas as pd
        all_records = []
        page_no = 1
        page_size = 10

        while True:
            params = {
                "column": "createTime",
                "order": "desc",
                "pageNo": page_no,
                "pageSize": page_size,
                "_t": int(time.time() * 1000)
            }
            tasks_url = f"{self.base_url}/act/task/list"
            response = self.session.get(tasks_url, headers=self.headers, params=params)
            try:
                data = response.json()
            except Exception:
                print("任务接口返回异常：", response.text[:200])
                break
            if data.get("success"):
                records = data.get("result", {}).get("records", [])
                if not records:
                    break
                all_records.extend(records)
                print(f"已获取第{page_no}页，共{len(records)}条")
                # 如果本页数量小于page_size，说明已经是最后一页
                if len(records) < page_size:
                    break
                page_no += 1
            else:
                print("任务接口返回失败：", data.get("message"))
                break

        if all_records:
            df = pd.DataFrame(all_records)
            df.to_excel("jeecg_my_tasks.xlsx", index=False)
            print(f"所有任务数据已保存到 jeecg_my_tasks.xlsx，共{len(all_records)}条")
        else:
            print("没有获取到任务数据")

def main():
    crawler = JeecgCrawler()
    check_key = crawler.get_captcha()
    if check_key:
        captcha = input("请输入验证码: ")
        if crawler.login("jeecg", "jeecg#123456", captcha, check_key):
            crawler.get_my_tasks()
        else:
            print("登录失败，程序退出")
    else:
        print("获取验证码失败，程序退出")

if __name__ == "__main__":
    main()