from flask import Flask
app = Flask(__name__)
f = open("id", "r")
id = f.read()
f.close()

f = open("url", "r")
url = f.read()
f.close()

@app.route(url)
def my_app():
    return 'Welcome to Instance with id: ' + id
