from flask import Flask, render_template, request, session
from vsearch import search4letters
from markupsafe import escape
from DBcm import UseDatabase, ConnectionError, CredentialsError, SQLError
from checker import check_logged_in
from flask import copy_current_request_context
from time import sleep
from threading import Thread
from dotenv import load_dotenv
import os


# 1. Принудительно находим путь к .env в папке со скриптом
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)

# 2. Загружаем в конфиг с "запасными" значениями (defaults)
# Если os.getenv вернет None, подставится значение после запятой
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', '127.0.0.1')
app.config['MYSQL_USER'] = os.getenv('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', '123')
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'vsearchlogDB')

# 3. Собираем словарь для вашей функции из vsearch
db_details = {
    'host': app.config['MYSQL_HOST'],
    'user': app.config['MYSQL_USER'],
    'password': app.config['MYSQL_PASSWORD'],
    'database': app.config['MYSQL_DB'],
}

# 4. Проверка в консоли
print(f"ПОДКЛЮЧЕНИЕ К: {db_details['host']}")

@app.route('/login')
def do_login() -> str:
    session['logged_in'] = True
    return 'You are now logged in'

@app.route('/logout')
def do_logout() -> str:
    session.pop('logged_in')
    return 'You are now logged out.'


                             
@app.route('/search4', methods = ['POST'])
def do_search() -> 'html':
    @copy_current_request_context
    def log_request(req: 'flask_request', res: str) -> None:
        sleep(15)
        browser = req.user_agent.string.split()[0]
        with UseDatabase(db_details) as cursor:
            _SQL = """INSERT INTO log 
                  (phrase, letters, ip, browser, results)
                  VALUES 
                  (%s, %s, %s, %s, %s)"""
            cursor.execute(_SQL, (req.form['phrase'],
                              req.form['letters'],
                              req.remote_addr,
                              browser,           
                              res, ))
    phrase = request.form ['phrase']
    letters = request.form ['letters']
    title = 'Here are your results:'
    results = str(search4letters(phrase,letters))
    try:
        t = Thread(target = log_request, args =(request,results))
        t.start()
    except Exception as err:
        print('***** Logging failed with this error:', str(err))
    return render_template('results.html',
                            the_title = title,
                            the_phrase = phrase,
                            the_letters = letters,
                            the_results = results,)
@app.route('/')
@app.route('/entry')
def entry_page() -> 'html':
    return render_template('entry.html',
                            the_title = 'Welcome to search4letters on the web!')
@app.route('/viewlog')
@check_logged_in
def view_the_log() -> 'html':
    try:
        with UseDatabase(db_details) as cursor:
            _SQL = """SELECT phrase, letters, ip, browser, results 
                  FROM log 
                  ORDER BY ts DESC"""
            cursor.execute(_SQL)
            contents = cursor.fetchall()
        #raise Exception("Some unknown exception.")
        titles = ('Phrase', 'Letters', 'IP', 'Browser', 'Results')
        return render_template('viewlog.html',
                           the_title='View Log',
                           the_row_titles=titles,
                           the_data=contents)
    except ConnectionError as err:
        print('Is your database switched on? Error:', str(err))
    except CredentialsError as err:
        print('User-id/Password issues. Error:', str(err))
    except SQLError as err:
        print('Is your query correct? Error:', str(err))
    except Exception as err:
        print('Something went wrong:', str(err))
    return 'Error'

app.secret_key ='YouWillNeverGuessMySecretKey'


if __name__ == '__main__':
    app.run(debug=True)