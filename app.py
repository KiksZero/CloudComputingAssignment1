from flask import Flask

app = Flask(__name__)
f = open("id", "r")
id = f.read()
f.close()

f = open("type", "r")
type = f.read()
f.close()

f = open("url", "r")
url = f.read()
f.close()


@app.route(url)
def my_app():
    return 'Welcome to <strong>' + type + '</strong> instance with id: <strong>' + id + '</strong>'
