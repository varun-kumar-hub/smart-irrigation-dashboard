"""
Smart Irrigation System - Enhanced Interactive Dashboard
Real Firebase data version without sample data generation
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pyrebase
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import json
from zoneinfo import ZoneInfo

# =====================================================
# TIMEZONE CONFIGURATION
# =====================================================
IST = ZoneInfo("Asia/Kolkata")  # Indian Standard Time (Kolkata/Chennai)

# =====================================================
# FIREBASE CONFIGURATION
# =====================================================
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDzRSz9-jvnaLas8GuLlL45tkCM-idewCw",
    "authDomain": "smart-irrigation-system-4010f.firebaseapp.com",
    "databaseURL": "https://smart-irrigation-system-4010f-default-rtdb.firebaseio.com/",
    "storageBucket": "smart-irrigation-system-4010f.appspot.com"
}

DEVICE_ID = "device_001"

try:
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    auth = firebase.auth()
    db = firebase.database()
except Exception as e:
    st.error(f"Firebase initialization error: {e}")

st.set_page_config(
    page_title="Smart Irrigation Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .metric-card {
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .pulse {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        animation: blink 1.5s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def login(email, password):
    """Authenticate user"""
    try:
        return auth.sign_in_with_email_and_password(email, password)
    except Exception as e:
        error_msg = str(e)
        if "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
            st.error("🔒 Invalid email or password")
        elif "EMAIL_NOT_FOUND" in error_msg:
            st.error("📧 Email not found. Please sign up first.")
        else:
            st.error(f"❌ Login failed: {error_msg}")
        return None

def signup(email, password):
    """Create new user account"""
    try:
        return auth.create_user_with_email_and_password(email, password)
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            st.error("📧 Email already exists. Please login instead.")
        elif "WEAK_PASSWORD" in error_msg:
            st.error("🔐 Password should be at least 6 characters")
        else:
            st.error(f"❌ Sign-up failed: {error_msg}")
        return None

def log_current_reading_to_history(moisture, pump_status, pump_mode):
    """Log current sensor reading to Firebase history with IST timezone"""
    try:
        # Get current time in IST
        timestamp = datetime.datetime.now(IST).isoformat()
        
        # Log moisture reading
        db.child("history").child(DEVICE_ID).child("moisture").push({
            "value": int(moisture),
            "timestamp": timestamp
        })
        
        # Log pump status
        db.child("history").child(DEVICE_ID).child("pump").push({
            "value": pump_status,
            "trigger": pump_mode,
            "timestamp": timestamp
        })
        
        return True
    except Exception as e:
        # Silent fail - don't disrupt dashboard
        return False

def clear_history_data():
    """Clear all historical data from Firebase"""
    try:
        db.child("history").child(DEVICE_ID).remove()
        return True
    except Exception as e:
        st.error(f"❌ Failed to clear history: {e}")
        return False

def get_device_data():
    """Fetch complete device data"""
    try:
        data = db.child("devices").child(DEVICE_ID).get().val()
        return data if data else {}
    except Exception as e:
        st.error(f"❌ Error fetching device data: {e}")
        return {}

def update_pump_status(status):
    """Update pump status in Firebase with IST timezone"""
    try:
        timestamp = datetime.datetime.now(IST).isoformat()
        
        db.child("devices").child(DEVICE_ID).child("actuators").child("pump").update({
            "status": status,
            "mode": "MANUAL",
            "lastChanged": timestamp
        })
        
        db.child("devices").child(DEVICE_ID).child("settings").update({
            "autoMode": False 
        })
        
        db.child("history").child(DEVICE_ID).child("pump").push({
            "value": status,
            "trigger": "MANUAL",
            "timestamp": timestamp
        })
        return True
    except Exception as e:
        st.error(f"❌ Failed to update pump: {e}")
        return False

def update_settings(auto_mode, threshold_low, threshold_high):
    """Update device settings"""
    try:
        db.child("devices").child(DEVICE_ID).child("settings").update({
            "autoMode": auto_mode,
            "thresholds": {
                "low": threshold_low,
                "high": threshold_high
            }
        })
        
        db.child("devices").child(DEVICE_ID).child("actuators").child("pump").update({
            "mode": "AUTO" if auto_mode else "MANUAL"
        })
        return True
    except Exception as e:
        st.error(f"❌ Failed to update settings: {e}")
        return False

def get_historical_data(data_type="moisture", hours=24):
    """Fetch historical data from Firebase with IST timezone conversion"""
    try:
        data = db.child("history").child(DEVICE_ID).child(data_type).get().val()
        
        if not data:
            return []
        
        # Calculate cutoff time in IST
        cutoff = datetime.datetime.now(IST) - datetime.timedelta(hours=hours)
        records = []
        
        for key, val in data.items():
            try:
                if not isinstance(val, dict):
                    continue
                    
                ts_str = val.get("timestamp", "")
                if not ts_str:
                    continue
                
                # Parse timestamp and convert to IST
                try:
                    # Try parsing ISO format
                    ts = datetime.datetime.fromisoformat(ts_str)
                    # Convert to IST if not already
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=IST)
                    else:
                        ts = ts.astimezone(IST)
                except:
                    try:
                        # Try parsing with Z suffix (UTC)
                        ts_str_clean = ts_str.replace("Z", "+00:00")
                        ts = datetime.datetime.fromisoformat(ts_str_clean)
                        ts = ts.astimezone(IST)
                    except:
                        # Skip if can't parse
                        continue
                
                if ts > cutoff:
                    record = {
                        "timestamp": ts,
                        "value": val.get("value"),
                        **{k: v for k, v in val.items() if k not in ["timestamp", "value"]}
                    }
                    records.append(record)
            except Exception:
                continue
        
        sorted_records = sorted(records, key=lambda x: x["timestamp"])
        return sorted_records
        
    except Exception:
        return []

def get_condition_from_moisture(moisture):
    """Determine soil condition"""
    if moisture < 25:
        return "Very Dry", "🔴", "#F44336", "⚠ Critical"
    elif moisture < 45:
        return "Dry", "🟠", "#FF9800", "⚡ Action Needed"
    elif moisture < 70:
        return "Moist", "🟢", "#4CAF50", "✅ Optimal"
    else:
        return "Wet", "🔵", "#2196F3", "💧 Saturated"

def get_ai_recommendation(moisture, pump_status):
    """AI-powered watering suggestion"""
    if moisture < 20:
        return "🚨", "CRITICAL", "Soil critically dry! Water immediately for 15-20 minutes.", "#F44336"
    elif moisture < 30:
        return "⚠", "URGENT", "Soil is dry. Water now for 10-15 minutes.", "#FF9800"
    elif moisture < 45:
        return "💡", "SUGGESTED", "Moisture low. Short watering (5-10 min) recommended.", "#FFC107"
    elif moisture < 70:
        return "✅", "OPTIMAL", "Soil healthy! No watering needed today.", "#4CAF50"
    elif moisture < 85:
        return "💧", "GOOD", "Soil adequately moist. Skip watering.", "#2196F3"
    else:
        return "🛑", "WARNING", "Soil saturated! Risk of overwatering. Stop pump!", "#9C27B0"

def calculate_pump_runtime(pump_history):
    """Calculate total pump runtime using IST timezone"""
    if not pump_history:
        return 0
    
    total_seconds = 0
    last_on_time = None
    
    sorted_history = sorted(pump_history, key=lambda x: x["timestamp"])
    
    for record in sorted_history:
        if record["value"] == "ON":
            last_on_time = record["timestamp"]
        elif record["value"] == "OFF" and last_on_time:
            duration = (record["timestamp"] - last_on_time).total_seconds()
            total_seconds += duration
            last_on_time = None
    
    # If pump is currently on
    if last_on_time:
        duration = (datetime.datetime.now(IST) - last_on_time).total_seconds()
        total_seconds += duration
    
    return total_seconds

def format_runtime(seconds):
    """Format runtime"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m {int(seconds%60)}s"
    else:
        hours = int(seconds/3600)
        minutes = int((seconds%3600)/60)
        return f"{hours}h {minutes}m"

