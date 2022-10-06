from flask import Flask
app = Flask(__name__)

@app.route('/')
def my_app():
    return 'First Flask application!'

if __name__ == '__main__':
    app.run('0.0.0.0',80)