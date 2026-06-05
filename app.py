from flask import Flask, render_template

app = Flask("%name%")

@app.route("/login")
def login():
    return render_template('web/index.html', title='Login page')

@app.route('/')
def mainpage():
    return render_template('web/index.html', title='Main page')

if __name__ == '__main__':
    app.run()