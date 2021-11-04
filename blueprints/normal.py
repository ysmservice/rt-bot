# RT.Blueprints - Normal

from sanic import Blueprint, response


bp = Blueprint("Normal")


@bp.route("/ping")
async def ping(self, request):
    return response.text("pong")