from flask import Flask, request, redirect, url_for, session, flash, render_template
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong secret key for session security


# Function to get database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database=os.getenv("DB_NAME", "attendance_c"),
        port=int(os.getenv("DB_PORT", 3308))  # Default to 3308 as per your previous config
    )



# Home Route
@app.route('/')
def home():
    return render_template('index.html')


# Login Route
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
            session.update({
                'loggedin': True,
                'name': user["name"],
                'role': user["role"],
                'id': user["id"]
            })
            return redirect(url_for(f'{user["role"]}_dashboard'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')


# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if session.get('loggedin') and session.get('role') == 'admin':
        return render_template('admin_dashboard.html')
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


# Teacher Dashboard
@app.route('/teacher')
def teacher_dashboard():
    if session.get('loggedin') and session.get('role') == 'teacher':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM subjects WHERE teacher_id = %s", (session['id'],))
        subjects = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('teacher_dashboard.html', subjects=subjects)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


# Student Dashboard
@app.route('/student')
def student_dashboard():
    if session.get('loggedin') and session.get('role') == 'student':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT subjects.subject_name, 
                   (COUNT(CASE WHEN attendance.status = 'Present' THEN 1 END) * 100 / COUNT(*)) AS percentage
            FROM attendance
            JOIN subjects ON attendance.subject_id = subjects.id
            WHERE attendance.student_id = %s
            GROUP BY subjects.subject_name
        """, (session['id'],))

        records = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert list of records to dictionary (if needed by template)
        attendance = {record["subject_name"]: record["percentage"] for record in records}

        return render_template('student_dashboard.html', attendance=attendance)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))



# Add Course
@app.route('/add_course', methods=['POST'])
def add_course():
    if session.get('loggedin') and session.get('role') == 'admin':
        course_name = request.form.get('course_name')
        if not course_name:
            flash('Course name is required!', 'warning')
        else:
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
    else:
        flash('Unauthorized access!', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    status = request.form.get('status')

    if not all([student_id, subject_id, status]):
        flash("Missing data. Please try again.", "danger")
        return redirect(url_for('teacher_dashboard'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO attendance (student_id, subject_id, date, status) VALUES (%s, %s, CURDATE(), %s)",
            (student_id, subject_id, status)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Attendance marked successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('teacher_dashboard'))


# Register User
@app.route('/register_user', methods=['POST'])
def register_user():
    if session.get('loggedin') and session.get('role') == 'admin':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
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


# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run()
