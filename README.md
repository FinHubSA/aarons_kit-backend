# aarons_kit-backend

brew install postgresql

python3 -m venv env

source env/bin/activate

# To leave the environment run:
deactivate

pip3 install -r requirements.txt

# If you get error of path not found on uWSGI install run this
sudo ln -s /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.8/lib/python3.8/config-3.8-darwin <INSERT YOUR NOT-FOUND-PATH HERE WITHOUT libpython3.8.a FILENAME>

# To build after changing code
docker-compose build

# To run in background
docker-compose up -d

# To run tests

- Connect to api app in docker
- Run this command to view the container ids:
```
docker ps
```
- Run this command to get into the postgres docker container:
```
docker exec -it app_container_id bash
```
- To run tests do this command:
```
python3 manage.py test
```

# To extract references
- Run the following
```
pip install wheel
pip install refextract 
brew install libmagic
python3
from refextract import extract_references_from_file
```

## API Endpoints
| Endpoints | HTTP Method | Action |
| --- | --- | --- |
| api/articles | GET  | To retrieve articles. Defaults to 50 articles. Set the page and page_size parameters to  |
| POST | /api/user/login | To login an existing user account |
| POST | /api/causes | To create a new cause |
| GET | /api/causes | To retrieve all causes on the platform |
| GET | /api/causes/:causeId | To retrieve details of a single cause |
| PATCH | /api/causes/:causeId | To edit the details of a single cause |
| DELETE | /api/causes/:causeId | To delete a single cause |

