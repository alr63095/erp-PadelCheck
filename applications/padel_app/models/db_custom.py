from datetime import datetime



db.define_table('dim_padel_club', 
    Field('name'),
    Field('description'), 
    Field('pistas'), 
    Field('ciudad'),
    Field('horario'),
)

db.define_table('dim_tercero',
    Field('name'),
    Field('description'),
    Field('disabled'),
)
db.define_table('man_tickets',
    Field('user_id'),
    Field('tercero_id'),
    Field('f_creation'),
    Field('f_last_update'),
    Field('user_last_update'),
    Field('id_amdocs'),
    Field('id_file'),
)
db.define_table('view_valores_defecto',
    Field('id_tercero'),
    Field('id_parameter'),
    Field('valor'),
    Field('valores'),
)
db.define_table('conf_user_linked_tercero',
    Field('id_user'),
    Field('id_tercero'),
)
db.define_table('ctrl_user_events',
    Field('user_id'),
    Field('client_ip'),
    Field('client_agent'),
    Field('f_event'),
    Field('event_user'),
)
db.define_table('ctrl_user_access',
    Field('user_id'),
    Field('f_access'),
    Field('device_hash'),
)