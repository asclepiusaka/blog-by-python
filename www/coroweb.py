#!/usr/bin/env python
# encoding: utf-8

import asyncio,os,inspect,logging

import functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):#path here should be a string
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'GET'   #add attribute 'method' to original function, and set it to 'GET'
        wrapper.__route__ = path   #add attribute 'route' to original function
        return wrapper
    return decorator

def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

#here are function that used to analysize function
#can help to get the parameter and or type of function
#use inspect module
#mainly deal with url handling function (?) which helps deal with url request

#return the keyword parameter without default value as a tuple
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

#return key world parameter of function, and return key words as a tuple.
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

#judge if fn has key word parameter, if so, return boolean value True
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True#what will be returned if not?

#judge if function has variable key world parameter(**kw), if it does, return True
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

#judge if function has 'request' as an paramter
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name,param in params.items():
        if name == 'request':
            found = True
            continue
        #continue end this loop, if there is any other parameter after 'request'
        #it cannot be an named parameter
        if found and (param.kind !=inspect.Parameter.VAR_POSITIONAL and param.kind !=inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function:%s%s'%(fn.__name__,str(sig)))
    return found


#define Requesthandler class, encapsulazation url function
#REQUEST handler get parameter from url function and get information from request
class RequestHandler(object):
    def __init__(self,app,fn):
        self._app=app
        self._func=fn
        self._has_request_arg=has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

#after __call__ is defined, instance of Handler can act as function
#parameter here is request

    async def __call__(self,request):
        kw = None #assume no keyword
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest('Json body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlecoded') or ct.startswith('multipart/form-data'):
                    #request is a post, read post parameters from request body
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type:%s'%request.content-type )


            if request.method =='GET':
                qs = request.query_string
                #the query string from url, example, the url of search page of google
                if qs:
                    kw=dict()
                    #parse is from lib urllib
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k]=v[0]

#if the kw is none, so the request is of type abstract match info

        if kw is None:
            kw=dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args:%s'%k)
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s'% name)

        logging.info('call with args:%s'%str(kw))
        try:
            print("Aaaaaaaaaaaaaa")
            print(self._func)
            print(self._func.__name__)
            r = await self._func(**kw)
            print(r)
            return r
        except APIError as e:
            return dict(error=e.error,data=e.data,message=e.message)


#add static file to app(?)
def add_static(app):
    #os.path.abspath(__file__) return the absolute directory of current file
    #os.path.dirname() remove the file name, at the end
    #join with directory static
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/',path)
    logging.info('add static %s =>%s'%('/static/',path))

def add_route(app,fn):
    method = getattr(fn,'__method__',None) #get the __method__ attr of fn, if not exist, return None
    path = getattr(fn,'__route__,None') #same as the last line
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.'str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s=>%s(%s)'%(method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method,path,RequestHandler(app,fn))


#module_name is the name of another .py file, in our project, it's handlers.py
def add_routes(app,module_name):
    n=module_name.rfind('.')
    if n ==(-1):
        mod = __import__(module_name,globals(),locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n],globals(),locals(),[name]),name)

    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod,attr)
        if callable(fn):
            method = getattr(fn,'__method__',None)
            path = getattr(fn,'__route__',None)
            if method and path:
                add_route(app,fn)
