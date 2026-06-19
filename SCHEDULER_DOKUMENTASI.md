# Dokumentasi Scheduler - Sistem Generate Jadwal Kerja

## 📋 Ringkasan Umum

Scheduler adalah sistem otomatis yang membuat jadwal kerja karyawan untuk satu bulan penuh. Sistemnya bekerja seperti **distributor yang adil** - memastikan setiap karyawan mendapat shift secara merata berdasarkan "beban kerja" mereka.

---

## 🎯 Tujuan Sistem

**Masalah yang dipecahkan:**
- Membuat jadwal untuk puluhan karyawan di puluhan hari kerja 📅
- Membagi shift secara **ADIL** - tidak ada yang terlalu banyak atau terlalu sedikit
- Mengikuti **pola kerja** yang telah ditentukan 🔄
- Menghindari penugasan ganda pada hari yang sama ❌

---

## 🔧 Cara Kerja (Penjelasan Sederhana)

### Konsep Utama: **Score System** (Sistem Poin)

Setiap karyawan punya **score (poin beban kerja)**:
- **Score rendah** = karyawan kurang ditugaskan → prioritas tinggi
- **Score tinggi** = karyawan sudah banyak ditugaskan → prioritas rendah

**Contoh:**
```
Jovi (score: 5)   ← Pilih ini dulu (kurang kerjaan)
Budi (score: 12)  ← Pilih yang ini kedua
Doni (score: 15)  ← Pilih yang ini terakhir (sudah banyak kerjaan)
```

---

## 📊 Alur Proses Generate Jadwal

```
START (Generate jadwal Mei 2026)
  │
  ├─ 1. SIAPKAN DATA
  │   ├─ Ambil semua PATTERN (pola kerja yang sudah dibuat)
  │   ├─ Ambil semua USER (daftar karyawan)
  │   └─ Ambil DAYS_OFF (hari libur: hari Minggu, libur nasional, dll)
  │
  ├─ 2. LOOP SETIAP TANGGAL dalam bulan (1-31 Mei)
  │   │
  │   ├─ Cek apakah HARI LIBUR?
  │   │   ├─ Ya? → SKIP tanggal ini, lanjut hari berikutnya
  │   │   └─ Tidak? → Lanjut step berikutnya
  │   │
  │   ├─ 3. AMBIL PATTERN untuk hari ini
  │   │   (Pattern apa yang berlaku di hari ke-X?)
  │   │   │
  │   │   └─ Pattern berisi:
  │   │       ├─ Pagi: 5 orang
  │   │       ├─ Siang: 5 orang
  │   │       └─ Malam: 3 orang
  │   │
  │   ├─ 4. UNTUK SETIAP SHIFT dalam pattern hari ini
  │   │   │
  │   │   └─ Contoh: SHIFT PAGI (perlu 5 orang)
  │   │       │
  │   │       └─ 5 KALI: PILIH KARYAWAN TERBAIK
  │   │           │
  │   │           ├─ Filter: Siapa yang BELUM ditugaskan hari ini?
  │   │           │           Jika 5 orang diganti, 2 orang (dari 7 total)
  │   │           │           sudah ditugaskan, tersisa 5 kandidat
  │   │           │
  │   │           ├─ Cari: Siapa yang punya score TERENDAH?
  │   │           │         Dari 5 kandidat, misal:
  │   │           │         - Jovi: 5 poin ← TERPILIH!
  │   │           │         - Budi: 10 poin
  │   │           │
  │   │           ├─ Tugaskan: Jovi → SHIFT PAGI → 1 Mei
  │   │           │
  │   │           └─ Update score: Jovi 5 + 3(shift pagi) = 8 poin
  │   │
  │   └─ Ulangi untuk Siang (5 org) dan Malam (3 org)
  │
  ├─ 5. LANJUT KE TANGGAL BERIKUTNYA
  │   └─ 2 Mei, 3 Mei, 4 Mei, ... (ulangi step 2-4)
  │
  └─ END: Semua jadwal untuk bulan selesai, simpan ke database ✅
```

---

## 🔍 Detail Setiap Function

### 1️⃣ `generate_dates(year, month)`

**Tujuan:** Membuat daftar semua tanggal dalam sebulan

**Input:**
```python
year = 2026
month = 5  # Mei
```

