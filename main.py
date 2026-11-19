import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def ip_ke_int(ip_str: str) -> int:
    if not isinstance(ip_str, str):
        raise ValueError("IP address harus berupa string")
    if " " in ip_str:
        raise ValueError("IP address tidak boleh mengandung spasi")

    oktet = ip_str.split(".")
    if len(oktet) != 4:
        raise ValueError("IP address harus terdiri dari 4 oktet")

    hasil = 0
    for o in oktet:
        if not o.isdigit():
            raise ValueError(f"Oktet '{o}' bukan angka yang valid")
        if len(o) > 1 and o.startswith("0"):
            raise ValueError(f"Leading zero tidak diperbolehkan pada oktet '{o}'")

        angka = int(o)
        if not (0 <= angka <= 255):
            raise ValueError(f"Nilai oktet {angka} harus antara 0 sampai 255")

        hasil = (hasil << 8) | angka
    return hasil


def int_ke_ip(nilai: int) -> str:
    return f"{(nilai >> 24) & 255}.{(nilai >> 16) & 255}.{(nilai >> 8) & 255}.{nilai & 255}"


def hitung_subnet(ip: str, prefix: int) -> dict:
    if isinstance(prefix, bool) or not isinstance(prefix, int) or not (0 <= prefix <= 32):
        raise ValueError("Prefix harus berupa bilangan bulat antara 0 sampai 32")

    ip_int = ip_ke_int(ip)

    if prefix == 0:
        mask_int = 0
    else:
        mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF

    network_int = ip_int & mask_int
    wildcard_int = (~mask_int) & 0xFFFFFFFF
    broadcast_int = network_int | wildcard_int

    if prefix == 32:
        return {
            "mask": int_ke_ip(mask_int),
            "network": int_ke_ip(network_int),
            "broadcast": None,
            "first_host": int_ke_ip(network_int),
            "last_host": int_ke_ip(network_int),
            "usable_hosts": 1,
        }

    if prefix == 31:
        return {
            "mask": int_ke_ip(mask_int),
            "network": int_ke_ip(network_int),
            "broadcast": None,
            "first_host": int_ke_ip(network_int),
            "last_host": int_ke_ip(network_int + 1),
            "usable_hosts": 2,
        }

    usable_hosts = (2 ** (32 - prefix)) - 2
    return {
        "mask": int_ke_ip(mask_int),
        "network": int_ke_ip(network_int),
        "broadcast": int_ke_ip(broadcast_int),
        "first_host": int_ke_ip(network_int + 1),
        "last_host": int_ke_ip(broadcast_int - 1),
        "usable_hosts": max(0, usable_hosts),
    }


def alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]:
    """Mengalokasikan subnet bertingkat berdasarkan kebutuhan host (VLSM)."""
    if not isinstance(network_cidr, str):
        raise ValueError("Network CIDR harus berupa string")
    if " " in network_cidr:
        raise ValueError("Network CIDR tidak boleh mengandung spasi")
    if "/" not in network_cidr:
        raise ValueError("Format network CIDR harus IP/prefix, contoh: 192.168.1.0/24")

    parts = network_cidr.split("/")
    if len(parts) != 2:
        raise ValueError("Format network CIDR harus IP/prefix, contoh: 192.168.1.0/24")

    ip_str, prefix_str = parts[0], parts[1]
    if not prefix_str.isdigit():
        raise ValueError("Prefix harus berupa bilangan bulat antara 0 sampai 32")

    prefix = int(prefix_str)
    if not (0 <= prefix <= 32):
        raise ValueError("Prefix harus bernilai antara 0 sampai 32")

    ip_int = ip_ke_int(ip_str)

    if prefix == 0:
        mask_int = 0
    else:
        mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF

    network_int = ip_int & mask_int
    if ip_int != network_int:
        raise ValueError(f"Alamat IP '{ip_str}' bukan alamat awal network untuk prefix /{prefix}")

    if not isinstance(kebutuhan_host, list) or len(kebutuhan_host) == 0:
        raise ValueError("Daftar kebutuhan host tidak boleh kosong")

    for req in kebutuhan_host:
        if isinstance(req, bool) or not isinstance(req, int) or req < 1:
            raise ValueError("Kebutuhan host harus berupa bilangan bulat positif (>= 1)")

    # 1. Urutkan daftar kebutuhan host dari yang terbesar ke terkecil (descending)
    sorted_kebutuhan = sorted(kebutuhan_host, reverse=True)

    total_capacity = 2 ** (32 - prefix)
    network_end_int = network_int + total_capacity
    current_ip_int = network_int

    hasil = []
    for req in sorted_kebutuhan:
        # 2. Hitung ukuran blok terkecil berpangkat 2 yang memenuhi 2^n - 2 >= kebutuhan (minimal /30)
        n = 2
        while (2 ** n) - 2 < req:
            n += 1
            if n > 32:
                raise ValueError("Kebutuhan host melebihi kapasitas maksimum IPv4")

        sub_prefix = 32 - n
        block_size = 2 ** n

        # 3. Alokasikan subnet secara berurutan mulai dari alamat network awal
        if current_ip_int + block_size > network_end_int:
            raise ValueError("Total alokasi subnet melebihi kapasitas blok network awal")

        sub_info = hitung_subnet(int_ke_ip(current_ip_int), sub_prefix)
        sub_info["kebutuhan"] = req
        sub_info["prefix"] = sub_prefix

        hasil.append(sub_info)
        current_ip_int += block_size

    return hasil


class VLSMRequest(BaseModel):
    network: str
    kebutuhan_host: list[int]


@app.get("/")
def home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Kalkulator Subnet API siap"}


@app.get("/api/subnet")
def api_subnet(ip: str = Query(...), prefix: int = Query(...)):
    try:
        return hitung_subnet(ip, prefix)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/vlsm")
def api_vlsm(payload: VLSMRequest):
    try:
        return alokasi_vlsm(payload.network, payload.kebutuhan_host)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
