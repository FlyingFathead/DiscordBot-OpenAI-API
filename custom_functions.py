# custom_functions.py

custom_functions = [
    {
        'name': 'extract_info',
        'description': 'Extract specific information from text',
        'parameters': {
            'type': 'object',
            'properties': {
                'info': {'type': 'string', 'description': 'Type of information to extract'}
            }
        }
    }
    # Add more functions as needed
]