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
    raise NotImplementedError


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
    raise NotImplementedError
