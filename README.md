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