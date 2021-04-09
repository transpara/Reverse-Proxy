# Reverse-Proxy
This project uses Microsoft examples to authenticate with Azure B2C Flows.

Important files:

app.py
aad.b2c.config.json

Base Project:
https://github.com/Azure-Samples/ms-identity-b2c-python-flask-webapp-authentication


Important note:

If the underlying site to be proxied has authentication enabled for example NTLM, just download the following library
and in the requests add the auth: auth=HttpNtlmAuth(user,pw)
it would look like:
requests.get(url, auth=HttpNtlmAuth(user,pw))
https://pypi.org/project/requests-ntlm2/