**Output:**
```
1 Mei 2026
2 Mei 2026
3 Mei 2026
...
31 Mei 2026
```

**Kode:**
```python
total_days = calendar.monthrange(year, month)[1]  # Dapat jumlah hari (31)
for day_num in range(1, total_days + 1):         # Loop 1-31
    yield datetime.date(year, month, day_num)    # Return setiap tanggal
```

---

### 2️⃣ `get_pattern_for_day(work_day_index, patterns)`

**Tujuan:** Menentukan pola shift mana yang berlaku di hari ke-X

**Contoh Skenario:**
```
Pattern yang ada:
  - Pattern A: Pagi 5 orang, Siang 5 orang, Malam 3 orang
  - Pattern B: Pagi 4 orang, Siang 6 orang, Malam 4 orang
  - Pattern C: Pagi 3 orang, Siang 3 orang, Malam 3 orang

Rotasi: A → B → C → A → B → C → ...

Hari ke-0 (1 Mei):   Pattern A
Hari ke-1 (2 Mei):   Pattern B
Hari ke-2 (3 Mei):   Pattern C
Hari ke-3 (4 Mei):   Pattern A (balik ke awal)
```

**Kode:**
```python
return patterns[work_day_index % len(patterns)]
# Contoh: patterns[2 % 3] = patterns[2] = Pattern C
```

**Operator `%` (modulo):**
- `0 % 3 = 0` → Pattern[0] = A
- `1 % 3 = 1` → Pattern[1] = B
- `2 % 3 = 2` → Pattern[2] = C
- `3 % 3 = 0` → Pattern[0] = A ← Balik ke awal (rotasi)

---

### 3️⃣ `select_user(users, assigned_today)`

**Tujuan:** Pilih 1 karyawan terbaik untuk shift ini

**Input:**
```
users = [Jovi(score:5), Budi(score:10), Doni(score:15)]
assigned_today = {1, 3}  # User ID 1 dan 3 sudah ditugaskan
```

**Proses:**
```
STEP 1: Filter - Siapa yang BELUM ditugaskan hari ini?
  ├─ Jovi? ID=1, ada di assigned_today? YA → Hapus
  ├─ Budi? ID=2, ada di assigned_today? TIDAK → Simpan
  └─ Doni? ID=3, ada di assigned_today? YA → Hapus
  
  Hasil: available_users = [Budi]

STEP 2: Cari score terendah
  └─ min_score = 10 (Budi)

STEP 3: Siapa yang punya score = 10?
  └─ candidates = [Budi]

STEP 4: Pilih random dari candidates (jika ada beberapa)
  └─ Terpilih: Budi ✅
```

**Output:** `Budi`

---

### 4️⃣ `generate_schedule()` - FUNGSI UTAMA

**Input Parameters:**
```python
year = 2026
month = 5
days_off = [6]  # 6 = Minggu (libur)
patterns_to_use = [1, 2, 3]  # Gunakan pattern ini (urutan penting!)
```

**Alur Lengkap:**

```
TAHAP 1: PERSIAPAN
  ├─ Ambil semua shift pattern dari database
  ├─ Ambil semua user (karyawan) dari database
  ├─ Filter pattern berdasarkan patterns_to_use (jika ada)
  └─ Validasi: Ada user? Ada pattern?

TAHAP 2: GENERATE JADWAL
  └─ Untuk setiap tanggal 1-31 Mei 2026:
     │
     ├─ Jika MINGGU (hari libur) → SKIP
     │
     └─ Jika WEEKDAY (Senin-Sabtu):
        │
        ├─ Ambil pattern untuk hari ini (berdasarkan urutan)
        ├─ Untuk setiap shift dalam pattern:
        │  ├─ Contoh: PAGI shift perlu 5 orang
        │  ├─ Loop 5 kali:
        │  │  ├─ Pilih user dengan score terendah (yang belum ditugaskan hari ini)
        │  │  ├─ Tambah penugasan: User X → Pagi, 1 Mei
        │  │  ├─ Update score: score += shift.score
        │  │  └─ Tandai user ini sebagai "assigned_today"
        │  │
        │  └─ Lanjut ke shift berikutnya (Siang, Malam)
        │
        └─ Lanjut ke tanggal berikutnya

TAHAP 3: RETURN HASIL
  └─ Array berisi semua penugasan:
     [
       {user: "Jovi", shift: "Pagi", date: "1 Mei", score: 3},
       {user: "Budi", shift: "Pagi", date: "1 Mei", score: 4},
       ...
     ]
```

