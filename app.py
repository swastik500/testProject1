from flask import Flask, request, redirect, url_for, session, flash, render_template
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong secret key for session security

# Function to get database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="attendance_c",
        port=3308
    )


# Home Route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session['loggedin'] = True
            session['name'] = user["name"]
            session['role'] = user["role"]
            session['id'] = user["id"]

            if user["role"] == "admin":
                return redirect(url_for('admin_dashboard'))
            elif user["role"] == "teacher":
                return redirect(url_for('teacher_dashboard'))
            elif user["role"] == "student":
                return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if 'loggedin' in session and session['role'] == 'admin':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                           (name, email, hashed_password, role))
            conn.commit()
            flash("User added successfully!", "success")
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_dashboard'))

    flash("Unauthorized action!", "danger")
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'loggedin' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


@app.route('/teacher')
def teacher_dashboard():
    if 'loggedin' in session and session['role'] == 'teacher':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM subjects WHERE teacher_id = %s", (session['id'],))
        subjects = cursor.fetchall()
        conn.close()
        return render_template('teacher_dashboard.html', subjects=subjects)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


@app.route('/student')
def student_dashboard():
    if 'loggedin' in session and session['role'] == 'student':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM attendance WHERE student_id = %s", (session['id'],))
        attendance_records = cursor.fetchall()
        conn.close()
        return render_template('student_dashboard.html', attendance_records=attendance_records)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/add_course', methods=['POST'])
def add_course():
    if 'loggedin' not in session or session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    course_name = request.form.get('course_name')

    if not course_name:
        flash('Course name is required!', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO courses (name) VALUES (%s)", (course_name,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Course added successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/register_user', methods=['POST'])
def register_user():
    if 'loggedin' in session and session['role'] == 'admin':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                           (name, email, hashed_password, role))
            conn.commit()
            flash("User registered successfully!", "success")
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_dashboard'))

    flash("Unauthorized action!", "danger")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
