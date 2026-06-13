from flask import Flask
from app.routes import bp


def create_app():
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB
    app.register_blueprint(bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8080)
