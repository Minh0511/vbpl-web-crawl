# VBPL Web Crawl.

## Steps to initialize app

### Install dependencies
```
pip install -r requirements.txt
```

### Install mysql docker
```
docker compose up -d
```

### Upgrade head migration
```
alembic upgrade head
```

### Install Ghostscript
[Download link](https://www.ghostscript.com/releases/gsdnld.html)

#### Note: there can be an error related to Window's Ghostscript execution file and the one defined in pdfplumber. Currently the only valid execution file name is 'gs' or 'gswin32c', change your execution file name accordingly.

## Other utilities
### Create migration versions
```
alembic revision --autogenerate
```

## Requirements
[Requirements PDF](https://drive.google.com/file/d/11nrMVCe2yCIuMI4zzX4Wcif_7lhCv1GT/view?usp=sharing)
