from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.utils import dates
from app.utils.log import logger

templates = Jinja2Templates(directory="app/templates")


def render_template(
    request: Request,
    template_name: str,
    *,
    context: dict | None = None,
    status_code: int = 200,
    headers: dict | None = None,
):
    is_demo_user = getattr(request.state, "is_demo_user", False)
    base_context = {"current_year": dates.now().year, "is_demo_user": is_demo_user}

    logger.debug(f"Base context: {base_context}")

    return templates.TemplateResponse(
        request,
        template_name,
        {**base_context, **(context or {})},
        status_code=status_code,
        headers=headers,
    )
