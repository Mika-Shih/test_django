FROM python:3.11

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .

# install python dependencies
RUN pip install --upgrade pip
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt

# COPY env.sample .env
COPY .env .env
COPY . .

# running migrations
# RUN python manage.py makemigrations
# RUN python manage.py migrate

# CMD ["python", "manage.py", "runserver"]
CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:8000"]
# gunicorn
# CMD ["gunicorn", "--config", "gunicorn-cfg.py", "core.wsgi"]

