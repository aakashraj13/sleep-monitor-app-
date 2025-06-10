import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, date, time, timedelta

# Database connection
def get_connection():
    return mysql.connector.connect(
        host="sql8.freesqldatabase.com",
        user="sql8783645",
        password="bXwTUfpwue",
        database="sql8783645",
        port=3306
    )

# Create tables
def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            date DATE NOT NULL,
            sleep_time TIME NOT NULL,
            wake_time TIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# User authentication and registration
def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return True
    except mysql.connector.errors.IntegrityError:
        return False
    finally:
        conn.close()

def save_sleep_data(user_id, log_date, sleep_time, wake_time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sleep_log (user_id, date, sleep_time, wake_time)
        VALUES (%s, %s, %s, %s)
    """, (user_id, log_date, sleep_time, wake_time))
    conn.commit()
    conn.close()

def parse_time(t):
    if isinstance(t, pd.Timedelta):
        total_seconds = int(t.total_seconds())
        return time(hour=total_seconds // 3600, minute=(total_seconds % 3600) // 60)
    if isinstance(t, str):
        return datetime.strptime(t, "%H:%M:%S").time()
    if isinstance(t, time):
        return t
    return None

def load_user_data(user_id):
    conn = get_connection()
    df = pd.read_sql(f"SELECT date, sleep_time, wake_time FROM sleep_log WHERE user_id = {user_id} ORDER BY date DESC", conn)
    conn.close()

    df['sleep_time'] = df['sleep_time'].apply(parse_time)
    df['wake_time'] = df['wake_time'].apply(parse_time)

    def calc_duration(row):
        sleep_dt = datetime.combine(date.min, row['sleep_time'])
        wake_dt = datetime.combine(date.min, row['wake_time'])
        if wake_dt < sleep_dt:
            wake_dt += timedelta(days=1)
        return round((wake_dt - sleep_dt).total_seconds() / 3600, 2)

    df['duration_hours'] = df.apply(calc_duration, axis=1)
    return df

def login_page():
    st.title("🛌 Sleep Monitor - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_id = authenticate_user(username, password)
        if user_id:
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Invalid username or password.")
    if st.button("Sign Up"):
        st.session_state.page = "signup"
        st.rerun()

def signup_page():
    st.title("📝 Sign Up")
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    if st.button("Register"):
        if register_user(username, password):
            st.success("Registration successful! Please log in.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Username already exists.")

def dashboard():
    st.title(f"📊 Welcome, {st.session_state['username']}!")
    
    st.subheader("Enter Today's Sleep Data")
    today = date.today()

    # Use session_state to preserve time values
    if "sleep_time" not in st.session_state:
        st.session_state["sleep_time"] = datetime.strptime("23:00", "%H:%M").time()  # default
    if "wake_time" not in st.session_state:
        st.session_state["wake_time"] = datetime.strptime("07:00", "%H:%M").time()  # default

    sleep_time = st.time_input("Sleep Time", value=st.session_state["sleep_time"], key="sleep_time")
    wake_time = st.time_input("Wake Time", value=st.session_state["wake_time"], key="wake_time")

    if st.button("Submit Sleep Log"):
        save_sleep_data(st.session_state['user_id'], today, sleep_time, wake_time)
        st.success("Data saved!")

    st.subheader("📅 Your Sleep Logs")
    df = load_user_data(st.session_state['user_id'])

    if df.empty:
        st.info("No data found.")
    else:
        # Calculate sleep duration
        def calc_duration(row):
            sleep_dt = datetime.combine(date.min, row['sleep_time'])
            wake_dt = datetime.combine(date.min, row['wake_time'])
            if wake_dt < sleep_dt:
                wake_dt += pd.Timedelta(days=1)
            return (wake_dt - sleep_dt).total_seconds() / 3600
        
        df['duration_hours'] = df.apply(calc_duration, axis=1)
        df['date'] = pd.to_datetime(df['date'])

        # KPIs
        st.metric("🕒 Avg Sleep Duration (hrs)", f"{df['duration_hours'].mean():.2f}")
        st.metric("📆 Latest Sleep Duration (hrs)", f"{df.iloc[0]['duration_hours']:.2f}")

        # Line chart
        df_sorted = df.sort_values("date")
        st.line_chart(df_sorted.set_index("date")["duration_hours"])

        # Show table
        st.dataframe(df[['date', 'sleep_time', 'wake_time', 'duration_hours']])

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()


# Main logic
initialize_database()
if "page" not in st.session_state:
    st.session_state.page = "login"

if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.page == "dashboard":
    dashboard()
