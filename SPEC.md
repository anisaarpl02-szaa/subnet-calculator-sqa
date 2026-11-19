# SPESIFIKASI TEKNIS (SPEC.md)
## Kalkulator Subnet IPv4 & Alokasi VLSM

### 1. Tujuan
Aplikasi web ini bertujuan membantu guru dan siswa SMK jurusan Teknik Komputer dan Jaringan (TKJ) dalam menghitung subnetting IPv4 dan alokasi VLSM (*Variable Length Subnet Masking*) secara presisi dengan verifikasi berbasis unit test.

---

### 2. Aturan Validasi Input

#### A. Alamat IP (IPv4):
* Harus terdiri dari tepat 4 oktet yang dipisahkan titik (`.`).
* Setiap oktet berupa angka bilangan bulat antara `0` sampai `255`.
* **Tanpa angka nol di depan (*no leading zeros*)**: contoh `192.168.01.1` tidak valid dan wajib ditolak.
* Tidak boleh mengandung spasi atau karakter selain angka dan titik.

#### B. Prefix (CIDR):
* Bilangan bulat antara `0` sampai `32`.
* Nilai di luar rentang (seperti `-1` atau `33`) tidak valid dan wajib ditolak.

#### C. Penanganan Kesalahan:
* Jika format IP atau prefix tidak valid, fungsi akan melempar (*raise*) exception `ValueError`.
* Pada level API, respons yang dikembalikan adalah HTTP `400 Bad Request` dengan struktur JSON: `{"detail": "Pesan error"}`.

---

### 3. Kontrak Fungsi Backend

#### A. Fungsi `hitung_subnet(ip: str, prefix: int) -> dict`
Menghitung parameter jaringan berdasarkan IP dan prefix menggunakan operasi bitwise AND.

* **Kunci Kembalian (*Return Dict*):**
  * `mask`: Subnet mask dalam format desimal bertitik (misal `255.255.255.128`).
  * `network`: Alamat network hasil operasi bitwise `IP AND Mask`.
  * `broadcast`: Alamat broadcast jaringan (atau `None` untuk /31 dan /32).
  * `first_host`: Alamat IP host pertama yang dapat digunakan.
  * `last_host`: Alamat IP host terakhir yang dapat digunakan.
  * `usable_hosts`: Jumlah host yang valid digunakan.

* **Aturan Khusus Kasus Tepi (*Edge Cases*):**
  * **Prefix /0 sampai /30**: `usable_hosts = 2^(32 - prefix) - 2`.
  * **Prefix /31 (RFC 3021 Point-to-Point)**: `usable_hosts = 2`, `broadcast = None`, `first_host = network`, `last_host = network + 1`.
  * **Prefix /32 (Single Host)**: `usable_hosts = 1`, `broadcast = None`, `first_host = last_host = IP`.

---

#### B. Fungsi `alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]`
Mengalokasikan subnet bertingkat berdasarkan kebutuhan host.

* **Aturan Alokasi:**
  1. Urutkan daftar kebutuhan host dari yang terbesar ke terkecil (*descending*).
  2. Untuk tiap kebutuhan, hitung ukuran blok terkecil berpangkat 2 yang memenuhi `2^n - 2 >= kebutuhan` (dengan batas minimal subnet /30).
  3. Alokasikan subnet secara berurutan mulai dari alamat network awal.
* **Validasi VLSM:**
  * Melempar `ValueError` bila `network_cidr` tidak valid atau bukan alamat awal network.
  * Melempar `ValueError` bila daftar kebutuhan kosong atau berisi angka `< 1`.
  * Melempar `ValueError` bila total alokasi melebihi kapasitas blok network awal.

---

### 4. Kontrak Antarmuka API (FastAPI)

1. **`GET /api/subnet?ip={ip}&prefix={prefix}`**
   * Status 200: Mengembalikan JSON hasil `hitung_subnet`.
   * Status 400: Mengembalikan `{"detail": "..."}` jika input salah.

2. **`POST /api/vlsm`**
   * Request Body: `{"network": "192.168.1.0/24", "kebutuhan_host": [100, 50, 20, 2]}`
   * Status 200: Mengembalikan daftar alokasi subnet.
   * Status 400: Mengembalikan `{"detail": "..."}` jika tidak muat atau input salah.

3. **`GET /`**
   * Status 200: Menampilkan halaman antarmuka web `index.html`.

---

### 5. Tabel Kasus Uji (Test Cases)

| No | Uraian Kasus | Input | Hasil yang Diharapkan | Status |
|:---|:---|:---|:---|:---|
| 1 | Subnet standar kelas C | `172.16.5.130`, Prefix `25` | Network: `172.16.5.128`, Broadcast: `172.16.5.255`, Usable: `126` | Pasti |
| 2 | Subnet point-to-point /30 | `10.0.0.0`, Prefix `30` | First: `10.0.0.1`, Last: `10.0.0.2`, Broadcast: `10.0.0.3`, Usable: `2` | Pasti |
| 3 | RFC 3021 Point-to-Point /31 | `192.168.1.0`, Prefix `31` | First: `192.168.1.0`, Last: `192.168.1.1`, Broadcast: `None`, Usable: `2` | Pasti |
| 4 | Host tunggal /32 | `192.168.1.5`, Prefix `32` | First: `192.168.1.5`, Last: `192.168.1.5`, Broadcast: `None`, Usable: `1` | Pasti |
| 5 | IP oktet > 255 | `256.1.1.1`, Prefix `24` | ValueError / HTTP 400 (Ditolak) | Pasti |
| 6 | IP leading zero | `192.168.01.1`, Prefix `24` | ValueError / HTTP 400 (Ditolak) | Pasti |
| 7 | IP tidak lengkap | `192.168.1`, Prefix `24` | ValueError / HTTP 400 (Ditolak) | Pasti |
| 8 | Prefix > 32 | `192.168.1.1`, Prefix `33` | ValueError / HTTP 400 (Ditolak) | Pasti |
| 9 | Prefix negatif | `192.168.1.1`, Prefix `-1` | ValueError / HTTP 400 (Ditolak) | Pasti |
| 10 | VLSM normal cukup | `192.168.1.0/24`, [100, 50, 20, 2] | /25 (.0), /26 (.128), /27 (.192), /30 (.224) | Pasti |
| 11 | VLSM melebihi kapasitas | `192.168.1.0/24`, [200, 100] | ValueError / HTTP 400 (Tidak Muat) | Pasti |
