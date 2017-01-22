#!/usr/bin/env python
# encoding: utf-8

__author__='saka'

'url handlers'

import re,time,json,logging,hashlib,base64,asyncio

from coroweb import get,post

from models import User,Comment,Blog,next_id

from apis import APIValueError,APIResourceNotFoundError,APIError,APIPermissionError,Page

from config import configs

from aiohttp import web

import markdown2

COOKIE_NAME = 'awesession'
_COOKIE_KEY=configs.session.secret
@get('/')
async def index(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num,page_index)
    if num==0:
        blogs= []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc',limit=(page.offset,page.limit))

    return {
        '__template__':'blogs.html',
        'page':page,
        'blogs':blogs
    }

#---------------day 10------------

@get('/signin')
def signin():
    return {
        '__template__':'signin.html'
    }
@get('/signout')
def signout(request):
    #referer, the last page
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
    logging.info('user signed out.')
    return r

@get('/register')
def register():
    return {
        '__template__':'register.html'
    }

@post('/api/authenticate')
async def authenticate(*,email,passwd):
    #check whether email and passwd is entered:
    if not email:
        raise APIValueError('email','Invalid email.')
    if not passwd:
        raise APIValueError('passwd','Invalid password.')
    users = await User.findAll('email=?',[email])
    if len(users) ==0:
        #user doesn't exist
        raise APIValueError('email','Email not exist.')
    user = users[0]
    #check the passwd db doesn't have the raw passwd of user, but encrypted string
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd','Invalid password')
    #user.passwd is the value saved in db, sha1 is the calculated value
    #if the passwd is right
    r = web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

def user2cookie(user,max_age):
    #the parameter user is of type model
    '''
    generate cookie str by user.
    '''
    expires = str(int(time.time()+max_age))#expire time, denote when will cookie expires
    s='%s-%s-%s-%s' % (user.id,user.passwd,expires,_COOKIE_KEY)#_COOKIE_KEY,see import, in config.py
    L = [user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

#decrypte cookie
async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid,expires,sha1 = L
        if int(expires) < time.time():
            return None #expire
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid,user.passwd,expires,_COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd='******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

#--------------day 11----------------
#check if user has the admin permission
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def text2html(text):
    lines = map(lambda s:'<p>%s</p>' % s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),filter(lambda s:s.strip()!='',text.split('\n')))
    return ''.join(lines)

@get('/blog/{id}')
async def get_blog(id,request):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?',[id],orderBy='Created_at desc')
    for c in comments:
        c.html_content=text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__':'blog.html',
        'blog':blog,
        '__user__':request.__user__,
        'comments':comments
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__':'manage_blog_edit.html',
        'id':'',
        'action':'/api/blogs'
    }


@get('/api/blogs/{id}')
async def api_get_blog(*,id):
    blog = await Blog.find(id)
    return blog

@post('/api/blogs')
async def api_create_blog(request,*,name,summary,content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name','name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content','content cannot be empty.')

    blog = Blog(user_id=request.__user__.id,user_name=request.__user__.name,user_image=request.__user__.image,name = name.strip(),summary=summary.strip(),content=content.strip())
    await blog.save()
    return blog

#--------------day 12----------------
@get('/api/blogs')
async def api_blogs(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num,page_index)
    if num == 0:
        return dict(page=p,blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,blogs=blogs)

@get('/manage/blogs')
def manage_blogs(*,page='1'):
    return {
        '__template__':'manage_blogs.html',
        'page_index':get_page_index(page)
    }


#--------------day 14----------------
@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*,page='1'):
    return {
        '__template__':'manage_comments.html',
        'page_index':get_page_index(page)
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
    return {
        '__template__':'manage_blog_edit.html',
        'id':id,
        'action':'api/blogs/%s'%id
    }

@get('/manage/users')
def manage_users(*,page='1'):
    return {
        '__template__':'manage_users.html',
        'page_index':get_page_index(page)

    }


#---------------api---------------
#API:get information about user
@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy="created_at desc")
    for u in users:
        u.passwd = "******"
    #overwrite passwd,return as dict
    return dict(users=users)

#API: user register
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*,email,name,passwd):
    #make sure that the input is right
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueERROR('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?',[email])
    if len(users)>0:
        raise APIError('register:failed','Email is lready in use.')

    uid = next_id() #generate a new id for this new user
    sha1_passwd='%s:%s'%(uid,passwd) #combine user name and passwd, and use to generate encrypted passwd
    #create new user, and save it into database
    #passwd is saved after being encrypted by sha1 algorithom while email by md5
    user = User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?d=mm&s=120'%hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()

    #make session cookie:
    r = web.Response()
    #get a response object and manipulation
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

@post('/api/authenticate')
async def authenticate(*,email,passwd):
    if not email:
        raise APIValueError('email','Invalid email.')
    if not passwd:
        raise APIValueError('passwd','Invalid password.')
    users = await User.findAll('email=?',[email])
    if len(users) == 0:
        raise APIValueError('email','Email not exist.')
    user = users[0]

    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd !=sha1.hexdigest():
        raise APIValueError('passwd','Invalid password.')
    r = web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

@get('/api/comments')
async def api_comments(*,page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num,page_index)
    if num == 0:
        return dict(page=p,comments=())
    comments = await Comment.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,comments=comments)

@post('/api/blogs/{id}/comments')
async def api_created_comment(id,request,*,content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id,user_id=user.id,user_name=user.name,user_image=user.image,content=content.strip())
    await comment.save()
    return comment

@post('/api/comments/{id}/delete')
async def api_delete_comments(id,request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.remove()
    return dict(id=id)

@post('/api/blogs/{id}')
async def api_update_blog(id,request,*,name,summary,content):
    check_admin(request)
    blog = await Blog.strip()
    if not name or not name.strip():
        raise APIValueError('name','name connot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content','content cannot be empty.')
    blog.name=name.strip()
    blog.summary=summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

@post('/api/delete/{id}/delete')
async def api_delete_blog(request,*,id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)
