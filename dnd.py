# -*- coding: utf-8 -*-
from flask import Flask, Response, request, jsonify, abort
from tinydb import TinyDB, Query
from tinydb.operations import increment
import sys
import aliases
import admin

app = Flask(__name__)
app.config.update(dict(
    SECRET_KEY='http://bfy.tw/1y51'
))
app.config.from_envvar('DNDSERVER_SETTINGS', silent=True)

from secrets import MY_SECRET_TOKENS
BOT_NAME = "PlusPlus"
DATABASE = "/home/kenzie/mattermost/db-dnd.json"

db = TinyDB(DATABASE)

def get_entry(ident):
    Entry = Query()
    data = db.search(Entry.ident == ident)
    if not data:
        return 0
    assert len(data) == 1, "unexpected data for " + entry
    return data[0]['count']
def increment_entry(ident):
    Entry = Query()
    cond = Entry.ident == ident
    if not db.contains(cond):
        db.insert({'ident': ident, 'count': 1})
        return
    db.update(increment('count'), cond)

def msg(text):
    return jsonify(username=BOT_NAME, text=text)
def no_msg():
    return jsonify()
def thegoodprint(*args):
    print(*args, file=sys.stderr)

@app.route("/", methods=("GET", "POST"))
def index():
    if request.form['token'] not in MY_SECRET_TOKENS:
        thegoodprint('Denying token', request.form['token'])
        abort(401)
    in_text = request.form['text'].strip()
    in_parts = in_text.split(' ')
    if len(in_parts) == 1 and in_parts[0][-2:] == '++':
        entry = in_parts[0][:-2]
        if not entry.isalnum():
            return msg(entry + ' is not a valid entry identifier.')
        ident = aliases.resolve_to_identifier(entry)
        increment_entry(ident)
        return msg(entry + " (" + ident + ") now has a score of " + str(get_entry(ident)))
    elif in_parts[0].startswith('++'):
        # PlusPlus commands!
        in_parts[0] = in_parts[0][2:]
        return handle_command(in_parts)
    return no_msg()


def handle_command(parts):
    is_admin = admin.is_admin(request.form['user_id'])
    if parts[0] == 'add_alias' and is_admin:
        if len(parts) < 3:
            return msg("Need 2 args: [ident, alias]")
        ident = parts[1]
        alias = parts[2]
        r = aliases.add_alias(ident, alias)
        if r:
            return msg(r)
        return no_msg()
    return msg("Unknown ++ command " + parts[0])


if not app.debug:
    import logging
    from logging import StreamHandler
    file_handler = StreamHandler(sys.stderr)
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

if __name__ == '__main__':
    app.run('0.0.0.0', 0x1F11, debug=True) # 7953

