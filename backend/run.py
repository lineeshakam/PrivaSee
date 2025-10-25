from .app import create_app, config

app = create_app()

if __name__ == "__main__":
    app.run(
        host=getattr(config, "HOST", "0.0.0.0"),
        port=getattr(config, "PORT", 5000),
        debug=getattr(config, "DEBUG", True),
    )