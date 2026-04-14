from flask import Flask,render_template,request,redirect, session,flash
import mysql.connector
from model import predict_student
from flask_mail import Mail, Message
from datetime import datetime
from datetime import timedelta
import random
import pandas as pd
import time
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor


   
        
import joblib
import csv
import os
import string
import random


app=Flask(__name__)
app.secret_key="secretkey"

# session timeout 30 minutes
app.permanent_session_lifetime = timedelta(minutes=30)


# db=mysql.connector.connect(
# host="localhost",
# user="root",
# password="root1234",
# database="student_ai"
# )

# cursor=db.cursor()

# cursor = db.cursor(dictionary=True)
def get_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root1234",
        database="student_ai"
    )
    return db, db.cursor(dictionary=True)

 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "apex.instituteiit@gmail.com"
app.config['MAIL_PASSWORD'] = "ouinxhmcjgmwtpfu"

mail = Mail(app)



@app.route('/')
def home():

    db, cursor = get_db()

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT AVG(total) AS avg_score FROM marks")
    avg_score = cursor.fetchone()['avg_score'] or 0

    cursor.execute("SELECT MIN(rank_no) AS top_rank FROM marks WHERE rank_no > 0")
    top_rank = cursor.fetchone()['top_rank'] or 0

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        total_students=total_students,
        avg_score=round(avg_score,2),
        top_rank=top_rank
    )
    
    
    
# _______________________________________________
                    #dashboard
# _______________________________________________
@app.route('/dashboard')
def dashboard():

    db, cursor = get_db()

    cursor.execute("SELECT * FROM marks ORDER BY total DESC")
    data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("dashboard.html", data=data)

#__________________end dashboard_____________________ 





# _____________________________________________
                #Student Login
# _______________________________________________

@app.route('/login',methods=['GET','POST'])
def login():

    if request.method=="POST":

        sid = request.form['student_id']
        password = request.form['password']

        db, cursor = get_db()

        cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (sid,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user['password'], password):

            session.permanent = True
            session['student_id'] = sid

            return redirect('/student_dashboard')

        else:

            flash("Invalid Student Id or Password","danger")
            return redirect('/login')

    return render_template("login.html")
# _______________end login___________________







# _______________________________________________
        # Student Dashboard Backend
# _______________________________________________
@app.route('/student_dashboard')
def student_dashboard():

    if 'student_id' not in session:
        return redirect('/login')

    sid = session['student_id']

    db, cursor = get_db()

    # student details
    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (sid,)
    )
    student = cursor.fetchone()

    # student marks
    cursor.execute(
        "SELECT * FROM marks WHERE student_id=%s",
        (sid,)
    )
    marks = cursor.fetchone()

    if not marks:
        marks = {
            "maths": 0,
            "physics": 0,
            "chemistry": 0,
            "biology": 0,
            "total": 0,
            "rank_no": "-"
        }

    # leaderboard top 5
    cursor.execute("""
    SELECT students.name, marks.student_id, marks.total, marks.rank_no
    FROM marks
    JOIN students
    ON marks.student_id = students.student_id
    ORDER BY marks.total DESC
    LIMIT 5
    """)

    leaderboard = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "student_dashboard.html",
        data=student,
        marks=marks,
        leaderboard=leaderboard
    )
# _____________end Student Dashboard Backend_____________________





# _______________________________________________
                    # logout
# _______________________________________________
@app.route('/logout')

def logout():

    session.clear()

    return redirect('/')
# _____________end logout_______________





# _______________________________________________
                #student profile
# _______________________________________________
@app.route('/profile', methods=['GET','POST'])
def profile():

    if 'student_id' not in session:
        return redirect('/login')

    sid = session['student_id']

    db, cursor = get_db()

    if request.method == "POST":

        mobile = request.form.get('mobile') or None
        email = request.form.get('email') or None
        gender = request.form.get('gender') or None
        father_name = request.form.get('father_name') or None
        batch = request.form.get('batch') or None
        admission_date = request.form.get('admission_date') or None
        address = request.form.get('address') or None
        dob = request.form.get('dob') or None

        photo = request.files.get('photo')
        filename = None

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join("static/profile", filename))

        sql = """
        UPDATE students
        SET mobile = COALESCE(%s,mobile),
            email = COALESCE(%s,email),
            gender = COALESCE(%s,gender),
            father_name = COALESCE(%s,father_name),
            batch = COALESCE(%s,batch),
            admission_date = COALESCE(%s,admission_date),
            address = COALESCE(%s,address),
            dob = COALESCE(%s,dob),
            photo = COALESCE(%s,photo)
        WHERE student_id=%s
        """

        cursor.execute(sql,(
            mobile,
            email,
            gender,
            father_name,
            batch,
            admission_date,
            address,
            dob,
            filename,
            sid
        ))

        db.commit()

        flash("Profile Updated Successfully","success")

    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (sid,)
    )

    data = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template("student_profile.html", data=data)