# =====================================================
# PAGES
# =====================================================

def landing_page():
    """Landing page"""
    st.markdown(
        """
        <div style='text-align:center;padding:40px 0;'>
            <h1 style='font-weight:800;color:#2E7D32;font-size:3.5em;margin-bottom:10px;'>
                🌱 Smart Irrigation Pro
            </h1>
            <p style='font-size:1.3em;color:#666;margin-bottom:30px;'>
                Intelligent Water Management for Modern Agriculture
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Get Started", use_container_width=True, type="primary"):
            st.session_state.page = "login"
            st.rerun()

    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    features = [
        ("📊", "Real-Time Analytics", "Track moisture, pump status, and trends with live updates every 5 seconds"),
        ("🤖", "Smart Automation", "AI-powered control with customizable thresholds and intelligent recommendations"),
        ("💾", "Complete Logging", "Full history of readings and operations with advanced analytics")
    ]
    
    for col, (icon, title, desc) in zip([col1, col2, col3], features):
        with col:
            st.markdown(f"""
            <div class='metric-card' style='text-align:center;background:linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);'>
                <h1 style='font-size:3em;margin:0;'>{icon}</h1>
                <h3 style='color:#2E7D32;margin:10px 0;'>{title}</h3>
                <p style='color:#666;font-size:0.9em;'>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

def login_page():
    """Login/signup page"""
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.markdown("""
        <div style='text-align:center;padding:20px;'>
            <h2 style='color:#2E7D32;'>🔐 Welcome Back</h2>
            <p style='color:#666;'>Access your smart irrigation dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                st.text_input("📧 Email", key="login_email")
                st.text_input("🔒 Password", type="password", key="login_pass")
                
                submitted = st.form_submit_button("🚀 Sign In", use_container_width=True, type="primary")
                
                if submitted:
                    email = st.session_state.login_email
                    password = st.session_state.login_pass
                    
                    if email and password:
                        with st.spinner("Authenticating..."):
                            user = login(email, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.page = "dashboard"
                                st.success("✅ Login successful!")
                                st.rerun()
                    else:
                        st.warning("⚠ Please enter both email and password")
        
        with tab2:
            with st.form("signup_form"):
                st.text_input("📧 Email", key="signup_email")
                st.text_input("🔒 Password (min 6 characters)", type="password", key="signup_pass")
                st.text_input("🔒 Confirm Password", type="password", key="confirm_pass")
                
                submitted = st.form_submit_button("📝 Create Account", use_container_width=True, type="primary")
                
                if submitted:
                    email = st.session_state.signup_email
                    password = st.session_state.signup_pass
                    confirm = st.session_state.confirm_pass
                    
                    if email and password and confirm:
                        if password != confirm:
                            st.error("❌ Passwords don't match!")
                        elif len(password) < 6:
                            st.error("❌ Password must be at least 6 characters")
                        else:
                            with st.spinner("Creating account..."):
                                user = signup(email, password)
                                if user:
                                    st.success("✅ Account created! Please sign in.")
                    else:
                        st.warning("⚠ Please fill all fields")

        st.markdown("---")
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def dashboard_page():
    """Dashboard with real Firebase data"""
    if "user" not in st.session_state:
        st.warning("⚠ Please login first.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    # Auto-refresh every 5 seconds for real-time updates
    count = st_autorefresh(interval=5000, key="refresh", limit=None)

    # Fetch data
    device_data = get_device_data()
    if not device_data:
        st.error("❌ Unable to connect to device. Check Firebase connection.")
        return

    sensor_data = device_data.get("sensors", {})
    pump_data = device_data.get("actuators", {}).get("pump", {})
    settings_data = device_data.get("settings", {})
    info_data = device_data.get("info", {})

    moisture = int(sensor_data.get("moisture", 0))
    pump_status = pump_data.get("status", "OFF")
    pump_mode = pump_data.get("mode", "AUTO")
    auto_mode = settings_data.get("autoMode", True)
    thresholds = settings_data.get("thresholds", {})
    threshold_low = thresholds.get("low", 30)
    threshold_high = thresholds.get("high", 70)

    # SIDEBAR
    with st.sidebar:
        st.markdown("### ⚙ Control Center")
        
        with st.expander("🤖 Automation Settings", expanded=True):
            new_auto_mode = st.toggle("Enable Auto Mode", value=auto_mode, key="auto_toggle")
            
            if new_auto_mode:
                st.markdown("Moisture Thresholds:")
                new_threshold_low = st.slider("🔽 Turn ON below", 10, 50, threshold_low)
                new_threshold_high = st.slider("🔼 Turn OFF above", 50, 90, threshold_high)
                
                if st.button("💾 Save Settings", use_container_width=True, type="primary"):
                    if update_settings(new_auto_mode, new_threshold_low, new_threshold_high):
                        st.success("✅ Settings saved!")
                        st.rerun()
            else:
                if st.button("💾 Save Settings", use_container_width=True, type="primary"):
                    if update_settings(new_auto_mode, threshold_low, threshold_high):
                        st.success("✅ Settings saved!")
                        st.rerun()
        
        with st.expander("📊 Display Options", expanded=True):
            time_range = st.selectbox(
                "History Range",
                ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours"],
                index=3
            )
            
            hours_map = {
                "Last 1 Hour": 1,
                "Last 6 Hours": 6,
                "Last 12 Hours": 12,
                "Last 24 Hours": 24
            }
            selected_hours = hours_map[time_range]
        
        st.markdown("---")
        
        # Data Management Section
        st.markdown("### 🗑️ Data Management")
        
        if st.button("🧹 Clear Old History", use_container_width=True, type="secondary"):
            if "confirm_clear" not in st.session_state:
                st.session_state.confirm_clear = False
            
            if not st.session_state.confirm_clear:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion")
            else:
                with st.spinner("Clearing history..."):
                    if clear_history_data():
                        st.success("✅ History cleared! Fresh data will start logging.")
                        st.session_state.confirm_clear = False
                        st.rerun()
        
        if st.session_state.get("confirm_clear", False):
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()
        
        st.caption("⚠️ This will delete all historical data and start fresh logging")
        
        st.markdown("---")
    
    # Log current reading to history every refresh (every 5 seconds)
    log_current_reading_to_history(moisture, pump_status, pump_mode)
    

    # MAIN DASHBOARD
    st.markdown("# 💧 Smart Irrigation Dashboard")
    
    # Show current IST time
    current_ist_time = datetime.datetime.now(IST).strftime("%d %B %Y, %I:%M:%S %p IST")
    st.caption(f"🕐 Current Time: {current_ist_time}")
    
    # Current Status
    col1, col2, col3, col4 = st.columns(4)
    
    condition, icon, color, status_text = get_condition_from_moisture(moisture)
    
    with col1:
        st.metric("💧 Soil Moisture", f"{moisture}%")
    with col2:
        st.metric("🌱 Condition", f"{icon} {condition}")
    with col3:
        st.metric("🚰 Pump Status", f"{'✅ ON' if pump_status == 'ON' else '⭕ OFF'}")
    with col4:
        st.metric("🎛 Mode", f"{'🤖 AUTO' if pump_mode == 'AUTO' else '🎮 MANUAL'}")

    st.markdown("---")

    # Controls
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        if st.button("🟢 TURN ON PUMP", use_container_width=True, disabled=(pump_status == "ON")):
            if update_pump_status("ON"):
                st.success("✅ Pump activated")
                st.rerun()
    with col_ctrl2:
        if st.button("🔴 TURN OFF PUMP", use_container_width=True, disabled=(pump_status == "OFF")):
            if update_pump_status("OFF"):
                st.success("✅ Pump deactivated")
                st.rerun()

    st.markdown("---")
    # AI Recommendation
    icon, level, message, color = get_ai_recommendation(moisture, pump_status)
    st.markdown(f"""
    <div style='background:{color}22;padding:15px;border-radius:10px;border-left:4px solid {color};margin-bottom:20px;'>
        <h4 style='margin:0;color:{color};'>{icon} AI Recommendation</h4>
        <p style='margin:5px 0 0 0;font-size:large'><strong>{level}</strong></p>
        <p style='margin:5px 0 0 0;font-size:large;'>{message}</p>
    </div>
    """, unsafe_allow_html=True)
    # GRAPHS SECTION
    st.markdown("### 📈 Real-Time Data Analytics")
    
    # Fetch historical data (now includes freshly logged readings)
    moisture_history = get_historical_data("moisture", selected_hours)
    pump_history = get_historical_data("pump", selected_hours)
    
    # Check if we have data
    has_moisture_data = moisture_history and len(moisture_history) > 0
    has_pump_data = pump_history and len(pump_history) > 0
    
    if has_moisture_data:
        # Convert to DataFrame
        df_moisture = pd.DataFrame(moisture_history)
        
        # Ensure value is numeric
        df_moisture["value"] = pd.to_numeric(df_moisture["value"], errors="coerce")
        df_moisture = df_moisture.dropna(subset=["value"])
        
        if not df_moisture.empty and len(df_moisture) > 0:
            # Create plots
            if has_pump_data:
                # Show both moisture and pump activity
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("📊 Moisture Trend", "🚰 Pump Activity"),
                    row_heights=[0.6, 0.4],
                    vertical_spacing=0.18
                )
                
                # Moisture plot - Highlight latest point
                marker_sizes = [5] * (len(df_moisture) - 1) + [12]  # Make last point bigger
                marker_colors = ['#2E7D32'] * (len(df_moisture) - 1) + ['#FF4081']  # Make last point pink
                
                fig.add_trace(
                    go.Scatter(
                        x=df_moisture["timestamp"],
                        y=df_moisture["value"],
                        mode="lines+markers",
                        name="Moisture",
                        line=dict(color="#2E7D32", width=3),
                        marker=dict(size=marker_sizes, color=marker_colors, line=dict(width=2, color='white')),
                        fill='tozeroy',
                        fillcolor='rgba(46, 125, 50, 0.1)',
                        hovertemplate="<b>%{y:.1f}%</b><br>%{x}<extra></extra>"
                    ),
                    row=1, col=1
                )
                
                # Add threshold lines
                if auto_mode:
                    fig.add_hline(
                        y=threshold_low, 
                        line_dash="dash", 
                        line_color="#F44336",
                        line_width=2,
                        annotation_text=f"Turn ON ({threshold_low}%)",
                        annotation_position="right",
                        row=1, col=1
                    )
                    fig.add_hline(
                        y=threshold_high,
                        line_dash="dash",
                        line_color="#2196F3",
                        line_width=2,
                        annotation_text=f"Turn OFF ({threshold_high}%)",
                        annotation_position="right",
                        row=1, col=1
                    )
                
                # Pump activity - Highlight latest point
                df_pump = pd.DataFrame(pump_history)
                df_pump["status_num"] = df_pump["value"].apply(lambda x: 1 if x == "ON" else 0)
                
                pump_marker_sizes = [8] * (len(df_pump) - 1) + [15]  # Make last point bigger
                
                fig.add_trace(
                    go.Scatter(
                        x=df_pump["timestamp"],
                        y=df_pump["status_num"],
                        mode="markers+lines",
                        name="Pump Status",
                        line=dict(color="#1976D2", width=2, shape='hv'),
                        marker=dict(size=pump_marker_sizes, color='#1976D2', line=dict(width=2, color='white')),
                        hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
                    ),
                    row=2, col=1
                )
                
                # Update axes
                fig.update_xaxes(title_text="Time", row=1, col=1)
                fig.update_yaxes(title_text="Moisture (%)", row=1, col=1)
                fig.update_xaxes(title_text="Time", row=2, col=1)
                fig.update_yaxes(
                    title_text="Status",
                    ticktext=["OFF", "ON"],
                    tickvals=[0, 1],
                    row=2, col=1
                )
                
                fig.update_layout(
                    height=700,
                    showlegend=True,
                    hovermode="x unified"
                )
            else:
                # Show only moisture data
                fig = go.Figure()
                
                fig.add_trace(
                    go.Scatter(
                        x=df_moisture["timestamp"],
                        y=df_moisture["value"],
                        mode="lines+markers",
                        name="Moisture Level",
                        line=dict(color="#2E7D32", width=3),
                        marker=dict(size=5),
                        fill='tozeroy',
                        fillcolor='rgba(46, 125, 50, 0.1)'
                    )
                )
                
                # Add threshold lines
                if auto_mode:
                    fig.add_hline(
                        y=threshold_low,
                        line_dash="dash",
                        line_color="#F44336",
                        line_width=2,
                        annotation_text=f"Turn ON ({threshold_low}%)",
                        annotation_position="right"
                    )
                    fig.add_hline(
                        y=threshold_high,
                        line_dash="dash",
                        line_color="#2196F3",
                        line_width=2,
                        annotation_text=f"Turn OFF ({threshold_high}%)",
                        annotation_position="right"
                    )
                
                fig.update_layout(
                    title="📊 Soil Moisture Trend",
                    xaxis_title="Time",
                    yaxis_title="Moisture (%)",
                    height=500,
                    hovermode="x unified"
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistics
            st.markdown("### 📊 Statistics")
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            with col_s1:
                st.metric("📊 Average", f"{df_moisture['value'].mean():.1f}%")
            with col_s2:
                st.metric("📉 Minimum", f"{df_moisture['value'].min():.1f}%")
            with col_s3:
                st.metric("📈 Maximum", f"{df_moisture['value'].max():.1f}%")
            with col_s4:
                if has_pump_data:
                    runtime = calculate_pump_runtime(pump_history)
                    st.metric("⏱ Pump Runtime", format_runtime(runtime))
                else:
                    st.metric("⏱ Pump Runtime", "No data")
            
            # Download Section
            st.markdown("---")
            st.markdown("### 💾 Export Data")
            
            col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
            
            with col_exp1:
                st.markdown("**Download irrigation data for analysis**")
                data_type_export = st.radio(
                    "Select data to export:",
                    ["Moisture Data Only", "Pump Data Only", "Combined Data"],
                    horizontal=True,
                    key="export_type"
                )
            
            with col_exp2:
                st.markdown("<br>", unsafe_allow_html=True)
                # Prepare export data
                if data_type_export == "Moisture Data Only":
                    export_df = df_moisture.copy()
                    export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    export_df = export_df.rename(columns={"value": "moisture_percent"})
                    filename_prefix = "moisture_data"
                    
                elif data_type_export == "Pump Data Only" and has_pump_data:
                    df_pump_export = pd.DataFrame(pump_history)
                    df_pump_export["timestamp"] = pd.to_datetime(df_pump_export["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                    export_df = df_pump_export[["timestamp", "value", "trigger"]]
                    export_df = export_df.rename(columns={"value": "pump_status", "trigger": "control_mode"})
                    filename_prefix = "pump_data"
                    
                else:  # Combined Data
                    # Prepare moisture data
                    moisture_export = df_moisture.copy()
                    moisture_export["timestamp"] = moisture_export["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                    moisture_export = moisture_export.rename(columns={"value": "moisture_percent"})
                    moisture_export["data_type"] = "moisture"
                    
                    # Prepare pump data
                    if has_pump_data:
                        pump_export = pd.DataFrame(pump_history)
                        pump_export["timestamp"] = pd.to_datetime(pump_export["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                        pump_export = pump_export.rename(columns={"value": "pump_status"})
                        pump_export["data_type"] = "pump"
                        pump_export["moisture_percent"] = None
                        
                        # Combine both datasets
                        export_df = pd.concat([
                            moisture_export[["timestamp", "moisture_percent", "data_type"]],
                            pump_export[["timestamp", "pump_status", "trigger", "data_type"]]
                        ], ignore_index=True)
                        export_df = export_df.sort_values("timestamp")
                    else:
                        export_df = moisture_export
                    
                    filename_prefix = "irrigation_data"
                
                timestamp_now = datetime.datetime.now(IST).strftime('%Y%m%d_%H%M%S')
                csv_data = export_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"{filename_prefix}_{timestamp_now}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_exp3:
                st.markdown("<br>", unsafe_allow_html=True)
                st.metric("📊 Total Records", len(export_df))
                st.caption(f"Time Range: {time_range}")
        else:
            st.warning("⚠ No valid moisture data points found")
    else:
        st.info(f"""
        📊 **No moisture history data available for {time_range.lower()}**
        
        Your ESP32/Arduino device needs to log moisture readings to Firebase at:
        ```
        history/{DEVICE_ID}/moisture/
        ```
        
        **Data Status:**
        - Current moisture: **{moisture}%** (live sensor reading)
        - Pump history: {len(pump_history)} records found
        - Moisture history: 0 records found
        
        Make sure your device is logging moisture data to the history path.
        """)
        
        # Show pump activity only if available
        if has_pump_data:
            st.markdown("### 🚰 Pump Activity")
            
            df_pump = pd.DataFrame(pump_history)
            df_pump["status_num"] = df_pump["value"].apply(lambda x: 1 if x == "ON" else 0)
            
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_pump["timestamp"],
                    y=df_pump["status_num"],
                    mode="markers+lines",
                    name="Pump Status",
                    line=dict(color="#1976D2", width=2, shape='hv'),
                    marker=dict(size=8, color='#1976D2')
                )
            )
            
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Status",
                yaxis=dict(
                    ticktext=["OFF", "ON"],
                    tickvals=[0, 1]
                ),
                height=400,
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Pump runtime stats
            runtime = calculate_pump_runtime(pump_history)
            st.metric("⏱ Total Pump Runtime", format_runtime(runtime))

    # Logout button at bottom
    st.markdown("---")
    if st.button("🚪 Logout", type="secondary"):
        del st.session_state.user
        st.session_state.page = "home"
        st.rerun()

# =====================================================
# APPLICATION ROUTER
# =====================================================

if "page" not in st.session_state:
    st.session_state.page = "home"

page = st.session_state.page

if page == "home":
    landing_page()
elif page == "login":
    login_page()
elif page == "dashboard":
    dashboard_page()
else:
    st.session_state.page = "home"
    st.rerun()