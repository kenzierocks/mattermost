# -*- coding: utf-8 -*-
from flask import Flask, Response, request, jsonify, abort, url_for
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
def get_entries():
    return db.all()
def get_largest_entry():
    Entry = Query()
    data = db.search(Entry.count > 0)
    max_score = None
    for e in data:
        e_count = e['count']
        if e_count > (max_score['count'] if max_score else 0):
            max_score = e
    return max_score
def change_entry(ident, amount):
    Entry = Query()
    cond = Entry.ident == ident
    if not db.contains(cond):
        db.insert({'ident': ident, 'count': 0})
    def change(entry):
        entry['count'] += amount
    db.update(change, cond)
def set_entry(ident, amount):
    Entry = Query()
    cond = Entry.ident == ident
    if not db.contains(cond):
        db.insert({'ident': ident, 'count': amount})
    else:
        def f(e):
            e['count'] = amount
        db.update(f, cond)
def merge_ident(i_from, i_to):
    Ident = Query()
    from_exists = db.contains(Ident.ident == i_from)
    to_exists = db.contains(Ident.ident == i_to)
    if from_exists and to_exists:
        i_from_data = db.get(Ident.ident == i_from)
        def add_score(entry):
            entry['count'] += i_from_data['count']
        db.update(add_score, Ident.ident == i_to)
        db.remove(Ident.ident == i_from)
        return aliases.merge_ident(i_from, i_to)
    else:
        s = ''
        if not from_exists:
            s += i_from
        if not to_exists:
            if s:
                s += ', '
            s += i_to
        return "Couldn't find {} in the DB.".format(s)

def ident_or_by_name(name):
    if name.startswith('ident!'):
        return name
    if name[0] == '@':
        name = name[1:]
    return aliases.resolve_to_identifier(name)

def msg(text):
    return jsonify(username=BOT_NAME, text=text)
def no_msg():
    return jsonify()
def thegoodprint(*args):
    print(*args, file=sys.stderr)

def emoji_for_dutcher(entry):
    return entry[0] == ':' and entry[-1] == ':' and entry[1:-1].isalnum()

def change_score(entry, amount):
    if not (entry.isalnum() or entry.startswith('ident!') or emoji_for_dutcher(entry)):
        return entry + ' is not a valid entry identifier.'
    ident = ident_or_by_name(entry)
    change_entry(ident, amount)
    return "{} now has score of {}.".format(entry, get_entry(ident))

def set_score(entry, amount):
    if not (entry.isalnum() or entry.startswith('ident!') or emoji_for_dutcher(entry)):
        return entry + ' is not a valid entry identifier.'
    ident = ident_or_by_name(entry)
    set_entry(ident, amount)
    return "{} now has score of {}.".format(entry, get_entry(ident))

@app.route("/", methods=("GET", "POST"))
def index():
    if request.form['token'] not in MY_SECRET_TOKENS:
        thegoodprint('Denying token', request.form['token'])
        abort(401)
    in_text = request.form['text'].strip().lower()
    try:
        linestosend = []
        for line in in_text.split('\n'):
            v = handle_in_msg(line)
            if v:
                linestosend.append(v)
        if linestosend:
            return msg('\n'.join(linestosend))
    except Exception as e:
        thegoodprint('err....', e)
        import traceback
        traceback.print_exc()
        # Be quiet if it didn't look like us
        if '++' in in_text:
            return msg("An unknown error occurred processing your input")
    return no_msg()

def handle_in_msg(in_text):
    in_parts = in_text.split(' ')
    if len(in_parts) == 1 and (in_parts[0][-2:] in ('++', '--')):
        entry = in_parts[0][:-2].lstrip('@')
        cmd = in_parts[0][-2:]
        data = 'Cannot handle ' + cmd
        if cmd == '++':
            data = change_score(entry, 1)
        elif cmd == '--':
            data = change_score(entry, -1)
        return data
    elif in_parts[0].startswith('++'):
        # PlusPlus commands!
        in_parts[0] = in_parts[0][2:]
        return handle_command(in_parts)

def filter_html(x):
    return (x.replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>')
                .replace('\x00&lt;', '<')
                .replace('\x00&gt;', '>'))

@app.route('/listcmd')
def listcmd():
    l = []
    for k, v in command_map.items():
        l.append("++{}: {}".format(k, v['desc']))
    return filter_html('\n'.join(l))

def htmlEsc(s, newlines=False):
    if newlines:
        s = s.replace('\n', '')
    return s.replace('<', '\x00<').replace('>', '\x00>')
