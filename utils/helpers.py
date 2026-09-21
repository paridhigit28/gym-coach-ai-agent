import streamlit as st
import plotly.graph_objects as go

def create_bmi_gauge(bmi: float):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = bmi,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "BMI"},
        gauge = {
            'axis': {'range': [10, 40]},
            'bar': {'color': "darkgray"},
            'steps': [
                {'range': [10, 18.5], 'color': "lightblue"},
                {'range': [18.5, 24.9], 'color': "lightgreen"},
                {'range': [25, 29.9], 'color': "gold"},
                {'range': [30, 40], 'color': "crimson"}
            ],
        }
    ))
    return fig

def render_sidebar_nav():
    st.sidebar.title(f"Welcome, {st.session_state.get('username', 'User')}!")
    
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/live_tracker.py", label="Live AI Gym Coach", icon="🎥")
    st.sidebar.page_link("pages/dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.page_link("pages/profile.py", label="Profile", icon="👤")
    st.sidebar.page_link("pages/assessment.py", label="Fitness Assessment", icon="📋")
    st.sidebar.page_link("pages/workout.py", label="AI Workout Planner", icon="🏋️‍♂️")
    st.sidebar.page_link("pages/diet.py", label="AI Diet Planner", icon="🥗")
    st.sidebar.page_link("pages/progress.py", label="Progress Tracker", icon="📈")
    st.sidebar.page_link("pages/analytics.py", label="Analytics Dashboard", icon="📉")
    st.sidebar.page_link("pages/chatbot.py", label="AI Fitness Coach", icon="🤖")

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", key="sidebar_logout"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
