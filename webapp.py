from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash
from markupsafe import Markup
#from flask_apscheduler import APScheduler
#from apscheduler.schedulers.background import BackgroundScheduler
from flask_oauthlib.client import OAuth
from bson.objectid import ObjectId

import pprint
import os
import time
import pymongo
import sys
 
app = Flask(__name__)

db_name = os.environ["MONGO_DBNAME"]

connection_string = os.environ["MONGO_CONNECTION_STRING"]
client = pymongo.MongoClient(connection_string)

galleryDB = client[db_name]
hawkishCR = galleryDB['hawkish']
app.debug = False #Change this to False for production
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

#Connect to database
url = os.environ["MONGO_CONNECTION_STRING"]
client = pymongo.MongoClient(url)
db = client[os.environ["MONGO_DBNAME"]]
collection = db['posts'] #TODO: put the name of the collection here

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/createPost', methods=["GET", "POST"])
def create_post():
    if "comment" in session:
        content = request.form['content']
        if session["comment"] != content:
            print("hi2")
            username = session['user_data']['login']
            doc = {"User":username, "Message":content }
            hawkishCR.insert_one(doc)
            session["comment"] = content
        else:
            posts = ""
            for doc in hawkishCR.find():
                posts += Markup("<p>" + str(doc["User"]) + ": " + str(doc["Message"]) + "</p>")
            return render_template('modern1.html', posts=posts)
    else:
        print("hi")
        content = request.form['content']
        username = session['user_data']['login']
        doc = {"User":username, "Message":content }
        hawkishCR.insert_one(doc)
        session["comment"] = content
    posts = ""
    for doc in hawkishCR.find():
        posts += Markup("<p>" + str(doc["User"]) + ": " + str(doc["Message"]) + "</p>")
    return render_template('modern1.html', posts=posts)


#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():  
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out.')
    return redirect('/')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args), 'error')      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            message = 'You were successfully logged in as ' + session['user_data']['login'] + '.'
        except Exception as inst:
            session.clear()
            print(inst)
            message = 'Unable to login, please try again.', 'error'
    return render_template('home.html', message=message)


@app.route('/modern1')
def renderModern1():
    if 'user_data' in session:
        user_data_pprint = pprint.pformat(session['user_data'])#format the user data nicely
    else:
        user_data_pprint = '';
    posts = ""
    for doc in hawkishCR.find():
        posts += Markup("<p>" + str(doc["User"]) + ": " + str(doc["Message"]) + "</p>")
    return render_template('page1.html', posts=posts)

@app.route('/ms1')
def renderMS1():
    return render_template('page2.html')

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run()
