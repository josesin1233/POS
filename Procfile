web: gunicorn dulceria_pos.wsgi --log-file -
release: python manage.py migrate && python init_railway.py