import os
import re

# Python Web framework
from flask import Flask, request, abort

# グラフ描画関連
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# LINE API
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

# AWS連携関連
import boto3

# インスタンス化
app = Flask(__name__)

channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
channel_secret       = os.environ['LINE_CHANNEL_SECRET']
line_bot_api         = LineBotApi(channel_access_token)
handler              = WebhookHandler(channel_secret)
aws_s3_bucket        = os.environ['AWS_BUCKET']

# デプロイ確認用ルーティング
@app.route("/")
def hello_world():
    return "hello world!"

# LINEからPOSTリクエストが届いたときの処理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    # LINEメッセージのフォーマットチェック
    # 正しくない場合はテキストメッセージをLINEに返す
    if not valid_message_format(event.message.text):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text = '入力が正しくないよ!!\n[<xの開始値>:<xの終了値>]\n<関数名>(x)\nの形で入力してください。')
        )
        return

    axis_range, func = event.message.text.split('\n')
    xmin_str, xmax_str = axis_range.strip('[]').split(':')

    xmin = float(xmin_str)
    xmax = float(xmax_str)

    # LINEメッセージの範囲指定チェック（大小関係）
    # 正しくない場合はテキストメッセージをLINEに返す
    if xmin > xmax:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='範囲指定が正しくないよ!!')
        )
        return
    
    # x軸の刻みは描画範囲を100等分で固定
    dx = (xmax-xmin) * 0.01
    x = np.arange(xmin, xmax, dx)

    # 送られてきた関数文字列に応じてnumpy標準の関数オブジェクトを取得
    y = func_generator(func, x)

    # 関数が取得できたかチェック
    # 取得できていない場合はテキストメッセージをLINEに返す
    if y is None:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='その関数は描画できません。'))
        return
    
    # 描画
    plt.figure()
    plt.plot(x, y)
    
    # ファイルを一時的にHeroku Dynoに保存
    file_name = func + '.png'
    plt.savefig(file_name)

    # S3へグラフ画像をアップロードする
    s3_resource = boto3.resource('s3')
    s3_resource.Bucket(aws_s3_bucket).upload_file(file_name, file_name)

    # S3へアップロードした画像の署名付きURLを取得する
    s3_client = boto3.client('s3')
    s3_image_url = s3_client.generate_presigned_url(
        ClientMethod = 'get_object',
        Params       = {'Bucket': aws_s3_bucket, 'Key': file_name},
        ExpiresIn    = 10,
        HttpMethod   = 'GET'
    )
    
    # 画像URLを指定してLINEに返す
    line_bot_api.reply_message(
        event.reply_token,
        ImageSendMessage(
            original_content_url = s3_image_url,
            preview_image_url    = s3_image_url
        )
    )

def valid_message_format(msg):
    pattern = '^\[-?[0-9]+.?[0-9]*:-?[0-9]+.?[0-9]*\]\n[a-zA-Z0-9()]+$'
    return re.match(pattern, msg)

def func_generator(func, x):
    if func == 'x':
        return x
    elif func == 'sin(x)':
        return np.sin(x)
    elif func == 'cos(x)':
        return np.cos(x)
    elif func == 'tan(x)':
        return np.tan(x)
    elif func == 'cos(x)':
        return np.cos(x)
    elif func == 'arcsin(x)':
        return np.arcsin(x)
    elif func == 'arccos(x)':
        return np.arccos(x)
    elif func == 'arctan(x)':
        return np.arctan(x)
    elif func == 'exp(x)':
        return np.exp(x)
    elif func == 'log(x)':
        return np.log(x)
    elif func == 'log2(x)':
        return np.log(x)
    elif func == 'log10(x)':
        return np.log10(x)
    elif func == 'sinh(x)':
        return np.sinh(x)
    elif func == 'cosh(x)':
        return np.cosh(x)
    elif func == 'tanh(x)':
        return np.tanh(x)
    elif func == 'arcsinh(x)':
        return np.arcsinh(x)
    elif func == 'arccosh(x)':
        return np.arccosh(x)
    elif func == 'arctanh(x)':
        return np.arctanh(x)
    elif func == 'floor(x)':
        return np.floor(x)
    elif func == 'round(x)':
        return np.round(x)
    elif func == 'fix(x)':
        return np.fix(x)
    else:
        return None

if __name__ == "__main__":
    app.run()