---

## 📈 Contoh Nyata: Generate Jadwal 3 Hari

### Setup:
```
Users:
  - Jovi (score: 0)
  - Budi (score: 0)
  - Doni (score: 0)

Pattern:
  - Pagi: 2 orang (score: 3 per orang)
  - Siang: 1 orang (score: 2 per orang)

Periode: 1-3 Mei (3 hari)
Days off: Minggu saja
```

### Eksekusi:

**HARI 1 (1 Mei - Senin):**
```
Pattern: Pagi 2 orang, Siang 1 orang

Shift PAGI (perlu 2):
  Orang ke-1:
    Kandidat: [Jovi(0), Budi(0), Doni(0)]
    Pilih: Jovi (random, semua sama)
    Score: Jovi 0 + 3 = 3
    assigned_today = {Jovi}
  
  Orang ke-2:
    Kandidat: [Budi(0), Doni(0)] (Jovi sudah ditugaskan)
    Pilih: Budi (random, semua sama)
    Score: Budi 0 + 3 = 3
    assigned_today = {Jovi, Budi}

Shift SIANG (perlu 1):
  Orang ke-1:
    Kandidat: [Doni(0)] (Jovi dan Budi sudah ditugaskan)
    Pilih: Doni
    Score: Doni 0 + 2 = 2
    assigned_today = {Jovi, Budi, Doni}

Hasil Hari 1:
  Jovi  → Pagi  (score: 3)
  Budi  → Pagi  (score: 3)
  Doni  → Siang (score: 2)
```

**HARI 2 (2 Mei - Selasa):**
```
Pattern: Pagi 2 orang, Siang 1 orang
assigned_today di-reset = {} (hari baru)

Status score saat ini:
  Jovi (3), Budi (3), Doni (2)

Shift PAGI (perlu 2):
  Orang ke-1:
    Kandidat: [Jovi(3), Budi(3), Doni(2)]
    Min score: 2 (Doni)
    Pilih: Doni
    Score: Doni 2 + 3 = 5

  Orang ke-2:
    Kandidat: [Jovi(3), Budi(3)] (Doni sudah ditugaskan)
    Pilih: Jovi (random, keduanya score 3)
    Score: Jovi 3 + 3 = 6

Shift SIANG (perlu 1):
  Orang ke-1:
    Kandidat: [Budi(3)]
    Pilih: Budi
    Score: Budi 3 + 2 = 5

Hasil Hari 2:
  Doni  → Pagi  (score: 5)
  Jovi  → Pagi  (score: 6)
  Budi  → Siang (score: 5)
```

**HARI 3 (3 Mei - Rabu):**
```
Status score saat ini:
  Jovi (6), Budi (5), Doni (5)

Shift PAGI (perlu 2):
  Orang ke-1:
    Kandidat: [Jovi(6), Budi(5), Doni(5)]
    Min score: 5 (Budi dan Doni)
    Pilih: Budi (random)
    Score: Budi 5 + 3 = 8

  Orang ke-2:
    Kandidat: [Jovi(6), Doni(5)]
    Min score: 5 (Doni)
    Pilih: Doni
    Score: Doni 5 + 3 = 8

Shift SIANG (perlu 1):
  Orang ke-1:
    Kandidat: [Jovi(6)]
    Pilih: Jovi
    Score: Jovi 6 + 2 = 8

Hasil Hari 3:
  Budi  → Pagi  (score: 8)
  Doni  → Pagi  (score: 8)
  Jovi  → Siang (score: 8)
```

### Hasil Akhir (Ringkasan):
```
JADWAL 3 HARI:

1 Mei:  Jovi(Pagi), Budi(Pagi), Doni(Siang)
2 Mei:  Doni(Pagi), Jovi(Pagi), Budi(Siang)
3 Mei:  Budi(Pagi), Doni(Pagi), Jovi(Siang)

Total Score Akhir:
  Jovi: 8 (Pagi 2x + Siang 1x)
  Budi: 8 (Pagi 2x + Siang 1x)
  Doni: 8 (Pagi 2x + Siang 1x)

KESIMPULAN: Jadwal ADIL! Semua dapat beban kerja sama. ✅
```