@app.route('/listscores')
def listscore():
    l = get_entries()
    s = htmlEsc("""
    <head>
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
    </head>
    <body>
    <table style="margin: 0 auto; width: inherit" class="table table-striped">
        <tr>
            <th>Identifier</th>
            <th>Score</th>
        </tr>
    </body>
    """, True)
    mn = min(f['count'] for f in l)
    mx = max(f['count'] for f in l)
    if mn == mx:
        s += htmlEsc("<h1>Warning: min == max, no scores?</h1>")
    for e in sorted(l, key=lambda f: -f['count']):
        tmpl = """
        <div class="progress" style="margin-bottom: 0">
            <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="{value}" aria-valuemin="{min}" aria-valuemax="{max}" style="width: {percent}%;">
            </div>
        </div>
        """.replace('\n', '')
        v = e['count']
        pcent = 0 if mx == mn else int((v-mn)/(mx-mn) * 100)
        s += (htmlEsc("<tr><td>{}</td><td align=\"right\">{}" + tmpl + "</td></tr>"
              .replace('<', '\x00<').replace('>', '\x00>'))
              .format(e['ident'].replace('ident!', ''), e['count'], value=v, min=mn, max=mx, percent=pcent))
    s += "</table>".replace('<', '\x00<').replace('>', '\x00>')
    return filter_html(s)

command_map = dict()

def command(name, desc, arg_list, admin=False, aliases=[]):
    def insert_f(f):
        command_map[name] = {
                'func': f,
                'desc': desc + ' Args: ' + args_to_string(arg_list),
                'args': arg_list,
                'admin': admin
        }
        return f
    return insert_f

def args_to_string(args):
    if args is None:
        return 'Unknown.'
    s = '['
    for x in range(len(args)):
        s += args[x]
        if x < (len(args) - 1):
            s += ', '
    return s + ']'


@command('add_alias', 'Adds an alias to an ident.', ['ident', 'alias'], True)
def c_add_alias(ident, alias):
    return aliases.add_alias(ident, alias)

@command('merge_idents', 'Merges `from` into `to`.', ['ident or alias from', 'ident or alias to'], True)
def c_merge_idents(fr, to):
    return merge_ident(ident_or_by_name(fr), ident_or_by_name(to))

@command('set_score', 'Sets the score of `ident` to `score`.', ['ident', 'score'], True)
def c_set_score(to, score):
    try:
        score = int(score)
    except ValueError:
        return score + " is not a valid score."
    return set_score(to, score)

@command('winner', 'Finds the user with the most points.', [])
def c_winner():
    top = get_largest_entry()
    return 'Current top score: {} with {}'.format(top['ident'], top['count'])

@command('get', 'Finds the score for the given user.', ['name'])
def c_get(name):
    count = get_entry(ident_or_by_name(name))
    return "{}'s score is {}".format(name, count)

@command('list', 'Lists all the scores', [])
def c_list():
    return 'Visit {} for the score listings.'.format(request.url_root + 'listscores')

@command('help', 'Lists help for all or a specified command.', None)
def c_help(args):
    if len(args) == 0:
        return "Visit {} for a full list of commands.".format(request.url_root + 'listcmd')
    cmd = args[0]
    if cmd not in command_map:
        return "The command {} does not exist.".format(cmd)
    return "```\n++{}: {}\n```".format(cmd, command_map[cmd]['desc'])

@command('remove_ident', 'Removes an ident entirely', ['ident or alias'], admin=True)
def c_remove_alias(ident):
    ident = ident_or_by_name(ident)
    ident_query = Query().ident == ident
    s = ''
    if db.contains(ident_query):
        db.remove(ident_query)
        s += "Removed scores for {}.\n".format(ident)
    s += aliases.remove_ident(ident)
    return s

@command('source', 'Retrieve the URL for source', [])
def c_source():
    return 'https://github.com/kenzierocks/mattermost'

@command('get_ident', 'Retrieve the ident for an alias', ['alias'])
def c_get_ident(name):
    ident = ident_or_by_name(name)
    return ident

def handle_command(parts):
    is_admin = admin.is_admin(request.form['user_id'])
    cmd_name = parts[0]
    if cmd_name in command_map:
        cmd_data = command_map[cmd_name]
        if cmd_data['admin'] and not is_admin:
            return msg("You don't have permission to run {}".format(cmd_name))
        if cmd_data['args'] is not None and  len(parts) < (1 + len(cmd_data['args'])):
            return msg("Need {} arg(s): {}".format(len(cmd_data['args']), args_to_string(cmd_data['args'])))
        args = parts[1:]
        r = None
        if cmd_data['args'] is None:
            r = cmd_data['func'](args)
        else:
            r = cmd_data['func'](*args)
        if r:
            return r
        return None
    return "Unknown ++ command " + parts[0]


if not app.debug:
    import logging
    from logging import StreamHandler
    file_handler = StreamHandler(sys.stderr)
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

if __name__ == '__main__':
    app.run('0.0.0.0', 0x1F11, debug=True) # 7953
