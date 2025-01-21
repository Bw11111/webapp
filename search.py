@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        flash("Please enter a search term.", "error")
        return redirect(url_for("home"))
    
    # Search for profiles with a matching username or display name
    profiles = Profile.query.filter(
        (Profile.user_name.like(f"%{query}%")) | 
        (Profile.display_name.like(f"%{query}%"))
    ).all()

    # Search for posts with a matching title or content
    posts = Post.query.filter(
        (Post.title.like(f"%{query}%")) | 
        (Post.content.like(f"%{query}%"))
    ).all()

    return render_template("search_results.html", query=query, profiles=profiles, posts=posts)
