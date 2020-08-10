def load_config(config_file: str):
    print(f'Reading config from {config_file}')
    return {
        'logging': {
            'log_path': 'c:/logs'
        },
        'network': {
            'http_port': 12345
        },
        'database': {
            'database_url': 'http://localhost:9999'
        }
    }