# _______________end student profile_______________






# _______________________________________________
            # user change Password
# _______________________________________________


@app.route('/change_password', methods=['POST'])
def change_password():

    if 'student_id' not in session:
        return {"message":"Login required"}

    db, cursor = get_db()

    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')

    # password match check
    if new != confirm:
        cursor.close()
        db.close()
        return {"message":"New password and confirm password do not match"}

    # get current password from database
    cursor.execute(
        "SELECT password FROM students WHERE student_id=%s",
        (session['student_id'],)
    )

    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        return {"message":"User not found"}

    # check old password
    if not check_password_hash(user['password'], current):
        cursor.close()
        db.close()
        return {"message":"Current password incorrect"}

    # hash new password
    new_hash = generate_password_hash(new)

    # update password
    cursor.execute(
        "UPDATE students SET password=%s WHERE student_id=%s",
        (new_hash, session['student_id'])
    )

    db.commit()

    cursor.close()
    db.close()

    return {"message":"Password updated successfully"}
            
# _______________________________________________        
            
            

# _______________________________________________
            # Send OTP During Signup
# _______________________________________________
@app.route('/signup', methods=['GET','POST'])
def signup():

    if request.method == "POST":

        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']

        # generate OTP
        otp = random.randint(100000,999999)

        session['otp'] = otp
        session['otp_time'] = time.time()

        session['signup_data'] = {
            "name": name,
            "mobile": mobile,
            "email": email,
            "password": generate_password_hash(password)
        }

        msg = Message(
            "OTP Verification - Apex Institute",
            sender = app.config['MAIL_USERNAME'],
            recipients = [email]
        )

        msg.body = f"""
Your OTP Verification Code

OTP : {otp}

This OTP will expire in 5 minutes.
"""

        mail.send(msg)

        flash("OTP sent to your email","success")

        return redirect('/verify_otp')

    return render_template("signup.html")
# ____________end signup_____________________________






# _______________________________________________
            #OTP Verification Route
# _______________________________________________
@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():

    db, cursor = get_db()

    # initialize attempt tracking
    if 'otp_attempts' not in session:
        session['otp_attempts'] = 0
        session['otp_first_try_time'] = time.time()

    # block if 3 attempts within 1 hour
    if session['otp_attempts'] >= 3:

        if time.time() - session['otp_first_try_time'] < 3600:
            flash("Too many wrong OTP attempts. Try again after 1 hour.","danger")
            cursor.close()
            db.close()
            return render_template("verify_otp.html")

        else:
            session['otp_attempts'] = 0
            session['otp_first_try_time'] = time.time()


    if request.method == "POST":

        user_otp = request.form['otp']

        if 'otp' not in session:
            flash("Session expired. Signup again.","danger")
            cursor.close()
            db.close()
            return redirect('/signup')

        if time.time() - session['otp_time'] > 300:
            flash("OTP expired. Try again.","danger")
            cursor.close()
            db.close()
            return redirect('/signup')

        if int(user_otp) == session['otp']:

            # reset attempts
            session.pop('otp_attempts', None)
            session.pop('otp_first_try_time', None)

            data = session['signup_data']
            year = datetime.now().year

            cursor.execute(
                "SELECT student_id FROM students WHERE student_id LIKE %s ORDER BY student_id DESC LIMIT 1",
                ("STU"+str(year)+"%",)
            )

            last = cursor.fetchone()

            if last:
                last_num = int(last['student_id'][-3:])
                new_num = last_num + 1
            else:
                new_num = 1

            student_id = "STU" + str(year) + f"{new_num:03d}"

            sql = """
            INSERT INTO students
            (student_id,name,mobile,email,password)
            VALUES(%s,%s,%s,%s,%s)
            """

            val = (
                student_id,
                data['name'],
                data['mobile'],
                data['email'],
                data['password']
            )

            cursor.execute(sql, val)
            db.commit()

            msg = Message(
                "Welcome to Apex Institute",
                sender=app.config['MAIL_USERNAME'],
                recipients=[data['email']]
            )

            msg.html = f"""
            <h2>Welcome to Apex Institute 🎓</h2>
            <p>Hello <b>{data['name']}</b>,</p>

            <p>Your account has been successfully created.</p>

            <h3 style="color:#26a69a;">Your Student ID: {student_id}</h3>

            <p>Please use this Student ID to login.</p>

            <a href="http://127.0.0.1:5000/login"
            style="background:#26a69a;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">
            Login Now
            </a>
            """

            mail.send(msg)

            flash({
                "name": data['name'],
                "email": data['email'],
                "id": student_id
            }, "student_data")

            session.pop('otp', None)
            session.pop('signup_data', None)
            session.pop('otp_time', None)

            cursor.close()
            db.close()

            return redirect('/login')

        else:

            session['otp_attempts'] += 1
            remaining = 3 - session['otp_attempts']

            if remaining > 0:
                flash(f"Invalid OTP. {remaining} attempt(s) left.","danger")
            else:
                flash("Too many wrong OTP attempts. Try again after 1 hour.","danger")

    cursor.close()
    db.close()

    return render_template("verify_otp.html")
