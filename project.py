import os
from functools import wraps

from flask import Flask, render_template, request, \
    redirect, url_for, session, abort, jsonify, request
import pymysql
from flask_cors import CORS
from datetime import timedelta

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=10)

cors_config = CORS(app, resources={r"/*": {"origins": "*"}})

app.secret_key = 'securekey'
app.config["JWT_SECRET_KEY"] = "ultra-secret"
app.config['MAX_FILE_SIZE'] = 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = ['.jpg', '.jpeg', '.pdf' , '.png']
app.config['FILES_DIR'] = 'uploaded_files'

jwt = JWTManager(app)

db_conn = pymysql.connect(
    host='localhost',
    user='root',
    password="newpassword",
    db='web_backend',
    cursorclass=pymysql.cursors.DictCursor
)
db_cursor = db_conn.cursor()

@app.route("/")
def landing_page():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register_user():
    user_table = '''CREATE TABLE users(id int NOT NULL AUTO_INCREMENT PRIMARY KEY, name varchar(50) NOT NULL, 
                    password varchar(255) NOT NULL, email_id varchar(100) NOT NULL, org_name varchar(100), 
                    street_address varchar (100), city_name varchar (100), state_name varchar (100), 
                    nation varchar (100), zip_code varchar(6))'''
    db_cursor.execute(user_table)
    
    sample_users = [
        ('1', 'Alice', 'pwd1', 'alice@example.com', 'Org1', 'Street1', 'City1', 'State1', 'Country1', '100001'),
        ('2', 'Bob', 'pwd2', 'bob@example.com', 'Org2', 'Street2', 'City2', 'State2', 'Country2', '100002'),
        ('3', 'Charlie', 'pwd3', 'charlie@example.com', 'Org3', 'Street3', 'City3', 'State3', 'Country3', '100003')
    ]
    
    insert_statement = '''INSERT INTO users values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
    db_cursor.executemany(insert_statement, sample_users)
    
    return jsonify({"message": "User Registered!"})

@app.route("/signin", methods=["POST"])
def authenticate():
    if request.method == 'POST':
        user_name = request.json.get("name", None)
        pwd = request.json.get("password", None)
        
        query = 'SELECT * FROM users WHERE name = %s AND password = %s'
        db_cursor.execute(query, (user_name, pwd))
        db_conn.commit()
        
        user = db_cursor.fetchone()
        if user:
            session.permanent = True
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            
            token = create_access_token(identity=user_name)
            return jsonify(token=token)
        else:
            return jsonify({"message": "Invalid credentials"}), 401

@app.route("/secure-data", methods=["GET"])
@jwt_required()
def access_secure_data():
    logged_user = get_jwt_identity()
    return jsonify(user=logged_user), 200

def require_role(role):
    def decorator(fn):
        @wraps(fn)
        def check_role(*args, **kwargs):
            uname = request.json.get("name", None)
            if uname != 'Charlie':
                abort(401)
            return fn(*args, **kwargs)
        return check_role
    return decorator

@app.route('/only-for-admin', methods=["POST"])
@require_role('admin')
def admin_only_route():
    db_cursor.execute('SELECT * FROM users')
    fetched_users = db_cursor.fetchall()
    return jsonify(users=fetched_users)

@app.route("/add-item", methods=['POST'])
@require_role('admin')
def add_data():
    create_item_table = '''CREATE TABLE items(item_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, 
                            item_name VARCHAR(20), item_desc TEXT, barcode_info TEXT, cost INT)'''
    try:
        db_cursor.execute(create_item_table)
    except:
        return "Items table already exists."
    
    items_data = [
        ('1', 'Mobile', 'Mobile Description', '123ABC', '250'),
        ('2', 'Computer', 'Computer Description', '456DEF', '450'),
        ('3', 'Charger', 'Charger Description', "789GHI", '50')
    ]
    
    insert_items = "INSERT INTO items values(%s,%s,%s,%s,%s)"
    db_cursor.executemany(insert_items, items_data)
    
    return jsonify("Items Added!")

@app.route('/file-upload', methods=['POST'])
@jwt_required()
def handle_upload():
    file = request.files['datafile']
    fname = secure_filename(file.filename)
    
    if os.path.splitext(fname)[1] not in app.config['ALLOWED_EXTENSIONS']:
        abort(400, "Unsupported File Type")
    
    file.save(os.path.join(app.config['FILES_DIR'], fname))
    return jsonify({"message": "File Successfully Uploaded"}), 200

@app.route("/public-items", methods=['GET'])
def get_public_items():
    try:
        db_cursor.execute('SELECT * FROM items')
    except:
        return 'Error fetching items.'
    
    items = []
    for record in db_cursor.fetchall():
        items.append(record)
    return jsonify(items)

# Error Handlers
@app.errorhandler(400)
def handle_400(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def handle_404(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(401)
def handle_401(e):
    return jsonify(error=str(e)), 401

@app.errorhandler(403)
def handle_403(e):
    return jsonify(error=str(e)), 403

@app.errorhandler(500)
def handle_500(e):
    return jsonify(error=str(e)), 500

@app.errorhandler(405)
def handle_405(e):
    return jsonify(error=str(e)), 405



if __name__ == "__main__":
    app.run(debug=True)
