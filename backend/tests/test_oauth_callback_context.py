import unittest
import uuid
from urllib.parse import parse_qs, urlparse

from starlette.requests import Request
from starlette.responses import Response

from routes.oauth import (
    _decode_state,
    _oauth_context_cookie_name,
    _set_oauth_context_cookie,
    oauth_callback,
)


def _request_with_cookies(cookies: dict[str, str] | None = None) -> Request:
    cookie_header = "; ".join(f"{key}={value}" for key, value in (cookies or {}).items())
    headers = []
    if cookie_header:
        headers.append((b"cookie", cookie_header.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/oauth/facebook/callback",
        "query_string": b"",
        "headers": headers,
        "scheme": "https",
        "server": ("sns.aimtop.ai", 443),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


class OAuthCallbackContextTest(unittest.IsolatedAsyncioTestCase):
    def test_auth_url_sets_short_lived_oauth_context_cookie(self):
        client_id = uuid.uuid4()
        payload = {
            "client_id": str(client_id),
            "frontend_redirect": f"/clients/{client_id}",
            "redirect_uri": "https://sns.aimtop.ai/api/v1/oauth/facebook/callback",
        }
        response = Response()

        _set_oauth_context_cookie(response, "facebook", payload, payload["redirect_uri"])

        set_cookie = response.headers["set-cookie"]
        self.assertIn(_oauth_context_cookie_name("facebook"), set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Max-Age=600", set_cookie)
        self.assertIn("SameSite=lax", set_cookie)
        self.assertIn("Secure", set_cookie)

    async def test_callback_without_state_uses_oauth_context_cookie(self):
        client_id = uuid.uuid4()
        redirect_uri = "https://sns.aimtop.ai/api/v1/oauth/facebook/callback"
        frontend_redirect = f"/clients/{client_id}"
        cookie_response = Response()
        _set_oauth_context_cookie(
            cookie_response,
            "facebook",
            {
                "client_id": str(client_id),
                "frontend_redirect": frontend_redirect,
                "redirect_uri": redirect_uri,
            },
            redirect_uri,
        )
        cookie_value = cookie_response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]

        response = await oauth_callback(
            request=_request_with_cookies({_oauth_context_cookie_name("facebook"): cookie_value}),
            platform="facebook",
            code=None,
            state=None,
            error=None,
            error_description=None,
            client_id=None,
            db=None,
        )

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        parsed = urlparse(location)
        self.assertEqual(parsed.path, f"/clients/{client_id}")
        query = parse_qs(parsed.query)
        self.assertEqual(query["oauth"], ["error"])
        self.assertEqual(query["platform"], ["facebook"])
        self.assertEqual(query["message"], ["OAuth code가 누락되었습니다"])
        self.assertIn(_oauth_context_cookie_name("facebook") + "=", response.headers["set-cookie"])

    async def test_callback_with_meta_error_code_surfaces_meta_message_before_code_check(self):
        client_id = uuid.uuid4()
        redirect_uri = "https://sns.aimtop.ai/api/v1/oauth/facebook/callback"
        frontend_redirect = f"/clients/{client_id}"
        cookie_response = Response()
        _set_oauth_context_cookie(
            cookie_response,
            "facebook",
            {
                "client_id": str(client_id),
                "frontend_redirect": frontend_redirect,
                "redirect_uri": redirect_uri,
            },
            redirect_uri,
        )
        cookie_value = cookie_response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]

        response = await oauth_callback(
            request=_request_with_cookies({_oauth_context_cookie_name("facebook"): cookie_value}),
            platform="facebook",
            code=None,
            state=None,
            error=None,
            error_description=None,
            error_code="1349048",
            error_message="URL을 읽어들일 수 없습니다: 앱 도메인에 포함되어 있지 않은 URL 도메인입니다.",
            error_reason=None,
            client_id=None,
            db=None,
        )

        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.headers["location"])
        self.assertEqual(parsed.path, f"/clients/{client_id}")
        query = parse_qs(parsed.query)
        self.assertEqual(query["oauth"], ["error"])
        self.assertEqual(query["platform"], ["facebook"])
        self.assertEqual(
            query["message"],
            ["Meta 오류 1349048: URL을 읽어들일 수 없습니다: 앱 도메인에 포함되어 있지 않은 URL 도메인입니다."],
        )

    async def test_callback_without_state_or_cookie_redirects_instead_of_raising_400(self):
        response = await oauth_callback(
            request=_request_with_cookies(),
            platform="facebook",
            code=None,
            state=None,
            error=None,
            error_description=None,
            client_id=None,
            db=None,
        )

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        parsed = urlparse(location)
        self.assertEqual(parsed.path, "/clients")
        query = parse_qs(parsed.query)
        self.assertEqual(query["oauth"], ["error"])
        self.assertEqual(query["platform"], ["facebook"])
        self.assertEqual(query["message"], ["OAuth client_id가 누락되었습니다. 클라이언트 화면에서 다시 연동을 시작해 주세요."])


if __name__ == "__main__":
    unittest.main()