# __________end_ verify_otp________________







# _______________________________________________
                # RESEND OTP 
# _______________________________________________

@app.route('/resend_otp')
def resend_otp():

    # session check
    if 'signup_data' not in session:
        flash("Session expired. Signup again.","danger")
        return redirect('/signup')

    # resend limit (1 minute)
    if 'otp_time' in session:
        if time.time() - session['otp_time'] < 60:
            flash("Wait 1 minute before requesting new OTP","warning")
            return redirect('/verify_otp')

    email = session['signup_data']['email']

    # generate new OTP
    otp = random.randint(100000,999999)

    session['otp'] = otp
    session['otp_time'] = time.time()

    msg = Message(
        "Resend OTP - Apex Institute",
        sender = app.config['MAIL_USERNAME'],
        recipients = [email]
    )

    msg.body = f"""
Your New OTP Code

OTP : {otp}

This OTP will expire in 5 minutes.
"""

    mail.send(msg)

    flash("New OTP sent to your email","success")

    return redirect('/verify_otp')
# _______________end___RESEND____OTP______________________






# _______________________________________________
              #forgot_password
# _______________________________________________
@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():

    if request.method == "POST":

        email = request.form['email']

        # generate OTP
        otp = random.randint(100000,999999)

        session['reset_otp'] = otp
        session['reset_email'] = email
        session['reset_time'] = time.time()

        msg = Message(
            "Password Reset OTP",
            sender = app.config['MAIL_USERNAME'],
            recipients = [email]
        )

        msg.body = f"""
Your Password Reset OTP

OTP : {otp}

This OTP will expire in 5 minutes.
"""

        mail.send(msg)

        flash("OTP sent to your email","success")

        return redirect('/reset_password')

    return render_template("forgot_password.html")
# ______________end forgot_password_____________






# _______________________________________________
            # Reset Password Backend
# _______________________________________________
@app.route('/reset_password',methods=['GET','POST'])
def reset_password():

    if request.method == "POST":

        otp = request.form['otp']
        password = request.form['password']

        # session check
        if 'reset_otp' not in session or 'reset_email' not in session:
            flash("Session expired. Try again.","danger")
            return redirect('/forgot_password')

        if int(otp) == session['reset_otp']:

            db, cursor = get_db()

            email = session['reset_email']
            hashed = generate_password_hash(password)

            sql = "UPDATE students SET password=%s WHERE email=%s"
            cursor.execute(sql,(hashed,email))

            db.commit()

            cursor.close()
            db.close()

            # clear session
            session.pop('reset_otp',None)
            session.pop('reset_email',None)

            flash("Password reset successfully","success")

            return redirect('/login')

        else:

            flash("Invalid OTP","danger")

    return render_template("reset_password.html")
#_____________end Reset Password Backend__________ 



    
    
    
    
# _______________________________________________   
                # admin login   
