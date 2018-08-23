from apistar import App
from bella.restful.routes import routes
from bella.restful.components import components


app = App(routes=routes, components=components)

if __name__ == '__main__':
    app.serve('0.0.0.0', 5000, use_debugger=True, use_reloader=True, debug=True)
