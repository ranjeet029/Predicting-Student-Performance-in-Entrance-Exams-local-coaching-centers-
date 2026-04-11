from flask import Flask,render_template,request,redirect, session,flash
import mysql.connector
from model import predict_student
from flask_mail import Mail, Message
import random
import pandas as pd
import time
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os


app=Flask(__name__)
app.secret_key="secretkey"


db=mysql.connector.connect(
host="localhost",
user="root",
password="root1234",
database="student_ai"
)

# cursor=db.cursor()

cursor = db.cursor(dictionary=True)

 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "iamranjeet2572@gmail.com"
app.config['MAIL_PASSWORD'] = "ujkwztiyaejcoxbh"

mail = Mail(app)




@app.route('/')
def home():

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT AVG(total) AS avg_score FROM marks")
    avg_score = cursor.fetchone()['avg_score'] or 0

    cursor.execute("SELECT MIN(rank_no) AS top_rank FROM marks WHERE rank_no > 0")
    top_rank = cursor.fetchone()['top_rank'] or 0

    return render_template(
        "index.html",
        total_students=total_students,
        avg_score=round(avg_score,2),
        top_rank=top_rank
    )
    
    
#__________________dashboard_____________________ 
@app.route('/dashboard')
def dashboard():

    cursor.execute("SELECT * FROM marks ORDER BY total DESC")

    data=cursor.fetchall()

    return render_template("dashboard.html",data=data)



#__________________end dashboard_____________________ 



# _____________Student Login________________
@app.route('/login',methods=['GET','POST'])

def login():

    if request.method=="POST":

        sid=request.form['student_id']
        password=request.form['password']

        sql="SELECT * FROM students WHERE student_id=%s AND password=%s"

        val=(sid,password)

        cursor.execute(sql,val)

        user=cursor.fetchone()

        if user:

            session['student_id']=sid

            return redirect('/student_dashboard')

        else:
            flash("Invalid Student Id or Password", "danger")
            return redirect('/login')

    return render_template("login.html")
# _______________end login___________________


# ____________Student Dashboard Backend____________

