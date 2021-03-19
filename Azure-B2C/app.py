import logging
from flask import Flask, current_app, render_template, redirect, url_for, request, g, Response
from flask_session import Session
from pathlib import Path
import app_config
from __init__ import IdentityWebPython
from adapters import FlaskContextAdapter
from errors import NotAuthenticatedError
from configuration import AADConfig
from flask_blueprint import FlaskAADEndpoints
import requests
import json
"""
Instructions for running the sample app. These are dev environment instructions ONLY.
Do not run using this configuration in production.

LINUX/OSX - in a terminal window, type the following:
=======================================================
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export FLASK_RUN_CERT=adhoc
    flask run

WINDOWS - in a powershell window, type the following:
====================================================
    $env:FLASK_APP="app.py"
    $env:FLASK_ENV="development"
    $env:FLASK_DEBUG="1"
    $env:FLASK_RUN_CERT="adhoc"
    flask run

You can also use "python -m flask run" instead of "flask run"
"""

def create_app(secure_client_credential=None):
    app = Flask(__name__, root_path=Path(__file__).parent) #initialize Flask app
    app.config.from_object(app_config) # load Flask configuration file (e.g., session configs)
    Session(app) # init the serverside session for the app: this is requireddue to large cookie size
    # tell flask to render the 401 template on not-authenticated error. it is not strictly required:
    app.register_error_handler(NotAuthenticatedError, lambda err: (render_template('auth/401.html'), err.code))
    # comment out the previous line and uncomment the following line in order to use (experimental) <redirect to page after login>
    # app.register_error_handler(NotAuthenticatedError, lambda err: (redirect(url_for('auth.sign_in', post_sign_in_url=request.url_rule))))
    # other exceptions - uncomment to get details printed to screen:
    # app.register_error_handler(Exception, lambda err: (f"Error {err.code}: {err.description}"))
    aad_configuration = AADConfig.parse_json(r'./aad.b2c.config.json') # parse the aad configs
    app.logger.level=logging.INFO # can set to DEBUG for verbose logs
    if app.config.get('ENV') == 'production':
        # The following is required to run on Azure App Service or any other host with reverse proxy:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        # Use client credential from outside the config file, if available.
        if secure_client_credential: aad_configuration.client.client_credential = secure_client_credential

    AADConfig.sanity_check_configs(aad_configuration)
    adapter = FlaskContextAdapter(app) # ms identity web for python: instantiate the flask adapter
    ms_identity_web = IdentityWebPython(aad_configuration, adapter) # then instantiate ms identity web for python

    @app.route('/')
    @app.route('/sign_in_status')
    def index():
        #return redirect(f'/auth/{aad_configuration.flask.auth_endpoints.sign_in}')
        return render_template('auth/status.html')


    @app.route('/token_details')
    @ms_identity_web.login_required # <-- developer only needs to hook up login-required endpoint like this
    def token_details():
        current_app.logger.info("token_details: user is authenticated, will display token details")
        return render_template('auth/token.html')

    @ms_identity_web.login_required
    @app.route('/<path:path>',methods=['GET','POST','DELETE'])
    def proxy(path):
        print(g.identity_context_data._id_token_claims)
        if g.identity_context_data.authenticated:
            SITE_NAME = "https://live.transpara.com/"
            try:
                if request.method=='GET': 
                    print(f'{SITE_NAME}{path}{request.query_string.decode()}')
                    resp = requests.get(f'{SITE_NAME}{path}?{request.query_string.decode()}')#, headers = get_headers(request.headers))
                    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
                    headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]
                    response = Response(resp.content, resp.status_code, headers)
                    #print(f'Request{request.method} to {SITE_NAME}{path} is {resp.status_code}')    
                    return response
                elif request.method=='POST':
                    if("raw" in path):
                        print(path)
                        print(request.form)
                        print(get_headers(request.headers))
                    resp = requests.post(f'{SITE_NAME}{path}?{request.query_string.decode()}',data=request.form)#, headers = get_headers(request.headers))
                    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
                    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
                    response = Response(resp.content, resp.status_code, headers)
                    #print(f'Request{request.method} to {SITE_NAME}{path} is {resp.status_code}')    
                    return response
                elif request.method=='DELETE':
                    resp = requests.delete(f'{SITE_NAME}{path}')
                    response = Response(resp.content, resp.status_code, headers)
                    #print(f'Request{request.method} to {SITE_NAME}{path} is {resp.status_code}')    
                    return response
                elif request.method=='PUT':
                    print("Put not yet supported/required")
            except Exception as ex:
                print(str(ex))
        else:
            return "unauthorized", 401#redirect here to login page instead.

    return app

def get_headers(headers):
    clean_headers = {}
    for header in headers:
        if header[0] != 'Host' and header[0] != 'Content-Length':
            clean_headers[header[0]] = header[1]
    return clean_headers
        

if __name__ == '__main__':
    app=create_app() # this is for running flask's dev server for local testing purposes ONLY
    app.run(ssl_context='adhoc') # create an adhoc ssl cert for HTTPS on 127.0.0.1
    #app.debug = True
    app.run()

app.debug = True    
app=create_app()
app.run()