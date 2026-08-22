# PROMPT — Revisi main.py sesuai "Business Rules & Workflow Use Case Suspend 2026" (Cedant ACA)

Kamu bertugas merevisi script produksi `main.py` (matching & join SUSPEND → OSBAL / R/I Slip DB / FACUL, khusus cedant ACA). Script SUDAH BERJALAN tapi menyimpang dari dokumen business rules di beberapa poin. Perbaiki SEMUA poin di bawah, jangan ada yang dilewati. Pertahankan gaya penamaan variabel/fungsi berbahasa Indonesia yang sudah ada. Utamakan keamanan (tidak ada baris data yang hilang/salah kategori), performa (arsitektur list-of-dict + inverted index HARUS dipertahankan, jangan diganti ke pandas vectorized), dan akurasi hasil terhadap dokumen.

Catatan penting: dokumen business rules ini berlaku general lintas cedant, tapi script ini khusus untuk cedant ACA. Jadi ADA aturan general di dokumen yang SENGAJA TIDAK diimplementasikan di sini karena tidak relevan untuk ACA:
- Cross-type matching (polis suspend ↔ kolom slip referensi, dan sebaliknya) — TIDAK PERLU ditambahkan.
- Exclusion insured afiliasi bank — TIDAK PERLU ditambahkan.
Jangan tambahkan kedua hal ini meskipun disebut di dokumen umum.

---

## LANGKAH 0 (WAJIB DILAKUKAN LEBIH DULU): Periksa data asli di workspace

Sebelum mengubah kode apa pun, buka dan inspeksi langsung file-file berikut yang ada di folder `data/` pada workspace:
- `data/suspend_clean_aca.xlsx`
- `data/osbal_clean_aca.xlsx`
- `data/facul_clean_aca.xlsx`
- `data/slipdb_clean_aca.xlsx`

Untuk masing-masing file, cek dan laporkan sebelum lanjut coding:
1. Nama kolom aktual (khususnya semua kolom yang diawali `clean polis`, `clean slip`, `clean insured`, kolom `polis_ori`, `slip_ori`, `insured_ori`, kolom FAC_CODE/CCOS_REF_CODE, dan kolom `CCOS_DOC_NO`, `CCOS_OR_BAL`, `CCOS_BAL_DUE`, `AMOUNT ORI`).
2. Contoh 5-10 baris riil untuk memastikan format nilai (apakah polis/slip berupa string, ada leading zero, dsb — supaya normalisasi `_normalisasi_teks` tidak merusak data).
3. Cek apakah ada baris duplikat di `suspend_clean_aca.xlsx` (dokumen eksplisit: "data 3 Suspend dipastikan tidak duplikat row-nya" — kalau ternyata ada duplikat di data aktual, laporkan ke saya sebelum lanjut, JANGAN otomatis di-drop tanpa konfirmasi).
4. Cek apakah ada FAC_CODE di `osbal_clean_aca.xlsx` yang bernilai kosong/NaN, karena ini pengaruh ke index resolusi FAC_CODE.
5. Cek sebaran nilai `CCOS_BAL_DUE` — apakah ada yang negatif (dokumen menyebut ini valid dan tetap dipakai hitung, bukan dianggap error).

Gunakan hasil pemeriksaan ini untuk memastikan implementasi di bawah benar-benar cocok dengan bentuk data asli, bukan cuma asumsi dari nama kolom di kode lama.

---

## KONTEKS BUSINESS RULES (yang relevan & berlaku untuk script ini)

