from .settings import env

# To use local settings, rename this file to be local_settings.py
# DB name is: <initials>_test_masterlist
def update_db_settings(db_settings):
    db_settings["TEST"] = {'NAME': 'tc_test_masterlist'}
    return db_settings


