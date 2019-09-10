#! /usr/bin/env python

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, MenuItem, User

import random
import string

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError

import httplib2
import json
from flask import make_response
import requests

from flask import flash, session as login_session
from flask import Flask, render_template, request, redirect, jsonify, url_for
app = Flask(__name__)

CLIENT_ID = json.loads(
  open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

# Connect to Database and create database session
engine = create_engine(
  'sqlite:///itemcatalog.db',
  connect_args={'check_same_thread': False}
  )
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create a state token to prevent request forgery.
# Store it in the session for later validation.
@app.route('/login/')
def showLogin():
    state = ''.join(
      random.choice(string.ascii_uppercase + string.digits) for x in xrange(32)
      )
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?' \
        'grant_type=fb_exchange_token&client_id=%s&client_secret=%s&' \
        'fb_exchange_token=%s' % (
            app_id, app_secret, access_token
            )
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server
        token exchange we have to split the token first on
        commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out
        the actual token value and replace the remaining quotes with
        nothing so that it can be used directly in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&' \
        'fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&' \
        'redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
        ' -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?' \
        'access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
          json.dumps('Failed to upgrade the authorization code.'),
          401
          )
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = (
      'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
      % access_token
      )
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
          json.dumps("Token's user ID doesn't match given user ID."),
          401
          )
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(
          json.dumps("Token's client ID doesn't match app's."),
          401
          )
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
          json.dumps('Current user is already connected.'),
          200
          )
        response.headers['Content-Type'] = 'application/json'

    login_session['provider'] = 'google'
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;' \
        'border-radius: 150px; -webkit-border-radius: 150px;' \
        '-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception:
        return None

# DISCONNECT - Revoke a current user's token and reset their login-session.
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('credentials')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(
          json.dumps('Current user not connected.'),
          401
          )
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/' \
        'revoke?token=%s' % login_session['credentials']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        # del login_session['username']
        # del login_session['email']
        # del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
          json.dumps(
            'Failed to revoke token for given user.',
            400
            )
            )
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Category Information
@app.route('/category/<int:category_id>/menu/JSON')
def categoryMenuJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(MenuItem).filter_by(category_id=category_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/category/<int:category_id>/item/<int:menu_id>/JSON')
def menuItemJSON(category_id, menu_id):
    Menu_Item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/category/JSON')
def catalogJSON():
    catalog = session.query(Category).all()
    return jsonify(catalog=[r.serialize for r in catalog])


# Show catalog
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    catalog = session.query(Category).order_by(asc(Category.name))
    items = session.query(MenuItem).order_by(MenuItem.time_in.desc()) \
        .limit(catalog.count())
    if 'username' not in login_session:
        return render_template(
          'publiccatalog.html',
          catalog=catalog,
          items=items
          )
    else:
        return render_template('catalog.html', catalog=catalog, items=items)

# Show a Category Items
@app.route('/category/<int:category_id>/items/')
def showMenu(category_id):
    catalog = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(id=category_id).one()

    items = session.query(MenuItem).filter_by(category_id=category_id).all()
    if 'username' not in login_session:
        return render_template(
          'publicmenu.html',
          items=items,
          category=category,
          catalog=catalog
          )
    else:
        return render_template(
          'menu.html', items=items,
          category=category,
          catalog=catalog
          )

# Show an item description
@app.route('/category/<int:category_id>/item/<int:menuitem_id>/')
def showMenuItem(category_id, menuitem_id):

    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(MenuItem).filter_by(id=menuitem_id).one()
    creator = getUserInfo(item.user_id)
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template(
          'publicmenuitem.html',
          item=item, category=category,
          creator=creator
          )
    else:
        return render_template(
          'menuitem.html',
          item=item,
          category=category,
          creator=creator
          )

# Create a new menu item from the page of latest items
@app.route('/category/item/new/', methods=['GET', 'POST'])
def newMenuItem():
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Category).order_by(asc(Category.name))
    category_id = 1
    if request.method == 'POST':
        newItem = MenuItem(
          name=request.form['name'],
          description=request.form['description'],
          category_id=request.form['category'],
          user_id=login_session['user_id']
          )
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showMenu', category_id=category_id))
    else:
        return render_template(
          'newmenuitem.html',
          category_id=category_id,
          catalog=catalog
          )

# Create a new menu item from the page of specified category
@app.route('/category/<int:category_id>/item/new/', methods=['GET', 'POST'])
def newMenuItemWithCat(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Category).order_by(asc(Category.name))
    if request.method == 'POST':
        newItem = MenuItem(
          name=request.form['name'],
          description=request.form['description'],
          category_id=request.form['category'],
          user_id=login_session['user_id']
          )
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showMenu', category_id=category_id))
    else:
        return render_template(
          'newmenuitem.html',
          category_id=category_id,
          catalog=catalog
          )

# Edit a menu item
@app.route('/category/menu/<int:menuitem_id>/edit', methods=['GET', 'POST'])
def editMenuItem(menuitem_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Category).order_by(asc(Category.name))
    editedItem = session.query(MenuItem).filter_by(id=menuitem_id).one()

    if login_session['user_id'] != editedItem.user_id:
        return "<script>function myFunction() {alert('You are not authorized"
        + " to edit menu items to this category. Please create your own"
        + " category in order to edit items.');}</script><body"
        + " onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['category']:
            editedItem.category_id = request.form['category']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(
          url_for(
            'showMenu',
            category_id=editedItem.category_id
            )
        )
    else:
        return render_template(
          'editmenuitem.html',
          item=editedItem,
          catalog=catalog
        )


# Delete a menu item
@app.route('/category/item/<int:menuitem_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(menuitem_id):
    if 'username' not in login_session:
        return redirect('/login')

    itemToDelete = session.query(MenuItem).filter_by(id=menuitem_id).one()
    if login_session['user_id'] != itemToDelete.user_id:
        return "<script>function myFunction(){alert('You are not authorized"
        + " to delete menu items to this category. Please create your own"
        + " category in order to delete items.');}</script><body"
        + " onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(
          url_for('showMenu', category_id=itemToDelete.category_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
