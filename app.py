# -*- coding: utf-8 -*-

import os
from flask import Flask, request, session, redirect, url_for,\
    render_template, flash
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import generate_password_hash, check_password_hash
from forms import SignupForm, LoginForm
from flask.ext import excel
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///data.db"
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    password = db.Column(db.String(120))
    email = db.Column(db.String(240), unique=True)

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User %r>' % self.name


@app.before_request
def check_user_status():
    if 'user_email' not in session:
        session['user_email'] = None
        session['user_name'] = None


@app.route('/', methods=('GET', 'POST'))
@app.route('/index.html', methods=('GET', 'POST'))
def home():
    if session['user_email']:
        return render_template('index.html', useremail=session['user_email'])
    return render_template('index.html')


@app.route('/login', methods=('GET', 'POST'))
def login():
    if session['user_email']:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.check_password(form.password.data):
            session['user_email'] = form.email.data
            session['user_name'] = user.name
            return redirect(url_for('home'))
        else:
            flash(u'对不起，用户不存在或密码错误！')
            return render_template('login.html', form=form)
    return render_template('login.html', form=form)


@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if session['user_email']:
        flash(u'你已经注册过了！')
        return redirect(url_for('home'))
    form = SignupForm()
    if form.validate_on_submit():
        user_email = User.query.filter_by(email=form.email.data).first()
        if user_email is None:
            user = User(form.name.data, form.email.data, form.password.data)
            db.session.add(user)
            db.session.commit()
            session['user_email'] = form.email.data
            session['user_name'] = form.name.data
            flash(u'感谢你的注册，你已登录！')
            return redirect(url_for('home'))
        else:
            flash(u'该邮箱已被注册，请重新选择一个！', 'error')
            render_template('signup.html', form=form)
    return render_template('signup.html', form=form)


@app.route('/logout', methods=('GET', 'POST'))
def logout():
    session.pop('user_email', None)
    session.pop('user_name', None)
    return redirect(request.referrer or url_for('home'))


@app.route('/info.html')
def info():
    if session['user_name']:
        return render_template('info.html')
    return redirect(url_for('login'))


@app.route('/download.html')
def download():
    if session['user_name']:
        return render_template('download.html')
    return redirect(url_for('login'))


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    middlegrade = db.Column(db.Integer)
    finalgrade = db.Column(db.Integer)
    grade = db.Column(db.Integer)

    def __init__(self, id, name, middlegrade, finalgrade, grade=None):
        self.id = id
        self.name = name
        self.middlegrade = middlegrade
        self.finalgrade = finalgrade
        grade = int(0.3 * middlegrade + 0.7 * finalgrade + 0.5)
        self.grade = grade

    def __repr__(self):
        return '<Post %r>' % self.name


@app.route("/import", methods=['GET', 'POST'])
def doimport():
    if request.method == 'POST':

        def post_init_func(row):
            p = Post(row['id'], row['name'], row['middlegrade'],
                     row['finalgrade'], row['grade'])
            return p
        request.save_book_to_database(field_name='file', session=db.session,
                                      tables=[Post],
                                      initializers=[post_init_func])

        return redirect(url_for('grades'))
    return render_template('upload.html')


@app.route("/delete", methods=['GET', 'POST'])
def dodelete():
    Post.query.delete()
    db.session.commit()
    return redirect(url_for('grades'))


@app.route("/export", methods=['GET'])
def doexport():
    return excel.make_response_from_tables(db.session, [Post], "xls")


@app.route('/grades.html')
def grades():
    if session['user_name']:
        admin = False
        alldata = Post.query.all()
        if session['user_email'] == 'admin@admin.com':
            admin = True
        return render_template('grades.html', alldata=alldata, admin=admin)
    return redirect(url_for('login'))


class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(240))
    title = db.Column(db.String(100))
    body = db.Column(db.Text)
    date = db.Column(db.DateTime)

    def __init__(self, title, body):
        self.email = session['user_email']
        self.title = title
        self.body = body
        self.date = (datetime.utcnow() + timedelta(hours=8))

    def __repr__(self):
        return '<Thread Title %r>' % self.title


@app.route('/new', methods=['POST'])
def add_thread():
    if request.method == 'POST':
        if request.form['title'] and request.form['body']:
            newThread = Thread(request.form['title'],
                               request.form['body'])
            db.session.add(newThread)
            db.session.commit()
    return redirect(url_for('bbs'))


@app.route('/bbs.html')
def bbs():
    if session['user_name']:
        threads = Thread.query.order_by(Thread.date.desc()).limit(10).all()
        return render_template('bbs.html', threads=threads)
    return redirect(url_for('login'))


@app.route('/test.html')
def test():
    if session['user_name']:
        return render_template('test.html')
    return redirect(url_for('login'))


if __name__ == '__main__':
    db.create_all()
    app.run()
