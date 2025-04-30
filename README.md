# 概要

Anthropic APIを使ったMCPサーバー呼び出しの勉強用に作成したチャットアプリのサンプル。

Anthropic APIを使用しているので、別途APIキーが必要になる。

# 環境の構築と実行

(1) 環境の構築
```
$ python -m venv .venv
$ . .venv/bin/activate
$ pip install -r requirements.txt
```

(2) APIキーの設定

dot.env.sampleをコピーして、.envにAPIキーを設定する。

```
$ cp dot.env.sample .env
```

.envの例。
```
API_KEY=取得したAPIキー
```

(3) 実行

```
$ python chat.py
Please enter the text and press Ctrl + D:
```

Ctrl + D押下で入力済みのテキストが送信される。


# サンプルのMCPサーバー

チャットアプリから呼び出せるMCPサーバーのサンプルは以下の二つ。LLMが複数のToolを使い分ける動作を見たかったので二つ用意した。

- mcp-servers/get-uuid.py

UUIDを作成して返す。

- mcp-servers/get-datetime.py

指定タイムゾーンの現在の日時を返す。 引数付のTool呼び出しを確認したかったので、タイムゾーンを引数で受け付けるようにしている。

# 実行例

MCPサーバーにUUIDを作成させる例。

```
% python chat.py          
Please enter the text and press Ctrl + D:
uuidを作って
Sending...
uuidを生成いたします。

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 502
Output Tokens: 46
Calling get_uuid {}　← LLMがget_uuidを呼び出すことを指示している。
Result: da654be8-9ebb-492c-be65-1b201a2f89dc ← MCPサーバーが返した結果
生成されたUUID: `da654be8-9ebb-492c-be65-1b201a2f89dc`

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 92
Output Tokens: 36
```

現在時刻を取得させる例(タイムゾーン指定なし)。

```
Please enter the text and press Ctrl + D:
今何時?
Sending...
現在の日時をお知らせします。

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 626
Output Tokens: 50
Calling get_datetime {}
  ← LLMがget_datetimeを呼び出すことを指示している。
Result: 2025-04-29 23:45:22 ← MCPサーバーが返した結果
現在の日時は 2025年4月29日 23時45分22秒 です。

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 209
Output Tokens: 29
```

現在時刻を取得させる例(タイムゾーン指定あり)。

```
Please enter the text and press Ctrl + D:
シンガポールは今何時？
Sending...
シンガポールの現在の日時をお知らせします。

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 741
Output Tokens: 74
Calling get_datetime {'timezone': 'Asia/Singapore'}
  ← LLMがget_datetimeを呼び出すことを指示している。
     タイムゾーンの指定もちゃんと'Asia/Singapore'になっている。
Result: 2025-04-29 22:45:44 ← MCPサーバーが返した結果
シンガポールの現在の日時は 2025年4月29日 22時45分44秒 です。

Cache Creation Input Tokens: 0
Cache Read Input Tokens: 0
Input Tokens: 348
Output Tokens: 35
```

# 実装に関するメモ

MCPサーバーの呼び出し前には、場合によってはユーザに許可を取る必要があるだろうが、今回はファイルを書き換えたりする危険なMCPサーバーはないので考慮していない

今回の実装ではMCP Serverは立ち上げっぱなしにはせず、必要になった時にその都度起動しなおしている。大量のMCP Serverを扱うことになった場合は、大量のプロセスを立ち上げっぱなしにしておくのも無駄かと考えたため。 チャットアプリにおいては、MCP Serverが必要になるのはメッセージを送信した時だけなので、パフォーマンス的には問題ないだろう。