---

## 🎓 Konsep Penting

### 1. **Modulo Operator (`%`) untuk Rotasi**
```
Jika ada 3 pattern dan 10 hari kerja:
  Hari 0: patterns[0 % 3] = A
  Hari 1: patterns[1 % 3] = B
  Hari 2: patterns[2 % 3] = C
  Hari 3: patterns[3 % 3] = A ← Otomatis balik ke awal
  ...
  Hari 9: patterns[9 % 3] = C

Hasil: Pattern berulang A-B-C-A-B-C-A-B-C-A
```

### 2. **Score System untuk Keadilan**
```
Ide: "Siapa yang paling belum bekerja, dia yang prioritas"

Mengapa penting?
  ├─ Tanpa score: Karyawan pertama bisa dapat 20 shift, 
  │               karyawan terakhir dapat 5 shift
  │
  └─ Dengan score: Semua mendapat ~15 shift, beban kerja merata
```

### 3. **assigned_today untuk Menghindari Ganda**
```
Tanpa assigned_today:
  Bisa terjadi Jovi ditugaskan 2 kali di hari yang sama:
    - Pagi 08:00
    - Siang 14:00  ← Conflict! (tidak bisa dua shift sekaligus)

Dengan assigned_today:
  Saat dipilih untuk shift 2, sistem cek:
    "Jovi sudah ditugaskan di hari ini? YA → SKIP"
    Pilih orang lain saja.
```

---

## 🚀 Alur Data dari Database ke Output

```
DATABASE:
  ├─ shift_patterns (Pola shift)
  │  ├─ Pattern A (Pagi 5, Siang 5, Malam 3)
  │  └─ Pattern B (Pagi 4, Siang 6, Malam 4)
  │
  ├─ users (Karyawan)
  │  ├─ Jovi (score: 0)
  │  ├─ Budi (score: 0)
  │  └─ Doni (score: 0)
  │
  └─ shifts (Jenis shift)
     ├─ Pagi (08:00-14:00, score: 3)
     ├─ Siang (14:00-20:00, score: 4)
     └─ Malam (20:00-02:00, score: 5)

        ↓ [generate_schedule() dijalankan]

MEMORY (Program berjalan):
  ├─ Buat daftar tanggal: 1-31 Mei
  ├─ Loop setiap tanggal:
  │  ├─ Ambil pattern untuk hari ini
  │  ├─ Untuk setiap shift dalam pattern:
  │  │  └─ Pilih user (update score di memory)
  │  └─ Lanjut tanggal berikutnya
  │
  └─ Array hasil: [50+ penugasan untuk sebulan]

        ↓ [Simpan ke database]

DATABASE (Akhir):
  schedules table:
    ├─ ID 1: Jovi, Pagi, 1 Mei, Pattern A
    ├─ ID 2: Budi, Pagi, 1 Mei, Pattern A
    ├─ ID 3: Doni, Siang, 1 Mei, Pattern A
    └─ ... (50+ baris untuk sebulan penuh)
```

---

## ⚡ Keunggulan & Batasan

### ✅ Keunggulan:
1. **Otomatis** - Tidak perlu buat jadwal manual
2. **Adil** - Beban kerja merata berdasarkan score
3. **Fleksibel** - Bisa pakai pattern berbeda, hari libur berbeda
4. **Cepat** - Proses dalam hitungan detik (walau 1000+ jadwal)

### ⚠️ Batasan:
1. **Random selection** - Jika 2 orang score sama, pilih acak
2. **Tidak ada preferensi** - Tidak bisa "Jovi tidak ingin shift malam"
3. **Tidak ada kontrol dinamis** - Jika ada karyawan sakit, harus generate ulang
4. **Score global** - Tidak bisa buat score per tipe shift (semua shift sama bobot)

---

## 📌 Kesimpulan

**Scheduler bekerja seperti:**
- 🎯 **Distributore yang adil** - Membagi pekerjaan merata
- 🔄 **Mesin rotasi** - Pattern berganti setiap hari
- ⚖️ **Sistem skor** - Orang dengan beban kurang dapat prioritas
- ✅ **Validator** - Mencegah orang ditugaskan 2x sehari

Hasilnya: **Jadwal kerja 1 bulan yang adil dan otomatis!**

---

Dibuat: 2026-05-19
