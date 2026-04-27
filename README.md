# RCC Receipt Validator

電子領収書の真正性を検証するためのCLIツールである。

## 必須要件

* Python 3.8以上
* [uv](https://github.com/astral-sh/uv)

## セットアップ手順

リポジトリをクローン後、以下のコマンドを実行して依存関係を追加する。
`gh repo clone git@github.com:ritscc/digitalReciept.git`

### 推奨環境
git
mise
 - gh
 - python
 - uv

```python
uv init
uv add cryptography
```

## 領収書の検証方法

1. 以下のコマンドで検証ツールを起動する。

`uv run main.py`

2. メニューから 3. Validate Receipt を選択する。
3. Enter key name to use for validation と表示されたら、公開鍵のファイル名（拡張子 .pub を除いたもの、例: rcc_2026）を入力する。
4. メールで送られてきた「領収書データ（Base64）」と「Ed25519署名（Base64）」をそれぞれペーストする。
5. 改ざんがなく、正しい鍵で署名されていれば [Success] Signature is VALID. と表示され、領収書の内容が出力される。

## 発行者向け手順（管理者用）

* 鍵の生成: メニューから 1. Generate Keypair を選択。生成された .pub ファイルはGitにコミットし、秘密鍵は絶対に公開しないこと。
* 領収書の発行: メニューから 2. Sign Receipt を選択。内容を入力して出力されたデータをメール等で送信する。
