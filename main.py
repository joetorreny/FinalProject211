from flask import Flask, redirect, render_template, request, session
import sqlite3

app = Flask(__name__)
my_db = None
logged_in = False
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
show_posts_un_published = False


@app.route('/')
def index():
    return redirect("/login")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "id" in session:
            return redirect("/dashboard")
        return render_template("login.html")
    username = request.form["username"]
    password = request.form["password"]
    user_id = my_db.get_user_id(username, password)
    if user_id is not None:
        session["id"] = user_id
        return redirect("/dashboard")
    return redirect("/login")


@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    if "id" not in session:
        return redirect("/login")
    user_id = session["id"]
    posts = my_db.get_posts_by_user_id(user_id)
    good_posts = list()
    for post in posts:
        if show_posts_un_published or post.visible == 1:
            good_posts.append(post)
    return render_template("dashboard.html", posts=good_posts)


@app.route('/post/add', methods=["GET", "POST"])
def add_post():
    if "id" not in session:
        return redirect("/login")
    user_id = session["id"]
    if request.method == "GET":
        all_categories = my_db.get_all_categories()
        return render_template("post_add.html", categories=all_categories)
    title = request.form["title"]
    content = request.form["content"]
    date = request.form["date"]
    category_id = request.form["category_id"]
    category_name = "categoriis saxeli davikidot"
    post = Post(title, content, date, category=Category(category_name, category_id))
    my_db.add_post_to_user(post, user_id)
    return redirect("/dashboard")


@app.route('/post/delete', methods=["POST"])
def delete_post():
    post_id = request.form["post_id"]
    my_db.delete_post(post_id)
    return redirect("/dashboard")


@app.route('/post/edit', methods=["GET", "POST"])
def edit_post():
    if "id" not in session:
        return redirect("/login")
    if request.method == "GET":
        my_categories = my_db.get_all_categories()
        cur_post = construct_post(request.args)
        cur_post.category = Category(request.args["name"], int(request.args["category_id"]))
        return render_template("post_edit.html", post=cur_post, categories=my_categories)
    post = construct_post(request.form)
    post.category = Category("", request.form["category_id"])
    my_db.update_post(post)
    return redirect("/dashboard")


def construct_post(arg_dict):
    return Post(arg_dict["title"], arg_dict["content"], arg_dict["date"], arg_dict["post_id"])


@app.route('/post/un_publish', methods=["POST"])
def un_publish_post():
    post_id = request.form["post_id"]
    my_db.change_post_state(post_id, 0)
    return redirect("/dashboard")


@app.route('/post/publish', methods=["POST"])
def publish_post():
    post_id = request.form["post_id"]
    my_db.change_post_state(post_id, 1)
    return redirect("/dashboard")


@app.route('/show_un_published_posts')
def show_un_published_posts():
    global show_posts_un_published
    show_posts_un_published = 1
    return redirect("/dashboard")


@app.route('/hide_un_published_posts')
def hide_un_published_posts():
    global show_posts_un_published
    show_posts_un_published = 0
    return redirect("/dashboard")


@app.route('/categories')
def categories():
    if "id" not in session:
        return redirect("/login")
    user_categories = my_db.get_all_categories()
    return render_template("categories.html", categories=user_categories)


@app.route('/category/add', methods=["POST"])
def add_category():
    category_name = request.form["name"]
    my_db.add_category(category_name)
    return redirect("/categories")


@app.route('/category/delete', methods=["POST"])
def delete_category():
    category_id = request.form["category_id"]
    my_db.delete_category(category_id)
    return redirect("/categories")


class MyDatabase:
    def __init__(self,):
        with sqlite3.connect("my_db.db") as connection:
            self.connection = connection
            self.create_tables()
            self.insert_first_users()

    def delete_category(self, category_id):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM Category where id=?", [category_id])
        self.connection.commit()

    def add_category(self, name):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO Category(name) values(?)", [name])
        self.connection.commit()

    def get_all_categories(self):
        cursor = self.connection.cursor()
        result = cursor.execute("select name, id from Category").fetchall()
        user_categories = [Category(cur[0], cur[1]) for cur in result]
        return user_categories

    def change_post_state(self, post_id, state_id):
        cursor = self.connection.cursor()
        cursor.execute("UPDATE post SET visible=? where id=?", [state_id, post_id])
        self.connection.commit()

    def update_post(self, post):
        cursor = self.connection.cursor()
        cursor.execute("UPDATE post SET title=?, content=?, date=?, category_id=? where id=?",
                       [post.title, post.content, post.date, post.category.category_id, int(post.post_id)])
        self.connection.commit()

    def delete_post(self, post_id):
        cursor = self.connection.cursor()
        cursor.execute("DELETE from post where id=?", [post_id])
        self.connection.commit()

    def add_post_to_user(self, post, user_id):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO post(title, content, date, user_id, visible, category_id) VALUES (?,?,?,?,?,?)",
                       [post.title, post.content, post.date, int(user_id), post.visible, post.category.category_id])
        self.connection.commit()

    def get_posts_by_user_id(self, user_id):
        cursor = self.connection.cursor()
        posts = cursor.execute("SELECT title, content, date, post.id, visible, name,category.id as c_id FROM post "
                               "INNER JOIN category on post.category_id = category.id where user_id=?",
                               [int(user_id)]).fetchall()
        real_posts = [Post(post[0], post[1], post[2], post[3], post[4], Category(post[5], post[6])) for post in posts]
        return real_posts

    def get_user_id(self, username, password):
        cursor = self.connection.cursor()
        user_id = cursor.execute("SELECT id FROM user WHERE username=? and password=?", [username, password]).fetchone()
        if user_id is None:
            return None
        return user_id[0]

    def create_tables(self):
        cursor = self.connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS Post(id INTEGER PRIMARY KEY, title TEXT, content TEXT,"
                       "date DATETIME, user_id INTEGER, visible INTEGER, category_id INTEGER,"
                       " FOREIGN KEY(category_id) REFERENCES Category(id), FOREIGN KEY(user_id) REFERENCES User(id));")
        cursor.execute("CREATE TABLE IF NOT EXISTS User(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Category(id INTEGER PRIMARY KEY, name TEXT)")

    def insert_first_users(self):
        cursor = self.connection.cursor()
        # creating some users

        # admin password
        cursor.execute("INSERT OR IGNORE INTO User(username, password) VALUES('admin', 'password')")
        # admin1 password1
        cursor.execute("INSERT OR IGNORE INTO User(username, password) VALUES('admin1', 'password1')")
        # admin2 password2
        cursor.execute("INSERT OR IGNORE INTO User(username, password) VALUES('admin2', 'password2')")

        cursor.execute("INSERT OR IGNORE INTO Category(id, name) VALUES(1,'normal')")


class Post:
    def __init__(self, title, content, date, post_id=None, visible=1, category=None):
        self.title = title
        self.content = content
        self.date = date
        self.post_id = post_id
        self.visible = visible
        self.category = category


class Category:
    def __init__(self, name, category_id=None):
        self.name = name
        self.category_id = category_id


def main():
    global my_db
    my_db = MyDatabase()
    app.run()


if __name__ == "__main__":
    main()
