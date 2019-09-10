# Item Catalog App
## Second Project - Nano Degree -1MAC - UDACITY

# Pre-requisite:
    -Git Bash(https://git-scm.com/downloads)
    - Vagrant(https://www.vagrantup.com/)
    - Download the VM configuration(https://s3.amazonaws.com/video.udacity-data.com/topher/2018/April/   5acfbfa3_fsnd-virtual-machine/fsnd-virtual-machine.zip)
    - Virtual Box(https://www.virtualbox.org/wiki/Download_Old_Builds_5_1)
    - DB file: newsdata.sql(https://d17h27t6h515a5.cloudfront.net/topher/2016/August/57b5f748_newsdata/newsdata.zip)

# Instructions:
    - In the vagrant directory in your vm, run Git Bash
    - run command "vagrant up"
    - run command "vagrant ssh"
    - run command "python project.py"

### In python file (project.py)
    - I connect to the DB then.
    - I put the code required to manage login processes.
    - I make routes and functions required to show pages successfully.

### DB:
    - database_setup.py has the classes for the database
    - The DataBase has three tables: User / Category / MenuItem
    - NOte: MenuItem has time_in field which help to get latest items

### Routes & function in project.py
    - routes and functions for login by facebook and google:
        -- @app.route('/login/') - function showLogin() 
        -- @app.route('/fbconnect', methods=['POST']) -function fbconnect()
        -- @app.route('/fbdisconnect') - function fbdisconnect()
        -- @app.route('/gconnect', methods=['POST']) - function gconnect()
        -- @app.route('/gdisconnect') - function gdisconnect()
    - User Helper Functions: function createUser / getUserInfo / getUserID
    - JSON APIs to view Category Information:
        -- @app.route('/category/<int:category_id>/menu/JSON') - function categoryMenuJSON(category_id)
        -- @app.route('/category/<int:category_id>/item/<int:menu_id>/JSON') - function menuItemJSON(category_id, menu_id)
        -- @app.route('/category/JSON') - function catalogJSON()
    - routes and functions for Item Catalog App:
        -- Show catalog: @app.route('/') / @app.route('/catalog/') - function showCatalog()
        -- Show a Category Items: @app.route('/category/<int:category_id>/items/') - function showMenu(category_id)
        -- Show an item description: @app.route('/category/<int:category_id>/item/<int:menuitem_id>/') - function showMenuItem(category_id, menuitem_id)
        -- Create a new menu item from the page of latest items: @app.route('/category/item/new/',methods=['GET','POST']) - function newMenuItem()
        -- Create a new menu item from the page of specified category: @app.route('/category/<int:category_id>/item/new/',methods=['GET','POST']) -             function newMenuItemWithCat(category_id)
        -- Edit a menu item: @app.route('/category/menu/<int:menuitem_id>/edit', methods=['GET','POST']) - function editMenuItem(menuitem_id)
        -- Delete a menu item: @app.route('/category/item/<int:menuitem_id>/delete', methods = ['GET','POST']) - function deleteMenuItem(menuitem_id)
        -- Disconnect based on provider: @app.route('/disconnect') - function disconnect()

### Static Folder:
    - styles.css has the required css for the html files

### Templates Folder: html files:
    -attached/ assistant pages:
        - header / login / majn /nav
    - Loggedin pages:
        -- catalog / menu / menuitem / newmenuitem / deletemenuitem / editmenuitem
    - Public pages:
        -- publiccatalog / publicmenu / publicmenuitem

### Another files:
    - client_secrets.json / fb_client_secrets.json: for the login processes with google and facebook

# Code written with python 2 - DB is sqlite - Tested with firefox browser

# Version:
    - 1.0

# Author:
    - Ahmed Shebl AbdElKader