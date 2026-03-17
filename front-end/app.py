from flask import Flask, redirect, render_template, request, url_for
from card_config import cards

app = Flask(__name__)

NEWS_POSTS = [
    {
        "title": "Ambassador Roel Nieuwenhuis meets WirelessWorks!",
        "author": "Pieter Oosthoek",
        "date": "Mar 10, 2023",
        "category": "News",
        "excerpt": "Many thanks for visiting and meeting us ambassador Roel Nieuwenkamp! WirelessWorks (0:44) modesty proud participated in this years Dutch Delegation for MWC2023/4FYN as one of the 16 selected startups. Your visit and interest is highly appreciated!...",
        "link": "#",
    },
    {
        "title": "WirelessWorks is thrilled to speak at LogiChem Europe 2023 and to participate in the Dragon's Den on Thursday, March 16th!",
        "author": "Pieter Oosthoek",
        "date": "Mar 8, 2023",
        "category": "News",
        "excerpt": "WirelessWorks provides globally the IoT Gateway-as-a-Service. This Gateway is very relevant for the Chemical Supply Chain too. With it, all sensors that log information can be integrated for near-real-time visibility and control.",
        "link": "#",
    },
]

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


@app.route('/about')
def about():
    return render_template('company/about.html')


@app.route('/news', methods=['GET', 'POST'])
def news():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip() or 'WirelessWorks.IT'
        date = request.form.get('date', '').strip() or 'Today'
        category = request.form.get('category', '').strip() or 'News'
        excerpt = request.form.get('excerpt', '').strip()
        link = request.form.get('link', '').strip() or '#'

        if title and excerpt:
            NEWS_POSTS.insert(
                0,
                {
                    'title': title,
                    'author': author,
                    'date': date,
                    'category': category,
                    'excerpt': excerpt,
                    'link': link,
                },
            )
        return redirect(url_for('news'))

    return render_template('company/news.html', posts=NEWS_POSTS)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    sent = False
    if request.method == 'POST':
        sent = True
    return render_template('company/contact.html', sent=sent)

if __name__ == '__main__':
    app.run(debug=True)
