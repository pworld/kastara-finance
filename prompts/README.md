# Persona Prompts — Panel 4 "4 Analisa (AI)"

Tiap file `persona_<lens>.txt` di folder ini adalah **system prompt** yang
dikirim ke OpenRouter untuk 1 persona (lihat `llm/persona_analysis.py`).
File-file ini **tidak dibuat otomatis** dan **tidak di-commit** (gitignored
lewat `prompts/persona_*.txt` — cuma README ini yang di-track), karena
isinya adalah cara berpikir/analisa Giel sendiri.

Lens yang harus diisi (nama file harus persis, huruf kecil):

| File | Persona (kode internal) | Label di UI |
|---|---|---|
| `persona_gema.txt` | GEMA | Global & Capital Flow |
| `persona_leon.txt` | LEON | Policy & Sistem Domestik |
| `persona_akela.txt` | AKELA | Dinamika Pasar & Waktu |
| `persona_rivan.txt` | RIVAN | Fundamental & Realist |

Isi tiap file adalah teks bebas (system prompt), contoh:

```
Kamu adalah analis makro global. Baca snapshot pasar & berita key yang
diberikan, lalu tulis 1 paragraf analisa singkat dari sudut pandang makro
global (DXY, US10Y, kebijakan The Fed, dll). Bahasa Indonesia, langsung ke
poin, tanpa disclaimer.
```

Selama file untuk 1 persona belum ada atau isinya kosong, tombol "Jalankan
Analisa" di Panel 4 akan menolak jalan dan memberi tahu di UI (bukan diam-
diam gagal atau memanggil OpenRouter dengan prompt kosong).
