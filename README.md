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
