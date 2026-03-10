from flask import Flask, render_template
from card_config import cards

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', cards=cards)

if __name__ == '__main__':
    app.run(debug=True)
