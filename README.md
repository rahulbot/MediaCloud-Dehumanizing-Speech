Dehumanizing Speech Explorer
============================

A quick web tool for looking at how much a newspaper is using dehumaninizing speech in their content.
This is based on a Media Cloud / Define American report that assessed this.

Dependencies
------------

This is built for Python 3.

```
pip install -r requirements.txt
```

Running Locally
---------------

* Run locally with Flask server: `python run.py`
* Run locally with Gunicorn: `./run.sh`

Deploying
---------

This is built to deploy to a containerized hosting service like Heroku. T

Also make sure to set the following env variables, as needed:
* MC_API_KEY
* MATOMO_HOST
* MATOMO_SITE_ID
