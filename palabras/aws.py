
from contextlib import redirect_stdout
from io import StringIO

from palabras import cli


def lambda_handler(event, context):

    print(event)

    word = event['pathParameters']['word']

    with StringIO() as buf, redirect_stdout(buf):
        cli.main([word], console_color_system='truecolor')
        output = buf.getvalue()

    return {
        'statusCode' : 200,
        'body': output
    }