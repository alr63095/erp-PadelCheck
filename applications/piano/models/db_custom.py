from datetime import datetime


db.define_table('conf_data_linked_tercero',
    Field('id_parameter_parent'),
    Field('id_parameter_child'),
)

db.define_table('conf_data_parameter_tercero',
    Field('id_tercero'),
    Field('id_parameter'),
    Field('valor'),
)

db.define_table('conf_parameter_tercero',
    Field('id_tercero'),
    Field('id_parameter'),
    Field('visible'),
    Field('editable'),
)

db.define_table('ctrl_process_update',
    Field('f_update'),
    Field('datos'),
    Field('n_tickets_proc'),
)

db.define_table('det_tickets_amdocs',
    Field('id_amdocs'),
    Field('json_data'),
    Field('status'),
    Field('cola'),
    Field('f_last_update'),
)

db.define_table('det_tickets_amdocs_his',
    Field('id_amdocs'),
    Field('json_data'),
    Field('status'),
    Field('cola'),
    Field('f_last_update'),
)

db.define_table('det_tickets_create',
    Field('id_ticket'),
    Field('id_parameter'),
    Field('valor'),
)

db.define_table('det_tickets_update',
    Field('id_ticket'),
    Field('comentario'),
    Field('f_update'),
    Field('user_id'),
    Field('id_file'),
)

db.define_table('dim_datatype',
    Field('name'),
    Field('tipo'),
    Field('subtype'),
)

db.define_table('dim_parameter', 
    Field('name'),
    Field('description'), 
    Field('id_datatype'), 
    Field('orden'),
    Field('disabled'),
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
db.define_table('det_files_ticket',
    Field('filename'),
    Field('contenido'),
    Field('tipo'),
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