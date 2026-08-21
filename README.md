# SKP Online Jasindo

Aplikasi Streamlit mandiri untuk **Surat Konfirmasi Premi Property/FLEXAS** dan **Endorsement**. Repository ini berdiri sendiri dan tidak bergantung pada platform atau aplikasi lain.

## Akses pelanggan
Aplikasi dapat dibuat **public di Streamlit Community Cloud**, tetapi seluruh fitur SKP berada di balik login aplikasi.

Setiap pelanggan memiliki akun sendiri yang disimpan di **Streamlit Secrets**, bukan di GitHub. Akun mendukung:
- username dan password ter-hash PBKDF2-SHA256 + salt;
- status `active = true/false`;
- tanggal kedaluwarsa `expires_at`;
- sesi login maksimal 12 jam;
- lock sementara setelah beberapa percobaan login gagal.

Template secrets tersedia di `.streamlit/secrets.toml.example`. File `.streamlit/secrets.toml` asli sudah di-ignore dan **tidak boleh di-commit**.

Untuk membuat hash password baru:
```bash
python generate_password_hash.py
```
Lalu salin `password_salt` dan `password_hash` yang dihasilkan ke Streamlit Secrets bersama data pelanggan.

## Alur pengguna
1. Login dengan akun pelanggan aktif.
2. Pilih **SKP Baru** atau **Endorsement**.
3. Isi data tertanggung dan periode.
4. Cari okupasi dengan nama sederhana atau kode OJK.
5. Pilih kelas konstruksi jika diperlukan; okupasi dengan tarif khusus ditangani otomatis.
6. Isi Nilai Pertanggungan (SI).
7. Tarif default menggunakan batas bawah master OJK; range dan validasi tersedia pada bagian detail.
8. Klik **Hitung Premi**, lalu unduh Word/PDF.

## Master okupasi
Master okupasi disimpan dalam `ojk_occupations_01.csv` sampai `ojk_occupations_04.csv` dan dibaca aplikasi sebagai satu master berisi **373 okupasi dengan rate numerik yang dapat dipilih**, berdasarkan SEOJK 6/SEOJK.05/2017 Lampiran I Tabel I.A. Baris judul tanpa tarif atau referensi tanpa rate mandiri tidak dijadikan pilihan.

Master mendukung:
- Tarif berdasarkan **Kelas Konstruksi 1, 2, dan 3**.
- **Tarif khusus tanpa kelas konstruksi** untuk okupasi yang memang memakai satu range.

## Prinsip perhitungan
- Premi dasar: `SI × rate (‰) / 1000 × faktor prorata`.
- Prorata memakai Actual/Actual berdasarkan anniversary polis; 12 bulan penuh = faktor 1,00 termasuk periode lintas 29 Februari.
- Endorsement: `premi sisa kondisi baru − premi sisa kondisi lama`, efektif sejak tanggal endorsement.
- Tarif polis lama menggunakan rate aktual yang tercantum pada polis lama.
- Tarif kondisi baru divalidasi terhadap range master OJK.
- Banjir, gempa bumi, dan perluasan lain dipisahkan dari rate okupasi FLEXAS.
- Biaya administrasi, meterai, fee bank, dan PPN adalah parameter SOP/PKS internal.

## Menjalankan lokal
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Community Cloud
- Repository: `jasindo-skp-online`
- Branch: `main`
- Entry point: `streamlit_app.py`
- App visibility: **Public**, dengan login aplikasi sebagai paywall.
