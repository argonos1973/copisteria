from flask import Flask

app = Flask(__name__)
app.config['DATABASE'] = '/var/www/html/aleph70.db'
