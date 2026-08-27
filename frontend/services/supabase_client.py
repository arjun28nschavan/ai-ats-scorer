import os
import logging
from pathlib import Path
from typing import Any, Dict
import streamlit as st
from supabase import Client, create_client, ClientOptions

logger = logging.getLogger('ats_resume_scorer')


try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
except ImportError:
    pass


def _secret(key: str, section: str = 'supabase') -> str:
    """Read from env first, then fall back to st.secrets[section][key]."""
    val = os.getenv(key, '')
    if val:
        return val
    try:
        return st.secrets[section][key]
    except (KeyError, FileNotFoundError, AttributeError):
        return ''


SUPABASE_URL = _secret('SUPABASE_URL')
SUPABASE_ANON_KEY = _secret('SUPABASE_ANON_KEY')

def get_oauth_redirect_url() -> str:
    """Return the base URL where Supabase should redirect the user after OAuth."""
    # 1. Environment variable
    env_url = os.getenv('AUTH_REDIRECT_URL', '').strip()
    if env_url and not env_url.endswith('/auth/v1/callback') and 'supabase.co' not in env_url:
        return env_url

    # 2. Streamlit secrets
    for section in ['app', 'general', 'google_oauth', 'github_oauth']:
        sec_url = _secret('redirect_uri', section).strip() or _secret('app_url', section).strip()
        if sec_url and not sec_url.endswith('/auth/v1/callback') and 'supabase.co' not in sec_url:
            return sec_url

    # 3. Check if deployed on Render or Streamlit Cloud
    if os.getenv('RENDER_EXTERNAL_URL'):
        return os.getenv('RENDER_EXTERNAL_URL')
    if os.path.exists('/mount/src') or os.getenv('STREAMLIT_SHARING_HOST'):
        return 'https://ai-ats-scorer.streamlit.app'

    return 'http://localhost:8501'


OAUTH_REDIRECT_URL = get_oauth_redirect_url()


def _missing_config() -> str | None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return 'Supabase is not configured — set SUPABASE_URL and SUPABASE_ANON_KEY in .env or .streamlit/secrets.toml'
    return None


@st.cache_resource
def get_client() -> Client | None:
    """Cached singleton Supabase client."""
    if _missing_config():
        return None
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def _session_dict(session, user) -> Dict[str, Any]:
    return {
        'access_token':  session.access_token,
        'refresh_token': session.refresh_token,
        'user_id':       user.id,
        'email':         user.email,
    }


def sign_in_with_password(email: str, password: str) -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        resp = get_client().auth.sign_in_with_password(
            {'email': email, 'password': password}
        )
        if not resp.session or not resp.user:
            return {'error': 'Invalid credentials'}
        return _session_dict(resp.session, resp.user)
    except Exception as exc:
        logger.warning(f'sign_in_with_password failed: {exc}')
        return {'error': _humanize(exc)}


def sign_up_with_password(email: str, password: str) -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        resp = get_client().auth.sign_up({'email': email, 'password': password})
        if resp.session and resp.user:
            return _session_dict(resp.session, resp.user)
        if resp.user:
            return {'pending_confirmation': True, 'email': email}
        return {'error': 'Sign-up failed'}
    except Exception as exc:
        logger.warning(f'sign_up failed: {exc}')
        return {'error': _humanize(exc)}


import urllib.parse


def _attach_cv_to_url(raw_url: str, verifier: str) -> str:
    if not verifier:
        return raw_url
    try:
        redirect_target = get_oauth_redirect_url()
        parsed = urllib.parse.urlparse(raw_url)
        qs = urllib.parse.parse_qs(parsed.query)
        base_redirect = qs.get('redirect_to', [redirect_target])[0]
        qs['redirect_to'] = [f"{base_redirect}?cv={verifier}"]
        new_query = urllib.parse.urlencode(qs, doseq=True)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return raw_url


def google_oauth_url() -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        client = get_client()
        redirect_target = get_oauth_redirect_url()
        resp = client.auth.sign_in_with_oauth({
            'provider': 'google',
            'options': {'redirect_to': redirect_target},
        })
        storage_key = f'{client.auth._storage_key}-code-verifier'
        verifier = client.auth._storage.get_item(storage_key) or ''
        url = _attach_cv_to_url(resp.url, verifier)
        return {'url': url}
    except Exception as exc:
        logger.warning(f'oauth url generation failed: {exc}')
        return {'error': _humanize(exc)}


def github_oauth_url() -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        client = get_client()
        redirect_target = get_oauth_redirect_url()
        resp = client.auth.sign_in_with_oauth({
            'provider': 'github',
            'options': {'redirect_to': redirect_target},
        })
        storage_key = f'{client.auth._storage_key}-code-verifier'
        verifier = client.auth._storage.get_item(storage_key) or ''
        url = _attach_cv_to_url(resp.url, verifier)
        return {'url': url}
    except Exception as exc:
        logger.warning(f'github oauth url generation failed: {exc}')
        return {'error': _humanize(exc)}


def exchange_code_for_session(auth_code: str, code_verifier: str = '') -> Dict[str, Any]:
    """Called once after the OAuth provider redirects back with `?code=...`."""
    err = _missing_config()
    if err:
        return {'error': err}
    client = get_client()
    try:
        storage_key = f'{client.auth._storage_key}-code-verifier'
        verifier = (
            code_verifier
            or st.session_state.get('oauth_code_verifier')
            or client.auth._storage.get_item(storage_key)
            or ''
        )
        redirect_base = get_oauth_redirect_url()
        if verifier:
            client.auth._storage.set_item(storage_key, verifier)
            redirect_to_used = f"{redirect_base}?cv={verifier}"
        else:
            redirect_to_used = redirect_base

        resp = client.auth.exchange_code_for_session({
            'auth_code': auth_code,
            'code_verifier': verifier,
        })
        if not resp.session or not resp.user:
            return {'error': 'OAuth exchange returned no session'}
        return _session_dict(resp.session, resp.user)
    except Exception as exc:
        logger.warning(f'exchange_code_for_session failed: {exc}')
        return {'error': _humanize(exc)}


def sign_out() -> None:
    if _missing_config():
        return
    try:
        get_client().auth.sign_out()
    except Exception as exc:
        logger.warning(f'sign_out failed: {exc}')


def _humanize(exc: Exception) -> str:
    msg = str(exc)
    # supabase errors arrive as "<status>: {json blob}" — surface the human bit
    if 'invalid_grant' in msg.lower() or 'invalid login' in msg.lower():
        return 'Wrong email or password'
    if 'user already registered' in msg.lower() or 'already been registered' in msg.lower():
        return 'An account with this email already exists — try signing in'
    if 'password should be at least' in msg.lower():
        return 'Password too short (Supabase default is 6 characters)'
    return msg