# _______________________________________________
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        db, cursor = get_db()

        sql = "SELECT * FROM admin WHERE username=%s AND password=%s"
        cursor.execute(sql,(username,password))

        admin = cursor.fetchone()

        cursor.close()
        db.close()

        if admin:

            session['admin'] = admin['username']

            return redirect('/admin_panel')

        else:

            return render_template(
                "admin_login.html",
                error="Invalid Admin Login"
            )

    return render_template("admin_login.html")


 # __________end _admin login route_________________






# _______________________________________________
        # Admin Panel Route (Protected)
# _______________________________________________

@app.route('/admin_panel')
def admin_panel():

    if 'admin' not in session:
        return redirect('/admin_login')

    update_rank()

    db, cursor = get_db()

    # total students
    cursor.execute("SELECT COUNT(*) AS total_students FROM students")
    total_students = cursor.fetchone()['total_students']

    # topper
    cursor.execute("""
    SELECT students.name, marks.total
    FROM marks
    JOIN students ON marks.student_id = students.student_id
    ORDER BY marks.total DESC
    LIMIT 1
    """)
    topper = cursor.fetchone()

    # average marks
    cursor.execute("SELECT AVG(total) AS avg_marks FROM marks")
    avg_marks = cursor.fetchone()['avg_marks']

    # subject data for chart
    cursor.execute("""
    SELECT 
    AVG(maths) AS maths,
    AVG(physics) AS physics,
    AVG(chemistry) AS chemistry,
    AVG(biology) AS biology
    FROM marks
    """)
    chart = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "admin_panel.html",
        total_students=total_students,
        topper=topper,
        avg_marks=round(avg_marks or 0,2),
        chart=chart
    )

# ____________end Admin Panel Route (Protected)_____________________





# _______________________________________________
                # Admin Logout
# _______________________________________________
@app.route('/admin_logout')
def admin_logout():


     # remove admin session
    session.pop('admin', None)

    return redirect('/admin_login')

# __________end Admin Logout_______________________






# _______________________________________________

            # admin student detail
# _______________________________________________

@app.route('/admin_settings')
def admin_settings():

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    search = request.args.get('search','')
    batch = request.args.get('batch','')
    gender = request.args.get('gender','')

    sql = "SELECT * FROM students WHERE 1=1"
    params = []

    # SEARCH FILTER
    if search:
        sql += " AND (name LIKE %s OR student_id LIKE %s OR email LIKE %s)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    # BATCH FILTER
    if batch:
        sql += " AND batch=%s"
        params.append(batch)

    # GENDER FILTER
    if gender:
        sql += " AND gender=%s"
        params.append(gender)

    cursor.execute(sql, params)

    students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_settings.html",
        students=students
    ) 
    
# _____________end admin student detail____________






# _______________________________________________
            # admin Edit Student Route  
# _______________________________________________
@app.route('/edit_student/<student_id>', methods=['GET','POST'])
def edit_student(student_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    if request.method == "POST":

        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        gender = request.form.get('gender')
        dob = request.form.get('dob')
        father_name = request.form.get('father_name')
        address = request.form.get('address')
        batch = request.form.get('batch')

        # FIX DOB ERROR
        if dob == "":
            dob = None

        cursor.execute("""
        UPDATE students
        SET
        name = COALESCE(%s,name),
        email = COALESCE(%s,email),
        mobile = COALESCE(%s,mobile),
        gender = COALESCE(%s,gender),
        dob = COALESCE(%s,dob),
        father_name = COALESCE(%s,father_name),
        address = COALESCE(%s,address),
        batch = COALESCE(%s,batch)
        WHERE student_id=%s
        """,(name,email,mobile,gender,dob,father_name,address,batch,student_id))

        db.commit()

        flash("Student details updated successfully","success")

        cursor.close()
        db.close()

        return redirect('/admin_settings')

    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "admin_edit_student.html",
        student=student
    )
# ____________end admin  edit student detail________





# _________________________________________________
            # add_student_admin
