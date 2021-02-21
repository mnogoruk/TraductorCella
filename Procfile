release: python manage.py makemigrations
release: python manage.py migrate
web: gunicorn TraductorCella.asgi:application -k uvicorn.workers.UvicornWorker