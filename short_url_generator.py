from flask import Flask, render_template, request, redirect, url_for, Response, session
import hashlib
import os
import pandas as pd
from io import BytesIO
import xlsxwriter
from urllib.parse import urlparse
from collections import OrderedDict


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'super_secret_key'

# 定义一个有序字典，用于保存短网址和长网址的映射关系
urls = OrderedDict()

def add_url(short_url, long_url):
    # 如果字典已经达到最大值，则删除最旧的一条记录
    if len(urls) >= 5:
        urls.popitem(last=False)
    urls[short_url] = long_url

# 确保上传文件夹存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

urls = {}

def generate_short_url(long_url):
    short_url_hash = hashlib.sha256(long_url.encode('utf-8')).hexdigest()[:6]
    while short_url_hash in urls:
        short_url_hash = hashlib.sha256(short_url_hash.encode('utf-8')).hexdigest()[:6]
    return short_url_hash

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        long_url = request.form.get('url')
        if long_url:
            parsed_url = urlparse(long_url)
            if parsed_url.scheme and parsed_url.netloc:  # 如果是 Scheme URL
                short_url = generate_short_url(long_url)
                urls[short_url] = long_url
                session['short_url'] = f"{request.url_root}{short_url}"
                return redirect(url_for('index', new_short_url=True))
            else:
                # 如果不是 Scheme URL，则提示错误信息
                return render_template('index.html', urls=urls, error_msg="请输入合法的网址或 Scheme URL。")
        file = request.files.get('file')
        if file and file.filename != '':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            df = pd.read_excel(filepath)
            long_urls = df['长网址'].tolist()
            short_urls = [generate_short_url(long_url) for long_url in long_urls]
            for short_url, long_url in zip(short_urls, long_urls):
                urls[short_url] = long_url

            # 生成包含短网址的新 Excel 文件
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()

            worksheet.write(0, 0, '长网址')
            worksheet.write(0, 1, '短网址')

            for index, (long_url, short_url) in enumerate(zip(long_urls, short_urls), start=1):
                worksheet.write(index, 0, long_url)
                worksheet.write(index, 1, f"{request.url_root}{short_url}")

            workbook.close()
            output.seek(0)

            # 将新生成的 Excel 文件发送给用户
            return Response(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment;filename=short_urls.xlsx'})

        else:
            # 如果没有提供长网址或上传文件，则提示错误信息
            return render_template('index.html', urls=urls, error_msg="请提供一个长网址或上传一个文件！")
    else:
        new_short_url = request.args.get("new_short_url") == "True"
        short_url = session.get("short_url")
        if new_short_url and short_url:
            return render_template('index.html', urls=urls, new_short_url=new_short_url, short_url=short_url)
        return render_template('index.html', urls=urls)

@app.route('/<short_url>')
def redirect_url(short_url):
    if short_url in urls:
        return redirect(urls[short_url])
    else:
        return "Error: URL not found", 404


# 添加新的路由和清除历史记录的函数
@app.route('/clear_history', methods=['POST'])
def clear_history():
    global urls
    urls = {}
    return redirect(url_for('index'))


“if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)”

