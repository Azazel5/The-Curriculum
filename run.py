from app import create_app

app = create_app()

if __name__ == '__main__':
    # use_reloader=False prevents APScheduler from starting twice
    app.run(debug=True, use_reloader=False, port=5001)
