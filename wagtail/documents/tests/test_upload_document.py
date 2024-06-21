import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from wagtail.documents.models import Document

UPLOAD_URL = reverse("wagtaildocs:add")

@pytest.fixture
def superuser_client(db, client):
    User = get_user_model()
    username = "test_admin"
    password = "password123"
    user = User.objects.create_superuser(username=username, email="admin@example.com", password=password)
    client.login(username=username, password=password)
    return client

@pytest.fixture
def normal_user_client(db, client):
    User = get_user_model()
    username = "user_normal"
    password = "password123"
    user = User.objects.create_user(username=username, email="user@example.com", password=password)
    client.login(username=username, password=password)
    return client

def make_file(name="file.txt", content=b"data", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)

@pytest.mark.django_db
def test_CT1_upload_sucesso(superuser_client, settings, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024, raising=False)
    monkeypatch.setattr(settings, "ALLOWED_DOCUMENT_MIME_TYPES", ["text/plain", "application/pdf"], raising=False)

    client = superuser_client
    small = b"a" * 1024
    uploaded_file = make_file("ok.txt", small, content_type="text/plain")
    data = {"title": "Doc Sucesso", "file": uploaded_file}

    response = client.post(UPLOAD_URL, data, follow=True)
    assert response.status_code in (200, 302)
    assert Document.objects.filter(title="Doc Sucesso").exists()

@pytest.mark.django_db
def test_CT2_nao_autenticado(client):
    uploaded_file = make_file("doc2.txt", b"a" * 10, content_type="text/plain")
    data = {"title": "Doc Sem Login", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data, follow=False)
    assert response.status_code in (302, 401, 403)

@pytest.mark.django_db
def test_CT3_sem_permissao(normal_user_client):
    client = normal_user_client
    uploaded_file = make_file("doc3.txt", b"a" * 10, content_type="text/plain")
    data = {"title": "Doc Sem Permissão", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data, follow=False)
    assert response.status_code == 403

@pytest.mark.django_db
def test_CT4_sem_arquivo(superuser_client):
    client = superuser_client
    data = {"title": "Doc Sem Arquivo"}
    response = client.post(UPLOAD_URL, data)
    assert response.status_code == 200
    assert not Document.objects.filter(title="Doc Sem Arquivo").exists()
    content = response.content.decode(errors="ignore")
    # Ajuste a string de erro conforme seu template
    assert "Este campo é obrigatório" in content or "file" in content.lower()

@pytest.mark.django_db
def test_CT5_arquivo_muito_grande(superuser_client, settings, monkeypatch):
    client = superuser_client
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 5, raising=False)  # 5 bytes
    large = b"a" * 100
    uploaded_file = make_file("large.txt", large, content_type="text/plain")
    data = {"title": "Doc Grande", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data)
    assert response.status_code == 200
    assert not Document.objects.filter(title="Doc Grande").exists()
    content = response.content.decode(errors="ignore")
    assert "tamanho" in content.lower() or "exced" in content.lower()

@pytest.mark.django_db
def test_CT6_tipo_invalido(superuser_client, settings, monkeypatch):
    client = superuser_client
    monkeypatch.setattr(settings, "ALLOWED_DOCUMENT_MIME_TYPES", ["application/pdf"], raising=False)
    uploaded_file = make_file("doc.txt", b"a" * 10, content_type="text/plain")
    data = {"title": "Doc Tipo Inválido", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data)
    assert response.status_code == 200
    assert not Document.objects.filter(title="Doc Tipo Inválido").exists()
    content = response.content.decode(errors="ignore")
    assert "tipo" in content.lower() or "permitido" in content.lower()

@pytest.mark.django_db
def test_CT7_precedencia_permissao(normal_user_client, settings, monkeypatch):
    client = normal_user_client
    monkeypatch.setattr(settings, "ALLOWED_DOCUMENT_MIME_TYPES", ["application/pdf"], raising=False)
    uploaded_file = make_file("doc.bin", b"a" * 10, content_type="application/octet-stream")
    data = {"title": "Doc Perm+Tipo Inválido", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data, follow=False)
    assert response.status_code == 403

@pytest.mark.django_db
def test_CT8_precedencia_autenticacao(client):
    uploaded_file = make_file("doc.bin", b"a" * 10, content_type="application/octet-stream")
    data = {"title": "Doc Sem Login+Inválido", "file": uploaded_file}
    response = client.post(UPLOAD_URL, data, follow=False)
    assert response.status_code in (302, 401, 403)