1. Urutan sumber data: Proses 1 = Suspend→OSBAL (data 2), Proses 2 = Suspend→R/I Slip DB (data 5), Proses 3 = Suspend→FACUL (data 1). Match pakai nomor polis atau slip; **jika tidak ketemu baru pakai insured name** ("Insured only (last choice)").
2. Untuk SLIPDB (data 5) dan FACUL (data 1): hasil match di sana **hanya dipakai untuk mengambil FAC_CODE**, lalu FAC_CODE itu di-resolve exact ke OSBAL untuk ambil CCOS_BAL_DUE. **Jika FAC_CODE tidak ketemu di OSBAL, hasil match SLIPDB/FACUL itu dianggap TIDAK match sama sekali** — pipeline harus lanjut coba sumber/pass berikutnya, bukan berhenti dan membawa data SLIPDB/FACUL mentah sebagai hasil akhir.
3. Insured matching adalah **pilihan paling terakhir**, dicoba lintas SEMUA sumber (OSBAL, SLIPDB→resolve, FACUL→resolve) HANYA setelah seluruh kombinasi polis/slip (exact + token, same-type saja) ke SEMUA sumber sudah dicoba dan gagal semua.
4. Narrowing/penyempitan kandidat (kalau >1 baris match) pakai field pelengkap: kalau match awal via SLIP, sempitkan pakai POLIS yang juga cocok (dan sebaliknya). Untuk FACUL/SLIPDB, narrowing berbasis FAC_CODE hanya dijalankan kalau kandidat menghasilkan >1 FAC_CODE berbeda (aturan khusus ACA: "cek slip dulu, kalau ketemu 2 fac code beda baru cek no polis").
5. **Akumulasi**: dibedakan dari jumlah CCOS_DOC_NO unik pada FAC_CODE yang sama — 1 doc no = tanpa akumulasi, >1 doc no = dengan akumulasi. Logika existing (proxy pakai jumlah baris OSBAL matched, karena "1 doc no pasti unik untuk 1 row data OSBAL") sudah benar — JANGAN diganti, cukup diverifikasi ulang terhadap data asli hasil Langkah 0.
6. **DIFERENCE = AMOUNT_ORI (nilai ASLI, BUKAN dikali -1) − CCOS_BAL_DUE.** Contoh eksplisit dari dokumen: Amount ori = 1.000.000, Bal due = -500.000 → Difference = 1.000.000 − (−500.000) = 1.500.000. AMOUNT_ORI_MIN1 (amount ori × -1) HANYA dipakai untuk logika pencocokan/threshold FLAG_PROD, TIDAK boleh dipakai untuk kolom DIFERENCE.
7. FLAG_PROD (kategori, pakai AMOUNT_ORI_MIN1 vs CCOS_BAL_DUE) — TETAP seperti kode existing, JANGAN diubah:
   - Matching >1 fac code: >1 FAC_CODE ditemukan di OSBAL setelah kombinasi matching.
   - Adjustment total tanpa akumulasi: amount_ori_min1 == bal_due, 1 row OSBAL.
   - Adjustment total dengan akumulasi: amount_ori_min1 == bal_due, >1 row OSBAL.
   - Adjustment sebagian tanpa akumulasi: amount_ori_min1 < bal_due, 1 row OSBAL.
   - Adjustment sebagian dengan akumulasi: amount_ori_min1 < bal_due, >1 row OSBAL.
   - New Entry: amount_ori_min1 > bal_due, ATAU amount_ori_min1 != 0 dan bal_due == 0.
   - Unmatching: default.
8. CCOS_DOC_NO **hanya diisi** untuk kasus "Adjustment total tanpa akumulasi" (1 row OSBAL, amount pas sama). Kasus lain dikosongkan. (Sudah benar — jangan diubah.)
9. **Penamaan SKENARIO wajib pakai bahasa yang mudah dipahami user**, HANYA dari daftar resmi berikut (tidak boleh ada nama teknis lain seperti SLIP_CLEAN/POLIS_TOKEN yang bocor ke kolom final):
   - `Polis only`
   - `Slip only`
   - `Insured only`
   - `Polis and slip`
   - `Polis and slip and insured`
   - `Unmatching`
   Format string final tetap sertakan sumber data & status resolve, mengikuti pola existing:
   - Match langsung OSBAL: `f"OSBAL_{nama_skenario}"` → contoh `"OSBAL_Polis and slip"`.
   - Match via SLIPDB/FACUL yang berhasil di-resolve ke OSBAL: `f"{sumber_perantara}_{nama_skenario}_RESOLVED"` → contoh `"SLIPDB_Slip only_RESOLVED"`.
   - Tidak ada lagi status "UNRESOLVED" (lihat poin perbaikan B di bawah) — kalau gagal resolve, dianggap tidak match dan lanjut ke pass berikutnya, bukan skenario tersendiri.
   - Kalau semua pass gagal total → `"Unmatching"` (SAMAKAN dengan string di kolom FLAG_PROD, JANGAN pakai `"UNMATCHED"` lagi supaya konsisten satu istilah).

---

## DAFTAR PERBAIKAN WAJIB (kerjakan semua, urut sesuai nomor)

### A. Restrukturisasi urutan matching: pisahkan polis/slip dari insured

Insured TIDAK BOLEH lagi dicoba dalam pass yang sama dengan polis/slip per sumber data. Insured harus jadi **pass terakhir tersendiri**, dicoba lintas semua sumber, hanya kalau semua pass polis/slip gagal total.

