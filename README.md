# Strange Fruit

## setup project

1. create venv: python3 -m venv venv
2. activate venv: source venv/bin/activate
3. after activate venv then go to project root directory(cd to the directory where requirements.txt is located): cd project_name
4. run: pip install -r requirements.txt
5. django server run: python manage.py runserver

## setup celery
6. sudo systemctl status redis(check active or inactive)
7. sudo systemctl restart redis.service(run this command after check redis status)
8. redis status is active then open two new terminal and activate venv then go to project root directory
9. first terminal run: celery -A SF  worker --loglevel=info   
10. second terminal run: celery -A SF worker -B