import os
import shutil

# カレントディレクトリの "saved_webpage" フォルダのパスを指定
folder_path = os.path.join(os.getcwd(), "saved_webpage")

# フォルダが存在する場合に削除
if os.path.exists(folder_path):
    shutil.rmtree(folder_path)
    print(f"{folder_path} を削除しました。")
else:
    print(f"{folder_path} は存在しません。")




import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import base64
import re



# 偽装

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
    #'Referer': 'https://example.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3'
}


def save_webpage(url, save_folder):
    # フォルダの作成
    os.makedirs(save_folder, exist_ok=True)

    # HTMLを取得
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # <html>が存在しない場合は新たに作成
    if soup.html is None:
        soup.html = soup.new_tag('html')
        soup.append(soup.html)

    # MathJaxのスクリプトと設定を<head>に追加
    if soup.head is None:
        soup.head = soup.new_tag('head')
        soup.html.insert(0, soup.head)

    # MathJaxスクリプトを追加
    mathjax_script = soup.new_tag('script', src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-mml-chtml.js")
    mathjax_config = soup.new_tag('script')
    mathjax_config.string = """
    window.MathJax = {
      tex: {
        inlineMath: [['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']]
      }
    };
    """
    soup.head.append(mathjax_config)
    soup.head.append(mathjax_script)

    # リソースの保存フォルダを作成
    resources_folder = os.path.join(save_folder, 'resources')
    os.makedirs(resources_folder, exist_ok=True)

    def save_resource(tag, attribute, resource_folder):
        resources = soup.find_all(tag)
        total_resources = len(resources)

        for index, element in enumerate(resources):
            resource_url = element.get(attribute)

            if resource_url:
                if resource_url.startswith('data:'):
                    match = re.match(r'data:(image/\w+);base64,(.*)', resource_url)
                    if match:
                        mime_type, base64_data = match.groups()
                        extension = mime_type.split('/')[-1]
                        resource_name = f"embedded_image.{extension}"
                        resource_path = os.path.join(resource_folder, resource_name)

                        with open(resource_path, 'wb') as f:
                            f.write(base64.b64decode(base64_data))

                        element[attribute] = os.path.join(os.path.basename(resource_folder), resource_name)
                    continue

                full_resource_url = urljoin(url, resource_url)
                parsed_url = urlparse(full_resource_url)

                # リソースをダウンロード
                try:
                    resource_response = requests.get(full_resource_url, headers=headers, stream=True)
                    response.encoding = response.apparent_encoding  # 自動検出されたエンコーディングに設定

                    resource_response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    print(f"Failed to download {full_resource_url}: {e}")
                    continue

                resource_name = os.path.basename(parsed_url.path)
                if not resource_name:
                    continue

                resource_path = os.path.join(resource_folder, resource_name)

                with open(resource_path, 'wb') as f:
                    for chunk in resource_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # 進行状況の表示
                progress = (index + 1) / total_resources * 100
                print(f"Saving {tag} {index + 1}/{total_resources}: {progress:.2f}% complete")

                element[attribute] = os.path.join(os.path.basename(resource_folder), resource_name)

    # srcset属性のリソースを保存する関数
    def save_srcset_resources(resource_folder):
        for img in soup.find_all('img'):
            if 'srcset' in img.attrs:
                srcset_values = img['srcset'].split(',')
                new_srcset = []

                for src in srcset_values:
                    # URL部分のみを抽出
                    resource_url = src.split()[0]
                    full_resource_url = urljoin(url, resource_url)

                    try:
                        resource_response = requests.get(full_resource_url, headers=headers, stream=True)
                        resource_response.raise_for_status()
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to download {full_resource_url}: {e}")
                        continue

                    resource_name = os.path.basename(urlparse(full_resource_url).path)
                    resource_path = os.path.join(resource_folder, resource_name)

                    with open(resource_path, 'wb') as f:
                        for chunk in resource_response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # srcset用の新しいURLパス
                    new_srcset.append(f"{os.path.join(os.path.basename(resource_folder), resource_name)} {src.split()[1]}")

                # srcsetの置き換え
                img['srcset'] = ", ".join(new_srcset)

    # リソースの保存を行う
    save_resource('img', 'src', resources_folder)
    save_srcset_resources(resources_folder)
    save_resource('link', 'href', resources_folder)
    save_resource('script', 'src', resources_folder)

    # 不要なスクリプトの削除
    for script in soup.find_all('script', src=True):
        if "v3-article-bundle-" in script['src']:
            script.decompose()

    # HTMLを保存
    html_file_path = os.path.join(save_folder, 'index.html')
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())

    print(f"Web page saved at {html_file_path}")
    return save_folder


# メインの実行
url = input('enter the url=')
print('読み込み中、そのまま待ってください。')
save_folder = "./saved_webpage"

# Webページを保存
save_webpage(url, save_folder)
print('完了')



import http.server
import socketserver
import os
import webbrowser

def start_server(directory, port=8001):
    # カレントディレクトリを指定されたディレクトリに変更
    os.chdir(directory)

    # サーバーの設定
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at port {port}")

        # ブラウザで自動的に開く
        webbrowser.open(f"http://localhost:{port}")

        # サーバーを起動し、無限ループで待機
        httpd.serve_forever()

# フォルダ名とポート番号を設定
directory_to_serve = 'saved_webpage'#input("Enter the directory to serve: ")
start_server(directory_to_serve)
