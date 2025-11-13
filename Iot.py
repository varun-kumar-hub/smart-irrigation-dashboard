"""
Smart Irrigation System - Enhanced Interactive Dashboard
Optimized for Firebase Real-time Database Structure
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pyrebase
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import json

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

# Custom CSS for enhanced interactivity
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

def get_device_data():
    """Fetch complete device data - optimized single call"""
    try:
        data = db.child("devices").child(DEVICE_ID).get().val()
        return data if data else {}
    except Exception as e:
        st.error(f"❌ Error fetching device data: {e}")
        return {}

def update_pump_status(status):
    """Update pump status in Firebase"""
    try:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Update device status
        db.child("devices").child(DEVICE_ID).child("actuators").child("pump").update({
            "status": status,
            "mode": "MANUAL",
            "lastChanged": timestamp
        })
        
        # Log to history
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
        # Update settings
        db.child("devices").child(DEVICE_ID).child("settings").update({
            "autoMode": auto_mode,
            "thresholds": {
                "low": threshold_low,
                "high": threshold_high
            }
        })
        
        # Update pump mode
        db.child("devices").child(DEVICE_ID).child("actuators").child("pump").update({
            "mode": "AUTO" if auto_mode else "MANUAL"
        })
        return True
    except Exception as e:
        st.error(f"❌ Failed to update settings: {e}")
        return False

def get_historical_data(data_type="moisture", hours=24):
    """Fetch historical data - optimized"""
    try:
        data = db.child("history").child(DEVICE_ID).child(data_type).get().val()
        if not data:
            return []
        
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
        records = []
        
        for key, val in data.items():
            try:
                ts_str = val.get("timestamp", "")
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                
                if ts > cutoff:
                    records.append({
                        "timestamp": ts,
                        "value": val.get("value"),
                        **{k: v for k, v in val.items() if k not in ["timestamp", "value"]}
                    })
            except Exception:
                continue
        
        return sorted(records, key=lambda x: x["timestamp"])
    except Exception:
        return []

def get_condition_from_moisture(moisture):
    """Determine soil condition with enhanced visuals"""
    if moisture < 25:
        return "Very Dry", "🔴", "#F44336", "⚠ Critical"
    elif moisture < 45:
        return "Dry", "🟠", "#FF9800", "⚡ Action Needed"
    elif moisture < 70:
        return "Moist", "🟢", "#4CAF50", "✅ Optimal"
    else:
        return "Wet", "🔵", "#2196F3", "💧 Saturated"

def get_ai_recommendation(moisture, pump_status):
    """Enhanced AI-powered watering suggestion"""
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
    """Calculate total pump runtime"""
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
        duration = (datetime.datetime.now(datetime.timezone.utc) - last_on_time).total_seconds()
        total_seconds += duration
    
    return total_seconds

def format_runtime(seconds):
    """Format runtime in human-readable format"""
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
    """Enhanced landing page with animations"""
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("💡 Smart Tip: Set custom moisture thresholds based on your crop type for optimal water conservation!")
    with col_b:
        st.success("🌍 Eco-Friendly: Save up to 40% water with intelligent automation and precise monitoring!")

def login_page():
    """Enhanced login/signup page"""
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
                
                col1, col2 = st.columns(2)
                with col1:
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
    """Enhanced interactive dashboard"""
    if "user" not in st.session_state:
        st.warning("⚠ Please login first.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    # Auto-refresh every 5 seconds
    count = st_autorefresh(interval=5000, key="refresh")

    # Fetch data (single optimized call)
    device_data = get_device_data()
    if not device_data:
        st.error("❌ Unable to connect to device. Check Firebase connection.")
        return

    sensor_data = device_data.get("sensors", {})
    pump_data = device_data.get("actuators", {}).get("pump", {})
    settings_data = device_data.get("settings", {})
    info_data = device_data.get("info", {})

    # Extract values
    moisture = int(sensor_data.get("moisture", 0))
    pump_status = pump_data.get("status", "OFF")
    pump_mode = pump_data.get("mode", "AUTO")
    auto_mode = settings_data.get("autoMode", True)
    thresholds = settings_data.get("thresholds", {})
    threshold_low = thresholds.get("low", 30)
    threshold_high = thresholds.get("high", 70)
    last_seen = info_data.get("lastSeen", "")

    # ===== SIDEBAR =====
    with st.sidebar:
        st.markdown("### ⚙ Control Center")
        
        with st.expander("🤖 Automation Settings", expanded=True):
            new_auto_mode = st.toggle("Enable Auto Mode", value=auto_mode, key="auto_toggle")
            
            if new_auto_mode:
                st.markdown("Moisture Thresholds:")
                new_threshold_low = st.slider(
                    "🔽 Turn ON below", 
                    10, 50, 
                    threshold_low,
                    help="Pump activates when moisture drops below this value"
                )
                new_threshold_high = st.slider(
                    "🔼 Turn OFF above", 
                    50, 90, 
                    threshold_high,
                    help="Pump deactivates when moisture rises above this value"
                )
                
                if st.button("💾 Save Settings", use_container_width=True, type="primary"):
                    if update_settings(new_auto_mode, new_threshold_low, new_threshold_high):
                        st.success("✅ Settings saved!")
                        st.balloons()
                        st.rerun()
            else:
                if st.button("💾 Save Settings", use_container_width=True, type="primary"):
                    if update_settings(new_auto_mode, threshold_low, threshold_high):
                        st.success("✅ Settings saved!")
                        st.rerun()
        
        with st.expander("📊 Display Options", expanded=False):
            time_range = st.selectbox(
                "History Range",
                ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours", "Last 3 Days", "Last Week"],
                index=3
            )
            
            hours_map = {
                "Last 1 Hour": 1,
                "Last 6 Hours": 6,
                "Last 12 Hours": 12,
                "Last 24 Hours": 24,
                "Last 3 Days": 72,
                "Last Week": 168
            }
            selected_hours = hours_map[time_range]
            
            show_stats = st.checkbox("Show detailed statistics", value=True)
            show_pie = st.checkbox("Show condition distribution", value=True)
        
        st.markdown("---")
        st.markdown("### 🗑 Data Management")
        
        if st.button("🧹 Clear History", use_container_width=True, type="secondary"):
            if "confirm_clear" not in st.session_state:
                st.session_state.confirm_clear = False
            
            if not st.session_state.confirm_clear:
                st.session_state.confirm_clear = True
                st.warning("⚠ Click again to confirm")
            else:
                try:
                    db.child("history").child(DEVICE_ID).remove()
                    st.success("✅ History cleared!")
                    st.session_state.confirm_clear = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.clear()
            st.session_state.page = "home"
            st.rerun()
        
        # System info
        st.markdown("---")
        st.caption(f"🔄 Auto-refresh: Active")
        st.caption(f"⏱ Refresh count: {count}")

    # ===== MAIN DASHBOARD =====
    st.markdown("""
    <div style='text-align:center;padding:20px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:10px;margin-bottom:20px;'>
        <h1 style='color:white;margin:0;'>💧 Smart Irrigation System</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Device Status Header
    col_dev1, col_dev2, col_dev3 = st.columns([2, 2, 1])
    with col_dev1:
        st.markdown(f"📍 Location:** {info_data.get('location', 'Field A')}")
    with col_dev2:
        st.markdown(f"🏷 Device:** {info_data.get('name', 'Main Field Sensor')}")
    with col_dev3:
        try:
            last_seen_dt = datetime.datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            time_diff = datetime.datetime.now(datetime.timezone.utc) - last_seen_dt
            
            if time_diff.total_seconds() < 60:
                st.markdown('<span class="status-indicator" style="background:#4CAF50;"></span>Online', unsafe_allow_html=True)
            elif time_diff.total_seconds() < 300:
                st.markdown(f'<span class="status-indicator" style="background:#FFC107;"></span>{int(time_diff.total_seconds())}s ago**', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-indicator" style="background:#F44336;"></span>Offline', unsafe_allow_html=True)
        except:
            st.markdown("⚪ Unknown")

    st.markdown("---")

    # Top Metrics Row
    condition, icon, color, status_text = get_condition_from_moisture(moisture)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card' style='background:linear-gradient(135deg, {color}20 0%, {color}40 100%);text-align:center;'>
            <h1 style='font-size:3em;margin:0;color:{color};'>{moisture}%</h1>
            <p style='margin:5px 0;color:#666;font-weight:600;'>💧 Soil Moisture</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background:linear-gradient(135deg, {color}20 0%, {color}40 100%);text-align:center;'>
            <h2 style='margin:5px 0;color:{color};font-size:2em;'>{icon} {condition}</h2>
            <p style='margin:5px 0;color:#666;font-weight:600;'>{status_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pump_icon = "✅" if pump_status == "ON" else "⭕"
        pump_color = "#4CAF50" if pump_status == "ON" else "#9E9E9E"
        pulse_class = "pulse" if pump_status == "ON" else ""
        
        st.markdown(f"""
        <div class='metric-card {pulse_class}' style='background:linear-gradient(135deg, {pump_color}20 0%, {pump_color}40 100%);text-align:center;'>
            <h2 style='margin:5px 0;color:{pump_color};font-size:2em;'>{pump_icon} {pump_status}</h2>
            <p style='margin:5px 0;color:#666;font-weight:600;'>🚰 Pump Status</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        mode_icon = "🤖" if pump_mode == "AUTO" else "🎮"
        mode_color = "#2196F3" if pump_mode == "AUTO" else "#FF9800"
        
        st.markdown(f"""
        <div class='metric-card' style='background:linear-gradient(135deg, {mode_color}20 0%, {mode_color}40 100%);text-align:center;'>
            <h2 style='margin:5px 0;color:{mode_color};font-size:2em;'>{mode_icon} {pump_mode}</h2>
            <p style='margin:5px 0;color:#666;font-weight:600;'>🎛 Control Mode</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Content
    left_panel, right_panel = st.columns([1, 2])

    # ===== LEFT PANEL =====
    with left_panel:
        # AI Recommendation
        ai_icon, ai_level, ai_msg, ai_color = get_ai_recommendation(moisture, pump_status)
        st.markdown(f"""
        <div style='padding:20px;background:linear-gradient(135deg, {ai_color}20 0%, {ai_color}40 100%);border-radius:10px;border-left:5px solid {ai_color};'>
            <h3 style='margin:0 0 10px 0;color:{ai_color};'>{ai_icon} AI Recommendation</h3>
            <p style='margin:0;font-size:1.1em;font-weight:600;color:#333;'>{ai_msg}</p>
            <p style='margin:5px 0 0 0;color:#666;font-size:0.9em;'>Confidence: {ai_level}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Control Panel
        st.markdown("### 🎮 Manual Controls")
        
        if auto_mode:
            st.info(f"🤖 Auto Mode Active\n\nPump will turn ON when moisture < {threshold_low}%\nPump will turn OFF when moisture > {threshold_high}%")
        else:
            st.warning("⚠ Manual Mode - Use buttons below to control pump")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🟢 TURN ON", use_container_width=True, type="primary", disabled=(pump_status == "ON")):
                with st.spinner("Activating pump..."):
                    if update_pump_status("ON"):
                        st.success("✅ Pump ON")
                        st.rerun()
        
        with col_btn2:
            if st.button("🔴 TURN OFF", use_container_width=True, disabled=(pump_status == "OFF")):
                with st.spinner("Stopping pump..."):
                    if update_pump_status("OFF"):
                        st.success("✅ Pump OFF")
                        st.rerun()
        
        st.caption("Manual override will temporarily disable auto mode")
        
        # Quick Stats
        st.markdown("---")
        st.markdown("### 📊 Live Statistics")
        
        pump_history = get_historical_data("pump", selected_hours)
        runtime_seconds = calculate_pump_runtime(pump_history)
        
        st.metric("⏱ Pump Runtime", format_runtime(runtime_seconds), 
                 delta=f"Last {time_range.lower()}", delta_color="off")
        
        recent_moisture = get_historical_data("moisture", hours=1)
        if len(recent_moisture) > 1:
            recent_values = [int(r["value"]) for r in recent_moisture if r["value"]]
            if recent_values:
                avg_moisture = sum(recent_values) / len(recent_values)
                trend = recent_values[-1] - recent_values[0]
                trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡"
                
                st.metric("📊 1-Hour Average", f"{avg_moisture:.1f}%")
                st.metric(f"{trend_icon} Trend", f"{trend:+.1f}%", 
                         delta="Increasing" if trend > 0 else "Decreasing" if trend < 0 else "Stable")

    # ===== RIGHT PANEL =====
    with right_panel:
        st.markdown("### 📈 Data Analytics")
        
        moisture_history = get_historical_data("moisture", selected_hours)
        pump_history = get_historical_data("pump", selected_hours)
        
        if moisture_history:
            df_moisture = pd.DataFrame(moisture_history)
            df_moisture["value"] = pd.to_numeric(df_moisture["value"], errors="coerce")
            df_moisture = df_moisture.dropna(subset=["value"])
            
            if not df_moisture.empty:
                # Create interactive plots
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("📊 Soil Moisture Trend", "🚰 Pump Activity Log"),
                    row_heights=[0.65, 0.35],
                    vertical_spacing=0.15
                )
                
                # Moisture trend with area fill
                fig.add_trace(
                    go.Scatter(
                        x=df_moisture["timestamp"],
                        y=df_moisture["value"],
                        mode="lines+markers",
                        name="Moisture Level",
                        line=dict(color="#2E7D32", width=3, shape="spline"),
                        marker=dict(size=6, symbol="circle"),
                        fill='tozeroy',
                        fillcolor='rgba(46, 125, 50, 0.15)',
                        hovertemplate="<b>%{y:.1f}%</b><br>%{x}<extra></extra>"
                    ),
                    row=1, col=1
                )
                
                # Threshold lines
                if auto_mode:
                    fig.add_hline(
                        y=threshold_low, line_dash="dash", line_color="#F44336", line_width=2,
                        annotation_text=f"Turn ON ({threshold_low}%)",
                        annotation_position="right",
                        row=1, col=1
                    )
                    fig.add_hline(
                        y=threshold_high, line_dash="dash", line_color="#2196F3", line_width=2,
                        annotation_text=f"Turn OFF ({threshold_high}%)",
                        annotation_position="right",
                        row=1, col=1
                    )
                
                # Pump activity timeline
                if pump_history:
                    df_pump = pd.DataFrame(pump_history)
                    df_pump["status_num"] = df_pump["value"].apply(lambda x: 1 if x == "ON" else 0)
                    
                    colors = df_pump["trigger"].apply(
                        lambda x: "#4CAF50" if x == "AUTO" else "#FF9800"
                    )
                    
                    fig.add_trace(
                        go.Scatter(
                            x=df_pump["timestamp"],
                            y=df_pump["status_num"],
                            mode="markers+lines",
                            name="Pump Activity",
                            line=dict(color="#1976D2", width=3, shape='hv'),
                            marker=dict(size=10, color=colors, line=dict(width=2, color='white')),
                            text=df_pump["trigger"],
                            hovertemplate="<b>%{text} Control</b><br>Time: %{x}<br>Status: %{y}<extra></extra>"
                        ),
                        row=2, col=1
                    )
                
                # Update layout
                fig.update_xaxes(title_text="Time", row=1, col=1, showgrid=True, gridcolor="rgba(128,128,128,0.1)")
                fig.update_yaxes(title_text="Moisture (%)", row=1, col=1, showgrid=True, gridcolor="rgba(128,128,128,0.1)")
                fig.update_xaxes(title_text="Time", row=2, col=1, showgrid=True, gridcolor="rgba(128,128,128,0.1)")
                fig.update_yaxes(
                    title_text="Status",
                    ticktext=["OFF", "ON"],
                    tickvals=[0, 1],
                    row=2, col=1,
                    showgrid=False
                )
                
                fig.update_layout(
                    height=750,
                    showlegend=True,
                    margin=dict(l=20, r=20, t=50, b=20),
                    hovermode="x unified",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=12)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistics Section
                if show_stats:
                    st.markdown("### 📊 Statistical Summary")
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    
                    stats_data = [
                        ("📊", "Average", f"{df_moisture['value'].mean():.1f}%", "#2196F3"),
                        ("📉", "Minimum", f"{df_moisture['value'].min():.1f}%", "#F44336"),
                        ("📈", "Maximum", f"{df_moisture['value'].max():.1f}%", "#4CAF50"),
                        ("📏", "Std Dev", f"{df_moisture['value'].std():.1f}%", "#FF9800")
                    ]
                    
                    for col, (icon, label, value, color) in zip([col_s1, col_s2, col_s3, col_s4], stats_data):
                        with col:
                            st.markdown(f"""
                            <div style='padding:15px;background:{color}20;border-radius:8px;text-align:center;border-left:4px solid {color};'>
                                <p style='margin:0;font-size:2em;'>{icon}</p>
                                <h3 style='margin:5px 0;color:{color};'>{value}</h3>
                                <p style='margin:0;color:#666;font-size:0.9em;'>{label}</p>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Condition Distribution
                if show_pie:
                    st.markdown("---")
                    st.markdown("### 🎨 Moisture Distribution Analysis")
                    
                    col_pie1, col_pie2 = st.columns([3, 2])
                    
                    with col_pie1:
                        conditions = df_moisture["value"].apply(lambda x: get_condition_from_moisture(x)[0])
                        condition_counts = conditions.value_counts()
                        
                        colors_map = {
                            "Very Dry": "#F44336",
                            "Dry": "#FF9800",
                            "Moist": "#4CAF50",
                            "Wet": "#2196F3"
                        }
                        pie_colors = [colors_map.get(c, "#9E9E9E") for c in condition_counts.index]
                        
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=condition_counts.index,
                            values=condition_counts.values,
                            marker=dict(colors=pie_colors, line=dict(color='white', width=2)),
                            hole=0.45,
                            textinfo='label+percent',
                            textfont=dict(size=14, color='white'),
                            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
                        )])
                        
                        fig_pie.update_layout(
                            height=350, 
                            margin=dict(l=10, r=10, t=10, b=10),
                            showlegend=False,
                            annotations=[dict(text=f'{len(conditions)}<br>Readings', x=0.5, y=0.5, font_size=20, showarrow=False)]
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col_pie2:
                        st.markdown("Distribution Breakdown:")
                        for condition, count in condition_counts.items():
                            percentage = (count / len(conditions)) * 100
                            _, icon, color, _ = get_condition_from_moisture(
                                15 if condition == "Very Dry" else 
                                35 if condition == "Dry" else 
                                55 if condition == "Moist" else 75
                            )
                            
                            st.markdown(f"""
                            <div style='padding:10px;margin:5px 0;background:{color}15;border-radius:5px;border-left:3px solid {color};'>
                                <span style='font-size:1.5em;'>{icon}</span>
                                <strong style='color:{color};'> {condition}</strong><br>
                                <span style='color:#666;'>{count} readings • {percentage:.1f}%</span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Irrigation efficiency score
                        optimal_readings = condition_counts.get("Moist", 0)
                        efficiency = (optimal_readings / len(conditions)) * 100
                        
                        if efficiency >= 70:
                            eff_color, eff_icon, eff_text = "#4CAF50", "🌟", "Excellent"
                        elif efficiency >= 50:
                            eff_color, eff_icon, eff_text = "#2196F3", "👍", "Good"
                        elif efficiency >= 30:
                            eff_color, eff_icon, eff_text = "#FF9800", "⚠", "Fair"
                        else:
                            eff_color, eff_icon, eff_text = "#F44336", "❗", "Needs Improvement"
                        
                        st.markdown(f"""
                        <div style='padding:15px;background:{eff_color}20;border-radius:8px;text-align:center;border:2px solid {eff_color};'>
                            <p style='margin:0;font-size:2em;'>{eff_icon}</p>
                            <h3 style='margin:5px 0;color:{eff_color};'>{efficiency:.1f}%</h3>
                            <p style='margin:0;color:#666;font-weight:600;'>Irrigation Efficiency<br>{eff_text}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Export Section
                st.markdown("---")
                col_exp1, col_exp2 = st.columns([2, 1])
                
                with col_exp1:
                    st.markdown("### 💾 Export Data")
                    export_format = st.radio("Format:", ["CSV", "JSON"], horizontal=True)
                
                with col_exp2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("⬇ Download", use_container_width=True, type="primary"):
                        export_df = df_moisture.copy()
                        export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                        export_df = export_df.rename(columns={"value": "moisture_percent"})
                        
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        if export_format == "CSV":
                            csv_data = export_df.to_csv(index=False)
                            st.download_button(
                                label="📄 Download CSV File",
                                data=csv_data,
                                file_name=f"irrigation_data_{timestamp}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            json_data = export_df.to_json(orient="records", indent=2)
                            st.download_button(
                                label="📋 Download JSON File",
                                data=json_data,
                                file_name=f"irrigation_data_{timestamp}.json",
                                mime="application/json",
                                use_container_width=True
                            )
            else:
                st.warning("📊 No valid moisture data available in selected time range.")
        else:
            st.info("📊 Waiting for data...")
            st.markdown("""
            <div style='padding:30px;text-align:center;background:linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);border-radius:10px;'>
                <h3 style='color:#2E7D32;'>🌱 Your Dashboard is Ready!</h3>
                <p style='color:#666;font-size:1.1em;'>Data will appear automatically as the system collects readings:</p>
                <ul style='text-align:left;max-width:400px;margin:20px auto;color:#666;'>
                    <li>📊 Moisture readings logged every 3 seconds</li>
                    <li>🚰 Pump status changes tracked in real-time</li>
                    <li>📈 Charts populate as data accumulates</li>
                    <li>🤖 AI recommendations update automatically</li>
                </ul>
                <p style='margin-top:20px;color:#2E7D32;font-weight:600;'>No action needed - just wait a moment!</p>
            </div>
            """, unsafe_allow_html=True)

# =====================================================
# APPLICATION ROUTER
# =====================================================

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False

# Route to appropriate page
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