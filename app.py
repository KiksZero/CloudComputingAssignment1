from flask import Flask
app = Flask(__name__)
f = open("id", "r")

@app.route('/')
def my_app():
    return 'Welcome to Instance with id: ' + f.read()
