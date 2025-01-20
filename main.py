from flask import Flask, render_template, redirect, request, flash, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime
import os
from sqlalchemy.sql.expression import func

app = Flask(__name__)
app.secret_key = "hdsaghiadshihidsgihadsghia"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Profile Model
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), unique=True, nullable=False)
    display_name = db.Column(db.String(20), unique=False, nullable=False)
    pass_word = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(128), nullable=True)  # Field for user avatar
    
    followers = db.relationship('Follow', backref='followed', foreign_keys='Follow.followed_id')
    following = db.relationship('Follow', backref='follower', foreign_keys='Follow.follower_id')

    def __init__(self, user_name, display_name, pass_word, avatar=None):
        self.user_name = user_name
        self.display_name = display_name
        self.pass_word = generate_password_hash(pass_word)
        self.avatar = avatar  # Default to None if no avatar provided

# Follow Model
class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    def __init__(self, follower_id, followed_id):
        self.follower_id = follower_id
        self.followed_id = followed_id

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    def __init__(self, post_id, user_id):
        self.post_id = post_id
        self.user_id = user_id

# Post Model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)

    user = db.relationship('Profile', backref=db.backref('posts', lazy=True))
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')

    def __init__(self, title, content, user_id):
        self.title = title
        self.content = content
        self.user_id = user_id

def user_has_liked(likes, username):
    user_profile = Profile.query.filter_by(user_name=username).first()
    if user_profile:
        return any(like.user_id == user_profile.id for like in likes)
    return False

# Register the function as a global Jinja2 function
app.jinja_env.globals['user_has_liked'] = user_has_liked

# Initialize database
def initialize_database():
    with app.app_context():  # Add this line to set up the application context
        db.create_all()
        print("Database tables created successfully.")

# Error Handlers
@app.errorhandler(400)
def handle_bad_request(e):
    return render_template("Bad_request.html"), 400

@app.errorhandler(404)
def err404(e):
    return render_template("404.html", url=request.path.replace("/", '')), 404

# Index Route
@app.route('/')
def index():
    initialize_database()
    if "user_name" in session:
        return redirect(url_for("user_page", handle=session["user_name"]))
    return render_template("Log_in.html")

# Like Post Route
@app.route('/like/<int:post_id>', methods=["POST"])
def like_post(post_id):
    initialize_database()
    if "user_name" not in session:
        flash("You need to log in to like posts.", "error")
        return redirect(url_for("login"))

    user = Profile.query.filter_by(user_name=session["user_name"]).first()
    post = Post.query.get_or_404(post_id)

    # Check if the user already liked the post
    existing_like = Like.query.filter_by(post_id=post_id, user_id=user.id).first()
    if existing_like:
        db.session.delete(existing_like)
        flash("Like removed.", "info")
    else:
        new_like = Like(post_id=post_id, user_id=user.id)
        db.session.add(new_like)
        flash("Post liked!", "success")
    
    db.session.commit()
    return redirect(url_for("home"))



# Update User Name Route
@app.route('/update_name', methods=["GET", "POST"])
def update_name():
    initialize_database()

    if "user_name" not in session:
        flash("You need to log in to update your name.", "error")
        return redirect(url_for("login"))

    user = Profile.query.filter_by(user_name=session["user_name"]).first()

    if request.method == "POST":
       
        new_display_name = request.form["name"]

        # Validate input
        if not new_display_name:
            flash("Both username and display name are required.", "error")
            return redirect(url_for("update_name"))

        # Check if new username is taken
       

        # Update the user details
        
        user.display_name = new_display_name

        # Update the session
        
        session["display_name"] = new_display_name

        db.session.commit()

        flash("Username and display name updated successfully!", "success")
        return redirect(url_for("user_page", handle=session['user_name']))

    return render_template("update_name.html", user=user)


@app.route('/delete_post/<int:post_id>', methods=["POST"])
def delete_post(post_id):
    initialize_database()

    if "user_name" not in session:
        flash("You need to log in to delete a post.", "error")
        return redirect(url_for("login"))

    # Check if the user is authorized
    if session["user_name"] != "VivaPlaysYT":
        flash("You are not authorized to delete this post.", "error")
        return redirect(url_for("home"))

    # Fetch the post to delete
    post = Post.query.get_or_404(post_id)

    # Delete associated likes
    likes_to_delete = Like.query.filter_by(post_id=post.id).all()
    for like in likes_to_delete:
        db.session.delete(like)

    # Delete the post
    db.session.delete(post)
    db.session.commit()

    flash("Post deleted successfully.", "success")
    return redirect(url_for("home"))
@app.route('/edit_profile', methods=["GET", "POST"])
def edit_profile():
    initialize_database()
    
    if "user_name" not in session:
        flash("You need to log in to edit your profile.", "error")
        return redirect(url_for("login"))
    
    user = Profile.query.filter_by(user_name=session["user_name"]).first()
    
    if request.method == "POST":
        display_name = request.form["user_name"]
        avatar = request.form.get("avatar")  # Allow changing avatar
        
        if display_name:
            user.display_name = display_name
        if avatar:
            user.avatar = avatar
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("user_page", handle=user.user_name))

    return render_template("settings.html", user=user)
# Home Route
@app.route('/home')
def home():
    # Fetch a random selection of posts (e.g., 5 posts)
    random_posts = Post.query.order_by(func.random()).limit(1000).all()
    return render_template('home.html', posts=random_posts)


