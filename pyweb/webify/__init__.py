from flask import Flask, request, escape, abort, render_template
import os
import re
from .webify import *

app = Flask(__name__)


@app.errorhandler(500)
def page_not_found(error):
   return render_template('error.html', status = '500', status_text = 'Internal Server Error'), 500


@app.errorhandler(404)
def page_not_found(error):
   return render_template('error.html', status = '404', status_text = 'Not Found'), 404


@app.route("/webify/", defaults={"path": ""})
@app.route("/webify/<path:path>")
def webify_app(path):
    # Remove illegal characters (Don't allow some legals either)
    path = re.sub(r'[^\w\-_\./]', '', path)
    # Normalize path under /files (Remove . and .. references)
    path = os.path.normpath(f"/files/{path}")
    # Check that path still is under /files and extension is .html
    if path.startswith("/files/") and path.endswith(".html"):
        # Replace .html extension with .txt
        path = re.sub(r'\.html$', '.txt', path)
        try:
            file = open(path, "r")
            text = file.read()
            file.close()
        except FileNotFoundError:
            abort(404)

        filename = os.path.basename(path)

        html = render_template('webify_header.html', title=filename, plain=path)
        html += webify(escape(text))
        html += render_template('webify_footer.html', plain=path)
    else:
        abort(404)

    return html
