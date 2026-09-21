import os
import streamlit as st
from dotenv import load_dotenv
from database.db import init_db
from services.ui.style_loader import load_css, inject_local_font
from services.ui.components import image_to_base64

# Load environment variables
load_dotenv()

# Authentication state management (must exist before set_page_config so we
# can decide whether to show the sidebar at all)
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

_is_logged_in = st.session_state.user_id is not None

# Configure the Streamlit application
st.set_page_config(
    page_title="Trainora",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load the shared theme (same look as the landing page) on every screen
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
load_css(os.path.join(_static_dir, "style.css"))
inject_local_font(os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

# No sidebar anywhere in this app — navigation happens via the Home hub
# and the top-right menu icon instead.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)



# Initialize the database on startup
@st.cache_resource
def setup_database():
    init_db()


try:
    setup_database()
except Exception as e:
    st.error(f"Failed to initialize database: {e}")


def render_login():
    """Centered premium login / sign-up card with the coach mascot floating
    beside it. All auth logic below is byte-for-byte the same as before —
    only the visual wrapper and copy changed.
    """
    _images_dir = os.path.join(_static_dir, "images")
    _brand_mascot = image_to_base64(os.path.join(_images_dir, "coach-mascot.png"))

    # Zero-size marker so our CSS can target *only* this screen's layout
    # (see "LOGIN SCREEN" section in static/style.css) without touching any
    # other page's columns, forms, or buttons.
    st.markdown('<div class="tr-login-shell"></div>', unsafe_allow_html=True)

    mascot, card = st.columns([2, 3], gap="large")

    with mascot:
        st.markdown(
            f"""
            <div class="tr-login-mascot-pane">
                <div class="tr-login-mascot-glow"></div>
                <img class="tr-login-floating-mascot" src="data:image/png;base64,{_brand_mascot}" alt="" />
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card:
        st.markdown(
            """
            <div class="tr-login-form-head">
                <div class="trainora-login-tag">
                    <span class="dot"></span>
                    <span>AI-POWERED · PERSONALIZED · FITNESS COACH</span>
                </div>
                <div class="trainora-login-title">Welcome back</div>
                <div class="trainora-login-sub">Sign in or create an account to access your personalized dashboard.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["Sign In", "Create Account"])

        with tab1:
            with st.form("login_form", clear_on_submit=False):
                login_email = st.text_input("Email", key="login_email", placeholder="you@example.com")
                login_password = st.text_input(
                    "Password", type="password", key="login_password", placeholder="••••••••"
                )
                submit_login = st.form_submit_button("Sign In", type="primary", width="stretch")

            if submit_login:
                if not login_email or not login_password:
                    st.error("Please enter both email and password.")
                else:
                    from services.auth_service import login_user
                    user = login_user(login_email.strip(), login_password)
                    if user:
                        st.session_state.user_id = user.id
                        st.session_state.username = user.full_name
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        with tab2:
            with st.form("signup_form", clear_on_submit=False):
                reg_name = st.text_input("Full Name", key="reg_name", placeholder="Jordan Lee")
                reg_email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
                reg_password = st.text_input(
                    "Password", type="password", key="reg_password", placeholder="At least 6 characters"
                )
                submit_signup = st.form_submit_button("Create Account", type="primary", width="stretch")

            if submit_signup:
                if not reg_name or not reg_email or not reg_password:
                    st.error("Please fill in all fields.")
                else:
                    from services.auth_service import register_user
                    success, msg = register_user(reg_name.strip(), reg_email.strip(), reg_password)
                    if success:
                        st.success("Registration successful! Please log in from the Sign In tab.")
                    else:
                        st.error(msg)


if not _is_logged_in:
    # Only the login/signup view is reachable - no other pages, no sidebar.
    pg = st.navigation([st.Page(render_login, title="Login", default=True)], position="hidden")
    pg.run()
else:
    # Persistent top bar (normal page flow, not an overlay): brand wordmark
    # on the left, themed account menu on the right. Sits above every page's
    # content with a subtle divider, so it never has to be re-aligned per
    # page like the old hero-corner overlay did.
    st.markdown('<div class="tr-topbar-marker"></div>', unsafe_allow_html=True)
    _brand_col, _menu_col = st.columns([9, 1], vertical_alignment="center")
    with _brand_col:
        st.markdown(
            '<div class="tr-topbar-brand"><span class="tr-topbar-dot"></span>TRAINORA</div>',
            unsafe_allow_html=True,
        )
    with _menu_col:
        with st.popover(" ", width="content"):
            st.markdown('<div class="tr-account-menu"></div>', unsafe_allow_html=True)
            if st.button("Home", width="stretch", key="menu_home"):
                st.switch_page("pages/home.py")
            if st.button("My Profile", width="stretch", key="menu_profile"):
                st.switch_page("pages/assessment.py")
            st.markdown("---")
            if st.button("Logout", width="stretch", key="menu_logout"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()

    # Land new users on the Profile/Assessment wizard first (so the 3 AI
    # agents always have data to work with); returning users land on Home.
    from database.db import SessionLocal
    from database.models import FitnessAssessment

    _db = SessionLocal()
    try:
        _has_assessment = (
            _db.query(FitnessAssessment)
            .filter(FitnessAssessment.user_id == st.session_state.user_id)
            .first()
            is not None
        )
    finally:
        _db.close()

    # Only these 5 routes exist - reachable via the Home hub cards and the
    # top-right menu, never via a sidebar.

    
    pages = [
        st.Page("pages/home.py", title="Home", default=_has_assessment),
        st.Page("pages/assessment.py", title="My Profile", default=not _has_assessment),
        st.Page("pages/workout.py", title="AI Workout Planner", icon="🏋️‍♂️"),
        st.Page("pages/diet.py", title="AI Diet Planner", icon="🥗"),
        st.Page("pages/live_tracker.py", title="Live AI Gym Coach", icon="🎥"),
    ]
    pg = st.navigation(pages, position="hidden")
    pg.run()