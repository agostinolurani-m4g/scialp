Backcountry Map
===============

Web app per gestire gite, giornate e valanghe.

Avvio locale
------------
1. `python -m venv .venv`  
2. `pip install -e .`
3. `set SCIALPI_SECRET_KEY=dev` (Windows)  
4. `python -m scialpi_web.app`

Deploy economico (Fly.io + Cloudflare R2)
-----------------------------------------
Serve per restare entro ~40 EUR/anno con molte immagini.

1. Crea bucket R2 e rendilo pubblico.
2. Crea un'app su Fly.io.
3. Configura un volume per i dati JSON (montato in `/data`).
4. Imposta le variabili ambiente (vedi sotto).

Variabili ambiente
------------------
- `SCIALPI_SECRET_KEY`: chiave Flask.
- `SCIALPI_LOG_HOME`: cartella dati (consigliato `/data` in prod).
- `SCIALPI_MEDIA_PROVIDER`: `local` o `s3`.
- `SCIALPI_MEDIA_BASE_URL`: URL pubblico base (es. https://<bucket>.<account>.r2.cloudflarestorage.com).
- `SCIALPI_S3_ENDPOINT`: endpoint S3 (R2).
- `SCIALPI_S3_REGION`: default `auto` per R2.
- `SCIALPI_S3_BUCKET`: nome bucket.
- `SCIALPI_S3_ACCESS_KEY` / `SCIALPI_S3_SECRET_KEY`.
- `PORT`: porta HTTP (default 8080).

Comandi Fly.io (esempio)
------------------------
1. `fly launch` (usa `fly.toml`).
2. `fly volumes create scialpi_data --size 1`
3. `fly secrets set SCIALPI_SECRET_KEY=...`
4. `fly secrets set SCIALPI_MEDIA_PROVIDER=s3`
5. `fly secrets set SCIALPI_MEDIA_BASE_URL=...`
6. `fly secrets set SCIALPI_S3_ENDPOINT=...`
7. `fly secrets set SCIALPI_S3_BUCKET=...`
8. `fly secrets set SCIALPI_S3_ACCESS_KEY=...`
9. `fly secrets set SCIALPI_S3_SECRET_KEY=...`
10. `fly deploy`
