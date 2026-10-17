from starlette.testclient import TestClient
from pipeline.web import app
from pipeline.config import create_session_token

client = TestClient(app)
client.cookies.set("session_token", create_session_token())


def test_index_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "Sosyal Medya Otomasyon" in res.text


def test_api_config():
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["app_name"] == "Sosyal Medya Otomasyon"
    assert "default_system_prompt" in data
    assert "auth" in data
    assert "formats" in data
    assert "brand" in data
    assert "styles" in data


def test_api_outputs():
    res = client.get("/api/outputs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_generate_mock():
    payload = {
        "topic": "Web Arayüzü Test Gönderisi",
        "image_count": "1",
        "format": "post_4x5",
        "style": "lifestyle",
        "overlay_text_val": "Örnek Başlık",
        "notes": "",
        "provider": "openai",
        "quality": "standard",
        "mock": "true",
        "reference_mode": "b1",
    }
    res = client.post("/api/generate", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["posts"]) == 1
    post = data["posts"][0]
    assert "background_url" in post
    assert "final_url" in post


def test_api_overlay_preview():
    # Run a mock generate first to get a post_dir
    payload = {
        "topic": "Overlay Test",
        "image_count": "1",
        "format": "post_1x1",
        "style": "minimal_flat",
        "overlay_text_val": "İlk Metin",
        "notes": "",
        "mock": "true",
    }
    gen_res = client.post("/api/generate", data=payload)
    assert gen_res.status_code == 200
    post_dir = gen_res.json()["posts"][0]["dir"]

    # Now test quick overlay update
    update_res = client.post(
        "/api/overlay-preview",
        json={"post_dir": post_dir, "overlay_text": "Yeni Güncellenmiş Metin", "align": "center"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["success"] is True
    assert "final_url" in update_res.json()


def test_auth_status():
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert "auth_required" in data
    assert "logged_in" in data


def test_auth_login_and_protection(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "test-secret-123")

    anon_client = TestClient(app)
    # Korumalı endpoint girişsiz denenince 401 dönmeli
    unauth_res = anon_client.get("/api/outputs")
    assert unauth_res.status_code == 401

    # Yanlış şifre ile login
    bad_login = anon_client.post("/api/auth/login", json={"password": "wrong"})
    assert bad_login.status_code == 401

    # Doğru şifre ile login
    good_login = anon_client.post("/api/auth/login", json={"password": "test-secret-123"})
    assert good_login.status_code == 200
    assert "session_token" in good_login.cookies

    # Oturum çerezi ile korumalı endpoint erişilebilir olmalı
    auth_client = TestClient(app, cookies=good_login.cookies)
    auth_res = auth_client.get("/api/outputs")
    assert auth_res.status_code == 200

    # Logout
    logout_res = auth_client.post("/api/auth/logout")
    assert logout_res.status_code == 200


def test_api_generate_with_system_prompt():
    payload = {
        "topic": "Özel Sistem Promptlu Test",
        "system_prompt": "Sen lüks ve minimalist bir mücevher markasının Instagram yöneticisisin.",
        "image_count": "1",
        "format": "post_4x5",
        "style": "product_photo",
        "mock": "true",
    }
    res = client.post("/api/generate", data=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["posts"]) == 1


def test_path_traversal_protection():
    # Attempting to access parent directories or arbitrary paths must return 400
    res = client.post(
        "/api/overlay-preview",
        json={"post_dir": "../../etc/passwd", "overlay_text": "Hacked", "align": "center"},
    )
    assert res.status_code == 400
    assert "Geçersiz veya yetkisiz" in res.json()["detail"]


def test_session_token_expiration():
    from pipeline.config import create_session_token, verify_session_token

    # 1. Fresh token
    fresh_token = create_session_token(expires_in_seconds=3600)
    assert verify_session_token(fresh_token) is True

    # 2. Expired token (expires in -10 seconds)
    expired_token = create_session_token(expires_in_seconds=-10)
    assert verify_session_token(expired_token) is False


def test_logo_format_validation():
    # SVG file upload must be rejected with 400
    svg_content = b"<svg xmlns='http://www.w3.org/2000/svg'><text>Logo</text></svg>"
    files = {"logo_file": ("test.svg", svg_content, "image/svg+xml")}
    data = {
        "topic": "SVG Test",
        "image_count": "1",
        "format": "post_4x5",
        "style": "lifestyle",
        "mock": "true",
    }
    res = client.post("/api/generate", data=data, files=files)
    assert res.status_code == 400
    assert "SVG formatı desteklenmemektedir" in res.json()["detail"]


def test_api_config_requires_auth(monkeypatch):
    # Oturumsuz istemci /api/config'e girememeli (bilgi sızıntısı kapatıldı)
    monkeypatch.setenv("APP_PASSWORD", "config-guard-123")
    anon = TestClient(app)
    res = anon.get("/api/config")
    assert res.status_code == 401


def test_legacy_session_token_rejected(monkeypatch):
    # Eski süresiz token formatı (imza=gizli_anahtar(sifre)) artık kabul edilmez
    monkeypatch.setenv("APP_PASSWORD", "legacy-test-123")
    import hashlib
    import hmac as hmac_mod

    from pipeline.config import get_session_secret, verify_session_token

    pwd = "legacy-test-123"
    secret = get_session_secret()
    legacy_token = hmac_mod.new(secret.encode(), pwd.encode(), hashlib.sha256).hexdigest()
    assert verify_session_token(legacy_token) is False


def test_upload_size_limit():
    # Sınırı aşan referans görseli 413 ile reddedilmeli
    from io import BytesIO

    big = BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    files = {"reference_file": ("buyuk.png", big, "image/png")}
    data = {"topic": "Boyut Testi", "image_count": "1", "mock": "true"}
    res = client.post("/api/generate", data=data, files=files)
    assert res.status_code == 413
    assert "çok büyük" in res.json()["detail"]


def test_stateless_overlay_preview_with_data_url():
    # Diske hiç yazmadan sadece in-memory data URL ile overlay yapabilme testi
    from PIL import Image
    from pipeline.canvas import image_to_data_url

    dummy_img = Image.new("RGB", (400, 400), (40, 40, 40))
    bg_data = image_to_data_url(dummy_img, format="JPEG")

    res = client.post(
        "/api/overlay-preview",
        json={
            "background_data_url": bg_data,
            "overlay_text": "Stateless Test Metni",
            "align": "center",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "final_data_url" in data
    assert data["final_data_url"].startswith("data:image/jpeg;base64,")


def test_vercel_entrypoint():
    # api/index.py üzerinden Vercel ASGI uygulamasının sorunsuz yüklendiği ve çalıştığı testi
    from api.index import app as vercel_app
    from starlette.testclient import TestClient

    v_client = TestClient(vercel_app)
    res = v_client.get("/")
    assert res.status_code == 200
    assert "Sosyal Medya Otomasyon" in res.text

    status_res = v_client.get("/api/auth/status")
    assert status_res.status_code == 200
    assert "auth_required" in status_res.json()


def test_vercel_configuration_files():
    # vercel.json ve .vercelignore dosyalarının kurallara uygunluğu
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    vercel_json_path = root / "vercel.json"
    vercel_ignore_path = root / ".vercelignore"

    assert vercel_json_path.is_file(), "vercel.json mevcut olmalı"
    assert vercel_ignore_path.is_file(), ".vercelignore mevcut olmalı"

    config = json.loads(vercel_json_path.read_text(encoding="utf-8"))
    assert "functions" in config
    assert "api/index.py" in config["functions"]
    assert "rewrites" in config
    assert any(r.get("destination") == "/api/index.py" for r in config["rewrites"])

    ignore_content = vercel_ignore_path.read_text(encoding="utf-8")
    assert ".venv" in ignore_content
    assert "outputs" in ignore_content


def test_stateless_pipeline_read_only_filesystem(tmp_path, monkeypatch):
    # Salt-okunur (read-only) dosya sisteminde diske yazma başarısız olsa bile
    # run_pipeline'ın çökmeden in-memory data_url üretip başarıyla döndüğünün testi
    from pipeline.generate import run_pipeline
    from pathlib import Path

    read_only_root = tmp_path / "read_only_outputs"

    orig_mkdir = Path.mkdir
    def mock_mkdir(self, *args, **kwargs):
        if str(read_only_root) in str(self):
            raise OSError("Read-only file system on Vercel")
        return orig_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    payload = {
        "topic": "Stateless Test Post",
        "image_count": 1,
        "format": "post_4x5",
        "style": "lifestyle",
        "overlay_text": "Stateless Başlık",
    }
    result = run_pipeline(payload, mock=True, out_root=read_only_root)
    assert len(result["posts"]) == 1
    post = result["posts"][0]
    assert "background_data_url" in post
    assert "final_data_url" in post
    assert post["final_data_url"].startswith("data:image/jpeg;base64,")



