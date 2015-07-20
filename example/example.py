"""

Example single-page Flask application demonstrating how to use the flask-ptrans extension

"""

from __future__ import print_function, absolute_import, unicode_literals

import os
from flask import Flask, render_template, request
from flask_ptrans import ptrans


def local_path(*path_elements):
    return os.path.abspath(os.path.join(__file__, "..", *path_elements))

# create the Flask application
app = Flask(__name__)
ptrans.init_localisation(local_path("localisation"))    # say where the localisation files are
app.jinja_env.add_extension('flask_ptrans.ptrans.ptrans')   # add ptrans extension

RENDER_COUNTER = 0

@app.route("/")
def index_page():
    locale = request.args.get('locale')
    if not locale:
        locale = ptrans.best_locale()
    global RENDER_COUNTER
    RENDER_COUNTER += 1
    return render_template('index.html', locale=locale, render_count=RENDER_COUNTER)


if __name__ == '__main__':
    app.run()


