# [Feature] Alokasi VLSM

## Deskripsi Fitur
Fitur perhitungan dan alokasi subnet menggunakan metode VLSM (*Variable Length Subnet Masking*) untuk membantu guru dan siswa SMK jurusan Teknik Komputer dan Jaringan (TKJ) dalam mengalokasikan subnet bertingkat secara efisien dan presisi berdasarkan kebutuhan host.

## Aturan Alokasi VLSM (Berdasarkan SPEC.md)
1. **Pengurutan Kebutuhan**: Daftar kebutuhan host wajib diurutkan dari yang terbesar ke terkecil (*descending*).
2. **Ukuran Blok Subnet**: Untuk tiap kebutuhan, hitung ukuran blok terkecil berpangkat 2 yang memenuhi rumus `2^n - 2 >= kebutuhan` (dengan batas minimal subnet `/30`).
3. **Alokasi Berurutan**: Alokasikan subnet secara berurutan mulai dari alamat network awal.

## Validasi & Error Handling
* Melempar `ValueError` bila `network_cidr` tidak valid atau bukan alamat awal network.
* Melempar `ValueError` bila daftar kebutuhan host kosong atau berisi nilai `< 1`.
* Melempar `ValueError` bila total alokasi melebihi kapasitas blok network awal.
* Pada antarmuka API, melempar exception `ValueError` akan menghasilkan HTTP `400 Bad Request` dengan format respons JSON `{"detail": "Pesan error"}`.

## Kontrak Backend & API

### Fungsi Backend
`alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]`
* Mengembalikan daftar subnet yang dialokasikan (`list[dict]`).

### Endpoint API (FastAPI)
`POST /api/vlsm`
* **Request Body**:
  ```json
  {
    "network": "192.168.1.0/24",
    "kebutuhan_host": [100, 50, 20, 2]
  }
  ```
* **Response 200 OK**: Daftar alokasi subnet hasil VLSM.
* **Response 400 Bad Request**: `{"detail": "..."}` jika input tidak valid atau kebutuhan melebihi kapasitas (tidak muat).

## Kasus Uji (Test Cases) Sesuai SPEC.md
* **Kasus Normal Cukup**:
  * Input: `network = "192.168.1.0/24"`, `kebutuhan_host = [100, 50, 20, 2]`
  * Hasil:
    * 100 host: `/25` (`192.168.1.0`)
    * 50 host: `/26` (`192.168.1.128`)
    * 20 host: `/27` (`192.168.1.192`)
    * 2 host: `/30` (`192.168.1.224`)
* **Kasus Melebihi Kapasitas (Tidak Muat)**:
  * Input: `network = "192.168.1.0/24"`, `kebutuhan_host = [200, 100]`
  * Hasil: `ValueError` / HTTP `400 Bad Request` (Tidak Muat).