@app.route('/student_dashboard')
def student_dashboard():

    if 'student_id' not in session:
        return redirect('/login')

    sid = session['student_id']

    cursor.execute("SELECT * FROM students WHERE student_id=%s",(sid,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM marks WHERE student_id=%s",(sid,))
    marks = cursor.fetchone()
    if marks is None:
        marks = {
            "maths":0,
            "physics":0,
            "chemistry":0,
            "biology":0,
            "total":0,
            "rank_no":"-"
        }

    return render_template(
        "student_dashboard.html",
        data=student,
        marks=marks
    )
# _____________end Student Dashboard Backend_____________________
# _______logout_______________
@app.route('/logout')

def logout():

    session.clear()

    return redirect('/')
# ________end logout________




# ______________student profile___________________
@app.route('/profile', methods=['GET','POST'])
def profile():

    if 'student_id' not in session:
        return redirect('/login')

    sid = session['student_id']

    if request.method == "POST":

        mobile = request.form.get('mobile') or None
        email = request.form.get('email') or None
        gender = request.form.get('gender') or None
        father_name = request.form.get('father_name') or None
        batch = request.form.get('batch') or None
        admission_date = request.form.get('admission_date') or None
        address = request.form.get('address') or None
        dob = request.form.get('dob') or None

        photo = request.files['photo']
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

    return render_template("student_profile.html",data=data)
# _______________end student profile_______________


# _____________Send OTP During Signup_________________
@app.route('/signup', methods=['GET','POST'])
def signup():

    if request.method == "POST":

        name=request.form['name']
        student_id=request.form['student_id']
        mobile=request.form['mobile']
        email=request.form['email']
        password=request.form['password']
        

        # check student id already exist
        cursor.execute("SELECT * FROM students WHERE student_id=%s",(student_id,))
        user=cursor.fetchone()

        if user:
            flash("Student ID already exists","danger")
            return redirect('/signup')

        # generate OTP
        otp=random.randint(100000,999999)

        session['otp']=otp
        session['otp_time']=time.time()

        session['signup_data']={
            "name":name,
            "student_id":student_id,
            "mobile":mobile,
            "email":email,
            "password":generate_password_hash(password)
        }

        msg=Message(
        "OTP Verification - AI Student System",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
        )

        msg.body=f"""
Your OTP Verification Code

OTP : {otp}

This OTP will expire in 5 minutes.
"""

        mail.send(msg)

        flash("OTP sent to your email","success")

        return redirect('/verify_otp')

    return render_template("signup.html")
# ____________end_____________________________

# __________OTP Verification Route___________________
@app.route('/verify_otp',methods=['GET','POST'])
def verify_otp():

    if request.method=="POST":

        user_otp=request.form['otp']

        # check otp exist
        if 'otp' not in session:
            flash("Session expired. Signup again.","danger")
            return redirect('/signup')

        # check expiry (5 min)
        if time.time()-session['otp_time']>300:
            flash("OTP expired. Try again.","danger")
            return redirect('/signup')

        if int(user_otp)==session['otp']:

            data=session['signup_data']

            sql="""
            INSERT INTO students
            (name,student_id,mobile,email,password)
            VALUES(%s,%s,%s,%s,%s)
            """

            val=(data['name'],data['student_id'],data['mobile'],data['email'],data['password'])

            cursor.execute(sql,val)
            db.commit()

            # clear session
            session.pop('otp',None)
            session.pop('signup_data',None)
            session.pop('otp_time',None)

            flash("Signup successful. Please login.","success")

            return redirect('/login')

        else:

            flash("Invalid OTP","danger")

    return render_template("verify_otp.html")
# __________end_________________



# __________ RESEND OTP __________

@app.route('/resend_otp')
def resend_otp():

    # session check
    if 'signup_data' not in session:
        return redirect('/signup')

    # 1 minute resend limit
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
        "Resend OTP - AI Student System",
        sender = app.config['MAIL_USERNAME'],
        recipients = [email]
    )

    msg.body = f"""
Your New OTP Code

OTP : {otp}

Valid for 1 minute.
"""

    mail.send(msg)

    flash("New OTP sent to your email","success")

    return redirect('/verify_otp')
# _______________end___RESEND____OTP______________________






# _____Send Reset OTP____________
@app.route('/forgot_password',methods=['GET','POST'])
def forgot_password():

    if request.method=="POST":

        email=request.form['email']

        otp=random.randint(100000,999999)

        session['reset_otp']=otp
        session['reset_email']=email

        msg=Message(
        "Password Reset OTP",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
        )

        msg.body=f"Your reset OTP is {otp}"

        mail.send(msg)

        return redirect('/reset_password')

    return render_template("forgot_password.html")
# _______end Send Reset OTP_____

# _____________Reset Password Backend__________
@app.route('/reset_password',methods=['GET','POST'])
def reset_password():

    if request.method=="POST":

        otp=request.form['otp']
        password=request.form['password']

        if int(otp)==session['reset_otp']:

            email=session['reset_email']
            hashed = generate_password_hash(password)

            cursor.execute(sql,(hashed,email))

            # sql="UPDATE students SET password=%s WHERE email=%s"

            cursor.execute(sql,(password,email))

            db.commit()

            return redirect('/login')

        else:

            return "Invalid OTP"

    return render_template("reset_password.html")
#_____________end Reset Password Backend__________ 

# ____________________________________________________
@app.route('/predict',methods=['POST'])

def predict():

    m=int(request.form['maths'])
    p=int(request.form['physics'])
    c=int(request.form['chemistry'])
    b=int(request.form['biology'])
    a=int(request.form['attendance'])
    pr=int(request.form['practice'])

    score,category,importance=predict_student(m,p,c,b,a,pr)

    return render_template(
    "prediction.html",
    score=score,
    category=category,
    importance=importance
    )
    
    # ____________________________
    
    
    
# _____________________admikn login__________________

@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        sql = "SELECT * FROM admin WHERE username=%s AND password=%s"

        cursor.execute(sql,(username,password))

        admin = cursor.fetchone()

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


#______________Admin Panel Route (Protected)__________________ 
@app.route('/admin_panel')
def admin_panel():

    if 'admin' not in session:
        return redirect('/admin_login')

    update_rank()   # ⭐ always refresh rank

    cursor.execute("""
    SELECT marks.*, students.name
    FROM marks
    JOIN students
    ON marks.student_id = students.student_id
    ORDER BY marks.total DESC
    """)

    students = cursor.fetchall()

    return render_template(
        "admin_panel.html",
        students=students
    )

# ____________end Admin Panel Route (Protected)_____________________
# __________Admin Logout____________
@app.route('/admin_logout')
def admin_logout():

    session.pop('admin', None)

    return redirect('/admin_login')

# __________end Admin Logout_______________________



# _____________Settings Route____________

@app.route('/admin_settings')
def admin_settings():

    if 'admin' not in session:
        return redirect('/admin_login')

    search = request.args.get('search')

    if search:

        sql = """
        SELECT * FROM students
        WHERE name LIKE %s
        OR student_id LIKE %s
        OR email LIKE %s
        """

        val = (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )

        cursor.execute(sql,val)

    else:

        cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template(
        "admin_settings.html",
        students=students
    )
# _____________end Settings Route_________

# __________Delete Student Route___________
@app.route('/delete_student/<id>')
def delete_student(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect('/admin_settings')

# __________end Delete Student Route________

    
    
    
    # _______Admin Add Marks________________
@app.route('/add_marks', methods=['POST'])
def add_marks():

    sid = request.form.get('student_id')

    m = int(request.form.get('maths'))
    p = int(request.form.get('physics'))
    c = int(request.form.get('chemistry'))
    b = int(request.form.get('biology'))
    a = int(request.form.get('attendance'))
    pr = int(request.form.get('practice'))

    total = m+p+c+b

    sql = """
    INSERT INTO marks
    (student_id,maths,physics,chemistry,biology,attendance,practice,total)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(sql,(sid,m,p,c,b,a,pr,total))

    db.commit()

    update_rank()   # ⭐ rank auto update

    return redirect('/admin_panel')
    # ___________end add_marks_______
    
    
    
    
    # __________add marks get_student_name____________
@app.route('/get_student_name', methods=['POST'])
def get_student_name():

    student_id = request.form['student_id']

    cursor.execute(
        "SELECT name FROM students WHERE student_id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    if student:
        return {"name": student['name']}
    else:
        return {"name": ""}
    
    # __________end add marks get_student_name____________
    
    
    
    # __________Rank Auto Update______
def update_rank():

    cursor.execute(
    "SELECT id,total FROM marks ORDER BY total DESC"
    )

    data = cursor.fetchall()

    rank = 1

    for row in data:

        cursor.execute(
        "UPDATE marks SET rank_no=%s WHERE id=%s",
        (rank,row['id'])
        )

        rank += 1

    db.commit()



# ________end Rank Auto Update__________



    
# _____________student_records'____________________________
@app.route('/student_records')
def student_records():

    if 'admin' not in session:
        return redirect('/admin_login')

    update_rank()   # ⭐ rank refresh

    search = request.args.get('search')

    if search:
        cursor.execute("""
        SELECT marks.*, students.name
        FROM marks
        JOIN students
        ON marks.student_id = students.student_id
        WHERE students.name LIKE %s OR marks.student_id LIKE %s
        ORDER BY marks.total DESC
        """,('%'+search+'%','%'+search+'%'))

    else:
        cursor.execute("""
        SELECT marks.*, students.name
        FROM marks
        JOIN students
        ON marks.student_id = students.student_id
        ORDER BY marks.total DESC
        """)

    students = cursor.fetchall()

    return render_template(
        "student_records.html",
        students=students
    )
# _________________________________________

#______________Delete Student Route_________________
@app.route('/delete_marks/<int:id>')
def delete_marks(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute(
        "DELETE FROM marks WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect('/student_records')
# ______________Delete Student Route_________________

# _______________Edit Marks Route_____________________
@app.route("/edit_marks/<int:id>", methods=["GET","POST"])
def edit_marks(id):

    # POST -> Update Marks
    if request.method == "POST":

        maths = int(request.form["maths"])
        physics = int(request.form["physics"])
        chemistry = int(request.form["chemistry"])
        biology = int(request.form["biology"])
        attendance = int(request.form["attendance"])
        practice = int(request.form["practice"])

        total = maths + physics + chemistry + biology

        cursor.execute("""
        UPDATE marks
        SET maths=%s,
            physics=%s,
            chemistry=%s,
            biology=%s,
            attendance=%s,
            practice=%s,
            total=%s
        WHERE id=%s
        """,(maths,physics,chemistry,biology,attendance,practice,total,id))

        db.commit()

        # Rank update
        update_rank()

        return redirect("/student_records")


    # GET -> Load data
    cursor.execute("SELECT * FROM marks WHERE id=%s",(id,))
    data = cursor.fetchone()

    return render_template("edit_marks.html", data=data)
# ________________Eend dit Marks Route____________________


# _______Dataset Upload Route_____________
@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():

    file = request.files['file']

    if file.filename == "":
        return "No file selected"

    df = pd.read_csv(file)

    # column names clean
    df.columns = df.columns.str.strip().str.lower()

    # NaN remove
    df = df.fillna(0)

    for index,row in df.iterrows():

        student_id = str(row.get('student_id',"")).strip()

        if student_id == "":
            continue

        maths = int(row.get('maths',0))
        physics = int(row.get('physics',0))
        chemistry = int(row.get('chemistry',0))
        biology = int(row.get('biology',0))
        attendance = int(row.get('attendance',0))
        practice = int(row.get('practice',0))

        total = maths + physics + chemistry + biology

        # check student exist
        cursor.execute(
            "SELECT * FROM students WHERE student_id=%s",
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:
            continue

        # check marks already exist
        cursor.execute(
            "SELECT * FROM marks WHERE student_id=%s",
            (student_id,)
        )

        exist = cursor.fetchone()

        if exist:

            cursor.execute("""
            UPDATE marks
            SET maths=%s,
                physics=%s,
                chemistry=%s,
                biology=%s,
                attendance=%s,
                practice=%s,
                total=%s
            WHERE student_id=%s
            """,(maths,physics,chemistry,biology,attendance,practice,total,student_id))

        else:

            cursor.execute("""
            INSERT INTO marks
            (student_id,maths,physics,chemistry,biology,attendance,practice,total)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            """,(student_id,maths,physics,chemistry,biology,attendance,practice,total))

    db.commit()

    update_rank()

    return redirect('/student_records')

# ________________end upload dataset_____________
    

    
@app.route('/leaderboard')
def leaderboard():

    cursor.execute("SELECT * FROM marks ORDER BY rank_no ASC")

    data=cursor.fetchall()

    return render_template("leaderboard.html",data=data)
    # ___________________
    
    
    # _________________________________________________________
@app.route('/check_student_id', methods=['POST'])
def check_student_id():

    student_id = request.form['student_id']

    sql = "SELECT * FROM students WHERE student_id=%s"
    cursor.execute(sql,(student_id,))
    user = cursor.fetchone()

    if user:
        return {"status":"exists"}
    else:
        return {"status":"available"}
    # _________________________________________________________

if __name__ == "__main__":
    app.run(debug=True)