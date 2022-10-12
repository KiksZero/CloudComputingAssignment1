from flask import Flask
app = Flask(__name__)
f = open("id", "r")
id = f.read()
f.close()

@app.route('/cluster1')
def my_app():
    return 'Welcome to Instance with id: ' + id
