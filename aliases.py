from tinydb import TinyDB, Query

_db = TinyDB('/home/kenzie/mattermost/db-aliases.json')

# DB setup is simple.
# Each entry contains a mappings from ident -> aliases { "ident": "<id>", "aliases": [ { "name": "<alias>" } ] }
# If none exists, use the alias as the new ident and that's it
def create_ident(alias):
    return "ident!" + alias

def resolve_to_identifier(pot_alias):
    # First, find any matches as the alias
    matches = _db.search(Query().aliases.any(Query().name == pot_alias))
    assert len(matches) < 2, "too many matches for " + pot_alias
    if matches:
        # Got the ID
        return matches[0]['ident']
    # Nothing in the DB. Set it up.
    ident = create_ident(pot_alias)
    _db.insert({"ident": ident, "aliases": [{"name": pot_alias}]})
    return ident

def add_alias(ident, alias):
    ident_query = Query().ident == ident
    if not _db.contains(ident_query):
        return "No such identifier " + ident
    def transform_add_alias(entry):
        entry['aliases'].append({"name": alias})
    _db.update(transform_add_alias, ident_query)
    return "Added alias {} to {}".format(alias, ident)

def merge_ident(i_from, i_to):
    Ident = Query()
    if not _db.contains(Ident.ident == i_from) or not _db.contains(Ident.ident == i_to):
        return "One of the idents does not exist: {} or {}".format(i_from, i_to)
    ident_from_data = _db.get(Ident.ident == i_from)
    def transform_add_aliases(entry):
        entry['aliases'] += ident_from_data['aliases']
    _db.update(transform_add_aliases, Ident.ident == i_to)
    _db.remove(Ident.ident == i_from)
    return "Merged {} into {}".format(i_from, i_to)

