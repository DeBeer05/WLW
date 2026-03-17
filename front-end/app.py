from flask import Flask, render_template
from card_config import cards

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', cards=cards)

@app.route('/postnl')
def postnl():
    return render_template('use_cases/postnl.html')


@app.route('/pharmaceutical')
def pharmaceutical():
    return render_template('use_cases/pharmaceutical.html')


@app.route('/hive-zox')
def hive_zox():
    return render_template('use_cases/Hive-zox.html')


@app.route('/fixed-wireless-access')
def fixed_wireless_access():
    return render_template('use_cases/fixed-wireless-access.html')


@app.route('/logistics-security')
def logistics_security():
    return render_template('use_cases/logistics-security.html')

if __name__ == '__main__':
    app.run(debug=True)
