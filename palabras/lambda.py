import sys
from io import StringIO

from contextlib import redirect_stdout

from palabras import cli 


def lambda_handler(event, context):

    with StringIO() as buf, redirect_stdout(buf):
        cli.main(["ser"])
        output = buf.getvalue()
    return {
        'statusCode' : 200,
        'body': output
    }