- Pecah `_cocokkan_baris` jadi dua fungsi:
  - `_cocokkan_polis_slip(...)` — HANYA mengevaluasi SLIP_CLEAN, POLIS_CLEAN, SLIP_ORI, POLIS_ORI (exact), lalu SLIP_TOKEN, POLIS_TOKEN (token). Insured dihapus total dari fungsi ini.
  - `_cocokkan_insured(...)` — HANYA mengevaluasi INSURED_CLEAN, INSURED_ORI (exact), lalu INSURED_TOKEN (token). Dipanggil terpisah, belakangan.
- Di `jalankan_proses`, restrukturisasi loop utama per baris Suspend menjadi urutan pass berikut:
  1. Pass 1: OSBAL via `_cocokkan_polis_slip` (exact)
  2. Pass 2: OSBAL via `_cocokkan_polis_slip` (token)
  3. Pass 3: SLIPDB via `_cocokkan_polis_slip` (exact) → resolve FAC_CODE ke OSBAL
  4. Pass 4: SLIPDB via `_cocokkan_polis_slip` (token) → resolve FAC_CODE ke OSBAL
  5. Pass 5: FACUL via `_cocokkan_polis_slip` (exact) → resolve FAC_CODE ke OSBAL
  6. Pass 6: FACUL via `_cocokkan_polis_slip` (token) → resolve FAC_CODE ke OSBAL
  7. **Pass 7 (BARU): kalau semua pass 1-6 gagal** → coba `_cocokkan_insured` ke OSBAL (exact lalu token) → kalau gagal, ke SLIPDB (exact lalu token) + resolve FAC_CODE → kalau gagal, ke FACUL (exact lalu token) + resolve FAC_CODE.
  8. Pass 8: kalau pass 7 juga gagal semua → `"Unmatching"` (fallback, lihat poin E).
- Perhatikan performa: pemecahan fungsi ini tidak boleh menambah kompleksitas iterasi (tetap 1x pass per baris suspend per kombinasi sumber+exact/token, jangan dobel-loop).

### B. Perbaiki bug resolusi FAC_CODE gagal yang menghentikan fallback

Di setiap pemanggilan `_resolusi_facode_ke_osbal` (Pass SLIPDB exact/token, Pass FACUL exact/token, dan versi insured di Pass 7), JIKA `ok == False` (FAC_CODE tidak ketemu di OSBAL):
- JANGAN set `indeks_matched = m_indeks` (data mentah SLIPDB/FACUL).
- Reset seolah pass ini TIDAK match sama sekali (`indeks_matched = []`), supaya loop lanjut mencoba pass berikutnya.
- Hapus total behavior lama yang menghasilkan skenario `..._UNRESOLVED` dengan data SLIPDB/FACUL mentah dibawa ke output. Kalau sampai akhir (termasuk Pass 7 insured) tetap gagal resolve, hasilnya jatuh ke fallback `"Unmatching"` biasa (Pass 8).
- Pastikan variabel `sumber_perantara`/`status_resolved` yang tidak lagi dipakai untuk kasus UNRESOLVED dibersihkan dari kode supaya tidak ada dead code atau state yang membingungkan.

### C. Perbaiki rumus kolom DIFERENCE

Di `_hitung_kolom_turunan`, ubah:
```python
df_output["DIFERENCE"] = df_output["AMOUNT_ORI_MIN1"] - balance_due
```
menjadi memakai AMOUNT_ORI asli (bukan yang dikali -1):
```python
df_output["DIFERENCE"] = amount_ori - balance_due
```
`AMOUNT_ORI_MIN1` tetap dipertahankan apa adanya dan tetap dipakai untuk logika `FLAG_PROD` (jangan diubah bagian itu). Verifikasi dengan contoh dari dokumen: amount_ori = 1.000.000, ccos_bal_due = -500.000 → DIFERENCE harus menghasilkan 1.500.000.

### D. Bangun ulang penamaan SKENARIO sesuai daftar resmi

- Buat fungsi mapping baru, misal `_petakan_nama_skenario(label_internal: str) -> str`, yang menerjemahkan label teknis internal ke istilah resmi:
  - `SLIP_CLEAN`, `SLIP_ORI`, `SLIP_TOKEN` → `"Slip only"`
  - `POLIS_CLEAN`, `POLIS_ORI`, `POLIS_TOKEN` → `"Polis only"`
  - `INSURED_CLEAN`, `INSURED_ORI`, `INSURED_TOKEN` → `"Insured only"`
