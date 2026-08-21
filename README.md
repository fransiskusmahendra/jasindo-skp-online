# SKP Online Jasindo

Aplikasi Streamlit mandiri untuk **Surat Konfirmasi Premi Property/FLEXAS** dan **Endorsement**. Repository ini berdiri sendiri dan tidak bergantung pada platform atau aplikasi lain.

## Alur pengguna
1. Pilih **SKP Baru** atau **Endorsement**.
2. Isi data tertanggung dan periode.
3. Cari okupasi dengan nama sederhana atau kode OJK.
4. Pilih kelas konstruksi jika diperlukan; okupasi dengan tarif khusus ditangani otomatis.
5. Isi Nilai Pertanggungan (SI).
6. Tarif default menggunakan batas bawah master OJK; range dan validasi tersedia pada bagian detail.
7. Klik **Hitung Premi**, lalu unduh Word/PDF.

## Master okupasi
`ojk_occupations_full.csv` memuat **373 okupasi dengan rate numerik yang dapat dipilih**, berdasarkan SEOJK 6/SEOJK.05/2017 Lampiran I Tabel I.A. Baris judul tanpa tarif atau referensi tanpa rate mandiri tidak dijadikan pilihan.

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
