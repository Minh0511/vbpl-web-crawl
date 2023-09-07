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

## Other utilities
### Create migration versions
```
alembic revision --autogenerate
```

## Requirements
[Requirements PDF](https://drive.google.com/file/d/11nrMVCe2yCIuMI4zzX4Wcif_7lhCv1GT/view?usp=sharing)