@app.route('/create_post', methods=["GET", "POST"])
def create_post():
    initialize_database()
    session.pop('_flashes', None)
    if "user_name" not in session:
        
        flash("You need to log in to create a post.", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        user_name = session["user_name"]
        

        user = Profile.query.filter_by(user_name=user_name).first()

        new_post = Post(title=title, content=content, user_id=user.id)
        db.session.add(new_post)
        db.session.commit()

        flash("Post created successfully!", "success")
        return redirect(url_for("user_page", handle=user_name))

    return render_template("create_post.html")

@app.route('/delete_posts/<user_name>', methods=["GET","POST"])
def delete_all_posts(user_name):
    initialize_database()

    if "user_name" not in session:
        flash("You need to log in to perform this action.", "error")
        return redirect(url_for("login"))

    # Check if the logged-in user matches the user requesting the deletion
    if session["user_name"] != "VivaPlaysYT":
        flash("You are not authorized to delete this user's posts.", "error")
        return redirect(url_for("user_page", handle=session["user_name"]))
   
    # Find the user by username
    user = Profile.query.filter_by(user_name=user_name).first()
    
    if not user:
        flash("User not found!", "error")
        return redirect(url_for("home"))

    # Delete all likes associated with the user's posts
    likes_to_delete = Like.query.filter_by(user_id=user.id).all()
    
    for like in likes_to_delete:
        db.session.delete(like)

    # Delete all posts by this user
    posts_to_delete = Post.query.filter_by(user_id=user.id).all()
    
    for post in posts_to_delete:
        db.session.delete(post)
    Profile.query.filter_by(user_name=user_name).delete()
    db.session.commit()
    flash("All posts and likes deleted successfully.", "success")

    return redirect(url_for("user_page", handle=user_name))




# Login Route
@app.route('/login', methods=["GET", "POST"])
def login():
    initialize_database()
    if request.method == "POST":
        user_name = request.form.get("handle")
        pass_word = request.form.get("pass_word")

        user = Profile.query.filter_by(user_name=user_name).first()

        if user and check_password_hash(user.pass_word, pass_word):
            session["user_name"] = user.user_name
            session['user_id'] = user.id
            session["display_name"] = user.display_name
            flash("Logged in successfully!", "success")
            return redirect(url_for("user_page", handle=user.user_name))
        else:
            print("invalid user or pass!")
            flash("Invalid username or password!", "error")
            return redirect(url_for("login"))
    return render_template("Log_in.html")

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("index"))

# Register Route
@app.route('/register', methods=["GET", "POST"])
def register():
    initialize_database()
    if request.method == "POST":
        user_name = request.form["handle"]
        display_name = request.form["user_name"]
        pass_word = request.form["pass_word"]
        avatar = request.form.get("avatar")  # Avatar URL or path if provided

        if not user_name or not display_name or not pass_word:
            flash("All fields are required!", "error")
            return redirect(url_for("register"))

        if Profile.query.filter_by(user_name=user_name).first():
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        new_user = Profile(user_name=user_name, display_name=display_name, pass_word=pass_word, avatar=avatar)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")
# User Profile Route
@app.route('/users/<handle>')
def user_page(handle):
    initialize_database()
    if "user_name" not in session:
        flash("You need to log in to view this page.", "error")
        return redirect(url_for("login"))
    
    profile = Profile.query.filter_by(user_name=handle).first()
    if not profile:
        return render_template("404.html", url=handle), 404

    # Get followers and following count
    followers_count = Follow.query.filter_by(followed_id=profile.id).count()
    following_count = Follow.query.filter_by(follower_id=profile.id).count()

    # Check if the logged-in user is following the profile
    is_following = Follow.query.filter_by(follower_id=session['user_id'], followed_id=profile.id).first() is not None

    # Default to "none" for avatar if not set
    avatar_url = profile.avatar if profile.avatar else "none"

    return render_template("User.html", name=profile.display_name, avatar=avatar_url, id=profile.id, handle=handle, posts=profile.posts, followers_count=followers_count, following_count=following_count, is_following=is_following)

@app.route('/increase_followers/<string:user_name>/<int:number>', methods=["GET"])
def increase_followers(user_name, number):
    initialize_database()

    if "user_name" not in session or session['user_name']!="VivaPlaysYT":
        flash("You need to log in to perform this action.", "error")
        return redirect(url_for("login"))

    logged_in_user = Profile.query.filter_by(user_name=session["user_name"]).first()

    # Get the user for whom the followers count is to be increased using the username
    user_to_increase = Profile.query.filter_by(user_name=user_name).first()
    if not user_to_increase:
        flash("User not found!", "error")
        return redirect(url_for("home"))

    for _ in range(number):
        # Create fake follow relationships where the logged-in user is the follower
        new_follow = Follow(follower_id=logged_in_user.id, followed_id=user_to_increase.id)
        db.session.add(new_follow)

    db.session.commit()
    flash(f"Successfully increased followers count for {user_to_increase.user_name} by {number}.", "success")
    
    # After modifying, redirect back to the user's profile page
    return redirect(url_for("user_page", handle=user_to_increase.user_name))

# Follow/Unfollow Route
@app.route('/follow/<int:user_id>', methods=["POST"])
def follow_user(user_id):
    initialize_database()

    if "user_name" not in session:
        flash("You need to log in to follow users.", "error")
        return redirect(url_for("login"))

    logged_in_user = Profile.query.filter_by(user_name=session["user_name"]).first()
    
    # Check if the user is already following
    follow_relation = Follow.query.filter_by(follower_id=logged_in_user.id, followed_id=user_id).first()
    
    if follow_relation:
        db.session.delete(follow_relation)
        flash("Unfollowed the user.", "info")
    else:
        new_follow = Follow(follower_id=logged_in_user.id, followed_id=user_id)
        db.session.add(new_follow)
        flash("Followed the user.", "success")
    
    db.session.commit()
    return redirect(url_for("user_page", handle=logged_in_user.user_name))
if __name__ == "__main__":
    initialize_database()
    app.run(host='0.0.0.0', port=81)

