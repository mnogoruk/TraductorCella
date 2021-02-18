release: python manage.py makemigrations
release: python manage.py migrate
web: gunicorn TroductorCella.asgi:application -k uvicorn.workers.UvicornWorker