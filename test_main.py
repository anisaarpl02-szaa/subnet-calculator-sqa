import pytest
from fastapi.testclient import TestClient
from main import app, hitung_subnet

client = TestClient(app)

# 1. Tes fungsi hitung_subnet untuk kasus normal
@pytest.mark.parametrize(
    "ip, prefix, expected_network, expected_broadcast, expected_usable",
    [
        ("172.16.5.130", 25, "172.16.5.128", "172.16.5.255", 126),
        ("10.0.0.0", 30, "10.0.0.0", "10.0.0.3", 2),
    ],
)
def test_hitung_subnet_normal(ip, prefix, expected_network, expected_broadcast, expected_usable):
    hasil = hitung_subnet(ip, prefix)
    assert hasil["network"] == expected_network
    assert hasil["broadcast"] == expected_broadcast
    assert hasil["usable_hosts"] == expected_usable

# 2. Tes kasus khusus /31 (Point-to-Point) dan /32 (Single Host)
def test_hitung_subnet_point_to_point_31():
    hasil = hitung_subnet("192.168.1.0", 31)
    assert hasil["usable_hosts"] == 2
    assert hasil["broadcast"] is None

def test_hitung_subnet_single_host_32():
    hasil = hitung_subnet("192.168.1.5", 32)
    assert hasil["usable_hosts"] == 1
    assert hasil["first_host"] == "192.168.1.5"
    assert hasil["last_host"] == "192.168.1.5"
    assert hasil["broadcast"] is None

# 3. Tes input tidak valid harus menghasilkan ValueError
@pytest.mark.parametrize(
    "ip, prefix",
    [
        ("256.1.1.1", 24),
        ("192.168.01.1", 24),
        ("192.168.1", 24),
        ("abc", 24),
        ("", 24),
        ("192.168.1.1", 33),
        ("192.168.1.1", -1),
    ],
)
def test_hitung_subnet_invalid(ip, prefix):
    with pytest.raises(ValueError):
        hitung_subnet(ip, prefix)

# 4. Tes Endpoint API
def test_api_subnet_success():
    res = client.get("/api/subnet?ip=172.16.5.130&prefix=25")
    assert res.status_code == 200
    assert res.json()["network"] == "172.16.5.128"

def test_api_subnet_invalid():
    res = client.get("/api/subnet?ip=256.1.1.1&prefix=24")
    assert res.status_code == 400
    assert "detail" in res.json()

def test_api_home():
    res = client.get("/")
    assert res.status_code == 200