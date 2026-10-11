"""Probe de roteamento da Vercel (temporario, sera removido)."""

from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/', defaults={'p': ''})
@app.route('/<path:p>')
def ping(p):
    return jsonify(msg='PING', path=p)
