# Theatre API

Django REST project for reservation tickets and manage plays in theatre

## Check it out!


## Test user, for quick start

**email:** `user@example.com`  
**password:** `User12345`

## Instalation using GitHub
Python3 must be already installed
Install PostgresSQL and create db

    git clone https://github.com/Artstrik/theatre_api_service.git
    cd theatre_api_service
    python -m .venv venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    set DB_PASSWORD=<your db user password>
    set DB_USER=<your db username>
    set DB_NAME=<your db name>
    set DB_HOST=<your db hostname>
    set SECRET_KEY=<your secret key>
    python manage.py migrate
    python manage.py runserver

## Access the application:

- API: http://127.0.0.1:8001/
- Admin: http://127.0.0.1:8001/admin/
- Documentation: http://127.0.0.1:8001/api/doc/swagger/
- Get token: http://127.0.0.1:8001/api/user/token/

## Run with Docker

Docker should be installed

    docker-compose build
    docker-compose up

## Features

- JWT authenticated
- Admin panel /admin/
- Documentation is located at /api/doc/swagger/ or /api/doc/redoc/
- Managing reservation and tickets
- Creating plays with genres and actors
- Creating theatre halls
- Adding performance
- Filtering plays and performances

