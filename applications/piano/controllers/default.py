# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
# This is a sample controller
# this file is released under public domain and you can use without limitations
# -------------------------------------------------------------------------

# ---- example index page ----
from contextlib import closing
from datetime import datetime
from os import remove
import shutil
import base64
import json
from datetime import timedelta
import requests
import os
import mimetypes
import pytz
import logging

@auth.requires_login()
def index():
    """
    Carga la pagina de entrada de la aplicacion, tambien accesible desde el menu desplegable "Dashboard"
    Se realiza una consulta a BBDD para cargar el resumen de la vista de los tickets abiertos y cerrados
    Se realiza otra consulta para recaudar la informacion referente a un ticket, para rellenar la tabla 

    return: 
        la información para crear el resument
        la informacion para crear la tabla de tickets del inicio 
    """
    try:
        tickets = []
        all_tickets = []
        resumen = {}
        userEmail = auth.user.email
        idTercero = db.conf_user_linked_tercero(db.conf_user_linked_tercero.id_user == auth.user.id).id_tercero
        nameTercero = db.dim_tercero(db.dim_tercero.id == idTercero).name
        usersTercero = db(db.conf_user_linked_tercero.id_tercero == idTercero).select(db.conf_user_linked_tercero.id_user)
        resumen['user'] = userEmail  
        resumen['tercero'] = nameTercero
        contadorcategory = {}
        lista_estados_abiertos = "ABIERTO#EN CURSO#PENDIENTE"
        lista_estados_cerrados = "CERRADO#CANCELADO#SOLUCIONADO"
        idParameter = db.dim_parameter(db.dim_parameter.name == 'category').id
        categorizations = db(db.view_valores_defecto.id_tercero == idTercero)(db.view_valores_defecto.id_parameter == idParameter).select()
        for cat in categorizations:   #valor de la categoria -> CORE O SEREVICES #valor de las colas asociadas -> ANOC O OYM
            contadorcategory[cat['valor']] = {}
            contadorcategory[cat['valor']]['open'] = 0
            contadorcategory[cat['valor']]['close'] = 0
               
        for i in usersTercero:
            contadores = db((db.man_tickets.id == db.det_tickets_create.id_ticket) & (db.man_tickets.user_id == i.id_user) & (db.man_tickets.id_amdocs == db.det_tickets_amdocs.id_amdocs) & (db.det_tickets_create.id_parameter == idParameter)).select()
            for row in contadores: 
                if(row.det_tickets_amdocs and row.det_tickets_amdocs.status.upper() in lista_estados_abiertos):
                    contadorcategory[row.det_tickets_create.valor]['open'] += 1
                elif row.det_tickets_amdocs and row.det_tickets_amdocs.status.upper() in lista_estados_cerrados:
                    contadorcategory[row.det_tickets_create.valor]['close'] += 1
            ticketsUser = db(db.man_tickets.user_id == i.id_user).select().as_list()
            tickets.extend(ticketsUser)
        for t in tickets:
            ticket = {}
            ticket_info = db(db.det_tickets_create.id_ticket == t['id'])(db.det_tickets_create.id_parameter == db.dim_parameter.id).select()
            if ticket_info:
                for i in ticket_info:
                    ticket[i.dim_parameter.name] = i.det_tickets_create.valor
            if not ticket.get('status'):
                ticket['status'] = ""
            status = db(db.man_tickets.id_amdocs == db.det_tickets_amdocs.id_amdocs)(db.man_tickets.id == t['id']).select()
            if status:
                ticket['status'] = status[0]['det_tickets_amdocs']['status']
            if not ticket.get('category'):
                ticket['category'] = ""
            ticket['id_amdocs'] = t['id_amdocs']
            ticket['id'] = t['id']
            ticket['user'] = db.auth_user(db.auth_user.id==t['user_id']).email
            ticket['user_id'] = db.auth_user(db.auth_user.id==t['user_id']).id
            ticket['user_act'] = auth.user.id # usuario actual
            ticket['f_creation'] = t['f_creation']
            ticket['f_last_update'] = t['f_last_update']
            if t['id_file']:
                attachment = db.det_files_ticket(db.det_files_ticket.id == t['id_file'])   
                ticket['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
            all_tickets.append(ticket)
        tickets_json = json.dumps(all_tickets, default=str)
        contadores_json = json.dumps(contadorcategory, default=str)
        resumen_json = json.dumps(resumen, default=str)
        control_user_events(request,"Entrando a Vista Tickets",auth.user.id)
        return dict(results=XML(tickets_json),resumen=XML(resumen_json),estados=XML(contadores_json))
    except Exception as e:
        logging.error(f'Error: {e}')

@auth.requires_login()
def newTicket():
    """
    Funcion del controlador de la vista encargada de crear los tickets
    Se comprueba el tercero al que pertenece el usuario si esta derhabilitado y se hace una consulta
    en BBDD para ver los parametros necesarios para la creacion de el formulario de creación de un ticket

    return:
        el formulario de creacion de un ticket
    """
    try:
        idTercero = db.conf_user_linked_tercero(db.conf_user_linked_tercero.id_user == auth.user.id).id_tercero
        rowTercero = db.dim_tercero(db.dim_tercero.id == idTercero)
        if (rowTercero['disabled'] == 1):
            return False  #to-do cuando esta desactivado el tercero
        idTercero = rowTercero['id']
        visibleParameters = db((db.conf_parameter_tercero.id_tercero==idTercero) & (db.conf_parameter_tercero.id_parameter == db.dim_parameter.id) & (db.dim_parameter.disabled == 0)).select(orderby=db.dim_parameter.orden)
        paramType = {}
        paramLabels = {}
        paramVisble = {}
        for param in visibleParameters:
            paramValues = []
            paramVisble[param.dim_parameter.name] = param.conf_parameter_tercero.visible
            valores = db((db.conf_data_parameter_tercero.id_tercero==idTercero) & (db.conf_data_parameter_tercero.id_parameter == param.dim_parameter.id)).select()
            datatype = db.dim_datatype(db.dim_datatype.id == param.dim_parameter.id_datatype)
            values = [v for v in valores]
            paramValues.append(datatype)
            paramValues.append(values)
            paramType[param.dim_parameter.name] = paramValues
            if(param.conf_parameter_tercero.visible == 1):
                paramLabels[param.dim_parameter.name] = param.dim_parameter.description         
            
        fields = []
        for field in paramType:
            if(paramVisble[field] == 1):
                if(len(paramType[field][1])>0):
                    if('set' in paramType[field][0].subtype):
                        setValues = [v.valor for v in paramType[field][1]]
                        if('category' in field):
                            f = Field(field,type=paramType[field][0].tipo,required=True,requires=IS_IN_SET(setValues),default=paramType[field][1][0].valor,readonly=True,widget = lambda field, value: SQLFORM.widgets.radio.widget(field, value, _class='radio-ticket'))
                        elif(len(paramType[field][1]) == 1):
                            f = Field(field,type=paramType[field][0].tipo,required=True,requires=IS_IN_SET(setValues),default=paramType[field][1][0].valor,readonly=True,widget = lambda field, value: SQLFORM.widgets.options.widget(field, value, _class='combo-ticket'))
                        elif(len(paramType[field][1]) > 1):
                            f = Field(field,type=paramType[field][0].tipo,required=True,requires=IS_IN_SET(setValues),default=paramType[field][1][0].valor,readonly=True,widget = lambda field, value: SQLFORM.widgets.options.widget(field, value, _class='combo-ticket',))
                    else:
                        f = Field(field,type=paramType[field][0].tipo,required=True,default=paramType[field][1][0].valor,widget = lambda field, value: SQLFORM.widgets.string.widget(field, value, _class='texto-ticket',))
                else:
                    if('datetime' in paramType[field][0].tipo):
                        f = Field(field,type=paramType[field][0].tipo,required=True,default=datetime.now(),)
                    else:
                        f = Field(field,type=paramType[field][0].tipo)    
            fields.append(f)
            
        form = SQLFORM.factory(*fields,labels=paramLabels,buttons=[BUTTON(T('Create Ticket'), _class="btn-primary btn center boton-ticket", _type="submit")])
        control_user_events(request,"Entrando a Vista Creacion Tickets",auth.user.id)
        result = {}
        resultado = json.dumps(result,default=str)
        if form.process().accepted:
            response.flash = 'form accepted'
            if len(form.vars.attachment) > 0:
                result = create_new_ticket(form.vars,paramType,request.vars.attachment.filename)
            else:
                result = create_new_ticket(form.vars,paramType)
            resultado = json.dumps(result,default=str)
        elif form.errors:
            response.flash = 'form has errors'
        else:
            response.flash = 'please fill out the form'
        return dict(form=form,resultado=XML(resultado))
    except Exception as e:
        logging.error(f'Error: {e}')

@auth.requires_login()
def worklog():
    """
    Funcion del controlador de la vista encargada de mostrar los detalle de creacion de un ticket
    Tambien muestra una tabla donde el usuario introduce comentarios y es posible leerlos por completo
    mediante un modal adicional
    Se consulta a bbdd los detalles de la creacion de un ticket para pasarlos a la vista,
    ademas de los comentarios realizados para este.
    
    return:
        la lista de comentarios asociados a el ticket, para formar la tabla
        la informacion relacionada con la creacion de un ticket
    """
    try:
        user_email = request.vars.user
        user_act = auth.user.id
        id_ticket = request.vars.id_ticket
        ticket = getTicketInfo(id_ticket) #posible refactorizacion 
        ticket['id'] = id_ticket
        ticket['user'] = user_email
        ticket['user_act'] = user_act
        t = db.man_tickets(id_ticket)
        if t:
            ticket['id_amdocs'] = t['id_amdocs']
            ticket['user_id'] = db.auth_user(db.auth_user.id==t['user_id']).id
            ticket['f_creation'] = t['f_creation']
            ticket['f_last_update'] = t['f_last_update']
            if t['id_file']:
                attachment = db.det_files_ticket(db.det_files_ticket.id == t['id_file'])   
                ticket['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
        comments = db(db.det_tickets_update.id_ticket == id_ticket).select()
        all_comments = []
        for comment in comments:
            comentario = {}
            comentario['user'] = db.auth_user(db.auth_user.id == comment.user_id).email
            comentario['comment'] = comment.comentario
            comentario['date'] = comment.f_update
            if comment.id_file:
                attachment = db.det_files_ticket(db.det_files_ticket.id == comment.id_file)   
                comentario['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
            all_comments.append(comentario)

        comments_json = json.dumps(all_comments, default=str)
        ticket_json = json.dumps(ticket, default=str)
        control_user_events(request,f"Entrando a Vista detalles Ticket: {ticket['id_amdocs']}",auth.user.id)
        return dict(results=XML(comments_json),ticket=XML(ticket_json))
    except Exception as e:
        logging.error(f'Error: {e}')


def reloadTickets():
    idTicket = request.vars.id_amdocs
    user_id = request.vars.id_user
    ticket = {}
    #para produccion
    #hacemos la consulta del ticket y traemos el estado actual de este
    try:
        data = create_smart_connect(ticket="",idTicket=idTicket)
        if data and 'amd_tickets' in data and data['amd_tickets']:
            amd_tickets = data['amd_tickets'] 
            estadoTicket = amd_tickets[0].get('estado_ticket')   
        else:
            estadoTicket = None
    except Exception as e:
        logging.error(f'Error: {e}')
    #estadoTicket = "Abierto"  #valido para local
    lastStatus = db.det_tickets_amdocs(db.det_tickets_amdocs.id_amdocs == idTicket)##buscar en bd por el idamdocs y coger el estado si es distinto actualizamos
    if estadoTicket and lastStatus:
        if estadoTicket.upper() not in lastStatus.status.upper():
            row = db.det_tickets_amdocs(lastStatus.id) 
            row.status = estadoTicket.capitalize()
            row.update_record()
    #volvemos a cargar la tabla principal
    tickets = []
    all_tickets = []
    idTercero = db.conf_user_linked_tercero(db.conf_user_linked_tercero.id_user == user_id).id_tercero
    usersTercero = db(db.conf_user_linked_tercero.id_tercero == idTercero).select(db.conf_user_linked_tercero.id_user)
    contadorcategory = {}
    lista_estados_abiertos = "ABIERTO#EN CURSO#PENDIENTE"
    lista_estados_cerrados = "CERRADO#CANCELADO#SOLUCIONADO"
    idParameter = db.dim_parameter(db.dim_parameter.name == 'category').id
    categorizations = db(db.view_valores_defecto.id_tercero == idTercero)(db.view_valores_defecto.id_parameter == idParameter).select()
    for cat in categorizations:   #valor de la categoria -> CORE O SEREVICES #valor de las colas asociadas -> ANOC O OYM
        contadorcategory[cat['valor']] = {}
        contadorcategory[cat['valor']]['open'] = 0
        contadorcategory[cat['valor']]['close'] = 0
    for i in usersTercero:
        contadores = db((db.man_tickets.id == db.det_tickets_create.id_ticket) & (db.man_tickets.user_id == i.id_user) & (db.man_tickets.id_amdocs == db.det_tickets_amdocs.id_amdocs) & (db.det_tickets_create.id_parameter == idParameter)).select()
        for row in contadores: 
            if(row.det_tickets_amdocs and row.det_tickets_amdocs.status.upper() in lista_estados_abiertos):
                contadorcategory[row.det_tickets_create.valor]['open'] += 1
            elif row.det_tickets_amdocs and row.det_tickets_amdocs.status.upper() in lista_estados_cerrados:
                contadorcategory[row.det_tickets_create.valor]['close'] += 1
        ticketsUser = db(db.man_tickets.user_id == i.id_user).select().as_list()
        tickets.extend(ticketsUser)
    for t in tickets:
        ticket = {}
        ticket_info = db(db.det_tickets_create.id_ticket == t['id'])(db.det_tickets_create.id_parameter == db.dim_parameter.id).select()
        if ticket_info:
            for i in ticket_info:
                ticket[i.dim_parameter.name] = i.det_tickets_create.valor
        if not ticket.get('status'):
            ticket['status'] = ""
        status = db(db.man_tickets.id_amdocs == db.det_tickets_amdocs.id_amdocs)(db.man_tickets.id == t['id']).select()
        if status:
            ticket['status'] = status[0]['det_tickets_amdocs']['status']
        if not ticket.get('category'):
            ticket['category'] = ""
        ticket['id_amdocs'] = t['id_amdocs']
        ticket['id'] = t['id']
        ticket['user'] = db.auth_user(db.auth_user.id==t['user_id']).email
        ticket['user_id'] = db.auth_user(db.auth_user.id==t['user_id']).id
        ticket['user_act'] = user_id # usuario actual
        ticket['f_creation'] = t['f_creation']
        ticket['f_last_update'] = t['f_last_update']
        if t['id_file']:
            attachment = db.det_files_ticket(db.det_files_ticket.id == t['id_file'])   
            ticket['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
        all_tickets.append(ticket)
    # tickets_json = json.dumps(all_tickets, default=str)
    # contadores_json = json.dumps(contadorcategory, default=str)
    #return dict(results=XML(tickets_json),estados=XML(contadores_json))
    response = {}
    response['tickets'] = all_tickets
    response['contadores'] = contadorcategory
    return json.dumps(response,default=str)
    
# ---- API (example) -----
@auth.requires_login()
def api_get_user_email():
    if not request.env.request_method == 'GET': raise HTTP(403)
    return response.json({'status':'success', 'email':auth.user.email})

# ---- Smart Grid (example) -----
@auth.requires_membership('admin') # can only be accessed by members of admin groupd
def grid():
    response.view = 'generic.html' # use a generic view
    tablename = request.args(0)
    if not tablename in db.tables: raise HTTP(403)
    grid = SQLFORM.smartgrid(db[tablename], args=[tablename], deletable=False, editable=False)
    return dict(grid=grid)

# ---- Embedded wiki (example) ----
def wiki():
    auth.wikimenu() # add the wiki to the menu
    return auth.wiki() 

# ---- Action for login/register/etc (required for auth) -----
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    user = None
    event = ""
    if "logout" in request.wsgi.environ['REQUEST_URI']:
        user = auth.user.id
        event = f"Usuario: {auth.user.email} saliendo de la aplicacion"
    if "login" in request.wsgi.environ['REQUEST_URI']:
        if len(request.post_vars) > 0:
            event = f"Entrando usuario {request.post_vars.email} en la aplicacion"
    if "register" in request.wsgi.environ['REQUEST_URI']:
        if len(request.post_vars) > 0: 
            event = f"Registrando usuario {request.post_vars.email} en la aplicacion"
    if event:
        control_user_events(request,event,user_act=user)
    return dict(form=auth())

# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)

def create_new_ticket(fields,paramType,filename = None):
    """
    Función llamada desde la vista de creacion del ticket, la cual mediante los parametros del formulario
    y otros obtenidos directamente desde base de datos proporcionados a la vista, rellenamos los detalle de creacion del ticket
    y se realiza la llamada a la funcion que conectara con smart con el json generado
    Tambien tratamos los parametros linkados, ya que hay valores que son seleccionados en funcion de el valor de otro parametro,
    como por ejemplo la cola de smart. 
    """
    try:
        if(fields['description']):
            fields['description'] = fields['description'].replace("\\r","").replace("\\n","").replace("\\f","").replace("\\b","").replace("\\t","").replace("\\u","")
            fields['description'] = fields['description'].replace("\\","").replace("'","").replace('"','')
        result = {}
        id_values = {}
        paramValues = {}
        parameters = db(db.dim_parameter.disabled == 0).select()
        tercero_id = paramType['category'][1][0].id_tercero
        tercero_name = db.dim_tercero(db.dim_tercero.id == tercero_id).name
        for p in parameters:
            if p.name in fields:
                if p.name == 'attachment' and filename:
                    id_values[p.id] = "attachment" 
                else:
                    id_values[p.id] = fields[p.name]
                    paramValues[p.name] = fields[p.name]
                parametro_id = p.id
                valor_parametro = id_values[p.id]
                query = db(db.view_valores_defecto.id_tercero == tercero_id)(db.view_valores_defecto.id_parameter == parametro_id)(db.view_valores_defecto.valor == valor_parametro).select()
                if query and query[0].valores:
                    valores = query[0].valores.split('#_#')
                    for valor in valores:
                        id_value = valor.split('@_@')
                        id_values[int(id_value[0])] = id_value[1]
                        child_parameter = next((item for item in parameters if item['id']==int(id_value[0])),None)
                        if child_parameter:
                            paramValues[child_parameter.name] = id_value[1]
            else:
                if paramType[p.name] and p.name not in paramValues.keys():
                    if paramType[p.name][1]:
                        paramValues[p.name] = paramType[p.name][1][0].valor
                        id_values[p.id] = paramType[p.name][1][0].valor
                    else:
                        paramValues[p.name] = ""
                        id_values[p.id] = ""

        decoded_attachment = ''
        if(filename):
            ENCODING = "utf-8"
            filepath = os.path.join(request.folder, 'uploads', fields.attachment)
            with open(filepath, 'rb') as f:
                encoded_attachment = base64.b64encode(f.read())
            decoded_attachment = encoded_attachment.decode(ENCODING)
            typeFile = mimetypes.guess_type(filename)[0]
        else:
            filename = ""
        timezone = pytz.timezone('Europe/Madrid')
        fecha_act = timezone.localize(datetime.now()).isoformat()
        ticket = {}
        if filename:
            idFile = db.det_files_ticket.insert(filename= filename,contenido = decoded_attachment,tipo=typeFile)
            id_man = db.man_tickets.insert(user_id = auth.user.id,tercero_id=tercero_id,f_creation = paramValues['f_discovered'],f_last_update=datetime.now(),
                                    user_last_update=auth.user.id,id_file=idFile)
        else:
            id_man = db.man_tickets.insert(user_id = auth.user.id,tercero_id = tercero_id,f_creation = paramValues['f_discovered'],f_last_update=datetime.now(),
                                    user_last_update=auth.user.id,)
        for idparam in id_values:
            if id_values[idparam] == "attachment":
                db.det_tickets_create.insert(id_ticket=id_man,id_parameter=idparam,valor=idFile)
            else: 
                db.det_tickets_create.insert(id_ticket=id_man,id_parameter=idparam,valor=id_values[idparam]) 
        
        ticket['IncidentVBO'] = {}
        ticket['IncidentVBO']['Details'] = {}
        ticket['IncidentVBO']['Details']['SeverityCode'] = paramValues['severity']
        ticket['IncidentVBO']['Details']['AlertRequestInd'] = paramValues['alert_request_ind']
        ticket['IncidentVBO']['Details']['ImpactCode'] = paramValues['impact_code']
        ticket['IncidentVBO']['Details']['UrgencyCode'] = paramValues['urgency']
        ticket['IncidentVBO']['IDs'] = {}
        ticket['IncidentVBO']['IDs']['ID'] = f"PIANO_{str(id_man)}"
        ticket['IncidentVBO']['Type'] = 'Red'
        ticket['IncidentVBO']['Name'] = f"#OMV_<{tercero_name}>#{paramValues['name']}"
        ticket['IncidentVBO']['Desc'] = paramValues['description']
        ticket['IncidentVBO']['Status'] = paramValues['status']
        ticket['IncidentVBO']['Roles'] = {}
        ticket['IncidentVBO']['Roles']['Assignee'] = {}
        ticket['IncidentVBO']['Roles']['Assignee']['AssignedToGroup'] = {}
        ticket['IncidentVBO']['Roles']['Assignee']['AssignedToGroup']['NameText'] = paramValues['pool_smart']
        ticket['IncidentVBO']['Roles']['Assignee']['Name'] = 'crm_heimdall'
        ticket['IncidentVBO']['Roles']['Assignee']['Desc'] = 'crm_heimdall'
        ticket['IncidentVBO']['Roles']['Requester'] = {}
        ticket['IncidentVBO']['Roles']['Requester']['Name'] = 'crm_heimdall'
        ticket['IncidentVBO']['Parts'] = {}
        ticket['IncidentVBO']['Parts']['Impact'] = []
        ticket['IncidentVBO']['Parts']['Impact'].append(['actionCode', 'EnvironmentalImpact', 'No'])
        ticket['IncidentVBO']['Parts']['Impact'].append(['actionCode', 'RiskJob', 'No'])
        ticket['IncidentVBO']['Parts']['Cause'] = {}
        ticket['IncidentVBO']['Parts']['Cause']['Desc'] = 'No'
        ticket['IncidentVBO']['Parts']['Cause']['Name'] = fecha_act
        # ticket['IncidentVBO']['Parts']['ServiceLevel'] = {}
        # ticket['IncidentVBO']['Parts']['ServiceLevel']['EstimatedOnholdDateTime'] = ""
        # ticket['IncidentVBO']['Parts']['ServiceLevel']['EstimatedCloseDateTime'] = ""
        # ticket['IncidentVBO']['Parts']['ServiceLevel']['RequestedResolutionDateTime'] = '' #FECHA
        # ticket['IncidentVBO']['Parts']['ServiceLevel']['RequestedResponseDateTime'] = '' #FECHA
        ticket['IncidentVBO']['Parts']['Symptom'] = {}
        ticket['IncidentVBO']['Parts']['Symptom']['DiscoveredDateTime'] = paramValues['f_discovered'].astimezone(timezone).isoformat()
        ticket['IncidentVBO']['Parts']['Resources'] = {}
        ticket['IncidentVBO']['Parts']['Resources']['Resource'] = {}
        ticket['IncidentVBO']['Parts']['Resources']['Resource']['IDs'] = {}
        ticket['IncidentVBO']['Parts']['Resources']['Resource']['IDs']['ID'] = []
        ticket['IncidentVBO']['Parts']['Resources']['Resource']['IDs']['ID'].append(['schemeName', 'ID', 'CDR-GENERICO'])
        ticket['IncidentVBO']['Parts']['Resources']['Resource']['Type'] = 'FIVF'
        ticket['IncidentVBO']['Parts']['IncidentSites'] = {}
        ticket['IncidentVBO']['Parts']['IncidentSites']['IncidentSite'] = {}
        ticket['IncidentVBO']['Parts']['IncidentSites']['IncidentSite']['IDs'] = {}
        ticket['IncidentVBO']['Parts']['IncidentSites']['IncidentSite']['IDs']['ID'] = paramValues['incident_site']
        ticket['IncidentVBO']['Parts']['Attachments'] = {}
        ticket['IncidentVBO']['Parts']['Attachments']['Attachment'] = {}
        ticket['IncidentVBO']['Parts']['Attachments']['Attachment']['Name'] = filename
        ticket['IncidentVBO']['Parts']['Attachments']['Attachment']['BinaryObject'] = decoded_attachment
        ticket['IncidentVBO']['Categories'] = {}
        ticket['IncidentVBO']['Categories']['Category'] = []
        ticket['IncidentVBO']['Categories']['Category'].append(['listName', 'RequestType', 'Vodafone'])
        ticket['IncidentVBO']['Categories']['Category'].append(['listName','OperationalCategorization1',paramValues['categorization']])
        ticket['IncidentVBO']['Version'] = '0'
        ticket['IncidentVBO']['ValidityPeriod'] = {}
        ticket['IncidentVBO']['ValidityPeriod']['FromDate'] = fecha_act
        ticket['IncidentVBO']['ValidityPeriod']['ToDate'] = (datetime.now() + timedelta(days=90)).astimezone(timezone).isoformat()
        json_ticket = str(ticket).replace("'","''")
        json_ticket = json_ticket.replace(r"\n", r"\\\n")
        call = {}
        call['X_IDTICKET'] = 'CRQAPIREST'
        call['X_USUARIO'] = 'PIANO'
        call['X_LLAMADA'] = json_ticket
        call['X_METODO'] = 'Create'     
        call['X_ENTORNO'] = 'PROD'     
        call['X_ORIGEN'] = 'PIANO'  
        call_json = json.dumps(call)
        smart_response = create_smart_connect(call_json)
        if smart_response and 'X_ESTADO' in smart_response and smart_response['X_ESTADO'] == 'PDTE APROBAR':    #EN PROD: PROCESADO
            # Para control de huerfanos mirar campo X_LLAMADA y ver campo ['IncidentVBO']['IDS']['ID'] y split('_')[1] para ver el id de man_tickets, actualizar id_amdocs
            db.det_tickets_amdocs.insert(id_amdocs=smart_response['X_IDTICKET'],json_data=smart_response['X_LLAMADA'],status="Abierto",cola=paramValues['pool_smart'],f_last_update=datetime.now(),)
            row = db.man_tickets(id_man) 
            row.id_amdocs = smart_response['X_IDTICKET']
            row.update_record()
            control_user_events(request,f"Se crea un Ticket con id: {smart_response['X_IDTICKET']}",auth.user.id)
            result['procesado'] = True
            result['resultado'] = smart_response['X_IDTICKET']
            print(smart_response['X_IDTICKET'])
        else:
            result['procesado'] = False
            result['resultado'] = "Error durante la creacion del ticket"
        return result
    except Exception as e:
        logging.error(f'Error: {e}')


def modifyTir():
    """
    Función llamada desde la vista del worklog, la cual se utiliza para añadir comentarios 
    a un ticket existente en Smart.

    return:
        la lista de comentarios para actualizar el nuevo sobre la tabla
    """
    try:
        id_amdocs = request.vars.id_amdocs
        id_ticket = request.vars.id_ticket
        user_id = request.vars.user_act
        comment = request.vars.comment
        idFile = None
        if (request.vars.attachment):
            attachment = json.loads(request.vars.attachment)
            idFile = db.det_files_ticket.insert(filename= attachment['name'],contenido = attachment['base64'],tipo=attachment['type'])
        else:
            attachment = ""

        data = {}
        data['IncidentVBO'] = {}
        data['IncidentVBO']['IDs']={}
        data['IncidentVBO']['IDs']['ID'] = id_amdocs
        data['IncidentVBO']['Parts'] = {}
        data['IncidentVBO']['Parts']['WorkLog']={}
        data['IncidentVBO']['Parts']['WorkLog']['WorkInfo']={}
        data['IncidentVBO']['Parts']['WorkLog']['WorkInfo']['Desc'] = comment
        if attachment:
            data['IncidentVBO']['Parts']['Attachments'] = {}
            data['IncidentVBO']['Parts']['Attachments']['Attachment'] = {}
            data['IncidentVBO']['Parts']['Attachments']['Attachment']['Name'] = attachment['name']
            data['IncidentVBO']['Parts']['Attachments']['Attachment']['BinaryObject'] = attachment['base64']
        data['IncidentVBO']['Roles'] ={}
        data['IncidentVBO']['Roles']['Assignee']={}
        data['IncidentVBO']['Roles']['Assignee']['Name']="crm_heimdall"
        data['IncidentVBO']['Roles']['Assignee']['Desc']="crm_heimdall"
        data['IncidentVBO']['Roles']['Requester'] = {}
        data['IncidentVBO']['Roles']['Requester']['Name']="crm_heimdall"
        json_ticket = str(data).replace("'","''")
        json_ticket = json_ticket.replace(r"\n", r"\\\n")
        call = {}
        call['X_IDTICKET'] = 'CRQAPIREST'
        call['X_USUARIO'] = 'PIANO'
        call['X_LLAMADA'] = json_ticket
        call['X_METODO'] = 'Update'     
        call['X_ENTORNO'] = 'PROD'     
        call['X_ORIGEN'] = 'PIANO'  
        call_json = json.dumps(call)
        smart_response = create_smart_connect(call_json)
        comment_list = []
        if smart_response and 'X_ESTADO' in smart_response and smart_response['X_ESTADO'] == 'PDTE APROBAR':    #EN PROD: PROCESADO
            if idFile:
                db.det_tickets_update.insert(id_ticket=id_ticket,comentario=comment,f_update=datetime.now(),user_id=user_id,id_file=idFile)    
            else:
                db.det_tickets_update.insert(id_ticket=id_ticket,comentario=comment,f_update=datetime.now(),user_id=user_id)    
        comment_list = getstrWorkLog(id_ticket) 
        comments_json = json.dumps(comment_list,default=str)
        if idFile:
            event = f"Añadiendo fichero con id: {idFile} al ticket con ID Amdocs: {id_amdocs}. (Comentario: {comment})"
        else:
            event = f"Añadiendo comentario al ticket con ID Amdocs: {id_amdocs}. (Comentario: {comment})"
        control_user_events(request,event,user_id)
        return comments_json
    except Exception as e:
        logging.error(f'Error: {e}')

def create_smart_connect(ticket = None,idTicket = None):
    """
    Funcion utilizada para realizar la conexion con smart, devulve el resultado de esta conexión

    return:
        el json de respuesta de smart despues de hacer la solicitud de creacion o modificacion
    """
    SMART_URL="https://137.116.240.44:5005/"
    SMART_USER="admin"
    SMART_PASSWORD="admin"
    urlLogin = f'{SMART_URL}login'
    urlConector = f'{SMART_URL}conector'
    try:
        response = requests.post(urlLogin,  
                auth=(SMART_USER, SMART_PASSWORD),
                timeout=10,
                verify=False)
        respuesta = json.loads(response.text) 
        token = respuesta.get('token')
        if not token:
            print(respuesta.get('message'))
            return False
        if not idTicket:
            headers = {'Content-type':'application/json', 'Accept':'application/json','x-access-tokens':token}
            response = requests.post(urlConector,
                    verify=False,
                    timeout=10,
                    data = ticket,
                    headers = headers)
        else:
            headers = {'x-access-tokens':token}
            urlConector = f'{SMART_URL}consulta/{idTicket}'
            response = requests.get(urlConector,
                verify=False,
                timeout=10,
                headers = headers)
        json_response = json.loads(response.text)
        ticket_data = json_response.get('data')
        if not ticket_data:
            print(json_response.get('message'))
            return False
        response.close()
        return ticket_data[0]
    except Exception as e:
        logging.error(f'Smart access failed: {e}')
        return False

def getstrWorkLog(id_ticket):
    """
    Función utilizada para obtener los comentarios de un ticket almacenados en bbdd 

    Parameters:
        id_ticket : id del ticket a buscar sus comentarios

    return:
        lista de comentarios asociados al ticket indicado

    """
    comments = db(db.det_tickets_update.id_ticket == id_ticket).select()
    all_comments = []
    for comment in comments:
        comentario = {}
        user = db.auth_user(comment.user_id).email
        comentario['user'] = user
        comentario['comment'] = comment.comentario
        comentario['date'] = comment.f_update
        if comment.id_file:
            attachment = db.det_files_ticket(db.det_files_ticket.id == comment.id_file)   
            comentario['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
        all_comments.append(comentario)
        
    return all_comments

def getTicketInfo(id_ticket):
    """
    obtenemos toda la informacion relacionada con la creacion de un ticket

    parameters:
        id_ticket: identificador del tickjet del que obtener informacion en bbdd
    
    return:
        devuelve un diccionadio con todos los parametros de creacion del ticket
    """
    ticket = {}
    ticket_info = db(db.det_tickets_create.id_ticket == id_ticket)(db.det_tickets_create.id_parameter == db.dim_parameter.id).select()
    if ticket_info:
        for i in ticket_info:
            ticket[i.dim_parameter.name] = i.det_tickets_create.valor
    return ticket

@auth.requires_login()
def graphs():
    try:
        tickets = db(db.man_tickets).select().as_list()
        all_tickets = []
        for t in tickets:
            ticket = {}
            ticket_info = db(db.det_tickets_create.id_ticket == t['id'])(db.det_tickets_create.id_parameter == db.dim_parameter.id).select()
            if ticket_info:
                for i in ticket_info:
                    ticket[i.dim_parameter.name] = i.det_tickets_create.valor
            if not ticket.get('status'):
                ticket['status'] = ""
            status = db(db.man_tickets.id_amdocs == db.det_tickets_amdocs.id_amdocs)(db.man_tickets.id == t['id']).select()
            if status:
                ticket['status'] = status[0]['det_tickets_amdocs']['status']
            if not ticket.get('category'):
                ticket['category'] = ""
            ticket['id_amdocs'] = t['id_amdocs']
            ticket['id'] = t['id']
            ticket['user'] = db.auth_user(db.auth_user.id==t['user_id']).email
            ticket['user_id'] = db.auth_user(db.auth_user.id==t['user_id']).id
            idTercero = db.conf_user_linked_tercero(db.conf_user_linked_tercero == ticket['user_id'])
            ticket['user_act'] = auth.user.id # usuario actual
            ticket['f_creation'] = t['f_creation']
            ticket['f_last_update'] = t['f_last_update']
            if t['id_file']:
                attachment = db.det_files_ticket(db.det_files_ticket.id == t['id_file'])   
                ticket['attachment'] = {'filename': attachment['filename'], 'content': attachment['contenido'], 'type':attachment['tipo']}
            all_tickets.append(ticket)
        users_events = db((db.ctrl_user_events.user_id == db.auth_user.id) & (db.conf_user_linked_tercero.id_user == db.auth_user.id) & (db.conf_user_linked_tercero.id_tercero == db.dim_tercero.id)).select(db.ctrl_user_events.ALL,db.auth_user.email,db.auth_user.id,db.dim_tercero.name).as_list()
        all_events = []
        for event in users_events:
            event_dict = {}
            user_name = event['auth_user']['email']
            if user_name:
                event_dict['user'] = user_name
            else:
                event_dict['user'] = ""
            tercero = event['dim_tercero']['name'] 
            if tercero:
                event_dict['tercero'] = tercero
            else:
                event_dict['tercero'] = ""
            user_ip = event['ctrl_user_events']['client_ip']
            if user_ip:
                event_dict['ip'] = user_ip
            else:
                event_dict['ip'] = ""
            event_dict['navegador'] = event['ctrl_user_events']['client_agent']
            event_dict['fecha'] = event['ctrl_user_events']['f_event']
            event_dict['evento'] = event['ctrl_user_events']['event_user']
            all_events.append(event_dict)

        users = db(db.auth_user).select()
        user_list_devices = []
        for user in users:
            user_count = {}
            user_count['usuario'] = user['email']
            user_devices = db(db.auth_user.id == user['id'])(db.auth_user.id == db.ctrl_user_access.user_id).select(groupby=db.ctrl_user_access.device_hash)
            cont = 0
            for device in user_devices:
                if(user['email'] == device.auth_user['email']):
                    cont+=1
            user_count['devices'] = cont
            user_list_devices.append(user_count)
        users_json = json.dumps(user_list_devices, default=str)
        events_json = json.dumps(all_events, default=str)
        tickets_json = json.dumps(all_tickets, default=str)
        control_user_events(request,"Entrando a Vista Dashboard",auth.user.id)
        return dict(results=XML(tickets_json),events=XML(events_json),users=XML(users_json))
    except Exception as e:
        logging.error(f'Error: {e}')

def control_user_events(client_request,user_event,user_act):
    user_ip = client_request.wsgi.environ['REMOTE_ADDR']
    user_agent = client_request.wsgi.environ['HTTP_USER_AGENT']
    
    db.ctrl_user_events.insert(user_id=user_act,client_ip=user_ip,client_agent=user_agent,f_event=datetime.now(),event_user=user_event)
    
def control_user_access():
    user_act = request.vars.user_act 
    device_hash = request.vars.device_hash
    db.ctrl_user_access.insert(user_id=user_act,f_access=datetime.now(),device_hash=device_hash)
    return True