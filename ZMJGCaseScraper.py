import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import os
import re
from urllib.parse import urljoin


class ZMJGCaseScraper:
    def __init__(self, username, password):
        self.base_url = "http://zmjg.zm.sc.yc"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.is_logged_in = False

        # 创建保存案件的目录
        self.output_dir = "案件数据"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_page(self, url, data=None, method='GET'):
        """获取页面内容"""
        try:
            print(f"正在访问: {url}")
            if method.upper() == 'POST':
                response = self.session.post(url, data=data, timeout=15)
            else:
                response = self.session.get(url, timeout=15)

            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return None

    def login(self):
        """登录系统"""
        print("正在尝试登录...")

        # 首先访问主页获取登录表单
        soup = self.get_page(self.base_url)
        if not soup:
            print("无法访问主页")
            return False

        # 查找登录表单
        login_form = soup.find('form')
        if not login_form:
            print("未找到登录表单")
            return False

        # 获取表单action
        login_url = login_form.get('action')
        if login_url:
            login_url = urljoin(self.base_url, login_url)
        else:
            # 常见的登录URL
            possible_login_urls = [
                f"{self.base_url}/login",
                f"{self.base_url}/user/login",
                f"{self.base_url}/admin/login",
                f"{self.base_url}/index.php/login"
            ]
            login_url = possible_login_urls[0]

        # 准备登录数据
        login_data = {
            'username': self.username,
            'password': self.password,
            'user': self.username,
            'pass': self.password,
            'login': '登录',
            'submit': '登录'
        }

        # 查找表单中的具体字段名
        username_field = login_form.find('input', {'type': 'text'}) or login_form.find('input', {
            'name': re.compile(r'user|name', re.I)})
        password_field = login_form.find('input', {'type': 'password'}) or login_form.find('input', {
            'name': re.compile(r'pass|pwd', re.I)})

        if username_field and username_field.get('name'):
            login_data[username_field['name']] = self.username
        if password_field and password_field.get('name'):
            login_data[password_field['name']] = self.password

        # 查找隐藏字段（如CSRF token）
        hidden_fields = login_form.find_all('input', {'type': 'hidden'})
        for field in hidden_fields:
            if field.get('name') and field.get('value'):
                login_data[field['name']] = field['value']

        # 执行登录
        login_response = self.get_page(login_url, data=login_data, method='POST')

        if login_response:
            # 检查是否登录成功
            if '登录' not in login_response.get_text() or '案件' in login_response.get_text():
                print("登录成功！")
                self.is_logged_in = True
                return True
            else:
                print("登录失败，请检查用户名和密码")
                return False
        else:
            print("登录请求失败")
            return False

    def get_case_list_url(self):
        """获取案件列表页面URL"""
        # 访问主页查找案件菜单
        soup = self.get_page(self.base_url)
        if not soup:
            return None

        # 查找案件相关的链接
        case_links = []
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().strip()
            if '案件' in link_text:
                case_links.append(urljoin(self.base_url, link['href']))

        if case_links:
            return case_links[0]

        # 如果没找到，尝试常见的案件页面URL
        possible_urls = [
            f"{self.base_url}/case",
            f"{self.base_url}/cases",
            f"{self.base_url}/case/list",
            f"{self.base_url}/index.php/case"
        ]

        return possible_urls[0]

    def get_case_list(self):
        """获取案件列表"""
        if not self.is_logged_in:
            print("请先登录")
            return []

        case_list_url = self.get_case_list_url()
        if not case_list_url:
            print("无法找到案件列表页面")
            return []

        soup = self.get_page(case_list_url)
        if not soup:
            return []

        cases_list = []

        # 查找案件表格
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue

            # 获取表头
            header_row = rows[0]
            headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

            # 检查是否是案件表格
            case_headers = ['案件编号', '查获单位', '承办部门', '查获部门', '当事人', '许可证号',
                            '案发时间', '录入时间', '立案时间', '鉴定时间', '处罚（处理）决定时间', '结案时间']

            if not any(header in ''.join(headers) for header in case_headers[:3]):
                continue

            print(f"找到案件表格，表头: {headers}")

            # 提取案件数据
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= len(headers):
                    case_data = {}

                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            case_data[headers[i]] = cell.get_text().strip()

                    # 查找详情链接
                    detail_links = []
                    for cell in cells:
                        links = cell.find_all('a', href=True)
                        for link in links:
                            link_text = link.get_text().strip()
                            if '案件在办' in link_text or '详情' in link_text or '查看' in link_text:
                                detail_links.append(urljoin(self.base_url, link['href']))

                    case_data['详情链接'] = detail_links

                    if case_data.get('案件编号'):
                        cases_list.append(case_data)

        print(f"共找到 {len(cases_list)} 个案件")
        return cases_list

    def extract_table_data(self, soup, table_title=""):
        """提取表格数据"""
        tables_data = []
        tables = soup.find_all('table')

        for i, table in enumerate(tables):
            table_info = {
                'title': table_title + f"_表格{i + 1}" if table_title else f"表格{i + 1}",
                'data': []
            }

            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text().strip() for cell in cells]
                if any(row_data):
                    table_info['data'].append(row_data)

            if table_info['data']:
                tables_data.append(table_info)

        return tables_data

    def get_case_detail(self, case_number, detail_url):
        """获取案件详情"""
        print(f"正在获取案件 {case_number} 的详情...")

        soup = self.get_page(detail_url)
        if not soup:
            return None

        case_detail = {
            'case_number': case_number,
            'url': detail_url,
            'sections': {}
        }

        # 定义案件的各个部分
        sections = {
            '案件信息': [],
            '涉案人信息': [],
            '涉案物品': [],
            '运输信息': [],
            '承办信息': [],
            '举报记录表': [],
            '涉案物品核价表': [],
            '物品确认': [],
            '结案报告表': []
        }

        # 查找页面中的所有表格
        all_tables = self.extract_table_data(soup)

        # 尝试根据上下文文本匹配表格到相应部分
        page_text = soup.get_text()

        for section_name in sections.keys():
            if section_name in page_text:
                # 查找该部分对应的表格
                section_tables = []

                # 查找包含该部分名称的元素
                section_elements = soup.find_all(text=re.compile(section_name))

                for element in section_elements:
                    parent = element.parent
                    # 查找该元素后面的表格
                    next_table = parent.find_next('table')
                    if next_table:
                        table_data = []
                        rows = next_table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text().strip() for cell in cells]
                            if any(row_data):
                                table_data.append(row_data)

                        if table_data:
                            section_tables.append({
                                'title': section_name,
                                'data': table_data
                            })

                sections[section_name] = section_tables

        # 如果无法精确匹配，将所有表格都保存
        if not any(sections.values()):
            sections['所有表格'] = all_tables

        case_detail['sections'] = sections

        return case_detail

    def save_case_to_files(self, case_detail):
        """将案件信息保存到文件"""
        case_number = case_detail['case_number']
        safe_case_number = re.sub(r'[<>:"/\\|?*]', '_', case_number)

        case_dir = os.path.join(self.output_dir, safe_case_number)
        if not os.path.exists(case_dir):
            os.makedirs(case_dir)

        # 保存JSON格式的完整数据
        json_file = os.path.join(case_dir, f"{safe_case_number}_完整数据.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(case_detail, f, ensure_ascii=False, indent=2)

        # 为每个部分创建单独的CSV文件
        for section_name, tables in case_detail['sections'].items():
            if tables:
                for i, table in enumerate(tables):
                    csv_filename = f"{safe_case_number}_{section_name}"
                    if len(tables) > 1:
                        csv_filename += f"_{i + 1}"
                    csv_filename += ".csv"

                    csv_file = os.path.join(case_dir, csv_filename)

                    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(table['data'])

        # 创建案件摘要文件
        summary_file = os.path.join(case_dir, f"{safe_case_number}_摘要.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"案件编号: {case_number}\n")
            f.write(f"详情页面: {case_detail['url']}\n")
            f.write(f"数据获取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("包含的数据部分:\n")
            for section_name, tables in case_detail['sections'].items():
                if tables:
                    f.write(f"- {section_name}: {len(tables)} 个表格\n")
                    for table in tables:
                        f.write(f"  * 表格行数: {len(table['data'])}\n")

        print(f"案件 {case_number} 的数据已保存到: {case_dir}")

    def scrape_all_cases(self):
        """爬取所有案件信息"""
        if not self.login():
            print("登录失败，无法继续")
            return

        # 获取案件列表
        all_cases = self.get_case_list()
        if not all_cases:
            print("未找到案件列表")
            return

        print(f"开始爬取 {len(all_cases)} 个案件的详细信息...")

        success_count = 0
        failed_cases = []

        for i,case in enumerate(all_cases,1):
            case_number = case.get('案件编号', f'案件_{i}')
            print(f"\n[{i}/{len(all_cases)}] 正在处理案件: {case_number}")

            # 获取详情链接
            detail_links = case.get('详情链接', [])
            if not detail_links:
                print(f"案件 {case_number} 没有详情链接，跳过")
                failed_cases.append(case_number)
                continue

            # 使用第一个详情链接
            detail_url = detail_links[0]

            try:
                # 获取案件详情
                case_detail = self.get_case_detail(case_number, detail_url)

                if case_detail:
                    # 添加列表页的基本信息
                    case_detail['basic_info'] = case

                    # 保存到文件
                    self.save_case_to_files(case_detail)
                    success_count += 1
                    print(f"案件 {case_number} 处理完成")
                else:
                    print(f"案件 {case_number} 详情获取失败")
                    failed_cases.append(case_number)

            except Exception as e:
                print(f"处理案件 {case_number} 时出错: {e}")
                failed_cases.append(case_number)

                # 添加延时避免请求过快
            time.sleep(2)

        # 生成总结报告
        self.generate_summary_report(all_cases, success_count, failed_cases)

        print(f"\n爬取完成！")
        print(f"成功处理: {success_count} 个案件")
        print(f"失败案件: {len(failed_cases)} 个")
        if failed_cases:
            print(f"失败的案件编号: {', '.join(failed_cases)}")

    def generate_summary_report(self, cases_list, success_count, failed_cases):
        report_file = os.path.join(self.output_dir, "爬取报告.txt")

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("案件数据爬取报告\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总案件数: {len(cases_list)}\n")
                f.write(f"成功爬取: {success_count}\n")
                f.write(f"失败案件: {len(failed_cases)}\n\n")

                if failed_cases:
                    f.write("失败案件列表:\n")
                    for case_num in failed_cases:
                        f.write(f"- {case_num}\n")
                    f.write("\n")

                f.write("所有案件概览:\n")
                f.write("-" * 30 + "\n")
                for i, case in enumerate(cases_list, 1):
                    case_number = case.get('案件编号', f'案件_{i}')
                    status = "✓ 成功" if case_number not in failed_cases else "✗ 失败"
                    f.write(f"{i:3d}. {case_number} - {status}\n")

            print(f"爬取报告已保存到: {report_file}")

        except Exception as e:
            print(f"生成报告时出错: {e}")

    def test_connection(self):
        """测试网站连接"""
        print("测试网站连接...")
        soup = self.get_page(self.base_url)
        if soup:
            print("网站连接正常")
            print(f"页面标题: {soup.title.string if soup.title else '无标题'}")
            return True
        else:
            print("网站连接失败")
            return False


# 高级功能：支持断点续传
class AdvancedZMJGScraper(ZMJGCaseScraper):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.progress_file = os.path.join(self.output_dir, "爬取进度.json")
        self.completed_cases = self.load_progress()

    def load_progress(self):
        """加载爬取进度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_progress(self, case_number):
        """保存爬取进度"""
        self.completed_cases.add(case_number)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.completed_cases), f, ensure_ascii=False, indent=2)

    def scrape_all_cases(self):
        """支持断点续传的爬取"""
        if not self.login():
            print("登录失败，无法继续")
            return

        all_cases = self.get_case_list()
        if not all_cases:
            print("未找到案件列表")
            return

        # 过滤已完成的案件
        remaining_cases = []
        for case in all_cases:
            case_number = case.get('案件编号', '')
            if case_number not in self.completed_cases:
                remaining_cases.append(case)
            else:
                print(f"案件 {case_number} 已完成，跳过")

        if not remaining_cases:
            print("所有案件都已完成爬取")
            return

        print(f"需要爬取 {len(remaining_cases)} 个案件（总共 {len(all_cases)} 个）")

        success_count = 0
        failed_cases = []

        for i, case in enumerate(remaining_cases, 1):
            case_number = case.get('案件编号', f'案件_{i}')
            print(f"\n[{i}/{len(remaining_cases)}] 正在处理案件: {case_number}")

            detail_links = case.get('详情链接', [])
            if not detail_links:
                print(f"案件 {case_number} 没有详情链接，跳过")
                failed_cases.append(case_number)
                continue

            try:
                case_detail = self.get_case_detail(case_number, detail_links[0])

                if case_detail:
                    case_detail['basic_info'] = case
                    self.save_case_to_files(case_detail)
                    self.save_progress(case_number)  # 保存进度
                    success_count += 1
                    print(f"案件 {case_number} 处理完成")
                else:
                    failed_cases.append(case_number)

            except Exception as e:
                print(f"处理案件 {case_number} 时出错: {e}")
                failed_cases.append(case_number)

            time.sleep(2)

        self.generate_summary_report(all_cases, success_count, failed_cases)
        print(f"\n爬取完成！成功: {success_count}, 失败: {len(failed_cases)}")


def main():
    """主函数"""
    print("ZMJG案件信息爬虫")
    print("=" * 50)

    # 获取登录信息
    username = input("请输入用户名: ").strip()
    password = input("请输入密码: ").strip()

    if not username or not password:
        print("用户名和密码不能为空")
        return

    # 选择爬虫模式
    print("\n请选择爬虫模式:")
    print("1. 基础模式 (一次性爬取所有案件)")
    print("2. 高级模式 (支持断点续传)")

    mode = input("请选择模式 (1/2): ").strip()

    # 创建爬虫实例
    if mode == "2":
        scraper = AdvancedZMJGScraper(username, password)
        print("使用高级模式 (支持断点续传)")
    else:
        scraper = ZMJGCaseScraper(username, password)
        print("使用基础模式")

    # 测试连接
    if not scraper.test_connection():
        print("网站连接失败，请检查网络或网址是否正确")
        return

    try:
        # 开始爬取
        scraper.scrape_all_cases()

    except KeyboardInterrupt:
        print("\n用户中断了爬取过程")
        if isinstance(scraper, AdvancedZMJGScraper):
            print("进度已保存，下次运行时可以继续")
    except Exception as e:
        print(f"爬取过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()