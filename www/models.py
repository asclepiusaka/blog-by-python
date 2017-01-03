#!/usr/bin/env python
# encoding: utf-8

'''
Models for user, blog, comment.
'''

__author__ ='saka'

import time,uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time()*1000),uuid.uuid4().hex)

class User(Model):
    __table__='users'
    #this class is connected to table users

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    #checked, the length is 50
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    #save image with varchar?
    created_at = FloatField(default=time.time)#time.time.is a function, so can be used as callable
    #check function in class Model, getValueOrDefault

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl = 'varchar(50)')
    user_image = StringField(ddl = 'varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    blog_id=StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)
