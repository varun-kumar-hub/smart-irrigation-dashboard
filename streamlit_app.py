"""
Smart Irrigation System - Enhanced Interactive Dashboard
Fixed version with graph display issues resolved
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

def get_device_data():
    """Fetch complete device data"""
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
    """Fetch historical data - FIXED VERSION"""
    try:
        data = db.child("history").child(DEVICE_ID).child(data_type).get().val()
        
        if not data:
            return []
        
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
        records = []
        
        for key, val in data.items():
            try:
                if not isinstance(val, dict):
                    continue
                    
                ts_str = val.get("timestamp", "")
                if not ts_str:
                    continue
                
                # Handle different timestamp formats
                ts_str = ts_str.replace("Z", "+00:00")
                try:
                    ts = datetime.datetime.fromisoformat(ts_str)
                except:
                    # Try parsing as different format if needed
                    ts = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                
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

def generate_sample_moisture_data():
    """Generate sample moisture data for testing (last 24 hours)"""
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Generate 48 data points (one every 30 minutes for 24 hours)
        for i in range(48):
            timestamp = now - datetime.timedelta(minutes=30 * (48 - i))
            
            # Simulate realistic moisture pattern
            # Start at 70%, gradually decrease, spike when pump runs
            base_moisture = 70 - (i * 0.8)  # Gradual decrease
            
            # Add some random variation
            import random
            moisture = max(15, min(85, base_moisture + random.uniform(-5, 5)))
            
            # Push to Firebase
            db.child("history").child(DEVICE_ID).child("moisture").push({
                "value": int(moisture),
                "timestamp": timestamp.isoformat().replace("+00:00", "Z")
            })
        
        return True
    except Exception as e:
        st.error(f"Error generating data: {e}")
        return False

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
    
    if last_on_time:
        duration = (datetime.datetime.now(datetime.timezone.utc) - last_on_time).total_seconds()
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
    """Dashboard - FIXED VERSION"""
    if "user" not in st.session_state:
        st.warning("⚠ Please login first.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    # Auto-refresh
    count = st_autorefresh(interval=5000, key="refresh")

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
    last_seen = info_data.get("lastSeen", "")

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
        
        with st.expander("📊 Display Options", expanded=False):
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
        st.markdown("### 🧪 Testing Tools")
        
        if st.button("📊 Generate Sample Data", use_container_width=True):
            with st.spinner("Generating 24 hours of sample moisture data..."):
                if generate_sample_moisture_data():
                    st.success("✅ Sample data created!")
                    st.info("Refresh the page to see the graphs")
                    st.rerun()

    # MAIN DASHBOARD
    st.markdown("# 💧 Smart Irrigation Dashboard")
    
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

    # GRAPHS SECTION
    st.markdown("### 📈 Historical Data")
    
    # Fetch historical data
    moisture_history = get_historical_data("moisture", selected_hours)
    pump_history = get_historical_data("pump", selected_hours)
    
    # Check if we have moisture data
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
                    vertical_spacing=0.15
                )
                
                # Moisture plot
                fig.add_trace(
                    go.Scatter(
                        x=df_moisture["timestamp"],
                        y=df_moisture["value"],
                        mode="lines+markers",
                        name="Moisture",
                        line=dict(color="#2E7D32", width=3),
                        marker=dict(size=5),
                        fill='tozeroy',
                        fillcolor='rgba(46, 125, 50, 0.1)'
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
                
                # Pump activity
                df_pump = pd.DataFrame(pump_history)
                df_pump["status_num"] = df_pump["value"].apply(lambda x: 1 if x == "ON" else 0)
                
                fig.add_trace(
                    go.Scatter(
                        x=df_pump["timestamp"],
                        y=df_pump["status_num"],
                        mode="markers+lines",
                        name="Pump Status",
                        line=dict(color="#1976D2", width=2, shape='hv'),
                        marker=dict(size=8, color='#1976D2')
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
        else:
            st.warning("⚠ No valid data points after processing")
    else:
        # No moisture data available
        st.info(f"""
        📊 **No moisture history data found**
        
        Your Firebase has pump activity records but no moisture sensor readings logged to history.
        
        **To see graphs, you need to:**
        1. Click the "📊 Generate Sample Data" button in the sidebar (Testing Tools section)
        2. OR configure your ESP32/Arduino to log moisture readings to:
           ```
           history/device_001/moisture/
           ```
        
        **Current data structure:**
        - ✅ Pump history: {len(pump_history)} records found
        - ❌ Moisture history: 0 records found
        
        The system shows current moisture as **{moisture}%** but this isn't being logged to history.
        """)
        
        # Show pump activity only if available
        if has_pump_data:
            st.markdown("### 🚰 Pump Activity (Available Data)")
            
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
            st.metric("⏱ Total Pump Runtime", format_runtime(runtime), 
                     delta=f"Last {time_range.lower()}")

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