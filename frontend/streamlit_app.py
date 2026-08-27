import streamlit as st
import sys
from pathlib import Path

# Put the repo root on sys.path so `from frontend.views import ...` resolves
# regardless of the directory streamlit was launched from.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure FastAPI backend is running in background on port 8000
import subprocess
try:
    import requests
    requests.get("http://127.0.0.1:8000/api/v1/health", timeout=0.5)
except Exception:
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ])

# Configure page
st.set_page_config(
    page_title="ATS Resume Scorer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auth state. Populated by Supabase sign-in / sign-up / OAuth.
# All four are None when signed out, all four are set when signed in.
for key, default in [
    ("access_token", None),
    ("refresh_token", None),
    ("user_id", None),       # Supabase auth user id (uuid); also used by api_client
    ("user_email", None),
    ("auth_error", None),
    ("auth_info", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# If we just came back from Google / GitHub OAuth, Supabase appends `?code=<authcode>`
if (
    not st.session_state.access_token
    and "code" in st.query_params
):
    from frontend.services import supabase_client as _sc
    code_param = st.query_params["code"]
    cv_param = st.query_params.get("cv", "")
    result = _sc.exchange_code_for_session(code_param, code_verifier=cv_param)
    st.query_params.clear()
    if "error" in result:
        st.session_state.auth_error = f"Sign-in failed: {result['error']}"
    else:
        st.session_state.access_token  = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id       = result["user_id"]
        st.session_state.user_email    = result["email"]
    st.rerun()

#Load custom CSS
def load_css():
    try:
        css_path = Path(__file__).parent / 'assets' / 'styles.css'
        with open(css_path, 'r') as f:
            return f'<style>{f.read()}</style>'
    except FileNotFoundError:
        return ''

st.markdown(load_css(), unsafe_allow_html=True)

# Initialize session state for view management
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'landing'

# Sidebar navigation
with st.sidebar:
    st.markdown("## Navigation")
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = 'landing'
        st.rerun()
    
    if st.button("🎯 ATS Scorer", use_container_width=True):
        st.session_state.current_view = 'scorer'
        st.rerun()
    
    if st.button("📊 History", use_container_width=True):
        st.session_state.current_view = 'history'
        st.rerun()
    
    if st.button("📚 Resources", use_container_width=True):
        st.session_state.current_view = 'resources'
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 👤 Account")

    from frontend.services import supabase_client

    if st.session_state.access_token:
        # Signed-in state: show email + sign-out button.
        st.caption(f"Signed in as **{st.session_state.user_email}**")
        if st.button("Sign out", use_container_width=True):
            supabase_client.sign_out()
            for k in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[k] = None
            st.rerun()
    else:
        # Signed-out state: tabs for sign-in vs sign-up + Google OAuth button.
        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.auth_info:
            st.info(st.session_state.auth_info)
            st.session_state.auth_info = None

        tab_in, tab_up = st.tabs(["Sign in", "Sign up"])

        with tab_in:
            with st.form("signin_form", clear_on_submit=False):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_pw")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                result = supabase_client.sign_in_with_password(email, password)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                st.rerun()

        with tab_up:
            with st.form("signup_form", clear_on_submit=False):
                email_up = st.text_input("Email", key="signup_email")
                password_up = st.text_input("Password (min 6 chars)", type="password", key="signup_pw")
                submitted_up = st.form_submit_button("Create account", use_container_width=True)
            if submitted_up:
                result = supabase_client.sign_up_with_password(email_up, password_up)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                elif result.get("pending_confirmation"):
                    st.session_state.auth_info = (
                        f"Check your inbox — confirmation email sent to {result['email']}."
                    )
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                st.rerun()

        st.markdown("<div style='text-align:center; margin: 8px 0; color:#94a3b8;'>or</div>",
                    unsafe_allow_html=True)

        # Google SVG logo (official colours)
        google_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="20" height="20" style="vertical-align:middle;margin-right:10px;">
          <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
          <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
          <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        </svg>"""

        oauth = supabase_client.google_oauth_url()
        if "error" in oauth:
            st.caption(f"Google sign-in unavailable: {oauth['error']}")
        else:
            st.markdown(
                f"""<a href="{oauth['url']}" target="_self" style="
                    display:flex; align-items:center; justify-content:center;
                    width:100%; padding:0.5rem 1rem;
                    background:white; color:#3c4043;
                    border:1px solid #dadce0; border-radius:6px;
                    text-decoration:none; font-size:0.95rem; font-weight:500;
                    margin-top:4px; box-sizing:border-box;
                ">{google_svg} Continue with Google</a>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

        # GitHub SVG logo
        github_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" style="vertical-align:middle;margin-right:10px;fill:white;">
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
        </svg>"""

        gh_oauth = supabase_client.github_oauth_url()
        if "error" in gh_oauth:
            st.caption(f"GitHub sign-in unavailable: {gh_oauth['error']}")
        else:
            st.markdown(
                f"""<a href="{gh_oauth['url']}" target="_self" style="
                    display:flex; align-items:center; justify-content:center;
                    width:100%; padding:0.5rem 1rem;
                    background:#24292e; color:white;
                    border-radius:6px; text-decoration:none;
                    font-size:0.95rem; font-weight:500;
                    margin-top:8px; box-sizing:border-box;
                ">{github_svg} Continue with GitHub</a>""",
                unsafe_allow_html=True,
            )

# Main content area - render based on current view
if st.session_state.current_view == 'landing':
    # Import and render landing page
    from frontend.views import landing
    landing.render()

elif st.session_state.current_view == 'scorer':
    # Import and render scorer page
    from frontend.views import scorer
    scorer.render()

elif st.session_state.current_view == 'history':
    # Import and render history page
    from frontend.views import history
    history.render()

elif st.session_state.current_view == 'resources':
    # Import and render resources page
    from frontend.views import resources
    resources.render()