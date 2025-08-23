release: python manage.py migrate && python manage.py collectstatic --noinput && python init_railway.py
web: gunicorn dulceria_pos.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-file - --log-level info
