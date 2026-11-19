import pytest
from fastapi.testclient import TestClient
from main import alokasi_vlsm, app, hitung_subnet

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


# 4. Tes Endpoint API Subnet
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


# 5. Tes fungsi alokasi_vlsm untuk kasus normal (Kasus 10 di SPEC.md)
def test_alokasi_vlsm_normal():
    hasil = alokasi_vlsm("192.168.1.0/24", [100, 50, 20, 2])
    assert len(hasil) == 4
    # Subnet 1: 100 host -> /25 (192.168.1.0)
    assert hasil[0]["network"] == "192.168.1.0"
    assert hasil[0]["prefix"] == 25
    # Subnet 2: 50 host -> /26 (192.168.1.128)
    assert hasil[1]["network"] == "192.168.1.128"
    assert hasil[1]["prefix"] == 26
    # Subnet 3: 20 host -> /27 (192.168.1.192)
    assert hasil[2]["network"] == "192.168.1.192"
    assert hasil[2]["prefix"] == 27
    # Subnet 4: 2 host -> /30 (192.168.1.224)
    assert hasil[3]["network"] == "192.168.1.224"
    assert hasil[3]["prefix"] == 30


# 6. Tes alokasi_vlsm saat urutan input kebutuhan acak (harus diurutkan descending)
def test_alokasi_vlsm_acak():
    hasil = alokasi_vlsm("192.168.1.0/24", [20, 2, 100, 50])
    assert len(hasil) == 4
    assert hasil[0]["prefix"] == 25
    assert hasil[0]["network"] == "192.168.1.0"
    assert hasil[1]["prefix"] == 26
    assert hasil[1]["network"] == "192.168.1.128"
    assert hasil[2]["prefix"] == 27
    assert hasil[2]["network"] == "192.168.1.192"
    assert hasil[3]["prefix"] == 30
    assert hasil[3]["network"] == "192.168.1.224"


# 7. Tes fungsi alokasi_vlsm melebihi kapasitas (Kasus 11 di SPEC.md)
def test_alokasi_vlsm_melebihi_kapasitas():
    with pytest.raises(ValueError):
        alokasi_vlsm("192.168.1.0/24", [200, 100])


# 8. Tes input alokasi_vlsm tidak valid (ValueError)
@pytest.mark.parametrize(
    "network, kebutuhan",
    [
        ("192.168.1.5/24", [50, 20]),  # bukan alamat awal network
        ("256.1.1.0/24", [50]),         # IP invalid
        ("192.168.1.0/33", [10]),      # prefix > 32
        ("192.168.1.0/24", []),        # kebutuhan kosong
        ("192.168.1.0/24", [50, 0]),   # host < 1
        ("192.168.1.0/24", [-5, 10]),  # host negatif
    ],
)
def test_alokasi_vlsm_invalid(network, kebutuhan):
    with pytest.raises(ValueError):
        alokasi_vlsm(network, kebutuhan)


# 9. Tes Endpoint POST /api/vlsm sukses
def test_api_vlsm_success():
    payload = {
        "network": "192.168.1.0/24",
        "kebutuhan_host": [100, 50, 20, 2],
    }
    res = client.post("/api/vlsm", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert data[0]["network"] == "192.168.1.0"
    assert data[0]["prefix"] == 25


# 10. Tes Endpoint POST /api/vlsm saat kebutuhan melebihi kapasitas (HTTP 400)
def test_api_vlsm_melebihi_kapasitas():
    payload = {
        "network": "192.168.1.0/24",
        "kebutuhan_host": [200, 100],
    }
    res = client.post("/api/vlsm", json=payload)
    assert res.status_code == 400
    assert "detail" in res.json()


# 11. Tes Endpoint POST /api/vlsm saat input tidak valid (HTTP 400)
def test_api_vlsm_invalid_input():
    # Input network bukan network awal
    res1 = client.post(
        "/api/vlsm",
        json={"network": "192.168.1.5/24", "kebutuhan_host": [50, 20]},
    )
    assert res1.status_code == 400
    assert "detail" in res1.json()

    # Input kebutuhan host kosong
    res2 = client.post(
        "/api/vlsm",
        json={"network": "192.168.1.0/24", "kebutuhan_host": []},
    )
    assert res2.status_code == 400
    assert "detail" in res2.json()

    # Input payload malformed / tipe data salah
    res3 = client.post(
        "/api/vlsm",
        json={"network": 12345, "kebutuhan_host": "bukan_list"},
    )
    assert res3.status_code == 400
    assert "detail" in res3.json()
