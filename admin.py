from tinydb import TinyDB, Query

_db = TinyDB("/home/kenzie/mattermost/db-admin.json")

if __name__ == "__main__":
    print("Adding admin to list!")
    admin = input("Insert admin: ")
    if admin:
        _db.insert({"uid": admin})
        print ("Adming added:", admin)

def rem_admin(uid):
    _db.remove(Query().uid == uid)

def is_admin(uid):
    return _db.contains(Query().uid == uid)