# _________________________________________________
@app.route('/add_student_admin', methods=['GET','POST'])
def add_student_admin():

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    if request.method == "POST":

        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        gender = request.form.get('gender')
        batch = request.form.get('batch')
        address = request.form.get('address')

        # -------- Profile Photo Upload --------
        photo = request.files.get('photo')
        filename = None

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join("static/profile", filename))

        # -------- Generate Student ID --------
        year = datetime.now().year

        cursor.execute(
        "SELECT student_id FROM students WHERE student_id LIKE %s ORDER BY student_id DESC LIMIT 1",
        ("STU"+str(year)+"%",)
        )

        last = cursor.fetchone()

        if last:
            last_num = int(last['student_id'][-3:])
            new_num = last_num + 1
        else:
            new_num = 1

        student_id = "STU" + str(year) + f"{new_num:03d}"

        # -------- Generate Password --------
        raw_password = generate_password()
        hashed_password = generate_password_hash(raw_password)

        # -------- Insert Student --------
        cursor.execute("""
        INSERT INTO students
        (student_id,name,email,mobile,gender,batch,address,photo,password)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,(student_id,name,email,mobile,gender,batch,address,filename,hashed_password))

        db.commit()

        # -------- Send Email --------
        msg = Message(
        "Your Apex Institute Account",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
        )

        msg.html = f"""
        <h2>Welcome to Apex Institute</h2>

        <p>Your account has been created.</p>

        <b>Student ID :</b> {student_id}<br>
        <b>Password :</b> {raw_password}

        <br><br>

        <a href="http://127.0.0.1:5000/login">
        Login Now
        </a>
        """

        mail.send(msg)

        cursor.close()
        db.close()

        # AJAX response
        return {"status":"success"}

    cursor.close()
    db.close()

    return render_template("add_student_admin.html")
# ________________end __add_student_admin_______________________________





# _______________________________________________
            # generate_password
# _______________________________________________


def generate_password(length=10):

    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "@#$%&*!?"

    all_chars = lower + upper + digits + special

    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special)
    ]

    password += random.choices(all_chars, k=length-4)

    random.shuffle(password)

    return "".join(password)
# _____________end generate_password__________________________________








# _______________________________________________
            # Delete Student Route
# _______________________________________________
@app.route('/delete_student/<student_id>', methods=['POST'])
def delete_student(student_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    if student:

        cursor.execute(
            "DELETE FROM students WHERE student_id=%s",
            (student_id,)
        )

        db.commit()

        flash("Student deleted successfully","success")

    else:

        flash("Student not found","danger")

    cursor.close()
    db.close()

    return redirect('/admin_settings')
# __________end Delete Student Route________

    
    
    
    
    
# _______________________________________________
                # upload_marks_page
# _______________________________________________ 

@app.route('/upload_marks_page')
def upload_marks_page():

    if 'admin' not in session:
        flash("Admin login required","danger")
        return redirect('/admin_login')

    return render_template("admin_upload_marks.html")
    
# @app.route('/upload_marks_page')
# def upload_marks_page():

#     if 'admin' not in session:
#         return redirect('/admin_login')

#     return render_template("admin_upload_marks.html")
# ________________upload_marks_page _________________
                
    
    
    
    
    
# _______________________________________________
                # Admin Add Marks
# _______________________________________________
@app.route('/add_marks', methods=['POST'])
def add_marks():

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    sid = request.form.get('student_id')

    # ✔ Check student exist
    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (sid,)
    )

    student = cursor.fetchone()

    if not student:
        cursor.close()
        db.close()
        flash("Student ID not found","danger")
        return redirect('/admin_panel')

    m = int(request.form.get('maths'))
    p = int(request.form.get('physics'))
    c = int(request.form.get('chemistry'))
    b = int(request.form.get('biology'))

    total = m + p + c + b

    sql = """
    INSERT INTO marks
    (student_id,maths,physics,chemistry,biology,total)
    VALUES(%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(sql,(sid,m,p,c,b,total))

    db.commit()

    cursor.close()
    db.close()

    update_rank()

    return redirect('/admin_panel')
# ___________end add_marks______________
    
    
    
    



# _______________________________________________
                # Admin upload_marks (Add Marks)
# _______________________________________________
@app.route('/upload_marks', methods=['POST'])
def upload_marks():

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    file = request.files['file']

    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    for index, row in df.iterrows():

        sid = row['student_id']

        # student exist check
        cursor.execute(
            "SELECT * FROM students WHERE student_id=%s",
            (sid,)
        )

        student = cursor.fetchone()

        if student:

            maths = int(row['maths'])
            physics = int(row['physics'])
            chemistry = int(row['chemistry'])
            biology = int(row['biology'])

            total = maths + physics + chemistry + biology

            # check marks already exist
            cursor.execute(
                "SELECT * FROM marks WHERE student_id=%s",
                (sid,)
            )

            existing = cursor.fetchone()

            if existing:

                # update marks
                cursor.execute("""
                UPDATE marks
                SET maths=%s,
                    physics=%s,
                    chemistry=%s,
                    biology=%s,
                    total=%s
                WHERE student_id=%s
                """,(maths,physics,chemistry,biology,total,sid))

            else:

                # insert marks
                cursor.execute("""
                INSERT INTO marks
                (student_id,maths,physics,chemistry,biology,total)
                VALUES(%s,%s,%s,%s,%s,%s)
                """,(sid,maths,physics,chemistry,biology,total))

    db.commit()

    cursor.close()
    db.close()

    update_rank()

    flash("Marks uploaded successfully","success")

    return redirect('/student_records')
 #__________end Admin upload_marks (Add Marks)______________
    
    
    
    
    
    
    
    
    
# _______________________________________________
            # add marks get_student_name
# _______________________________________________
@app.route('/get_student_name', methods=['POST'])
def get_student_name():

    db, cursor = get_db()

    student_id = request.form['student_id']

    cursor.execute(
        "SELECT name FROM students WHERE student_id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    cursor.close()
    db.close()

    if student:
        return {"name": student['name']}
    else:
        return {"name": ""}
    
# __________end add marks get_student_name____________
    
    
    
    
    
    
    
    
# _______________________________________________
            # Rank Auto Update
# _______________________________________________
def update_rank():

    db, cursor = get_db()

    cursor.execute(
        "SELECT student_id,total FROM marks ORDER BY total DESC"
    )

    data = cursor.fetchall()

    rank = 1

    for row in data:

        cursor.execute(
            "UPDATE marks SET rank_no=%s WHERE student_id=%s",
            (rank, row['student_id'])
        )

        rank += 1

    db.commit()

    cursor.close()
    db.close()

# ________end Rank Auto Update__________







# _______________________________________________
            # Student_records
# _______________________________________________
@app.route('/student_records')
def student_records():

    if 'admin' not in session:
        return redirect('/admin_login')

    update_rank()   # rank refresh

    db, cursor = get_db()

    search = request.args.get('search','')

    if search:

        cursor.execute("""
        SELECT 
        marks.student_id,
        students.name,
        marks.maths,
        marks.physics,
        marks.chemistry,
        marks.biology,
        marks.total,
        marks.rank_no
        FROM marks
        JOIN students
        ON marks.student_id = students.student_id
        WHERE students.name LIKE %s
        OR marks.student_id LIKE %s
        ORDER BY marks.total DESC
        """,(f"%{search}%",f"%{search}%"))

    else:

        cursor.execute("""
        SELECT 
        marks.student_id,
        students.name,
        marks.maths,
        marks.physics,
        marks.chemistry,
        marks.biology,
        marks.total,
        marks.rank_no
        FROM marks
        JOIN students
        ON marks.student_id = students.student_id
        ORDER BY marks.total DESC
        """)

    students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "student_records.html",
        students=students
    )
# _______________END STUDENT RECORD__________________________







# _______________________________________________
            # Delete Student Route
# _______________________________________________
@app.route('/delete_marks/<student_id>')
def delete_marks(student_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    cursor.execute(
        "DELETE FROM marks WHERE student_id=%s",
        (student_id,)
    )

    db.commit()

    cursor.close()
    db.close()

    update_rank()

    return redirect('/student_records')
# ______________end Delete Student Route_________________






# _______________________________________________
            # Edit student Marks Route
# _______________________________________________
@app.route("/edit_marks/<student_id>", methods=["GET","POST"])
def edit_marks(student_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    db, cursor = get_db()

    if request.method == "POST":

        maths = int(request.form["maths"])
        physics = int(request.form["physics"])
        chemistry = int(request.form["chemistry"])
        biology = int(request.form["biology"])

        total = maths + physics + chemistry + biology

        cursor.execute("""
        UPDATE marks
        SET maths=%s,
            physics=%s,
            chemistry=%s,
            biology=%s,
            total=%s
        WHERE student_id=%s
        """,(maths,physics,chemistry,biology,total,student_id))

        db.commit()

        cursor.close()
        db.close()

        update_rank()

        return redirect("/student_records")

    cursor.execute(
        "SELECT * FROM marks WHERE student_id=%s",
        (student_id,)
    )

    data = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template("edit_marks.html", data=data)
# ________________End student edit Marks Route____________________






# _______________________________________________
            # Dataset Upload Route
# _______________________________________________

@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():

    if 'admin' not in session:
        return redirect('/admin_login')

    file = request.files.get('file')

    if not file:
        flash("No dataset uploaded","danger")
        return redirect('/prediction_page')

    # create dataset folder if not exist
    if not os.path.exists("dataset"):
        os.makedirs("dataset")

    path = "dataset/dataset.csv"
    file.save(path)

    df = pd.read_csv(path)

    # clean column names
    df.columns = df.columns.str.strip().str.lower()

    # replace blank values
    df.replace("",0,inplace=True)

    # convert numeric safely
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except:
            pass

    # fill missing values
    df.fillna(0,inplace=True)

    numeric_cols = df.select_dtypes(include=['int64','float64']).columns

    if len(numeric_cols) < 2:
        flash("Dataset must contain numeric columns","danger")
        return redirect('/prediction_page')

    X = df[numeric_cols[:-1]]
    y = df[numeric_cols[-1]]

    try:

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = RandomForestRegressor()
        model.fit(X_train, y_train)

        joblib.dump(model, "model.pkl")

        flash("Dataset uploaded & AI model trained","success")

    except Exception as e:

        flash("Dataset training failed","danger")

    return redirect('/prediction_page?run=1')
# ________________end upload dataset_____________







# _______________________________________________
                    # predict_dynamic
# _______________________________________________

@app.route('/predict_dynamic', methods=['POST'])
def predict_dynamic():

    # check model file exist
    if not os.path.exists("model.pkl"):
        flash("AI model not trained yet","danger")
        return redirect('/prediction_page')

    model = joblib.load("model.pkl")

    data = request.form.to_dict()

    # convert numeric values
    for key in data:
        try:
            data[key] = float(data[key])
        except:
            data[key] = 0

    df = pd.DataFrame([data])

    prediction = model.predict(df)[0]

    return render_template(
        "prediction_result.html",
        prediction=round(prediction,2)
    )
# ________________predict_dynamic____________________   
    
    
    

# _______________________________________________
            # Prediction_page
# _______________________________________________
@app.route('/prediction_page')
def prediction_page():

    students = []
    columns = []
    chart_labels = []
    chart_values = []

    run = request.args.get("run")

    if run:

        try:

            df = pd.read_csv("dataset/dataset.csv")

            df.columns = df.columns.str.strip().str.lower()

            # CLEAN DATA
            df.replace("",0,inplace=True)
            df.fillna(0,inplace=True)

            numeric_cols = df.select_dtypes(include=['int64','float64']).columns

            ignore_cols = [
                "id","age","attendance","study_hours","practice_hours",
                "internal_marks","result","rank","total","total_score"
            ]

            subject_cols = [c for c in numeric_cols if c not in ignore_cols]

            if len(subject_cols) == 0:
                subject_cols = numeric_cols

            df["Total_Score"] = df[subject_cols].sum(axis=1)

            df["Rank"] = df["Total_Score"].rank(ascending=False).astype(int)

            df["Weak_Subject"] = df[subject_cols].idxmin(axis=1)

            target = df["Total_Score"].max()

            df["Target_Score"] = target

            df["Improvement_Needed"] = target - df["Total_Score"]

            # feature importance
            X = df[subject_cols]
            y = df["Total_Score"]

            model = RandomForestRegressor()
            model.fit(X,y)

            importance = model.feature_importances_

            chart_labels = list(subject_cols)
            chart_values = importance.tolist()

            students = df.to_dict(orient="records")
            columns = list(df.columns)

        except Exception as e:

            flash("Dataset processing error","danger")

    return render_template(
        "prediction_page.html",
        students=students,
        columns=columns,
        chart_labels=chart_labels,
        chart_values=chart_values
    )
# ______________end _Prediction_page________________________________
           
    
    
    
  


# _______________________________________________
                # Leaderboard
# _______________________________________________

@app.route('/leaderboard')
def leaderboard():

    db, cursor = get_db()

    cursor.execute("""
        SELECT 
        marks.student_id,
        students.name,
        marks.total,
        marks.rank_no
        FROM marks
        JOIN students 
        ON marks.student_id = students.student_id
        ORDER BY marks.rank_no ASC
    """)

    data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("leaderboard.html", data=data)
  
# ____________________end  Leaderboard_____________________________________







if __name__ == "__main__":
    app.run(debug=True)
    
    
    