- Modifikasi `_penyempitan_pasangan` (atau tambahkan wrapper baru di sekitarnya) supaya SETELAH narrowing berhasil, fungsi mengecek apakah field pelengkap (polis kalau match awal via slip, atau slip kalau match awal via polis) benar-benar TERBUKTI COCOK pada baris-baris hasil narrowing (bukan cuma dipakai sebagai filter, tapi statusnya dikembalikan). Kalau field pelengkap terbukti cocok → nama skenario final jadi `"Polis and slip"` (menggantikan `"Slip only"`/`"Polis only"`). Kalau field pelengkap tidak match di baris hasil (narrowing tidak mengurangi apa pun / kandidat tetap sama) → tetap pakai nama single-field (`"Slip only"` atau `"Polis only"`).
- Case `"Polis and slip and insured"` HANYA dipakai kalau ketiga field (polis, slip, insured) semuanya terbukti cocok bersamaan pada baris hasil akhir yang sama — situasi ini kemungkinan besar TIDAK muncul secara alami dari alur Pass 1-7 yang sudah dipisah (karena insured baru dicoba di Pass 7, setelah polis/slip). Kalau setelah implementasi ternyata kombinasi tiga-field ini tidak pernah tercapai secara logis dalam alur baru, JANGAN dipaksakan membuat kondisi buatan — cukup laporkan ke saya bahwa skenario ini secara struktural tidak pernah terjadi dengan alur Pass 1-7, dan biarkan kode tanpa cabang khusus untuk itu (atau beri komentar `# TODO-VALIDASI:` di titik yang relevan).
- Update `_susun_baris_output` supaya string SKENARIO final dibangun dari nama hasil pemetaan ini (lihat format string di poin 9 bagian KONTEKS di atas), bukan label teknis mentah.

### E. Rapikan fallback UNMATCHED

Pastikan seluruh kode yang sebelumnya memakai string literal `"UNMATCHED"` (termasuk di `_susun_baris_output` dan baris `df_output.loc[df_output["SKENARIO"] == "UNMATCHED", "FLAG_PROD"] = "Unmatching"` di `jalankan_proses`) diganti konsisten menjadi `"Unmatching"`, supaya kolom SKENARIO dan FLAG_PROD memakai istilah yang sama persis untuk kasus tidak match, sesuai dokumen.

### F. Pastikan tidak ada regresi

- Semua nama fungsi, gaya penamaan Indonesia, dan struktur list-of-dict/inverted-index yang sudah ada untuk performa TETAP DIPERTAHANKAN — jangan refactor ke pandas vectorized ops, jangan ubah arsitektur performa, jangan tambah dependency baru.
- `FINAL_COLUMNS`, `_hitung_kolom_turunan` (selain DIFERENCE), `_agregasi_nilai_ccos`, `_dapatkan_label_facode`, penentuan CCOS_DOC_NO tetap seperti sekarang — JANGAN diubah kecuali disebutkan eksplisit di atas.
- JANGAN menambahkan cross-type matching (polis↔slip silang) dan JANGAN menambahkan exclusion insured afiliasi bank — kedua hal ini sengaja di luar cakupan untuk script khusus ACA ini.
- Setelah kode jadi, jalankan script terhadap data asli di folder `data/` (bukan cuma baca sekilas), lalu laporkan ringkasan `value_counts()` untuk kolom SKENARIO dan FLAG_PROD supaya saya bisa cross-check angkanya masuk akal (tidak ada kategori "UNRESOLVED" tersisa, tidak ada nama skenario di luar daftar resmi, dsb).

---

## OUTPUT YANG DIMINTA

1. Ringkasan hasil pemeriksaan data asli dari Langkah 0 (nama kolom, contoh nilai, temuan duplikat/kosong bila ada) — laporkan ini DULU sebelum kode final.
2. Versi lengkap `main.py` yang sudah direvisi (full file, bukan potongan diff saja), siap dijalankan langsung.
3. Ringkasan perubahan per fungsi (bullet list singkat) di akhir, supaya bisa saya cross-check ke daftar poin A-F di atas.
4. Hasil `value_counts()` SKENARIO dan FLAG_PROD dari run terhadap data asli di `data/`.
5. Tandai dengan komentar `# TODO-VALIDASI:` di kode pada bagian yang butuh saya konfirmasi manual (khususnya soal kondisi `"Polis and slip and insured"` di poin D).
