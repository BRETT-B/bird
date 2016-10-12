from flask import Flask, render_template, redirect, request, session, jsonify
from flaskext.mysql import MySQL
import bcrypt
# Set up mysql connection here later
mysql = MySQL()
# bring in the flask object
app = Flask(__name__)
# Congiguratey the database options
app.config['MYSQL_DATABASE_USER'] = 'x'
app.config['MYSQL_DATABASE_PASSWORD'] = 'x'
app.config['MYSQL_DATABASE_DB'] = 'bird'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
# Initiate the app
mysql.init_app(app)
# create a secret key (random)
app.secret_key = 'abcdefghijklmnopqrstuvwxyz'
#Make one connection and use it over, and over, and over...
conn = mysql.connect()
# set up a cursor object whihc is what the sql object uses to connect and run queries
cursor = conn.cursor()

# Create a route to home page
@app.route('/')
def index():
	if 'username' in session:
		profile_pic_query = "SELECT picture FROM users WHERE username = '%s'" % session['username']
		cursor.execute(profile_pic_query)
		profile_pic = cursor.fetchone()

		homepage_page_query = "SELECT users.id,username,picture,post_content,current_vote,posts.id FROM users INNER JOIN posts ON users.id = posts.uid ORDER BY current_vote DESC"
		cursor.execute(homepage_page_query)
		homepage_page_query = cursor.fetchall()

		comment_page_query = "SELECT users.id,username,picture,post_content,current_vote FROM users LEFT JOIN comments ON users.id = comments.uid"
		cursor.execute(comment_page_query)
		comment_page_query = cursor.fetchall()
		print comment_page_query
		return render_template('index.html',
			profile_pic = profile_pic,
			homepage_page_query = homepage_page_query,
			comment_page_query = comment_page_query)
	else:
		return redirect('/login?message=YouMustLogIn')

# Create a register page
@app.route('/register')
def register():
	if request.args.get('username'):
		return render_template('register.html', message = "Username Taken")
	elif request.args.get('password'):
		return render_template('register.html', message = "Passwords Do Not Match")
	else:
		return render_template('register.html')
# Create a submit route to insert into database
@app.route('/register_submit', methods=['POST'])
def register_submit():
    # First check to see if username is already taken
    # this means a select statement
    check_username_query="SELECT * FROM users WHERE username = '%s'"%request.form['username']
    # print check_username_query
    cursor.execute(check_username_query)
    check_username_result = cursor.fetchone()
    if check_username_result is None:
        #no match. Insert
        email=request.form['email']
        username=request.form['username']
        password=request.form['password'].encode('utf-8')
        password2=request.form['password2'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password,bcrypt.gensalt())
        picture = request.files['picture']
        # image.save passes where we want to save it which is image.filename
        picture.save('static/images/'+picture.filename)
        picture_path=picture.filename
        bio= request.form['bio']
        if password==password2:
            user_insert_query="INSERT INTO users VALUES(DEFAULT,'"+username+"','"+hashed_password+"','"+email+"','"+picture_path+"','"+bio+"')"
            cursor.execute(user_insert_query)
            conn.commit()
            session['username'] = request.form['username']
            session['id'] = check_username_query[0]
            return redirect('/login')
        else:
        	return redirect('/register?password=nomatch')
    else:
        return redirect('/register?username=taken')
# Create a login page
@app.route('/login')
def login():
	if request.args.get('message'):
		return render_template('login.html', message = "Please Login")
	elif request.args.get('credentials'):
		return render_template('login.html', message = "Login Failed")
	else:
		return render_template('login.html')
@app.route('/login_submit', methods = ['POST', 'GET'])
def login_submit():
	username = request.form['username']
	password = request.form['password'].encode('utf-8')
	# hashed_password = bcrypt.hashpw(password,bcrypt.gensalt())
	user = "SELECT id, username, password FROM users WHERE username = '"+username+"'"
	cursor.execute(user)
	result = cursor.fetchone()
	print result
	if bcrypt.checkpw(password, result[2].encode('utf-8')):
		session['username'] = request.form['username']
		session['id'] = user[0]
		return render_template('index.html')
	else:
		return redirect('/login?credentials=failed')

@app.route('/logout')
def logout():
	session.clear()
	return redirect('/login?message=loggedOut')

@app.route('/post_submit', methods=['POST'])
def post_submit():
	post = request.form['post_content']
	get_user_id_query = "SELECT id FROM users WHERE username = '%s'"% session['username']
	cursor.execute(get_user_id_query)
	get_user_id_result = cursor.fetchone()
	uid = get_user_id_result[0]
	insert_post_query = "INSERT INTO posts (post_content, uid, current_vote) VALUES ('"+post+"', "+str(uid)+", 0)"
	cursor.execute(insert_post_query)
	conn.commit()
	return redirect('/?message=post')

@app.route('/process_vote', methods=['POST'])
def process_vote():
	# check to see, has th euser voted on this particular item
	post_id = request.form['vid'] # the post they voted on. This came from jquery $.ajax
	vote_type = request.form['voteType']
	check_user_votes_query = "SELECT * FROM votes INNER JOIN users ON users.id = votes.uid WHERE users.username = '%s' AND votes.post_id = '%s'" % (session['username'], post_id)
	# print check_user_votes_query
	cursor.execute(check_user_votes_query)
	check_user_votes_result = cursor.fetchone()

	# It's possible we get None back, becaues the user hsn't voted on this post
	if check_user_votes_result is None:
		# User hasn't voted. Insert.

		insert_user_vote_query = "INSERT INTO votes (post_id, uid, vote_type) VALUES ('"+str(post_id)+"', '"+str(session['id'])+"', '"+str(vote_type)+"')"
		# print insert_user_vote_query
		cursor.execute(insert_user_vote_query)
		conn.commit()
		return jsonify("voteCounted")
	else:
		check_user_vote_direction_query = "SELECT * FROM votes INNER JOIN users ON users.id = votes.uid WHERE users.username = '%s' AND votes.post_id = '%s' AND votes.vote_type = %s" % (session['username'], post_id, vote_type)
		cursor.execute(check_user_vote_direction_query)
		check_user_vote_direction_result = cursor.fetchone()
		if check_user_vote_direction_result is None:
			# User has voted, but not this direction. Update
			update_user_vote_query = "UPDATE votes SET vote_type = %s WHERE user_id = '%s' AND post_id = '%s'" % (vote_type, session['id'], post_id)
			cursor.execute(update_user_vote_query)
			conn.commit()
			return "voteChanged"
		else:
			# User has already voted this directino on this post. No dice.
			return "alreadyVoted"
# @app.route('/follow')
# def follow():
	

if __name__ == "__main__":
	app.run(debug=True)
